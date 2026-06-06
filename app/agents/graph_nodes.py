import math
from typing import Any

import pandas as pd

from app.agents.audit import build_audit_trail
from app.agents.extraction import StructuredFactorExtractor
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
from app.data.provider_factory import CachedAshareDataProvider, ProviderSelection, select_data_provider
from app.factor.dsl import FactorSpec
from app.factor.executor import FactorExecutor
from app.factor.validator import FactorDslValidator
from app.rag.chunker import DocumentChunk, SimpleChunker
from app.rag.embeddings import HashingTextEmbedder
from app.rag.retriever import KeywordRetriever
from app.rag.vector_retriever import HybridRetriever, RetrievalResult, VectorRetriever
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
            "source_diagnostics": item.get("source_diagnostics", {}),
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
            "retrieval_mode": item.get("retrieval_mode", "hybrid"),
        },
        lambda item: {
            "chunk_count": len(item.get("chunks", [])),
            "source_titles": sorted({chunk.get("source_title", "") for chunk in item.get("chunks", [])}),
            "retrieval_diagnostics": item.get("retrieval_diagnostics", {}),
        },
    )


def extract_hypotheses_node(state: ResearchState) -> ResearchState:
    return run_traced_node(
        state,
        "ExtractHypothesesNode",
        _extract_hypotheses,
        lambda item: {
            "chunk_count": len(item.get("chunks", [])),
            "extraction_mode": item.get("extraction_mode", "hybrid"),
            "enable_llm_extraction": item.get("enable_llm_extraction", False),
        },
        lambda item: {
            "hypothesis_count": len(item.get("hypotheses", [])),
            "factor_names": [hypothesis.get("factor_name") for hypothesis in item.get("hypotheses", [])],
            "extraction_diagnostics": item.get("extraction_diagnostics", {}),
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
            "data_provider": item.get("data_provider", "fixture"),
        },
        lambda item: {
            "market_data_summary": item.get("market_data_summary", {}),
            "market_data_diagnostics": item.get("market_data_diagnostics", {}),
            "backtest_assumptions": item.get("backtest_assumptions", {}),
        },
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
        lambda item: {
            "report_length": len(item.get("report_markdown", "")),
            "audit_count": len(item.get("audit_trail", [])),
        },
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
    source_diagnostics: dict[str, Any] = {
        "mode": source_mode,
        "accepted_count": 0,
        "rejected_count": 0,
        "accepted": [],
        "rejected": [],
    }
    if source_mode in {"auto", "hybrid"}:
        discovered, discovery_diagnostics = PublicSourceDiscovery().discover_with_diagnostics(
            query=state["research_topic"],
            max_sources=state.get("max_sources", 3),
            allow_live_fetch=state.get("allow_live_fetch", False),
        )
        discovered_sources = [source.to_source_dict() for source in discovered]
        source_diagnostics = {**source_diagnostics, **discovery_diagnostics, "mode": source_mode}
        if not discovered_sources:
            tracer.node_fallback("LoadDocumentsNode", {"reason": "public_source_discovery_empty"})

    sources = [_document_to_dict(document) for document in documents] + discovered_sources
    uploaded_diagnostics = [
        {
            "title": document.source_title,
            "url": document.source_url,
            "source_type": document.source_type,
            "policy": "user_upload",
        }
        for document in documents
    ]
    if uploaded_diagnostics:
        source_diagnostics["accepted"] = uploaded_diagnostics + source_diagnostics.get("accepted", [])
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
        source_diagnostics["accepted"] = [
            {
                "title": "demo factor note",
                "url": None,
                "source_type": "user_upload",
                "policy": "deterministic_fallback",
            }
        ]
        tracer.node_fallback("LoadDocumentsNode", {"reason": "using_demo_source"})

    source_diagnostics["accepted_count"] = len(sources)
    source_diagnostics["rejected_count"] = len(source_diagnostics.get("rejected", []))
    state["sources"] = sources
    state["discovered_sources"] = discovered_sources
    state["source_diagnostics"] = source_diagnostics
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
    retrieval_mode = state.get("retrieval_mode", "hybrid")
    if chunks:
        retrieved, diagnostics = _retrieve_by_mode(
            chunks=chunks,
            query=state["research_topic"],
            top_k=max_chunks,
            retrieval_mode=retrieval_mode,
            embedding_dim=state.get("embedding_dim", 256),
        )
        state["retrieval_diagnostics"] = diagnostics
        if retrieved:
            chunks = retrieved
        else:
            tracer.node_fallback(
                "RetrieveChunksNode",
                {"reason": "retrieval_empty", "retrieval_mode": retrieval_mode},
            )
            chunks = chunks[:max_chunks]

    if not chunks:
        tracer.node_fallback("RetrieveChunksNode", {"reason": "no_chunks_available"})
        chunks = [_demo_chunk()]

    state["chunks"] = [_chunk_to_dict(chunk) for chunk in chunks]
    return state


def _retrieve_by_mode(
    chunks: list[DocumentChunk],
    query: str,
    top_k: int,
    retrieval_mode: str,
    embedding_dim: int,
) -> tuple[list[DocumentChunk], dict[str, Any]]:
    embedder = HashingTextEmbedder(dim=embedding_dim)
    if retrieval_mode == "keyword":
        retrieved = KeywordRetriever(chunks).search(query, top_k=top_k)
        return retrieved, {
            "retrieval_mode": "keyword",
            "embedding_dim": None,
            "retrieved_count": len(retrieved),
        }
    if retrieval_mode == "vector":
        results = VectorRetriever(chunks, embedder).search_with_scores(query, top_k=top_k)
        return [item.chunk for item in results], _retrieval_diagnostics("vector", embedding_dim, results)
    if retrieval_mode == "hybrid":
        results = HybridRetriever(chunks, embedder).search_with_scores(query, top_k=top_k)
        return [item.chunk for item in results], _retrieval_diagnostics("hybrid", embedding_dim, results)

    retrieved = KeywordRetriever(chunks).search(query, top_k=top_k)
    return retrieved, {
        "retrieval_mode": "keyword",
        "requested_retrieval_mode": retrieval_mode,
        "embedding_dim": None,
        "retrieved_count": len(retrieved),
        "fallback_reason": "unknown_retrieval_mode",
    }


def _retrieval_diagnostics(
    retrieval_mode: str,
    embedding_dim: int,
    results: list[RetrievalResult],
) -> dict[str, Any]:
    return {
        "retrieval_mode": retrieval_mode,
        "embedding_dim": embedding_dim,
        "retrieved_count": len(results),
        "top_scores": [round(item.score, 6) for item in results[:5]],
        "methods": [item.method for item in results[:5]],
    }


def _extract_hypotheses(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    chunks = [_chunk_from_dict(chunk) for chunk in state.get("chunks", [])]
    extraction = StructuredFactorExtractor().extract(
        research_topic=state["research_topic"],
        chunks=chunks,
        extraction_mode=state.get("extraction_mode", "hybrid"),
        enable_llm_extraction=state.get("enable_llm_extraction", False),
        llm_retry_count=state.get("llm_retry_count", 1),
    )
    hypotheses = extraction.hypotheses
    state["extraction_diagnostics"] = extraction.diagnostics
    if extraction.diagnostics.get("fallback_used"):
        tracer.node_fallback(
            "ExtractHypothesesNode",
            {
                "reason": extraction.diagnostics.get("fallback_reason") or "llm_fallback",
                "extraction_mode": extraction.diagnostics.get("extraction_mode"),
            },
        )
    if not hypotheses:
        tracer.node_fallback("ExtractHypothesesNode", {"reason": "no_rule_based_hypothesis"})
        hypotheses = extract_hypotheses_from_chunks(state["research_topic"], [_demo_chunk()])
        state["extraction_diagnostics"] = {
            **state.get("extraction_diagnostics", {}),
            "fallback_used": True,
            "fallback_reason": "demo_hypothesis",
            "hypothesis_count": len(hypotheses),
        }
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
    selection = select_data_provider(
        provider_name=state.get("data_provider", "fixture"),
        cache_enabled=state.get("cache_enabled", True),
        cache_dir=state.get("market_data_cache_dir", "data_cache"),
    )
    data, symbols, diagnostics = _fetch_market_data_with_fallback(state, selection, tracer)
    if data.empty:
        raise ValueError(f"No market data returned by {diagnostics.get('provider')}")

    state["_market_data"] = data
    state["market_data_diagnostics"] = diagnostics
    state["market_data_summary"] = {
        "provider": diagnostics.get("provider"),
        "symbol_count": len(symbols),
        "row_count": int(len(data)),
        "start_date": str(data.index.get_level_values("date").min().date()),
        "end_date": str(data.index.get_level_values("date").max().date()),
    }
    state["backtest_assumptions"] = _build_backtest_assumptions(state, diagnostics)
    return state


def _fetch_market_data_with_fallback(
    state: ResearchState,
    selection: ProviderSelection,
    tracer: GraphEventTracer,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    diagnostics = dict(selection.diagnostics)
    try:
        symbols = selection.provider.get_universe(
            state.get("universe", "CSI300"),
            state.get("start_date", "2020-01-01"),
        )[:20]
        data = selection.provider.get_daily_bars(
            symbols=symbols,
            start_date=state.get("start_date", "2020-01-01"),
            end_date=state.get("end_date", "2020-12-31"),
        )
        diagnostics.update(_cache_diagnostics(selection.provider))
        if data.empty:
            raise ValueError("provider_returned_empty_data")
        diagnostics["fallback_used"] = False
        return data, symbols, diagnostics
    except Exception as exc:
        diagnostics["provider_error"] = str(exc)
        if selection.provider_name == "fixture" or not state.get("fallback_to_fixture", True):
            raise

        tracer.node_fallback(
            "LoadMarketDataNode",
            {
                "reason": "data_provider_failed",
                "provider": selection.provider_name,
                "fallback_provider": "fixture",
            },
        )
        fixture = FixtureAshareDataProvider()
        symbols = fixture.get_universe(
            state.get("universe", "CSI300"),
            state.get("start_date", "2020-01-01"),
        )[:20]
        data = fixture.get_daily_bars(
            symbols=symbols,
            start_date=state.get("start_date", "2020-01-01"),
            end_date=state.get("end_date", "2020-12-31"),
        )
        diagnostics.update(
            {
                "provider": "fixture",
                "fallback_used": True,
                "fallback_reason": "data_provider_failed",
                "failed_provider": selection.provider_name,
                "cache_hits": 0,
                "cache_misses": 0,
            }
        )
        return data, symbols, diagnostics


def _cache_diagnostics(provider: Any) -> dict[str, int]:
    if isinstance(provider, CachedAshareDataProvider):
        return {"cache_hits": provider.cache_hits, "cache_misses": provider.cache_misses}
    return {"cache_hits": 0, "cache_misses": 0}


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
    market_data_diagnostics = state.get("market_data_diagnostics", {})
    provider = market_data_diagnostics.get("provider", "fixture")
    if market_data_diagnostics.get("fallback_used"):
        data_limitation = (
            f"请求的数据源为 {market_data_diagnostics.get('failed_provider')}，"
            "因外部数据不可用已回退到 fixture 数据演示完整流程。"
        )
    elif provider == "akshare":
        data_limitation = "当前报告使用 AKShare A 股日线数据；数据可用性取决于公开接口状态。"
    else:
        data_limitation = "当前报告使用 fixture 数据演示完整流程。"
    state["audit_trail"] = build_audit_trail(state)
    state["report_markdown"] = render_report(
        research_topic=state["research_topic"],
        sources=[
            {"source_title": item.get("source_title"), "source_url": item.get("source_url")}
            for item in hypotheses
        ],
        factors=state.get("factor_specs", []),
        metrics=state.get("metrics", []),
        source_diagnostics=state.get("source_diagnostics", {}),
        backtest_assumptions=state.get("backtest_assumptions", {}),
        audit_trail=state.get("audit_trail", []),
        limitations=[
            data_limitation,
            "正式研究需要使用合法、稳定、可复现的 A 股数据源。",
            "历史回测不构成投资建议。",
        ],
    )
    return state


def _build_backtest_assumptions(
    state: ResearchState,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    provider = diagnostics.get("provider", state.get("data_provider", "fixture"))
    return {
        "universe": state.get("universe", "CSI300"),
        "start_date": state.get("start_date", "2020-01-01"),
        "end_date": state.get("end_date", "2020-12-31"),
        "data_provider": provider,
        "fallback_used": bool(diagnostics.get("fallback_used", False)),
        "rebalance_frequency": "daily",
        "forward_return_period": "1 trading day",
        "transaction_cost_bps": 0,
        "adjustment": "fixture 模式使用确定性示例日线；AKShare 模式依赖公开接口返回的数据。",
        "universe_note": "当前股票池最多取前 20 个标的用于可复现实验演示。",
        "bias_notes": [
            "fixture 数据不代表真实 A 股全市场表现。",
            "真实研究需要处理停牌、涨跌停、复权、ST、退市和生存者偏差。",
            "当前回测不执行真实交易，也不构成投资建议。",
        ],
    }


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
