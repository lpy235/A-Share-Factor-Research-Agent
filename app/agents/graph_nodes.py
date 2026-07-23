import math
from typing import Any

import pandas as pd

from app.agents.audit import build_audit_trail
from app.agents.extraction import StructuredFactorExtractor
from app.agents.graph_events import GraphEventTracer, run_traced_node
from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.agents.schemas import FactorHypothesis
from app.agents.state import ResearchState
from app.backtest.combination import combine_factor_values
from app.backtest.correlation import compute_factor_correlation_matrix
from app.backtest.config import BacktestConfig
from app.backtest.metrics import (
    annualized_return,
    beta,
    excess_return,
    information_ratio,
    max_drawdown,
    sharpe_ratio,
    tracking_error,
)
from app.backtest.portfolio import PortfolioBacktestResult, run_long_only_backtest
from app.backtest.selector import FactorScore, FactorSelector
from app.backtest.single_factor import (
    compute_forward_returns,
    compute_rank_ic,
    grouped_forward_returns,
)
from app.backtest.walk_forward import walk_forward_ic
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
from app.storage.universes import HistoricalUniverseStore


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
    extraction = StructuredFactorExtractor(_build_llm_client(state)).extract(
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


def _build_llm_client(state: ResearchState):
    if not _should_use_llm(state):
        return None
    llm_config = state.get("llm_config", {}) or {}
    try:
        from app.llm.client import LlmClient

        return LlmClient(
            provider=llm_config.get("provider"),
            api_key=llm_config.get("api_key"),
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model"),
        )
    except Exception:
        return None


def _should_use_llm(state: ResearchState) -> bool:
    extraction_mode = state.get("extraction_mode", "hybrid")
    return extraction_mode == "llm" or (
        extraction_mode == "hybrid" and bool(state.get("enable_llm_extraction", False))
    )


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
    data = _apply_historical_universe(state, data)

    dates = pd.DatetimeIndex(pd.to_datetime(data.index.get_level_values("date"))).unique().sort_values()
    if len(dates) > 1:
        oos_split_index = min(max(int(len(dates) * 0.7), 1), len(dates) - 1)
        oos_split_date = str(pd.Timestamp(dates[oos_split_index]).date())
    else:
        oos_split_date = str(pd.Timestamp(dates[0]).date()) if len(dates) == 1 else ""

    state["_market_data"] = data
    state["_oos_split_date"] = oos_split_date
    state["market_data_diagnostics"] = diagnostics
    state["market_data_summary"] = {
        "provider": diagnostics.get("provider"),
        "symbol_count": len(symbols),
        "row_count": int(len(data)),
        "start_date": str(data.index.get_level_values("date").min().date()),
        "end_date": str(data.index.get_level_values("date").max().date()),
        "oos_split_date": oos_split_date,
    }
    state["backtest_assumptions"] = _build_backtest_assumptions(state, diagnostics)
    return state


def _apply_historical_universe(state: ResearchState, data: pd.DataFrame) -> pd.DataFrame:
    universe_id = state.get("historical_universe_id")
    if not universe_id:
        state["universe_diagnostics"] = {
            "source": "fixed_provider_universe",
            "historical_membership_applied": False,
            "warning": "未提供历史成分股，结果可能存在生存者偏差。",
        }
        return data
    try:
        membership = HistoricalUniverseStore().load(universe_id)
    except KeyError as exc:
        raise ValueError(f"Historical universe not found: {universe_id}") from exc
    membership = membership.reorder_levels(["symbol", "date"]).sort_index()
    result = data.drop(columns=["in_universe"], errors="ignore").join(
        membership.rename("in_universe"), how="left"
    )
    matched_rows = int(result["in_universe"].notna().sum())
    result["in_universe"] = result["in_universe"].fillna(False).astype(bool)
    state["universe_diagnostics"] = {
        "source": "historical_universe_artifact",
        "historical_universe_id": universe_id,
        "historical_membership_applied": True,
        "matched_rows": matched_rows,
        "member_rows": int(result["in_universe"].sum()),
    }
    return result


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
    oos_split_date = state.get("_oos_split_date", "")
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Market data is missing before backtest")
    if not factor_values:
        raise ValueError("Factor values are missing before backtest")

    # Split IS / OOS by date
    data_is, data_oos = _split_is_oos(data, oos_split_date)

    metrics = []
    oos_metrics = []
    backtest_series = {}
    gross_backtest_series = {}
    net_backtest_series = {}
    turnover_series = {}
    cost_series = {}
    long_only_metrics = []
    tradability_diagnostics = {}
    factor_directions = {
        item.get("factor_name"): item.get("direction", "unknown")
        for item in state.get("factor_specs", [])
    }
    portfolio_config = BacktestConfig(
        execution_mode=state.get("execution_mode", "next_open_to_next_open"),
        commission_bps=state.get("commission_bps", 3.0),
        stamp_duty_bps=state.get("stamp_duty_bps", 5.0),
        slippage_bps=state.get("slippage_bps", 5.0),
        exclude_st=state.get("exclude_st", True),
        min_listing_days=state.get("min_listing_days", 60),
    )
    benchmark_returns = _compute_benchmark_returns(data)

    for factor_name, factor in factor_values.items():
        # ------- In-sample -------
        factor_is = _clip_series_to_data(factor, data_is) if data_is is not None else factor
        forward_returns_is = compute_forward_returns(data_is["close"], periods=1) if data_is is not None else None
        is_result = (
            _backtest_single_factor(factor_name, factor_is, forward_returns_is)
            if forward_returns_is is not None
            else {}
        )
        metric = _build_metric_dict(factor_name, is_result, segment="IS")
        metrics.append(metric)

        # ------- Out-of-sample -------
        factor_oos = _clip_series_to_data(factor, data_oos) if data_oos is not None else factor
        forward_returns_oos = compute_forward_returns(data_oos["close"], periods=1) if data_oos is not None else None
        oos_result = (
            _backtest_single_factor(factor_name, factor_oos, forward_returns_oos)
            if forward_returns_oos is not None
            else {}
        )
        oos_metrics.append(_build_metric_dict(factor_name, oos_result, segment="OOS"))

        # IC decay ratio: |mean_IC_IS| / |mean_IC_OOS|，>1 means IS stronger (potential overfitting)
        ic_is = is_result.get("mean_rank_ic", 0.0)
        ic_oos = oos_result.get("mean_rank_ic", 0.0)
        ic_decay = abs(ic_is) / max(abs(ic_oos), 1e-8) if ic_oos else None

        # Merge IS+OOS series for full-period charts
        merged_rank_ic = _merge_series(is_result.get("rank_ic"), oos_result.get("rank_ic"))
        merged_long_short = _merge_series(
            is_result.get("long_short_returns"), oos_result.get("long_short_returns")
        )
        equity_full = (1 + merged_long_short.fillna(0)).cumprod()
        drawdown_full = equity_full / equity_full.cummax() - 1
        walk_forward = walk_forward_ic(merged_rank_ic)

        backtest_series[factor_name] = {
            "rank_ic": _series_to_points(merged_rank_ic),
            "cumulative_rank_ic": _series_to_points(merged_rank_ic.fillna(0).cumsum()),
            "long_short_returns": _series_to_points(merged_long_short),
            "equity_curve": _series_to_points(equity_full),
            "drawdown": _series_to_points(drawdown_full),
            "grouped_returns": _frame_to_records(is_result.get("grouped", pd.DataFrame())),
            "ic_decay_ratio": ic_decay,
            "oos_split_date": oos_split_date,
            "rank_ic_is": _series_to_points(
                is_result.get("rank_ic") if is_result.get("rank_ic") is not None else pd.Series(dtype=float)
            ),
            "rank_ic_oos": _series_to_points(
                oos_result.get("rank_ic") if oos_result.get("rank_ic") is not None else pd.Series(dtype=float)
            ),
            "walk_forward": walk_forward,
        }

        metric["mean_rank_ic_oos"] = round(_safe_float(ic_oos), 6)
        metric["ic_decay_ratio"] = round(ic_decay, 4) if ic_decay is not None else None
        metric["walk_forward_positive_ratio"] = walk_forward["stability"].get("positive_ratio")
        metric["walk_forward_sign_consistent"] = walk_forward["stability"].get("sign_consistent")

        portfolio_is = _run_portfolio_segment(
            factor_is, data_is, factor_directions.get(factor_name, "unknown"), portfolio_config
        )
        portfolio_oos = _run_portfolio_segment(
            factor_oos, data_oos, factor_directions.get(factor_name, "unknown"), portfolio_config
        )
        gross_full = _merge_series(portfolio_is.gross_returns, portfolio_oos.gross_returns)
        net_full = _merge_series(portfolio_is.net_returns, portfolio_oos.net_returns)
        turnover_full = _merge_series(portfolio_is.turnover, portfolio_oos.turnover)
        costs_full = _merge_frames(portfolio_is.costs, portfolio_oos.costs)
        gross_backtest_series[factor_name] = _series_to_points(gross_full)
        net_backtest_series[factor_name] = _series_to_points(net_full)
        turnover_series[factor_name] = _series_to_points(turnover_full)
        cost_series[factor_name] = {
            "is": _frame_to_records(portfolio_is.costs),
            "oos": _frame_to_records(portfolio_oos.costs),
            "full": _frame_to_records(costs_full),
        }
        factor_excess = excess_return(net_full, benchmark_returns)
        long_only_metrics.append(
            {
                "factor_name": factor_name,
                "annualized_return": round(annualized_return(net_full), 6),
                "sharpe": round(sharpe_ratio(net_full), 6),
                "max_drawdown": round(max_drawdown(net_full), 6),
                "cumulative_cost": round(
                    float(costs_full.get("total_cost", pd.Series(dtype=float)).sum()), 8
                ),
                "observation_count": int(len(net_full)),
                "benchmark_beta": round(beta(net_full, benchmark_returns), 6),
                "tracking_error": round(tracking_error(factor_excess), 6),
                "information_ratio": round(information_ratio(factor_excess), 6),
                "excess_annualized_return": round(annualized_return(factor_excess), 6),
                "relative_max_drawdown": round(max_drawdown(factor_excess), 6),
            }
        )
        tradability_diagnostics[factor_name] = _merge_portfolio_diagnostics(
            portfolio_is, portfolio_oos
        )

    state["metrics"] = metrics
    state["oos_metrics"] = oos_metrics
    state["backtest_series"] = backtest_series
    state["gross_backtest_series"] = gross_backtest_series
    state["net_backtest_series"] = net_backtest_series
    state["turnover_series"] = turnover_series
    state["cost_series"] = cost_series
    state["long_only_metrics"] = long_only_metrics
    state["tradability_diagnostics"] = tradability_diagnostics
    state["_benchmark_returns"] = benchmark_returns
    state["_portfolio_config"] = portfolio_config
    state["_data_is"] = data_is
    state["_data_oos"] = data_oos

    # Compute factor correlation matrix
    if len(factor_values) >= 2:
        corr_matrix = compute_factor_correlation_matrix(factor_values)
        state["_factor_correlation"] = {
            "labels": list(corr_matrix.index) if not corr_matrix.empty else [],
            "values": corr_matrix.values.tolist() if not corr_matrix.empty else [],
        }
    else:
        state["_factor_correlation"] = {"labels": [], "values": []}

    return state


def _run_portfolio_segment(
    factor: pd.Series,
    data: pd.DataFrame | None,
    direction: str,
    config: BacktestConfig,
) -> PortfolioBacktestResult:
    if data is None or data.empty:
        empty_data = pd.DataFrame(
            {"open": pd.Series(dtype=float)},
            index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
        )
        empty_factor = pd.Series(dtype=float, index=empty_data.index)
        return run_long_only_backtest(
            empty_factor, empty_data, direction=direction, config=config
        )
    return run_long_only_backtest(factor, data, direction=direction, config=config)


def _compute_benchmark_returns(data: pd.DataFrame) -> pd.Series:
    """Equal-weight open-to-open daily returns of the data universe as benchmark."""
    if "open" not in data.columns:
        return pd.Series(dtype=float)
    opens = data["open"].unstack(level="symbol")
    daily_returns = opens.pct_change()
    benchmark = daily_returns.mean(axis=1)
    return benchmark.dropna()


def _merge_frames(first: pd.DataFrame, second: pd.DataFrame) -> pd.DataFrame:
    parts = [frame for frame in (first, second) if not frame.empty]
    if not parts:
        return pd.DataFrame()
    merged = pd.concat(parts)
    return merged[~merged.index.duplicated(keep="first")].sort_index()


def _merge_portfolio_diagnostics(
    is_result: PortfolioBacktestResult,
    oos_result: PortfolioBacktestResult,
) -> dict[str, Any]:
    is_diagnostics = is_result.diagnostics
    oos_diagnostics = oos_result.diagnostics
    return {
        "executable": bool(
            is_diagnostics.get("executable", False)
            or oos_diagnostics.get("executable", False)
        ),
        "missing_fields": sorted(
            set(is_diagnostics.get("missing_fields", []))
            | set(oos_diagnostics.get("missing_fields", []))
        ),
        "applied_rules": sorted(
            set(is_diagnostics.get("applied_rules", []))
            | set(oos_diagnostics.get("applied_rules", []))
        ),
        "blocked_buys": int(is_diagnostics.get("blocked_buys", 0))
        + int(oos_diagnostics.get("blocked_buys", 0)),
        "blocked_sells": int(is_diagnostics.get("blocked_sells", 0))
        + int(oos_diagnostics.get("blocked_sells", 0)),
        "empty_candidate_dates": int(is_diagnostics.get("empty_candidate_dates", 0))
        + int(oos_diagnostics.get("empty_candidate_dates", 0)),
        "is": is_diagnostics,
        "oos": oos_diagnostics,
    }


def _split_is_oos(
    data: pd.DataFrame, split_date: str
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Split market data into in-sample (before split_date) and out-of-sample (on/after)."""
    if not split_date:
        return data, None
    dates = pd.to_datetime(data.index.get_level_values("date"))
    split_ts = pd.Timestamp(split_date)
    mask_is = dates < split_ts
    mask_oos = dates >= split_ts
    data_is: pd.DataFrame | None = data.loc[mask_is].copy() if mask_is.any() else None
    data_oos: pd.DataFrame | None = data.loc[mask_oos].copy() if mask_oos.any() else None
    return data_is, data_oos


def _clip_series_to_data(series: pd.Series, data: pd.DataFrame) -> pd.Series:
    """Clip a factor value series to only include dates present in the data slice."""
    if data is None or data.empty:
        return series
    data_dates = data.index.get_level_values("date").unique()
    series_dates = series.index.get_level_values("date")
    keep = series_dates.isin(data_dates)
    return series.loc[keep].copy()


def _merge_series(
    s1: pd.Series | None, s2: pd.Series | None
) -> pd.Series:
    """Concatenate two Series, removing duplicates by index."""
    parts = []
    if s1 is not None and not s1.empty:
        parts.append(s1)
    if s2 is not None and not s2.empty:
        parts.append(s2)
    if not parts:
        return pd.Series(dtype=float)
    merged = pd.concat(parts)
    return merged[~merged.index.duplicated(keep="first")].sort_index()


def _backtest_single_factor(
    factor_name: str,
    factor: pd.Series,
    forward_returns: pd.Series,
) -> dict[str, Any]:
    """Compute all backtest metrics for a single factor on a data segment."""
    result: dict[str, Any] = {"factor_name": factor_name}
    if factor.empty:
        return result
    if forward_returns.empty:
        return result
    rank_ic = compute_rank_ic(factor, forward_returns)
    grouped = grouped_forward_returns(factor, forward_returns, groups=5)
    if {1, 5}.issubset(grouped.columns):
        long_short = grouped[5] - grouped[1]
    else:
        long_short = grouped.mean(axis=1) * 0
    rank_ic_std = rank_ic.std()
    result.update({
        "mean_rank_ic": rank_ic.mean(),
        "icir": (rank_ic.mean() / rank_ic_std) if rank_ic_std else 0.0,
        "coverage_ratio": float(factor.notna().mean()),
        "missing_ratio": float(factor.isna().mean()),
        "max_drawdown": max_drawdown(long_short),
        "sharpe": sharpe_ratio(long_short),
        "rank_ic": rank_ic,
        "long_short_returns": long_short,
        "grouped": grouped,
    })
    return result


def _build_metric_dict(
    factor_name: str, result: dict[str, Any], segment: str
) -> dict[str, Any]:
    """Convert a backtest result dict into the frontend metric format."""
    suffix = f"_{segment.lower()}" if segment != "IS" else ""
    metric = {
        "factor_name": factor_name,
        f"mean_rank_ic{suffix}": round(_safe_float(result.get("mean_rank_ic", 0.0)), 6),
        f"icir{suffix}": round(_safe_float(result.get("icir", 0.0)), 6),
        f"coverage_ratio{suffix}": round(_safe_float(result.get("coverage_ratio", 0.0)), 6),
        f"missing_ratio{suffix}": round(_safe_float(result.get("missing_ratio", 0.0)), 6),
        f"max_drawdown{suffix}": round(_safe_float(result.get("max_drawdown", 0.0)), 6),
        f"sharpe{suffix}": round(_safe_float(result.get("sharpe", 0.0)), 6),
    }
    if segment != "IS":
        metric[f"factor_name{suffix}"] = factor_name
    return metric


def _select_factors(state: ResearchState, tracer: GraphEventTracer) -> ResearchState:
    warnings = list(state.get("warnings", []))
    selected_input = [
        FactorScore(
            factor_name=score.get("factor_name", ""),
            mean_rank_ic=score.get("mean_rank_ic", 0.0),
            icir=score.get("icir", 0.0),
            coverage_ratio=score.get("coverage_ratio", 0.0),
            missing_ratio=score.get("missing_ratio", 0.0),
            max_drawdown=score.get("max_drawdown", 0.0),
            mean_rank_ic_oos=score.get("mean_rank_ic_oos"),
            ic_decay_ratio=score.get("ic_decay_ratio"),
        )
        for score in state.get("metrics", [])
    ]
    selector = FactorSelector(
        min_abs_rank_ic=0.02,
        min_abs_icir=0.3,
        min_coverage=0.5,
        max_missing=0.5,
        max_ic_decay_ratio=2.0,
    )
    selected = selector.select(selected_input)
    state["selected_factors"] = [item.factor_name for item in selected]
    state["combination_backtest"] = _build_combination_backtest(state)

    # Log rejection reasons
    rejection_info = selector.rejection_reasons(selected_input)
    for factor_name, reasons in rejection_info.items():
        warnings.append(f"Factor [{factor_name}] rejected: {'; '.join(reasons)}")
    state["warnings"] = warnings
    return state


def _build_combination_backtest(state: ResearchState) -> dict[str, Any]:
    """Build equal-weight / IC-weight / risk-parity combination backtests
    over the selected factors. Runs after SelectFactorsNode."""
    selected = state.get("selected_factors", [])
    factor_values = state.get("_factor_values", {})
    if not selected or not factor_values:
        return {}
    metrics = state.get("metrics", [])
    benchmark_returns = state.get("_benchmark_returns", pd.Series(dtype=float))
    portfolio_config = state.get("_portfolio_config")
    data_is = state.get("_data_is")
    data_oos = state.get("_data_oos")
    if portfolio_config is None:
        return {}
    ic_weights = {m.get("factor_name"): m.get("mean_rank_ic", 0.0) for m in metrics}
    combination_backtest: dict[str, Any] = {}
    for method in ("equal_weight", "ic_weight", "risk_parity"):
        combined = combine_factor_values(
            factor_values, selected, method=method, ic_weights=ic_weights
        )
        if combined.empty:
            continue
        combined_is = (
            _clip_series_to_data(combined, data_is) if data_is is not None else combined
        )
        combined_oos = (
            _clip_series_to_data(combined, data_oos) if data_oos is not None else combined
        )
        port_is = _run_portfolio_segment(combined_is, data_is, "positive", portfolio_config)
        port_oos = _run_portfolio_segment(combined_oos, data_oos, "positive", portfolio_config)
        net_full = _merge_series(port_is.net_returns, port_oos.net_returns)
        excess = excess_return(net_full, benchmark_returns)
        combination_backtest[method] = {
            "method": method,
            "factor_count": len([name for name in selected if name in factor_values]),
            "net_series": _series_to_points(net_full),
            "annualized_return": round(annualized_return(net_full), 6),
            "sharpe": round(sharpe_ratio(net_full), 6),
            "max_drawdown": round(max_drawdown(net_full), 6),
            "benchmark_beta": round(beta(net_full, benchmark_returns), 6),
            "information_ratio": round(information_ratio(excess), 6),
            "tracking_error": round(tracking_error(excess), 6),
            "excess_annualized_return": round(annualized_return(excess), 6),
            "observation_count": int(len(net_full)),
        }
    return combination_backtest


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
        oos_metrics=state.get("oos_metrics", []),
        factor_correlation=state.get("_factor_correlation", {"labels": [], "values": []}),
        source_diagnostics=state.get("source_diagnostics", {}),
        backtest_assumptions=state.get("backtest_assumptions", {}),
        audit_trail=state.get("audit_trail", []),
        warnings=state.get("warnings", []),
        long_only_metrics=state.get("long_only_metrics", []),
        tradability_diagnostics=state.get("tradability_diagnostics", {}),
        universe_diagnostics=state.get("universe_diagnostics", {}),
        combination_backtest=state.get("combination_backtest", {}),
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
    oos_date = state.get("_oos_split_date", "")
    return {
        "universe": state.get("universe", "CSI300"),
        "start_date": state.get("start_date", "2020-01-01"),
        "end_date": state.get("end_date", "2020-12-31"),
        "data_provider": provider,
        "fallback_used": bool(diagnostics.get("fallback_used", False)),
        "rebalance_frequency": "daily",
        "forward_return_period": "1 trading day",
        "transaction_cost_bps": 0,
        "execution_mode": state.get("execution_mode", "next_open_to_next_open"),
        "commission_bps": state.get("commission_bps", 3.0),
        "stamp_duty_bps": state.get("stamp_duty_bps", 5.0),
        "slippage_bps": state.get("slippage_bps", 5.0),
        "exclude_st": state.get("exclude_st", True),
        "min_listing_days": state.get("min_listing_days", 60),
        "adjustment": "fixture 模式使用确定性示例日线；AKShare 模式依赖公开接口返回的数据。",
        "universe_note": "当前股票池最多取前 20 个标的用于可复现实验演示。",
        "oos_split_date": oos_date,
        "oos_split_ratio": "前 70% 样本内 (IS)，后 30% 样本外 (OOS)",
        "benchmark": "universe_equal_weight_open_to_open",
        "benchmark_note": "基准为当前股票池等权 open-to-open 日收益序列，用于计算超额收益、Beta、信息比与跟踪误差；正式研究应替换为沪深300等真实指数。",
        "bias_notes": [
            "fixture 数据不代表真实 A 股全市场表现。",
            "真实研究需要处理停牌、涨跌停、复权、ST、退市和生存者偏差。",
            "当前回测不执行真实交易，也不构成投资建议。",
            f"样本内/外按日期分割：IS 为 {oos_date} 之前，OOS 为 {oos_date} 起（若数据区间足够）",
        ],
    }


def _safe_float(value: float) -> float:
    if value is None or math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


def _series_to_points(series: pd.Series) -> list[dict[str, Any]]:
    clean = series.dropna()
    return [
        {
            "date": str(index.date() if hasattr(index, "date") else index),
            "value": round(_safe_float(value), 8),
        }
        for index, value in clean.items()
    ]


def _frame_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    records = []
    for index, row in frame.dropna(how="all").iterrows():
        item = {"date": str(index.date() if hasattr(index, "date") else index)}
        for column, value in row.items():
            item[str(column)] = round(_safe_float(value), 8)
        records.append(item)
    return records


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
