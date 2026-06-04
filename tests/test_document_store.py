from app.storage.documents import DocumentStore


def test_document_store_saves_and_gets_markdown(tmp_path):
    store = DocumentStore(str(tmp_path))
    record = store.save("demo.md", "成交量放大且价格上涨".encode("utf-8"), "text/markdown")

    loaded = store.get(record.document_id)
    assert loaded.filename == "demo.md"
    assert loaded.content_type == "text/markdown"
    assert loaded.path.endswith("demo.md")


def test_document_store_rejects_unsupported_type(tmp_path):
    store = DocumentStore(str(tmp_path))
    try:
        store.save("demo.exe", b"bad")
    except ValueError as exc:
        assert "Unsupported document type" in str(exc)
    else:
        raise AssertionError("expected ValueError")

