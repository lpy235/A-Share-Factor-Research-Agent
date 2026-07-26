import threading
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field

from app.agents.graph import run_research_workflow
from app.storage.db import init_db
from app.storage.artifacts import ArtifactStore
from app.storage.events import EventStore
from app.storage.runs import RunStore
from app.storage.universes import HistoricalUniverseStore

router = APIRouter(prefix="/research", tags=["research"])

DB_PATH = "runs.db"
init_db(DB_PATH)
event_store = EventStore(DB_PATH)
artifact_store = ArtifactStore()
run_store = RunStore(DB_PATH)


class ResearchRunRequest(BaseModel):
    research_topic: str | None = None
    source_mode: str = "upload"
    document_ids: list[str] = []
    universe: str = "CSI300"
    start_date: str = "2020-01-01"
    end_date: str = "2020-12-31"
    max_chunks: int = 5
    max_sources: int = 3
    allow_live_fetch: bool = False
    retrieval_mode: str = "hybrid"
    embedding_dim: int = 256
    extraction_mode: str = "hybrid"
    enable_llm_extraction: bool = False
    llm_retry_count: int = 1
    llm_config: dict = Field(default_factory=dict)
    data_provider: str = "fixture"
    cache_enabled: bool = True
    fallback_to_fixture: bool = True
    market_data_cache_dir: str = "data_cache"
    data_version: str | None = None
    market_data_root: str = "market_data"
    max_universe_size: int | None = Field(default=None, ge=1)
    price_adjustment_mode: Literal["raw", "corporate_action_total_return"] = (
        "corporate_action_total_return"
    )
    execution_mode: Literal["next_open_to_next_open"] = "next_open_to_next_open"
    commission_bps: float = Field(default=3.0, ge=0)
    stamp_duty_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    exclude_st: bool = True
    min_listing_days: int = Field(default=60, ge=0)
    holding_period_days: int = Field(default=1, ge=1, le=60)
    historical_universe_id: str | None = Field(
        default=None, pattern=r"^universe_[0-9a-f]{12}$"
    )
    async_run: bool = False


