from uuid import uuid4

from fastapi import APIRouter, HTTPException
from typing import Literal

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
    research_topic: str
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
    execution_mode: Literal["next_open_to_next_open"] = "next_open_to_next_open"
    commission_bps: float = Field(default=3.0, ge=0)
    stamp_duty_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    exclude_st: bool = True
    min_listing_days: int = Field(default=60, ge=0)
    historical_universe_id: str | None = Field(
        default=None, pattern=r"^universe_[0-9a-f]{12}$"
    )


@router.post("/runs")
def create_research_run(request: ResearchRunRequest):
    if request.historical_universe_id:
        try:
            HistoricalUniverseStore().load(request.historical_universe_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Historical universe not found") from exc
    run_id = f"run_{uuid4().hex[:12]}"
    request_config = request.model_dump()
    llm_config_summary = _summarize_llm_config(request.llm_config)
    request_config["llm_config"] = llm_config_summary
    document_paths = []
    if request.document_ids:
        from app.storage.documents import DocumentStore

        document_store = DocumentStore()
        document_paths = [document_store.get(document_id).path for document_id in request.document_ids]

    event_store.append(
        run_id,
        "CreateRun",
        "run_started",
        {
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
            "execution_mode": request.execution_mode,
            "commission_bps": request.commission_bps,
            "stamp_duty_bps": request.stamp_duty_bps,
            "slippage_bps": request.slippage_bps,
            "exclude_st": request.exclude_st,
            "min_listing_days": request.min_listing_days,
            "historical_universe_id": request.historical_universe_id,
        },
    )
    state = run_research_workflow(
        {
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
            "event_db_path": DB_PATH,
            "execution_mode": request.execution_mode,
            "commission_bps": request.commission_bps,
            "stamp_duty_bps": request.stamp_duty_bps,
            "slippage_bps": request.slippage_bps,
            "exclude_st": request.exclude_st,
            "min_listing_days": request.min_listing_days,
            "historical_universe_id": request.historical_universe_id,
        }
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
    }
    run_store.save_run(
        run_id,
        research_topic=request.research_topic,
        status="completed",
        config=request_config,
        response=response,
    )
    return response


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
