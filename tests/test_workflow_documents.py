from pathlib import Path

from app.agents.graph import run_research_workflow


def test_workflow_uses_uploaded_document_content(tmp_path):
    doc = tmp_path / "factor_note.md"
    doc.write_text("成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。", encoding="utf-8")

    state = run_research_workflow(
        {
            "run_id": "test",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "document_paths": [str(doc)],
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
        }
    )

    assert state["factor_specs"][0]["source_title"] == "factor_note.md"
    assert "volume_price_momentum" in state["selected_factors"]

