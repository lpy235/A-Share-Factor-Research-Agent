import pytest

from app.agents.experiments import ExperimentBudget, ResearchExperimentService
from app.storage.experiments import ExperimentStore


def _spec() -> dict:
    return {
        "factor_name": "momentum",
        "hypothesis": "momentum",
        "formula": "rank(returns(close, 20))",
        "required_fields": ["close"],
        "direction": "positive",
        "category": "price",
        "frequency": "daily",
        "lookback": 20,
        "source_title": "report",
        "source_excerpt": "evidence",
        "confidence": 0.8,
    }


def _runner(state):
    names = [item["factor_name"] for item in state["factor_specs_seed"]]
    return {"selected_factors": [names[0]], "metrics": [{"factor_name": name, "mean_rank_ic_oos": 0.03} for name in names]}


def test_experiment_pins_source_version_and_records_candidate_results(tmp_path):
    service = ResearchExperimentService(ExperimentStore(tmp_path / "experiments.db"), _runner)
    result = service.run(
        source_run_id="run_1",
        source_config={"data_provider": "warehouse", "data_version": "v1"},
        source_response={"selected_factors": ["momentum"], "factor_specs": [_spec()], "market_data_metadata": {"manifest_hash": "a" * 64}},
        budget=ExperimentBudget(max_candidates=3, max_backtests=3),
    )

    assert result["status"] == "completed"
    assert result["data_version"] == "v1"
    assert result["budget"]["llm_calls"] == 0
    assert result["candidates"][0]["status"] == "selected"
    assert any(item["rejection_reasons"] for item in result["candidates"][1:])


def test_experiment_refuses_non_versioned_source_runs(tmp_path):
    service = ResearchExperimentService(ExperimentStore(tmp_path / "experiments.db"), _runner)

    with pytest.raises(ValueError, match="warehouse-backed"):
        service.run(
            source_run_id="run_1",
            source_config={"data_provider": "fixture"},
            source_response={"selected_factors": ["momentum"], "factor_specs": [_spec()]},
            budget=ExperimentBudget(),
        )
