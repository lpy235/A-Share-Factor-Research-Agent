from fastapi.testclient import TestClient

from app.api import factor_registry
from app.main import app
from app.storage.db import init_db
from app.storage.factor_registry import FactorRegistryStore
from app.storage.runs import RunStore


def test_register_selected_factor_and_append_human_decision(tmp_path, monkeypatch):
    run_db = tmp_path / "runs.db"
    init_db(str(run_db))
    runs = RunStore(str(run_db))
    runs.save_run(
        "run_completed", research_topic="test", status="completed",
        config={"data_version": "v20200101_test"},
        response={"selected_factors": ["momentum"], "metrics": [{"factor_name": "momentum", "mean_rank_ic_oos": 0.03}], "factor_specs": [{"factor_name": "momentum", "formula": "rank(close)", "direction": "positive", "required_fields": ["close"], "source_title": "report", "source_excerpt": "evidence"}], "market_data_metadata": {"manifest_hash": "b" * 64}},
    )
    monkeypatch.setattr(factor_registry, "run_store", runs)
    monkeypatch.setattr(factor_registry, "registry_store", FactorRegistryStore(tmp_path / "factors.db"))
    client = TestClient(app)

    registered = client.post("/factor-registry/from-run/run_completed")
    version_id = registered.json()["factors"][0]["version_id"]
    decision = client.post(f"/factor-registry/{version_id}/decisions", json={"status": "approved", "decision_maker": "pm", "reason": "stable"})

    assert registered.status_code == 200
    assert registered.json()["registered_count"] == 1
    assert decision.status_code == 200
    assert client.get("/factor-registry").json()["factors"][0]["status"] == "approved"
