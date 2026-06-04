from app.storage.db import init_db
from app.storage.events import EventStore


def test_event_store_appends_and_lists_events(tmp_path):
    db_path = tmp_path / "runs.db"
    init_db(str(db_path))
    store = EventStore(str(db_path))

    store.append("run_test", "ExtractHypothesesNode", "node_completed", {"count": 3})

    events = store.list_events("run_test")
    assert len(events) == 1
    assert events[0]["node"] == "ExtractHypothesesNode"
    assert events[0]["payload"]["count"] == 3

