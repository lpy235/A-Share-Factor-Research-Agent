from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage.factor_registry import FactorRegistryStore
from app.storage.runs import RunStore


router = APIRouter(prefix="/factor-registry", tags=["factor-registry"])
run_store = RunStore("runs.db")
registry_store = FactorRegistryStore()


class DecisionRequest(BaseModel):
    status: Literal["approved", "rejected", "retired"]
    decision_maker: str
    reason: str


@router.post("/from-run/{run_id}")
def register_from_run(run_id: str):
    run = run_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    if run["status"] != "completed":
        raise HTTPException(status_code=409, detail="run_not_completed")
    selected = set(run["response"].get("selected_factors", []))
    if not selected:
        raise HTTPException(status_code=422, detail="run_has_no_selected_factors")
    specs = {item.get("factor_name"): item for item in run["response"].get("factor_specs", [])}
    metrics = {item.get("factor_name"): item for item in run["response"].get("metrics", [])}
    missing = sorted(selected - set(specs))
    if missing:
        raise HTTPException(status_code=422, detail=f"selected_factor_specs_missing: {missing}")
    config = run["config"]
    registered = []
    for name in sorted(selected):
        spec = specs[name]
        registered.append(
            registry_store.register_candidate(
                {
                    "factor_name": name,
                    "formula": spec["formula"],
                    "direction": spec["direction"],
                    "required_fields": spec["required_fields"],
                    "source_evidence": {
                        "source_title": spec.get("source_title"),
                        "source_url": spec.get("source_url"),
                        "source_excerpt": spec.get("source_excerpt"),
                    },
                    "metrics": metrics.get(name, {}),
                    "run_id": run_id,
                    "data_version": config.get("data_version"),
                    "manifest_hash": run["response"].get("market_data_metadata", {}).get("manifest_hash"),
                }
            )
        )
    return {"registered_count": len(registered), "factors": registered}


@router.get("")
def list_factors():
    return {"factors": registry_store.list()}


@router.post("/{version_id}/decisions")
def decide(version_id: str, request: DecisionRequest):
    try:
        decision = registry_store.record_decision(
            version_id, request.status, request.decision_maker, request.reason
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="factor_version_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"version_id": version_id, "decision": decision}
