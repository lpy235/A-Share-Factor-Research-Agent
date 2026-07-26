import re

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
    assert "最近实验" in response.text
    assert "/docs" in response.text
    assert "/research/runs" in response.text
    assert 'id="run-form"' in response.text
    assert 'id="workflow-steps"' in response.text
    assert 'id="metric-summary"' in response.text
    assert 'id="source-list"' in response.text
    assert 'id="metrics-table"' in response.text
    assert 'id="artifact-list"' in response.text
    assert 'id="run-history"' in response.text
    assert 'id="source-diagnostics"' in response.text
    assert 'id="backtest-assumptions"' in response.text
    assert 'id="audit-trail"' in response.text
    assert 'id="register-current-run"' in response.text
    assert 'id="factor-decision-form"' in response.text
    assert 'id="decision-status"' in response.text
    assert 'id="commission-bps"' in response.text
    assert 'id="stamp-duty-bps"' in response.text
    assert 'id="slippage-bps"' in response.text
    assert 'id="exclude-st"' in response.text
    assert 'id="min-listing-days"' in response.text
    assert 'id="holding-period-days"' in response.text
    assert 'id="price-adjustment-mode"' in response.text
    assert 'id="long-only-metrics"' in response.text
    assert 'id="tradability-diagnostics"' in response.text
    assert 'id="llm-provider"' in response.text
    assert 'id="llm-model"' in response.text
    assert 'id="llm-base-url"' in response.text
    assert 'id="llm-api-key"' in response.text
    assert 'id="save-llm-config"' in response.text
    assert 'id="clear-llm-config"' in response.text
    assert "研究图表与下载" in response.text
    assert "Agent 审计链" in response.text
    assert "/static/app.js" in response.text


def test_dashboard_static_assets_served():
    client = TestClient(app)

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert ".workspace-grid" in css_response.text
    assert "@media (max-width: 1460px)" in css_response.text
    assert ".launch-grid" in css_response.text
    assert ".api-panel" in css_response.text
    assert ".artifact-list" in css_response.text
    assert ".history-list" in css_response.text
    assert ".audit-list" in css_response.text
    assert ".summary-grid" in css_response.text
    assert js_response.status_code == 200
    assert "prepareLaunch" in js_response.text
    assert "sourceModeLabels" in js_response.text
    assert "renderArtifacts" in js_response.text
    assert "loadRunHistory" in js_response.text
    assert "renderAuditTrail" in js_response.text
    assert "renderMetricSummary" in js_response.text
    assert "renderMetrics" in js_response.text
    assert "ashare-factor-agent-llm-config" in js_response.text
    assert "readLlmConfig" in js_response.text
    assert "maskSecret" in js_response.text
    assert "registerSelectedFactors" in js_response.text
    assert "submitFactorDecision" in js_response.text
    assert "price_adjustment_mode" in js_response.text
    assert "POST" in js_response.text


def test_dashboard_starts_with_an_empty_research_topic_for_uploads():
    response = TestClient(app).get("/")

    topic_field = re.search(
        r'<textarea[^>]*id="research-topic"[^>]*>\s*</textarea>',
        response.text,
    )

    assert topic_field is not None
    assert "上传研报时可留空" in topic_field.group(0)


def test_openapi_schema_uses_chinese_product_name():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "A股因子研究智能体"
