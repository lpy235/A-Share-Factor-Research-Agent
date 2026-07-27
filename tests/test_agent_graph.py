import pandas as pd

from app.agents.graph import NODE_ORDER, build_research_graph, run_research_workflow
from app.agents.graph_nodes import _select_factors, _select_universe_symbols
from app.factor.dsl import FactorSpec


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


def test_seeded_factor_report_uses_uploaded_source_not_demo_fallback(tmp_path):
    doc = tmp_path / "verified_public_source.md"
    doc.write_text("A preserved public-source evidence record.", encoding="utf-8")
    spec = FactorSpec(
        factor_name="seeded_reversal",
        hypothesis="预注册的反转因子。",
        formula="rank(-returns(close, 20))",
        required_fields=["close"],
        direction="positive",
        category="reversal",
        frequency="daily",
        lookback=20,
        source_title="Verified public source",
        source_url="https://example.com/public-source",
        source_excerpt="预注册证据。",
        confidence=0.9,
    )

    state = run_research_workflow(
        {
            "run_id": "test_seeded_factor_source",
            "research_topic": "预注册反转研究",
            "source_mode": "upload",
            "document_paths": [str(doc)],
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "factor_specs_seed": [spec.model_dump()],
        }
    )

    assert "verified_public_source.md" in state["report_markdown"]
    assert "demo factor note" not in state["report_markdown"]


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


def test_node_order_is_stable_and_readable():
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


def test_select_factors_rejects_opposite_oos_direction():
    state = {
        "warnings": [],
        "metrics": [
            {
                "factor_name": "is_only_factor",
                "mean_rank_ic": 0.04,
                "icir": 0.6,
                "coverage_ratio": 0.9,
                "missing_ratio": 0.1,
                "max_drawdown": -0.12,
                "mean_rank_ic_oos": -0.03,
                "ic_decay_ratio": 1.0,
                "walk_forward_positive_ratio": 1.0,
                "walk_forward_sign_consistent": True,
                "walk_forward_insufficient_data": False,
            }
        ],
        "_factor_values": {},
    }

    result = _select_factors(state, None)

    assert result["selected_factors"] == []
    assert result["combination_backtest"] == {}
    assert any("oos_direction_mismatch" in warning for warning in result["warnings"])


def test_workflow_exposes_cost_aware_long_only_outputs(tmp_path):
    state = run_research_workflow(
        {
            "run_id": "test_cost_aware_portfolio",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "start_date": "2020-01-01",
            "end_date": "2020-06-30",
            "cache_enabled": False,
            "market_data_cache_dir": str(tmp_path),
        }
    )
    factor = "volume_price_momentum"

    assert state["gross_backtest_series"][factor]
    assert state["net_backtest_series"][factor]
    assert state["turnover_series"][factor]
    assert state["cost_series"][factor]["full"]
    assert state["long_only_metrics"][0]["factor_name"] == factor
    assert state["tradability_diagnostics"][factor]["executable"] is True
    assert state["universe_diagnostics"]["historical_membership_applied"] is False
    assert "生存者偏差" in state["universe_diagnostics"]["warning"]


def test_workflow_uses_the_predeclared_holding_period_for_evaluation_and_portfolios(tmp_path):
    state = run_research_workflow(
        {
            "run_id": "test_holding_period",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "start_date": "2020-01-01",
            "end_date": "2020-06-30",
            "cache_enabled": False,
            "market_data_cache_dir": str(tmp_path),
            "holding_period_days": 5,
        }
    )

    assert state["backtest_assumptions"]["holding_period_days"] == 5
    assert state["backtest_assumptions"]["forward_return_period"] == "5 trading days"
    assert state["tradability_diagnostics"]["volume_price_momentum"]["holding_period_days"] == 5


def test_workflow_samples_factor_metrics_on_holding_period_signal_dates(tmp_path):
    state = run_research_workflow(
        {
            "run_id": "test_holding_period_signal_cadence",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "start_date": "2020-01-01",
            "end_date": "2020-06-30",
            "cache_enabled": False,
            "market_data_cache_dir": str(tmp_path),
            "holding_period_days": 5,
        }
    )

    points = state["backtest_series"]["volume_price_momentum"]["rank_ic"]
    dates = pd.to_datetime([point["date"] for point in points])

    assert state["backtest_assumptions"]["factor_evaluation_frequency"] == "every 5 trading days"
    assert state["backtest_assumptions"]["factor_evaluation_signal_count"] == len(points)
    assert len(points) > 2
    assert (dates[1:] - dates[:-1]).days.min() >= 5


def test_warehouse_universe_is_not_silently_limited_to_demo_size():
    symbols = [f"{number:06d}.SZ" for number in range(30)]

    warehouse_symbols, warehouse_diagnostics = _select_universe_symbols(
        symbols, provider_name="warehouse", max_universe_size=None
    )
    fixture_symbols, fixture_diagnostics = _select_universe_symbols(
        symbols, provider_name="fixture", max_universe_size=None
    )

    assert warehouse_symbols == symbols
    assert warehouse_diagnostics == {
        "available_symbol_count": 30,
        "selected_symbol_count": 30,
        "max_universe_size": None,
    }
    assert fixture_symbols == symbols[:20]
    assert fixture_diagnostics["selected_symbol_count"] == 20
    assert fixture_diagnostics["max_universe_size"] == 20


def test_is_and_oos_portfolios_each_start_flat(tmp_path):
    state = run_research_workflow(
        {
            "run_id": "test_portfolio_segments_start_flat",
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "start_date": "2020-01-01",
            "end_date": "2020-06-30",
            "cache_enabled": False,
            "market_data_cache_dir": str(tmp_path),
        }
    )
    costs = state["cost_series"]["volume_price_momentum"]

    assert costs["is"][0]["sell_turnover"] == 0
    assert costs["oos"][0]["sell_turnover"] == 0
    first_is_buy = next(item for item in costs["is"] if item["buy_turnover"] > 0)
    first_oos_buy = next(item for item in costs["oos"] if item["buy_turnover"] > 0)
    assert first_is_buy["sell_turnover"] == 0
    assert first_oos_buy["sell_turnover"] == 0
