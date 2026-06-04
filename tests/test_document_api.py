from fastapi.testclient import TestClient

from app.main import app


def test_document_upload_and_get():
    client = TestClient(app)
    response = client.post(
        "/documents",
        files={"file": ("factor.md", "成交量放大且价格上涨，可能代表趋势延续。", "text/markdown")},
    )
    assert response.status_code == 200
    document_id = response.json()["document_id"]

    get_response = client.get(f"/documents/{document_id}")
    assert get_response.status_code == 200
    assert get_response.json()["filename"] == "factor.md"

