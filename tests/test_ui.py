from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_index_served():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "A-Share Factor Research Agent" in response.text
    assert "Run sample research" in response.text
    assert "Start from topic" in response.text
    assert "Upload material" in response.text
    assert "Advanced settings" in response.text
    assert 'id="run-form"' in response.text
    assert 'id="workflow-steps"' in response.text
    assert 'id="metric-summary"' in response.text
    assert 'id="source-list"' in response.text
    assert 'id="metrics-table"' in response.text
    assert "/static/app.js" in response.text


def test_dashboard_static_assets_served():
    client = TestClient(app)

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert ".workspace-grid" in css_response.text
    assert ".launch-grid" in css_response.text
    assert ".summary-grid" in css_response.text
    assert js_response.status_code == 200
    assert "prepareLaunch" in js_response.text
    assert "renderMetricSummary" in js_response.text
    assert "renderMetrics" in js_response.text
    assert "POST" in js_response.text
