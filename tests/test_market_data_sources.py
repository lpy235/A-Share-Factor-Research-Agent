import pandas as pd
import pytest

from app.market_data.sources.akshare_raw import AkshareRawDataSource
from app.market_data.sources.csv_import import CsvRawDataSource
from app.data.ashare_provider import AkshareAshareDataProvider


class FakeAkshareClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def stock_zh_a_hist(self, **kwargs) -> pd.DataFrame:
        self.calls.append(kwargs)
        return pd.DataFrame(
            {
                "日期": ["2020-01-02"],
                "开盘": [10.0],
                "最高": [10.5],
                "最低": [9.9],
                "收盘": [10.3],
                "成交量": [1000.0],
                "成交额": [10300.0],
            }
        )


def test_akshare_source_requests_unadjusted_daily_bars():
    client = FakeAkshareClient()
    source = AkshareRawDataSource(client=client)

    bars = source.fetch_daily_bars(["000001.SZ"], "2020-01-01", "2020-01-31")

    assert client.calls[0]["adjust"] == ""
    assert list(bars.columns) == [
        "symbol",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    ]
    assert bars.loc[0, "symbol"] == "000001.SZ"


def test_csv_source_requires_source_metadata_and_unique_raw_keys(tmp_path):
    path = tmp_path / "daily_bars.csv"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ"],
            "trade_date": ["2020-01-02", "2020-01-02"],
            "open": [10.0, 10.0],
            "high": [10.5, 10.5],
            "low": [9.9, 9.9],
            "close": [10.3, 10.3],
            "volume": [1000.0, 1000.0],
            "amount": [10300.0, 10300.0],
        }
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="source metadata"):
        CsvRawDataSource.from_daily_bars_csv(path, source="")
    with pytest.raises(ValueError, match="duplicate"):
        CsvRawDataSource.from_daily_bars_csv(path, source="team_csv")


def test_legacy_provider_delegates_to_normalized_unadjusted_source():
    class FakeRawSource:
        def fetch_daily_bars(self, symbols, start_date, end_date):
            return pd.DataFrame(
                {
                    "symbol": symbols,
                    "trade_date": ["2020-01-02"],
                    "open": [10.0],
                    "high": [10.5],
                    "low": [9.9],
                    "close": [10.3],
                    "volume": [1000.0],
                    "amount": [10300.0],
                }
            )

    provider = AkshareAshareDataProvider(source=FakeRawSource())

    bars = provider.get_daily_bars(["000001.SZ"], "2020-01-01", "2020-01-31")

    assert bars.index.names == ["symbol", "date"]
    assert bars.loc[("000001.SZ", pd.Timestamp("2020-01-02")), "close"] == 10.3
