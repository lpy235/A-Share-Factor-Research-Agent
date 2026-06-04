from app.sources.discovery import PublicSourceDiscovery


def test_public_source_discovery_returns_relevant_public_sources():
    discovery = PublicSourceDiscovery()

    results = discovery.discover("A股量价类动量因子", max_sources=2)

    assert len(results) == 2
    assert all(result.url.startswith("https://") for result in results)
    assert any("量价" in result.text or "成交量" in result.text for result in results)


def test_public_source_discovery_filters_login_sources():
    discovery = PublicSourceDiscovery(
        seeds=[
            {
                "title": "登录研报",
                "url": "https://broker.example.com/login/report/123",
                "source_type": "public_report",
                "text": "成交量放大且价格上涨。",
            },
            {
                "title": "公开量价研究",
                "url": "https://example.com/public/volume-price",
                "source_type": "public_article",
                "text": "成交量放大且价格上涨，可构造量价动量因子。",
            },
        ]
    )

    results = discovery.discover("量价动量", max_sources=5)

    assert len(results) == 1
    assert results[0].title == "公开量价研究"


def test_public_source_discovery_uses_seed_text_when_live_fetch_fails():
    class FailingFetcher:
        def fetch_text(self, url: str) -> str:
            raise RuntimeError("network unavailable")

    discovery = PublicSourceDiscovery(
        seeds=[
            {
                "title": "公开量价研究",
                "url": "https://example.com/public/volume-price",
                "source_type": "public_article",
                "text": "成交量放大且价格上涨，可构造量价动量因子。",
            }
        ],
        fetcher=FailingFetcher(),
    )

    results = discovery.discover("量价动量", allow_live_fetch=True)

    assert results[0].text == "成交量放大且价格上涨，可构造量价动量因子。"
