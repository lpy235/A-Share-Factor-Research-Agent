from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_index_served():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "A-Share Factor Research Agent" in response.text
    assert 'id="run-form"' in response.text
    assert "/static/app.js" in response.text


def test_dashboard_static_assets_served():
    client = TestClient(app)

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert "Quant Agent Workbench" not in css_response.text
    assert js_response.status_code == 200
    assert "POST" in js_response.text
