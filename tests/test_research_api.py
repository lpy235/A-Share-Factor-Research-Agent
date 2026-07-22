import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_research_api_returns_v2_compatible_response_and_node_trace():
    client = TestClient(app)

    response = client.post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "source_mode": "upload",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {
        "run_id",
        "status",
        "selected_factors",
        "factor_specs",
        "metrics",
        "oos_metrics",
        "factor_correlation",
        "backtest_series",
        "gross_backtest_series",
        "net_backtest_series",
        "turnover_series",
        "cost_series",
        "long_only_metrics",
        "tradability_diagnostics",
        "universe_diagnostics",
        "report_markdown",
        "artifacts",
        "source_diagnostics",
        "backtest_assumptions",
        "audit_trail",
    }.issubset(body)
    assert body["status"] == "completed"
    assert body["selected_factors"] == ["volume_price_momentum"]
    assert body["metrics"][0]["factor_name"] == "volume_price_momentum"
    assert "mean_rank_ic_oos" in body["metrics"][0]
    assert body["oos_metrics"]
    assert {"labels", "values"}.issubset(body["factor_correlation"])
    assert body["backtest_series"]["volume_price_momentum"]["rank_ic"]
    assert body["gross_backtest_series"]["volume_price_momentum"]
    assert body["net_backtest_series"]["volume_price_momentum"]
    assert body["long_only_metrics"][0]["factor_name"] == "volume_price_momentum"
    assert body["source_diagnostics"]["accepted_count"] >= 1
    assert body["backtest_assumptions"]["universe"] == "CSI300"
    assert body["audit_trail"]
    artifact_names = {item["name"] for item in body["artifacts"]}
    assert {
        "report.md",
        "bundle.json",
        "backtest_series.json",
        "metric_overview.png",
        "factor_quality.png",
        "oos_metrics.json",
        "factor_correlation.json",
        "rank_ic_timeseries.png",
        "long_short_equity.png",
        "grouped_returns.png",
        "portfolio_backtest.json",
        "backtest_diagnostics.json",
    }.issubset(artifact_names)

    events_response = client.get(f"/runs/{body['run_id']}/events")
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert any(
        event["node"] == "LoadDocumentsNode" and event["event_type"] == "node_started"
        for event in events
    )
    assert any(
        event["node"] == "GenerateReportNode" and event["event_type"] == "run_completed"
        for event in events
    )

    artifacts_response = client.get(f"/runs/{body['run_id']}/artifacts")
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["artifacts"]

    report_response = client.get(f"/runs/{body['run_id']}/artifacts/report.md")
    assert report_response.status_code == 200
    assert "历史回测不构成投资建议" in report_response.text

    chart_response = client.get(f"/runs/{body['run_id']}/artifacts/metric_overview.png")
    assert chart_response.status_code == 200
    assert chart_response.headers["content-type"] == "image/png"

    runs_response = client.get("/runs")
    assert runs_response.status_code == 200
    assert any(item["run_id"] == body["run_id"] for item in runs_response.json()["runs"])

    run_response = client.get(f"/runs/{body['run_id']}")
    assert run_response.status_code == 200
    assert run_response.json()["response"]["run_id"] == body["run_id"]


def test_research_api_supports_auto_public_sources():
    client = TestClient(app)

    response = client.post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "universe": "CSI300",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "max_chunks": 5,
            "max_sources": 2,
            "allow_live_fetch": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "volume_price_momentum" in body["selected_factors"]
    assert body["factor_specs"][0]["source_url"]


def test_research_api_supports_vector_retrieval_mode():
    client = TestClient(app)

    response = client.post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "retrieval_mode": "vector",
            "embedding_dim": 128,
            "max_sources": 2,
            "allow_live_fetch": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "volume_price_momentum" in body["selected_factors"]


def test_research_api_accepts_extraction_controls():
    client = TestClient(app)

    response = client.post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "retrieval_mode": "hybrid",
            "extraction_mode": "rule",
            "enable_llm_extraction": False,
            "llm_retry_count": 1,
            "max_sources": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "volume_price_momentum" in body["selected_factors"]


def test_research_api_accepts_data_provider_controls(tmp_path):
    client = TestClient(app)

    response = client.post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "source_mode": "auto",
            "data_provider": "fixture",
            "cache_enabled": True,
            "fallback_to_fixture": True,
            "market_data_cache_dir": str(tmp_path),
            "max_sources": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "volume_price_momentum" in body["selected_factors"]


def test_research_api_accepts_realistic_backtest_configuration():
    response = TestClient(app).post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "execution_mode": "next_open_to_next_open",
            "commission_bps": 2,
            "stamp_duty_bps": 4,
            "slippage_bps": 6,
            "exclude_st": False,
            "min_listing_days": 20,
        },
    )

    assert response.status_code == 200
    assumptions = response.json()["backtest_assumptions"]
    assert assumptions["execution_mode"] == "next_open_to_next_open"
    assert assumptions["commission_bps"] == 2
    assert assumptions["stamp_duty_bps"] == 4
    assert assumptions["slippage_bps"] == 6
    assert assumptions["exclude_st"] is False
    assert assumptions["min_listing_days"] == 20


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("commission_bps", -1),
        ("stamp_duty_bps", -1),
        ("slippage_bps", -1),
        ("min_listing_days", -1),
        ("execution_mode", "same_close"),
    ],
)
def test_research_api_rejects_invalid_backtest_configuration(field, value):
    response = TestClient(app).post(
        "/research/runs",
        json={"research_topic": "test", field: value},
    )

    assert response.status_code == 422


def test_research_api_applies_registered_historical_universe():
    client = TestClient(app)
    upload = client.post(
        "/universes",
        files={
            "file": (
                "membership.csv",
                b"date,symbol,in_universe\n2020-01-02,000001,true\n",
                "text/csv",
            )
        },
    )
    universe_id = upload.json()["historical_universe_id"]

    response = client.post(
        "/research/runs",
        json={
            "research_topic": "A股量价类动量因子",
            "historical_universe_id": universe_id,
        },
    )

    assert response.status_code == 200
    diagnostics = response.json()["universe_diagnostics"]
    assert diagnostics["historical_membership_applied"] is True
    assert diagnostics["historical_universe_id"] == universe_id


@pytest.mark.parametrize("universe_id", ["../membership.csv", "universe_000000000000"])
def test_research_api_rejects_uncontrolled_or_missing_universe(universe_id):
    response = TestClient(app).post(
        "/research/runs",
        json={"research_topic": "test", "historical_universe_id": universe_id},
    )

    assert response.status_code == 422
