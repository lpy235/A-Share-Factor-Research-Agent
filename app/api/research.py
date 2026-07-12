from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.graph import run_research_workflow
from app.storage.db import init_db
from app.storage.artifacts import ArtifactStore
from app.storage.events import EventStore
from app.storage.runs import RunStore

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
    data_provider: str = "fixture"
    cache_enabled: bool = True
    fallback_to_fixture: bool = True
    market_data_cache_dir: str = "data_cache"


@router.post("/runs")
def create_research_run(request: ResearchRunRequest):
    run_id = f"run_{uuid4().hex[:12]}"
    request_config = request.model_dump()
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
            "data_provider": request.data_provider,
            "cache_enabled": request.cache_enabled,
            "fallback_to_fixture": request.fallback_to_fixture,
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
            "data_provider": request.data_provider,
            "cache_enabled": request.cache_enabled,
            "fallback_to_fixture": request.fallback_to_fixture,
            "market_data_cache_dir": request.market_data_cache_dir,
            "event_db_path": DB_PATH,
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