@router.post("/runs")
def create_research_run(request: ResearchRunRequest):
    if request.data_provider == "warehouse":
        if not request.data_version:
            raise HTTPException(status_code=422, detail="warehouse data_provider requires data_version")
        from app.market_data.catalog import DataCatalog

        try:
            version = DataCatalog(request.market_data_root).get_version(request.data_version)
        except KeyError as exc:
            raise HTTPException(status_code=422, detail="market data version not found") from exc
        if version.status != "published":
            raise HTTPException(status_code=422, detail="market data version must be published")
    if request.historical_universe_id:
        try:
            HistoricalUniverseStore().load(request.historical_universe_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Historical universe not found") from exc
    run_id = f"run_{uuid4().hex[:12]}"
    llm_config_summary = _summarize_llm_config(request.llm_config)
    document_paths = []
    if request.document_ids:
        from app.storage.documents import DocumentStore

        document_store = DocumentStore()
        document_paths = [document_store.get(document_id).path for document_id in request.document_ids]

    if not request.research_topic and request.source_mode == "auto" and not document_paths:
        raise HTTPException(
            status_code=422,
            detail="research_topic is required for auto source mode without uploaded documents",
        )

    request_config = request.model_dump()
    request_config["llm_config"] = llm_config_summary

    event_store.append(
        run_id,
        "CreateRun",
        "run_started",
        _build_run_started_payload(request, llm_config_summary),
    )

    if request.async_run:
        run_store.save_run(
            run_id,
            research_topic=request.research_topic or _derive_research_topic(document_paths),
            status="running",
            config=request_config,
            response={"run_id": run_id, "status": "running"},
        )
        thread = threading.Thread(
            target=_execute_run_async,
            args=(run_id, request, document_paths, llm_config_summary, request_config),
            daemon=True,
        )
        thread.start()
        return {"run_id": run_id, "status": "running"}

    return _execute_and_build_response(
        run_id, request, document_paths, llm_config_summary, request_config
    )


def _execute_and_build_response(
    run_id: str,
    request: ResearchRunRequest,
    document_paths: list[str],
    llm_config_summary: dict,
    request_config: dict,
) -> dict:
    state = run_research_workflow(
        _build_workflow_state(run_id, request, document_paths, llm_config_summary)
    )
    event_store.append(
        run_id,
        "GenerateReportNode",
        "run_completed",
        {
            "factor_count": len(state.get("factor_specs", [])),
            "selected_factors": state.get("selected_factors", []),
        },
    )
    artifacts = artifact_store.write_run_artifacts(
        run_id,
        report_markdown=state["report_markdown"],
        metrics=state.get("metrics", []),
        factor_specs=state.get("factor_specs", []),
        selected_factors=state.get("selected_factors", []),
        backtest_series=state.get("backtest_series", {}),
        oos_metrics=state.get("oos_metrics", []),
        factor_correlation=state.get("_factor_correlation"),
        portfolio_results={
            "gross_backtest_series": state.get("gross_backtest_series", {}),
            "net_backtest_series": state.get("net_backtest_series", {}),
            "turnover_series": state.get("turnover_series", {}),
            "cost_series": state.get("cost_series", {}),
            "long_only_metrics": state.get("long_only_metrics", []),
        },
        backtest_diagnostics={
            "tradability": state.get("tradability_diagnostics", {}),
            "universe": state.get("universe_diagnostics", {}),
        },
        market_data_metadata=state.get("market_data_diagnostics", {}),
    )
    response = {
        "run_id": run_id,
        "status": "completed",
        "selected_factors": state.get("selected_factors", []),
        "factor_specs": state.get("factor_specs", []),
        "metrics": state.get("metrics", []),
        "oos_metrics": state.get("oos_metrics", []),
        "factor_correlation": state.get("_factor_correlation", {"labels": [], "values": []}),
        "backtest_series": state.get("backtest_series", {}),
        "gross_backtest_series": state.get("gross_backtest_series", {}),
        "net_backtest_series": state.get("net_backtest_series", {}),
        "turnover_series": state.get("turnover_series", {}),
        "cost_series": state.get("cost_series", {}),
        "long_only_metrics": state.get("long_only_metrics", []),
        "tradability_diagnostics": state.get("tradability_diagnostics", {}),
        "universe_diagnostics": state.get("universe_diagnostics", {}),
        "report_markdown": state["report_markdown"],
        "artifacts": artifacts,
        "source_diagnostics": state.get("source_diagnostics", {}),
        "backtest_assumptions": state.get("backtest_assumptions", {}),
        "audit_trail": state.get("audit_trail", []),
        "combination_backtest": state.get("combination_backtest", {}),
        "market_data_metadata": state.get("market_data_diagnostics", {}),
    }
    run_store.save_run(
        run_id,
        research_topic=request.research_topic or _derive_research_topic(document_paths),
        status="completed",
        config=request_config,
        response=response,
    )
    return response


def _execute_run_async(
    run_id: str,
    request: ResearchRunRequest,
    document_paths: list[str],
    llm_config_summary: dict,
    request_config: dict,
) -> None:
    try:
        _execute_and_build_response(
            run_id, request, document_paths, llm_config_summary, request_config
        )
    except Exception as exc:
        error_message = str(exc)
        event_store.append(
            run_id,
            "CreateRun",
            "run_failed",
            {"error": error_message},
        )
        run_store.save_run(
            run_id,
            research_topic=request.research_topic or _derive_research_topic(document_paths),
            status="failed",
            config=request_config,
            response={"run_id": run_id, "status": "failed", "error": error_message},
        )


def _build_workflow_state(
    run_id: str,
    request: ResearchRunRequest,
    document_paths: list[str],
    llm_config_summary: dict,
) -> dict:
    return {
        "run_id": run_id,
        "research_topic": request.research_topic,
        "source_mode": request.source_mode,
        "universe": request.universe,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "document_paths": document_paths,
        "max_chunks": request.max_chunks,
        "max_sources": request.max_sources,
        "allow_live_fetch": request.allow_live_fetch,
        "retrieval_mode": request.retrieval_mode,
        "embedding_dim": request.embedding_dim,
        "extraction_mode": request.extraction_mode,
        "enable_llm_extraction": request.enable_llm_extraction,
        "llm_retry_count": request.llm_retry_count,
        "llm_config": request.llm_config,
        "llm_config_summary": llm_config_summary,
        "data_provider": request.data_provider,
        "cache_enabled": request.cache_enabled,
        "fallback_to_fixture": request.fallback_to_fixture,
        "market_data_cache_dir": request.market_data_cache_dir,
        "data_version": request.data_version,
        "market_data_root": request.market_data_root,
        "max_universe_size": request.max_universe_size,
        "price_adjustment_mode": request.price_adjustment_mode,
        "event_db_path": DB_PATH,
        "execution_mode": request.execution_mode,
        "commission_bps": request.commission_bps,
        "stamp_duty_bps": request.stamp_duty_bps,
        "slippage_bps": request.slippage_bps,
        "exclude_st": request.exclude_st,
        "min_listing_days": request.min_listing_days,
        "holding_period_days": request.holding_period_days,
        "historical_universe_id": request.historical_universe_id,
    }


def _build_run_started_payload(request: ResearchRunRequest, llm_config_summary: dict) -> dict:
    return {
        "research_topic": request.research_topic,
        "source_mode": request.source_mode,
        "document_ids": request.document_ids,
        "max_sources": request.max_sources,
        "allow_live_fetch": request.allow_live_fetch,
        "retrieval_mode": request.retrieval_mode,
        "embedding_dim": request.embedding_dim,
        "extraction_mode": request.extraction_mode,
        "enable_llm_extraction": request.enable_llm_extraction,
        "llm_retry_count": request.llm_retry_count,
        "llm_config": llm_config_summary,
        "data_provider": request.data_provider,
        "cache_enabled": request.cache_enabled,
        "fallback_to_fixture": request.fallback_to_fixture,
        "data_version": request.data_version,
        "max_universe_size": request.max_universe_size,
        "price_adjustment_mode": request.price_adjustment_mode,
        "execution_mode": request.execution_mode,
        "commission_bps": request.commission_bps,
        "stamp_duty_bps": request.stamp_duty_bps,
        "slippage_bps": request.slippage_bps,
        "exclude_st": request.exclude_st,
        "min_listing_days": request.min_listing_days,
        "holding_period_days": request.holding_period_days,
        "historical_universe_id": request.historical_universe_id,
        "async_run": request.async_run,
    }


def _derive_research_topic(document_paths: list[str]) -> str:
    if document_paths:
        from pathlib import Path
        return Path(document_paths[0]).stem
    return "上传文档因子研究"


def _summarize_llm_config(config: dict) -> dict:
    api_key = config.get("api_key") or ""
    return {
        "provider": config.get("provider") or "openai",
        "model": config.get("model") or "",
        "base_url": config.get("base_url") or "",
        "api_key_configured": bool(api_key),
        "api_key_preview": _preview_secret(api_key),
    }


def _preview_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:3]}...{value[-4:]}"
