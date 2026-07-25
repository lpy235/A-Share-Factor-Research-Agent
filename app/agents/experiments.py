"""Finite research-experiment orchestration over one fixed data version."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.factor.dsl import FactorSpec
from app.factor.variation import FactorVariation, FactorVariationEngine
from app.storage.experiments import ExperimentStore


@dataclass(frozen=True)
class ExperimentBudget:
    max_candidates: int = 8
    max_variation_rounds: int = 1
    max_backtests: int = 8

    def as_dict(self) -> dict[str, int]:
        if self.max_candidates < 1 or self.max_variation_rounds < 0 or self.max_backtests < 1:
            raise ValueError("experiment budget values must be positive except variation rounds")
        return {
            "max_candidates": self.max_candidates,
            "max_variation_rounds": self.max_variation_rounds,
            "max_backtests": self.max_backtests,
            "llm_calls": 0,
        }


class ResearchExperimentService:
    """Runs bounded candidates through the existing research backtest workflow."""

    def __init__(
        self,
        store: ExperimentStore,
        runner: Callable[[dict[str, Any]], dict[str, Any]],
        variation_engine: FactorVariationEngine | None = None,
    ) -> None:
        self.store = store
        self.runner = runner
        self.variation_engine = variation_engine or FactorVariationEngine()

    def run(
        self,
        *,
        source_run_id: str,
        source_config: dict[str, Any],
        source_response: dict[str, Any],
        budget: ExperimentBudget,
    ) -> dict[str, Any]:
        if source_config.get("data_provider") != "warehouse" or not source_config.get("data_version"):
            raise ValueError("experiments require a warehouse-backed source run with data_version")
        selected = set(source_response.get("selected_factors", []))
        parents = [
            FactorSpec(**spec)
            for spec in source_response.get("factor_specs", [])
            if spec.get("factor_name") in selected
        ]
        if not parents:
            raise ValueError("source run has no selected factor specifications")
        limits = budget.as_dict()
        experiment = self.store.create(
            source_run_id=source_run_id,
            data_version=source_config["data_version"],
            manifest_hash=source_response.get("market_data_metadata", {}).get("manifest_hash"),
            budget=limits,
        )
        candidates = self._build_candidates(parents, budget)
        try:
            state = self.runner(
                {
                    **source_config,
                    "run_id": experiment["experiment_id"],
                    "factor_specs_seed": [candidate.spec.model_dump() for candidate in candidates],
                    "enable_llm_extraction": False,
                    "llm_config": {},
                    "fallback_to_fixture": False,
                }
            )
            selected_names = set(state.get("selected_factors", []))
            metrics_by_name = {item.get("factor_name"): item for item in state.get("metrics", [])}
            for candidate in candidates:
                metric = metrics_by_name.get(candidate.spec.factor_name, {})
                accepted = candidate.spec.factor_name in selected_names
                self.store.add_candidate(
                    experiment["experiment_id"],
                    spec=candidate.spec.model_dump(),
                    parent_factor_names=list(candidate.parent_factor_names),
                    reason=candidate.reason,
                    round_number=candidate.round_number,
                    status="selected" if accepted else "rejected",
                    rejection_reasons=[] if accepted else ["未通过既有 OOS 与 Walk-forward 选择门禁"],
                    metrics=metric,
                )
            return self.store.finish(experiment["experiment_id"], status="completed")
        except Exception:
            self.store.finish(experiment["experiment_id"], status="failed")
            raise

    def _build_candidates(self, parents: list[FactorSpec], budget: ExperimentBudget) -> list[FactorVariation]:
        candidates = [
            FactorVariation(parent, (parent.factor_name,), "原始已选因子作为实验基准", 0)
            for parent in parents
        ]
        if budget.max_variation_rounds:
            for parent in parents:
                remaining = budget.max_candidates - len(candidates)
                if remaining <= 0:
                    break
                candidates.extend(
                    self.variation_engine.generate(parent, max_variants=remaining, round_number=1)
                )
        if len(parents) >= 2 and len(candidates) < budget.max_candidates:
            candidates.append(self.variation_engine.combine(parents[0], parents[1], round_number=1))
        return candidates[: min(budget.max_candidates, budget.max_backtests)]
