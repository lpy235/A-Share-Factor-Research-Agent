from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.graph import run_research_workflow
from app.storage.db import init_db
from app.storage.events import EventStore

router = APIRouter(prefix="/research", tags=["research"])

DB_PATH = "runs.db"
init_db(DB_PATH)
event_store = EventStore(DB_PATH)


class ResearchRunRequest(BaseModel):
    research_topic: str
    source_mode: str = "upload"
    universe: str = "CSI300"
    start_date: str = "2020-01-01"
    end_date: str = "2020-12-31"


@router.post("/runs")
def create_research_run(request: ResearchRunRequest):
    run_id = f"run_{uuid4().hex[:12]}"
    event_store.append(
        run_id,
        "CreateRun",
        "run_started",
        {"research_topic": request.research_topic, "source_mode": request.source_mode},
    )
    state = run_research_workflow(
        {
            "run_id": run_id,
            "research_topic": request.research_topic,
            "source_mode": request.source_mode,
            "universe": request.universe,
            "start_date": request.start_date,
            "end_date": request.end_date,
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
    return {
        "run_id": run_id,
        "status": "completed",
        "selected_factors": state.get("selected_factors", []),
        "report_markdown": state["report_markdown"],
    }

