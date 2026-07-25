from fastapi.testclient import TestClient

from app.api import experiments
from app.main import app
from app.storage.db import init_db
from app.storage.runs import RunStore


def test_experiment_api_rejects_completed_run_without_fixed_warehouse_version(tmp_path, monkeypatch):
    run_db = tmp_path / "runs.db"
    init_db(str(run_db))
    runs = RunStore(str(run_db))
    runs.save_run(
        "run_fixture",
        research_topic="test",
        status="completed",
        config={"data_provider": "fixture"},
        response={"selected_factors": ["momentum"], "factor_specs": []},
    )
    monkeypatch.setattr(experiments, "run_store", runs)

    response = TestClient(app).post("/research-experiments/from-run/run_fixture", json={})

    assert response.status_code == 422
    assert "warehouse-backed" in response.json()["detail"]
