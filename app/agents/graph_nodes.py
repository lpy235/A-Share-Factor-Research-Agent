import math
from typing import Any

import pandas as pd

from app.agents.graph_events import GraphEventTracer, run_traced_node
from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.agents.schemas import FactorHypothesis
from app.agents.state import ResearchState
from app.backtest.metrics import max_drawdown, sharpe_ratio
from app.backtest.selector import FactorScore, FactorSelector
from app.backtest.single_factor import (
    compute_forward_returns,
    compute_rank_ic,
    grouped_forward_returns,
)
from app.data.fixture_provider import FixtureAshareDataProvider
from app.factor.dsl import FactorSpec
from app.factor.executor import FactorExecutor
from app.factor.validator import FactorDslValidator
from app.rag.chunker import DocumentChunk, SimpleChunker
from app.rag.retriever import KeywordRetriever
from app.reports.markdown_report import render_report
from app.sources.discovery import PublicSourceDiscovery
from app.sources.parser import DocumentParser, ParsedDocument


def load_documents_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "LoadDocumentsNode",
        _load_documents,
        lambda item: {
            "source_mode": item.get("source_mode", "upload"),
            "document_path_count": len(item.get("document_paths", [])),
            "max_sources": item.get("max_sources", 3),
        },
        lambda item: {
            "source_count": len(item.get("sources", [])),
            "discovered_source_count": len(item.get("discovered_sources", [])),
        },
    )


def retrieve_chunks_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "RetrieveChunksNode",
        _retrieve_chunks,
        lambda item: {
            "source_count": len(item.get("sources", [])),
            "max_chunks": item.get("max_chunks", 5),
        },
        lambda item: {
            "chunk_count": len(item.get("chunks", [])),
            "source_titles": sorted({chunk.get("source_title", "") for chunk in item.get("chunks", [])}),
        },
    )


def extract_hypotheses_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "ExtractHypothesesNode",
        _extract_hypotheses,
        lambda item: {"chunk_count": len(item.get("chunks", []))},
        lambda item: {
            "hypothesis_count": len(item.get("hypotheses", [])),
            "factor_names": [hypothesis.get("factor_name") for hypothesis in item.get("hypotheses", [])],
        },
    )


def generate_factor_dsl_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "GenerateFactorDSLNode",
        _generate_factor_dsl,
        lambda item: {"hypothesis_count": len(item.get("hypotheses", []))},
        lambda item: {
            "factor_count": len(item.get("factor_specs", [])),
            "factor_names": [spec.get("factor_name") for spec in item.get("factor_specs", [])],
        },
    )


def validate_dsl_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "ValidateDSLNode",
        _validate_dsl,
        lambda item: {"factor_count": len(item.get("factor_specs", []))},
        lambda item: {
            "valid_factor_count": len(item.get("factor_specs", [])),
            "validation_results": item.get("validation_results", []),
        },
    )


def load_market_data_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "LoadMarketDataNode",
        _load_market_data,
        lambda item: {
            "universe": item.get("universe", "CSI300"),
            "start_date": item.get("start_date", "2020-01-01"),
            "end_date": item.get("end_date", "2020-12-31"),
        },
        lambda item: item.get("market_data_summary", {}),
    )


def execute_factors_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "ExecuteFactorsNode",
        _execute_factors,
        lambda item: {"factor_count": len(item.get("factor_specs", []))},
        lambda item: {"executed_factor_count": len(item.get("_factor_values", {}))},
    )


def run_backtest_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "RunBacktestNode",
        _run_backtest,
        lambda item: {"executed_factor_count": len(item.get("_factor_values", {}))},
        lambda item: {"metric_count": len(item.get("metrics", []))},
    )


def select_factors_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "SelectFactorsNode",
        _select_factors,
        lambda item: {"metric_count": len(item.get("metrics", []))},
        lambda item: {"selected_factors": item.get("selected_factors", [])},
    )


def generate_report_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "GenerateReportNode",
        _generate_report,
        lambda item: {
            "factor_count": len(item.get("factor_specs", [])),
            "metric_count": len(item.get("metrics", [])),
        },
        lambda item: {"report_length": len(item.get("report_markdown", ""))},
    )


