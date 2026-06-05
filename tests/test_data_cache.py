import pandas as pd

from app.data.cache import DailyBarCache
from app.data.provider_factory import CachedAshareDataProvider


def _daily_bars(symbol: str = "000001") -> pd.DataFrame:
    index = pd.MultiIndex.from_product(
        [[symbol], pd.date_range("2024-01-01", periods=2)],
        names=["symbol", "date"],
    )
    return pd.DataFrame(
        {
            "open": [10.0, 10.2],
            "high": [10.5, 10.4],
            "low": [9.8, 10.0],
            "close": [10.3, 10.1],
            "volume": [1000, 1200],
            "amount": [10300, 12120],
        },
        index=index,
    )


def test_daily_bar_cache_round_trips_daily_bars(tmp_path):
    cache = DailyBarCache(str(tmp_path))
    data = _daily_bars()

    cache.write("fixture", "000001", "2024-01-01", "2024-01-02", data)
    loaded = cache.read("fixture", "000001", "2024-01-01", "2024-01-02")

    assert loaded is not None
    assert list(loaded.index.names) == ["symbol", "date"]
    assert loaded["close"].tolist() == [10.3, 10.1]


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def get_universe(self, universe_name: str, date: str) -> list[str]:
        return ["000001"]

    def get_daily_bars(self, symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        self.calls += 1
        return _daily_bars(symbols[0])


def test_cached_provider_uses_cache_after_first_fetch(tmp_path):
    provider = CountingProvider()
    cached = CachedAshareDataProvider(provider, "fake", DailyBarCache(str(tmp_path)))

    first = cached.get_daily_bars(["000001"], "2024-01-01", "2024-01-02")
    second = cached.get_daily_bars(["000001"], "2024-01-01", "2024-01-02")

    assert provider.calls == 1
    assert cached.cache_misses == 1
    assert cached.cache_hits == 1
    assert first["close"].tolist() == second["close"].tolist()
