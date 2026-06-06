from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_index_served():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "A股因子研究智能体" in response.text
    assert "跑一个示例研究" in response.text
    assert "从主题开始" in response.text
    assert "上传论文/研报" in response.text
    assert "高级设置" in response.text
    assert "/docs" in response.text
    assert "/research/runs" in response.text
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
    assert ".api-panel" in css_response.text
    assert ".summary-grid" in css_response.text
    assert js_response.status_code == 200
    assert "prepareLaunch" in js_response.text
    assert "sourceModeLabels" in js_response.text
    assert "renderMetricSummary" in js_response.text
    assert "renderMetrics" in js_response.text
    assert "POST" in js_response.text


def test_openapi_schema_uses_chinese_product_name():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "A股因子研究智能体"
