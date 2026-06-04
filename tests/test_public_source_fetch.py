from app.sources.fetch import html_to_text
from app.sources.search import ManualSourceSearch


def test_manual_source_search_filters_by_query():
    search = ManualSourceSearch(
        [
            {"title": "A股动量因子研究", "url": "https://example.com/momentum"},
            {"title": "债券久期研究", "url": "https://example.com/bond"},
        ]
    )
    result = search.search("动量因子", max_sources=3)
    assert len(result) == 1
    assert result[0]["title"] == "A股动量因子研究"


def test_html_to_text_strips_scripts():
    html = "<html><script>bad()</script><body><h1>因子研究</h1><p>量价齐升。</p></body></html>"
    text = html_to_text(html)
    assert "bad()" not in text
    assert "因子研究" in text
    assert "量价齐升" in text

