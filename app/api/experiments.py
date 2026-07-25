from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.experiments import ExperimentBudget, ResearchExperimentService
from app.agents.graph import run_research_workflow
from app.storage.experiments import ExperimentStore
from app.storage.runs import RunStore


router = APIRouter(prefix="/research-experiments", tags=["research-experiments"])
run_store = RunStore("runs.db")
experiment_store = ExperimentStore("runs.db")


class ExperimentRequest(BaseModel):
    max_candidates: int = Field(default=8, ge=1, le=24)
    max_variation_rounds: int = Field(default=1, ge=0, le=3)
    max_backtests: int = Field(default=8, ge=1, le=24)


@router.post("/from-run/{run_id}")
def create_experiment(run_id: str, request: ExperimentRequest):
    run = run_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    if run["status"] != "completed":
        raise HTTPException(status_code=409, detail="run_not_completed")
    try:
        service = ResearchExperimentService(experiment_store, run_research_workflow)
        experiment = service.run(
            source_run_id=run_id,
            source_config=run["config"],
            source_response=run["response"],
            budget=ExperimentBudget(**request.model_dump()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return experiment


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str):
    try:
        return experiment_store.get(experiment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="experiment_not_found") from exc
