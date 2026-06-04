from app.agents.graph import NODE_ORDER, run_research_workflow
from app.storage.events import EventStore


def test_graph_writes_node_level_events_in_order(tmp_path):
    db_path = tmp_path / "runs.db"
    doc = tmp_path / "factor_note.md"
    doc.write_text("成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。", encoding="utf-8")

    run_research_workflow(
        {
            "run_id": "run_trace_upload",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "document_paths": [str(doc)],
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "event_db_path": str(db_path),
        }
    )

    events = EventStore(str(db_path)).list_events("run_trace_upload")
    started_nodes = [event["node"] for event in events if event["event_type"] == "node_started"]
    completed_nodes = [event["node"] for event in events if event["event_type"] == "node_completed"]

    expected_nodes = [name for name, _ in NODE_ORDER]
    assert started_nodes == expected_nodes
    assert completed_nodes == expected_nodes
    assert events[0]["node"] == "LoadDocumentsNode"
    assert events[0]["payload"]["input_summary"]["document_path_count"] == 1


def test_graph_records_fallback_event_when_no_documents(tmp_path):
    db_path = tmp_path / "runs.db"

    state = run_research_workflow(
        {
            "run_id": "run_trace_fallback",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "event_db_path": str(db_path),
        }
    )

    events = EventStore(str(db_path)).list_events("run_trace_fallback")
    fallback_events = [event for event in events if event["event_type"] == "node_fallback"]

    assert state["selected_factors"] == ["volume_price_momentum"]
    assert fallback_events[0]["node"] == "LoadDocumentsNode"
    assert fallback_events[0]["payload"]["reason"] == "no_parseable_documents"
