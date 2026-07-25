from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.portfolio_manager import PortfolioManagerAgent
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
    long_only_metrics = {
        item.get("factor_name"): item for item in run["response"].get("long_only_metrics", [])
    }
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
                    "metrics": {
                        **metrics.get(name, {}),
                        "long_only_metrics": long_only_metrics.get(name, {}),
                    },
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


@router.post("/{version_id}/recommendations")
def recommend(version_id: str):
    try:
        factor = registry_store.get(version_id)
        other_formulas = [item["formula"] for item in registry_store.list() if item["version_id"] != version_id]
        similarity = _formula_similarity(factor["formula"], other_formulas)
        long_only = factor["metrics"].get("long_only_metrics")
        recommendation = PortfolioManagerAgent().recommend(
            metrics=factor["metrics"],
            long_only_metrics=long_only if isinstance(long_only, dict) else None,
            data_version=factor.get("data_version"),
            manifest_hash=factor.get("manifest_hash"),
            similarity=similarity,
        )
        stored = registry_store.record_recommendation(
            version_id,
            recommendation.recommendation,
            recommendation.reasons,
            recommendation.evidence,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="factor_version_not_found") from exc
    return {"version_id": version_id, "recommendation": stored}


def _formula_similarity(formula: str, comparisons: list[str]) -> float | None:
    tokens = set(formula.replace("(", " ").replace(")", " ").replace(",", " ").split())
    if not comparisons or not tokens:
        return None
    scores = []
    for candidate in comparisons:
        other = set(candidate.replace("(", " ").replace(")", " ").replace(",", " ").split())
        if other:
            scores.append(len(tokens & other) / len(tokens | other))
    return round(max(scores), 6) if scores else None