def _load_documents(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    parser = DocumentParser()
    documents: list[ParsedDocument] = []
    warnings = list(state.get("warnings", []))
    source_mode = state.get("source_mode", "upload")

    if source_mode in {"upload", "hybrid"}:
        for path in state.get("document_paths", []):
            try:
                documents.append(parser.parse_file(path))
            except Exception as exc:
                warning = f"Failed to parse document {path}: {exc}"
                warnings.append(warning)
                tracer.node_fallback("LoadDocumentsNode", {"reason": "document_parse_failed", "path": path})

    discovered_sources = []
    if source_mode in {"auto", "hybrid"}:
        discovered = PublicSourceDiscovery().discover(
            query=state["research_topic"],
            max_sources=state.get("max_sources", 3),
            allow_live_fetch=state.get("allow_live_fetch", False),
        )
        discovered_sources = [source.to_source_dict() for source in discovered]
        if not discovered_sources:
            tracer.node_fallback("LoadDocumentsNode", {"reason": "public_source_discovery_empty"})

    sources = [_document_to_dict(document) for document in documents] + discovered_sources
    if source_mode not in {"auto", "upload", "hybrid"}:
        warnings.append(f"Unknown source_mode={source_mode}; using deterministic demo source.")
        tracer.node_fallback("LoadDocumentsNode", {"reason": "unknown_source_mode", "source_mode": source_mode})

    if not sources and source_mode == "hybrid":
        tracer.node_fallback("LoadDocumentsNode", {"reason": "hybrid_sources_empty"})
    if not documents:
        if source_mode == "upload":
            tracer.node_fallback("LoadDocumentsNode", {"reason": "no_parseable_documents"})

    if not sources:
        sources = [_document_to_dict(_demo_document())]
        tracer.node_fallback("LoadDocumentsNode", {"reason": "using_demo_source"})

    state["sources"] = sources
    state["discovered_sources"] = discovered_sources
    state["warnings"] = warnings
    return state


def _retrieve_chunks(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    chunker = SimpleChunker()
    chunks: list[DocumentChunk] = []
    for source in state.get("sources", []):
        chunks.extend(
            chunker.chunk(
                source.get("source_title", "source"),
                source.get("source_type", "user_upload"),
                source.get("text", ""),
                source.get("source_url"),
            )
        )

    max_chunks = state.get("max_chunks", 5)
    if chunks:
        retrieved = KeywordRetriever(chunks).search(state["research_topic"], top_k=max_chunks)
        if retrieved:
            chunks = retrieved
        else:
            tracer.node_fallback("RetrieveChunksNode", {"reason": "keyword_retrieval_empty"})
            chunks = chunks[:max_chunks]

    if not chunks:
        tracer.node_fallback("RetrieveChunksNode", {"reason": "no_chunks_available"})
        chunks = [_demo_chunk()]

    state["chunks"] = [_chunk_to_dict(chunk) for chunk in chunks]
    return state


def _extract_hypotheses(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    chunks = [_chunk_from_dict(chunk) for chunk in state.get("chunks", [])]
    hypotheses = extract_hypotheses_from_chunks(state["research_topic"], chunks)
    if not hypotheses:
        tracer.node_fallback("ExtractHypothesesNode", {"reason": "no_rule_based_hypothesis"})
        hypotheses = extract_hypotheses_from_chunks(state["research_topic"], [_demo_chunk()])
    state["hypotheses"] = [hypothesis.model_dump() for hypothesis in hypotheses]
    return state


def _generate_factor_dsl(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    hypotheses = [FactorHypothesis(**item) for item in state.get("hypotheses", [])]
    specs = generate_factor_specs(hypotheses)
    if not specs:
        tracer.node_fallback("GenerateFactorDSLNode", {"reason": "no_generated_specs"})
        specs = generate_factor_specs([_demo_hypothesis()])
    state["factor_specs"] = [spec.model_dump() for spec in specs]
    return state


def _validate_dsl(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    validator = FactorDslValidator()
    valid_specs: list[FactorSpec] = []
    validation_results: list[dict[str, Any]] = []
    warnings = list(state.get("warnings", []))
    for item in state.get("factor_specs", []):
        spec = FactorSpec(**item)
        result = validator.validate(spec)
        validation_results.append(
            {"factor_name": spec.factor_name, "valid": result.valid, "errors": result.errors}
        )
        if result.valid:
            valid_specs.append(spec)
        else:
            warnings.append(f"Invalid Factor DSL excluded: {spec.factor_name} {result.errors}")

    if not valid_specs:
        tracer.node_fallback("ValidateDSLNode", {"reason": "no_valid_specs"})
        fallback_spec = generate_factor_specs([_demo_hypothesis()])[0]
        fallback_result = validator.validate(fallback_spec)
        validation_results.append(
            {
                "factor_name": fallback_spec.factor_name,
                "valid": fallback_result.valid,
                "errors": fallback_result.errors,
            }
        )
        if not fallback_result.valid:
            raise ValueError(f"No executable factor after fallback validation: {fallback_result.errors}")
        valid_specs = [fallback_spec]

    state["factor_specs"] = [spec.model_dump() for spec in valid_specs]
    state["validation_results"] = validation_results
    state["warnings"] = warnings
    return state


def _load_market_data(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    provider = FixtureAshareDataProvider()
    symbols = provider.get_universe(
        state.get("universe", "CSI300"),
        state.get("start_date", "2020-01-01"),
    )[:20]
    data = provider.get_daily_bars(
        symbols=symbols,
        start_date=state.get("start_date", "2020-01-01"),
        end_date=state.get("end_date", "2020-12-31"),
    )
    if data.empty:
        raise ValueError("No market data returned by fixture provider")

    state["_market_data"] = data
    state["market_data_summary"] = {
        "symbol_count": len(symbols),
        "row_count": int(len(data)),
        "start_date": str(data.index.get_level_values("date").min().date()),
        "end_date": str(data.index.get_level_values("date").max().date()),
    }
    return state


def _execute_factors(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    data = state.get("_market_data")
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Market data is missing before factor execution")

    executor = FactorExecutor()
    factor_values: dict[str, pd.Series] = {}
    warnings = list(state.get("warnings", []))
    for item in state.get("factor_specs", []):
        spec = FactorSpec(**item)
        try:
            factor_values[spec.factor_name] = executor.execute(spec, data).values
        except Exception as exc:
            warnings.append(f"Factor execution failed: {spec.factor_name} {exc}")
            tracer.node_fallback(
                "ExecuteFactorsNode",
                {"reason": "factor_execution_failed", "factor_name": spec.factor_name},
            )

    if not factor_values:
        raise ValueError("No executable factor values")

    state["_factor_values"] = factor_values
    state["warnings"] = warnings
    return state


def _run_backtest(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    data = state.get("_market_data")
    factor_values = state.get("_factor_values", {})
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Market data is missing before backtest")
    if not factor_values:
        raise ValueError("Factor values are missing before backtest")

    metrics = []
    forward_returns = compute_forward_returns(data["close"], periods=1)
    for factor_name, factor in factor_values.items():
        rank_ic = compute_rank_ic(factor, forward_returns)
        grouped = grouped_forward_returns(factor, forward_returns, groups=5)
        if {1, 5}.issubset(grouped.columns):
            long_short = grouped[5] - grouped[1]
        else:
            long_short = grouped.mean(axis=1) * 0
        rank_ic_std = rank_ic.std()
        metrics.append(
            {
                "factor_name": factor_name,
                "mean_rank_ic": round(_safe_float(rank_ic.mean()), 6),
                "icir": round(_safe_float(rank_ic.mean() / rank_ic_std) if rank_ic_std else 0.0, 6),
                "coverage_ratio": round(float(factor.notna().mean()), 6),
                "missing_ratio": round(float(factor.isna().mean()), 6),
                "max_drawdown": round(max_drawdown(long_short), 6),
                "sharpe": round(sharpe_ratio(long_short), 6),
            }
        )
    state["metrics"] = metrics
    return state


def _select_factors(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    selected_input = [
        FactorScore(
            factor_name=score["factor_name"],
            mean_rank_ic=score["mean_rank_ic"],
            icir=score["icir"],
            coverage_ratio=score["coverage_ratio"],
            missing_ratio=score["missing_ratio"],
            max_drawdown=score["max_drawdown"],
        )
        for score in state.get("metrics", [])
    ]
    selected = FactorSelector(
        min_abs_rank_ic=0.0,
        min_abs_icir=0.0,
        min_coverage=0.7,
        max_missing=0.3,
    ).select(selected_input)
    state["selected_factors"] = [item.factor_name for item in selected]
    return state


def _generate_report(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    hypotheses = state.get("hypotheses", [])
    state["report_markdown"] = render_report(
        research_topic=state["research_topic"],
        sources=[
            {"source_title": item.get("source_title"), "source_url": item.get("source_url")}
            for item in hypotheses
        ],
        factors=state.get("factor_specs", []),
        metrics=state.get("metrics", []),
        limitations=[
            "当前版本使用 fixture 数据演示完整流程。",
            "正式研究需要替换为 AKShare/Tushare 等合法 A 股数据源。",
            "历史回测不构成投资建议。",
        ],
    )
    return state


def _safe_float(value: float) -> float:
    if value is None or math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


def _demo_document() -> ParsedDocument:
    return ParsedDocument(
        source_title="demo factor note",
        source_type="user_upload",
        text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。过去收益率较高的股票也可能体现动量效应。",
    )


def _demo_chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="demo:0",
        source_title="demo factor note",
        source_type="user_upload",
        text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。",
    )


def _demo_hypothesis() -> FactorHypothesis:
    return FactorHypothesis(
        factor_name="volume_price_momentum",
        hypothesis="成交量放大且价格上涨可能代表趋势延续。",
        evidence="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。",
        source_title="fallback factor note",
        source_url=None,
        category="volume_price",
        required_fields=["close", "volume"],
        confidence=0.75,
    )


def _document_to_dict(document: ParsedDocument) -> dict[str, Any]:
    return {
        "source_title": document.source_title,
        "source_type": document.source_type,
        "text": document.text,
        "source_url": document.source_url,
    }


def _chunk_to_dict(chunk: DocumentChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "source_title": chunk.source_title,
        "source_type": chunk.source_type,
        "text": chunk.text,
        "source_url": chunk.source_url,
    }


def _chunk_from_dict(chunk: dict[str, Any]) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk.get("chunk_id", ""),
        source_title=chunk.get("source_title", ""),
        source_type=chunk.get("source_type", "user_upload"),
        text=chunk.get("text", ""),
        source_url=chunk.get("source_url"),
    )
