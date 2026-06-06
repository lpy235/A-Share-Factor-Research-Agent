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
        "report_markdown",
        "artifacts",
        "source_diagnostics",
        "backtest_assumptions",
        "audit_trail",
    }.issubset(body)
    assert body["status"] == "completed"
    assert body["selected_factors"] == ["volume_price_momentum"]
    assert body["metrics"][0]["factor_name"] == "volume_price_momentum"
    assert body["source_diagnostics"]["accepted_count"] >= 1
    assert body["backtest_assumptions"]["universe"] == "CSI300"
    assert body["audit_trail"]
    artifact_names = {item["name"] for item in body["artifacts"]}
    assert {"report.md", "bundle.json", "metric_overview.png", "factor_quality.png"}.issubset(
        artifact_names
    )

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
