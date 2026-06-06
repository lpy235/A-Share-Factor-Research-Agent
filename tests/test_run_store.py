from app.storage.db import init_db
from app.storage.runs import RunStore


def test_run_store_saves_lists_and_gets_runs(tmp_path):
    db_path = tmp_path / "runs.db"
    init_db(str(db_path))
    store = RunStore(str(db_path))

    store.save_run(
        "run_test",
        research_topic="A股量价类动量因子",
        status="completed",
        config={"source_mode": "auto"},
        response={"selected_factors": ["momentum_20"], "factor_specs": [{"factor_name": "momentum_20"}]},
    )

    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run_test"
    assert runs[0]["selected_count"] == 1
    assert runs[0]["factor_count"] == 1

    run = store.get_run("run_test")
    assert run["config"]["source_mode"] == "auto"
    assert run["response"]["selected_factors"] == ["momentum_20"]
