from app.agents.graph import NODE_ORDER, build_research_graph, run_research_workflow


def test_build_research_graph_invokes_minimal_state():
    graph = build_research_graph()

    state = graph.invoke(
        {
            "run_id": "test_graph_minimal",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "warnings": [],
            "errors": [],
            "trace": [],
        }
    )

    assert state["selected_factors"] == ["volume_price_momentum"]
    assert state["factor_specs"][0]["factor_name"] == "volume_price_momentum"
    assert state["report_markdown"].startswith("# A 股因子研究报告")


def test_workflow_preserves_uploaded_document_source(tmp_path):
    doc = tmp_path / "factor_note.md"
    doc.write_text("成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。", encoding="utf-8")

    state = run_research_workflow(
        {
            "run_id": "test_uploaded_doc_graph",
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
    assert state["selected_factors"] == ["volume_price_momentum"]


def test_workflow_auto_mode_discovers_public_sources():
    state = run_research_workflow(
        {
            "run_id": "test_auto_public_sources",
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "max_sources": 2,
            "allow_live_fetch": False,
        }
    )

    assert len(state["discovered_sources"]) == 2
    assert state["factor_specs"][0]["source_url"]
    assert "volume_price_momentum" in state["selected_factors"]


def test_workflow_vector_retrieval_mode_records_diagnostics():
    state = run_research_workflow(
        {
            "run_id": "test_vector_retrieval_mode",
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "max_sources": 2,
            "allow_live_fetch": False,
            "retrieval_mode": "vector",
            "embedding_dim": 128,
        }
    )

    assert state["retrieval_diagnostics"]["retrieval_mode"] == "vector"
    assert state["retrieval_diagnostics"]["embedding_dim"] == 128
    assert state["retrieval_diagnostics"]["retrieved_count"] >= 1
    assert "volume_price_momentum" in state["selected_factors"]


def test_workflow_rule_extraction_mode_records_diagnostics():
    state = run_research_workflow(
        {
            "run_id": "test_rule_extraction_mode",
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "max_sources": 2,
            "allow_live_fetch": False,
            "extraction_mode": "rule",
            "enable_llm_extraction": False,
        }
    )

    assert state["extraction_diagnostics"]["extraction_mode"] == "rule"
    assert state["extraction_diagnostics"]["llm_attempted"] is False
    assert "volume_price_momentum" in state["selected_factors"]


def test_workflow_fixture_data_provider_records_market_diagnostics(tmp_path):
    state = run_research_workflow(
        {
            "run_id": "test_fixture_data_provider",
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "max_sources": 2,
            "allow_live_fetch": False,
            "data_provider": "fixture",
            "cache_enabled": True,
            "market_data_cache_dir": str(tmp_path),
        }
    )

    assert state["market_data_summary"]["provider"] == "fixture"
    assert state["market_data_diagnostics"]["cache_enabled"] is True
    assert state["market_data_diagnostics"]["cache_misses"] >= 1
    assert "fixture 数据" in state["report_markdown"]
    assert "volume_price_momentum" in state["selected_factors"]


def test_workflow_hybrid_mode_combines_upload_and_public_sources(tmp_path):
    doc = tmp_path / "factor_note.md"
    doc.write_text("成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。", encoding="utf-8")

    state = run_research_workflow(
        {
            "run_id": "test_hybrid_sources",
            "research_topic": "A股量价类动量因子",
            "source_mode": "hybrid",
            "document_paths": [str(doc)],
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "max_sources": 2,
            "allow_live_fetch": False,
        }
    )

    source_titles = {source["source_title"] for source in state["sources"]}
    assert "factor_note.md" in source_titles
    assert len(state["discovered_sources"]) == 2
    assert "volume_price_momentum" in state["selected_factors"]


def test_node_order_is_resume_readable():
    assert [name for name, _ in NODE_ORDER] == [
        "LoadDocumentsNode",
        "RetrieveChunksNode",
        "ExtractHypothesesNode",
        "GenerateFactorDSLNode",
        "ValidateDSLNode",
        "LoadMarketDataNode",
        "ExecuteFactorsNode",
        "RunBacktestNode",
        "SelectFactorsNode",
        "GenerateReportNode",
    ]
