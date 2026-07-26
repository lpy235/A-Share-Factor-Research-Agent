import pandas as pd
import pytest

import app.market_data.sources.akshare_sina_hs as akshare_sina_hs_module
from app.market_data.sources.akshare_raw import AkshareRawDataSource
from app.market_data.sources.akshare_sina_hs import AkshareSinaHsRawDataSource
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


class FakeAkshareSinaClient:
    def __init__(self) -> None:
        self.daily_calls: list[dict] = []

    @staticmethod
    def stock_info_a_code_name() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "code": ["000001", "300001", "600000", "688001", "200001", "920001"],
                "name": ["SZ Main", "SZ ChiNext", "SH Main", "STAR", "SZ B", "Beijing"],
            }
        )

    def stock_zh_a_daily(self, **kwargs) -> pd.DataFrame:
        self.daily_calls.append(kwargs)
        return pd.DataFrame(
            {
                "date": ["2020-01-02"],
                "open": [10.0],
                "high": [10.5],
                "low": [9.9],
                "close": [10.3],
                "volume": [1000.0],
                "amount": [10300.0],
            }
        )

    @staticmethod
    def tool_trade_date_hist_sina() -> pd.DataFrame:
        return pd.DataFrame({"trade_date": ["2020-01-01", "2020-01-02", "2020-01-03"]})

    @staticmethod
    def stock_info_sh_name_code(symbol: str) -> pd.DataFrame:
        del symbol
        return pd.DataFrame({"证券代码": ["600000", "688001"], "证券简称": ["SH Main", "STAR"], "上市日期": ["1999-11-10", "2020-01-01"]})

    @staticmethod
    def stock_info_sz_name_code() -> pd.DataFrame:
        return pd.DataFrame({"A股代码": ["000001", "300001"], "A股简称": ["SZ Main", "SZ ChiNext"], "A股上市日期": ["1991-04-03", "2020-01-01"]})

    @staticmethod
    def stock_info_sh_delist(symbol: str) -> pd.DataFrame:
        del symbol
        return pd.DataFrame({"公司代码": ["600001", "900001"], "公司简称": ["SH Delist", "SH B"], "上市日期": ["1998-01-22", "1999-01-01"], "暂停上市日期": ["2024-01-01", "2024-01-01"]})

    @staticmethod
    def stock_info_sz_delist(symbol: str) -> pd.DataFrame:
        del symbol
        return pd.DataFrame({"证券代码": ["000004", "200001"], "证券简称": ["SZ Delist", "SZ B"], "上市日期": ["1990-12-01", "1999-01-01"], "终止上市日期": ["2024-02-01", "2024-02-01"]})


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


def test_akshare_sina_hs_source_limits_universe_and_normalizes_raw_bars():
    client = FakeAkshareSinaClient()
    source = AkshareSinaHsRawDataSource(client=client)

    securities = source.list_securities("2020-01-31")
    bars = source.fetch_daily_bars(["000001.SZ", "600000.SH"], "2020-01-01", "2020-01-31")
    calendar = source.fetch_calendar("2020-01-02", "2020-01-02")

    assert securities["symbol"].tolist() == ["000001.SZ", "300001.SZ", "600000.SH", "688001.SH"]
    assert [call["symbol"] for call in client.daily_calls] == ["sz000001", "sh600000"]
    assert all(call["adjust"] == "" for call in client.daily_calls)
    assert list(bars.columns) == [
        "symbol", "trade_date", "open", "high", "low", "close", "volume", "amount",
    ]
    assert bars["symbol"].tolist() == ["000001.SZ", "600000.SH"]
    assert calendar.to_dict("records") == [
        {"exchange": "CN", "trade_date": pd.Timestamp("2020-01-02"), "is_trading_day": True}
    ]


def test_akshare_sina_hs_source_can_include_delisted_a_shares_and_build_master():
    source = AkshareSinaHsRawDataSource(client=FakeAkshareSinaClient(), include_delisted=True)

    securities = source.list_securities("2020-01-31")
    master = source.fetch_security_master("2020-01-31")

    assert set(securities["symbol"]) == {"000001.SZ", "000004.SZ", "300001.SZ", "600000.SH", "600001.SH", "688001.SH"}
    assert set(master["symbol"]) == {"000001.SZ", "000004.SZ", "300001.SZ", "600000.SH", "600001.SH", "688001.SH"}
    assert master.loc[master["symbol"].eq("600001.SH"), "market_exit_date"].item() == pd.Timestamp("2024-01-01")
    assert master.loc[master["symbol"].eq("600001.SH"), "market_exit_type"].item() == "suspension"
    assert master.loc[master["symbol"].eq("000004.SZ"), "market_exit_date"].item() == pd.Timestamp("2024-02-01")
    assert master.loc[master["symbol"].eq("000004.SZ"), "market_exit_type"].item() == "delisting"


def test_akshare_sina_hs_source_drops_zero_value_placeholder_rows():
    class PlaceholderClient(FakeAkshareSinaClient):
        def stock_zh_a_daily(self, **kwargs) -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "date": ["2024-11-05", "2024-11-06"],
                    "open": [10.0, 0.0], "high": [10.5, 0.0], "low": [9.9, 0.0],
                    "close": [10.2, 10.2], "volume": [1000.0, 0.0], "amount": [10200.0, 0.0],
                }
            )

    bars = AkshareSinaHsRawDataSource(client=PlaceholderClient()).fetch_daily_bars(
        ["688089.SH"], "2024-11-01", "2024-11-30"
    )

    assert bars["trade_date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-11-05"]


def test_akshare_sina_hs_source_falls_back_when_share_amount_endpoint_is_unavailable(monkeypatch):
    class MissingShareAmountClient(FakeAkshareSinaClient):
        def stock_zh_a_daily(self, **kwargs) -> pd.DataFrame:
            raise ValueError("No value to decode")

    fallback = pd.DataFrame(
        {
            "date": ["2020-10-29T00:00:00.000Z"], "open": [33.0], "high": [49.8], "low": [33.0],
            "close": [38.5], "volume": [40954922.0], "amount": [1584100687.0],
        }
    )
    monkeypatch.setattr(akshare_sina_hs_module, "_fetch_sina_price_history", lambda _: fallback)

    bars = AkshareSinaHsRawDataSource(client=MissingShareAmountClient()).fetch_daily_bars(
        ["689009.SH"], "2020-10-01", "2020-10-31"
    )

    assert bars.to_dict("records") == [
        {
            "symbol": "689009.SH", "trade_date": pd.Timestamp("2020-10-29"), "open": 33.0,
            "high": 49.8, "low": 33.0, "close": 38.5, "volume": 40954922.0, "amount": 1584100687.0,
        }
    ]


def test_akshare_sina_hs_source_normalizes_cninfo_corporate_actions():
    class CorporateActionClient(FakeAkshareSinaClient):
        @staticmethod
        def stock_dividend_cninfo(code):
            assert code == "600000"
            return pd.DataFrame({"除权日": ["2020-07-01"], "派息比例": [2.0], "送股比例": [1.0], "转增比例": [0.0]})

    actions = AkshareSinaHsRawDataSource(client=CorporateActionClient()).fetch_cninfo_corporate_actions_for_symbol(
        "600000.SH", "2020-01-01", "2020-12-31"
    )

    assert actions.to_dict("records") == [
        {"symbol": "600000.SH", "ex_date": pd.Timestamp("2020-07-01"), "action_type": "cash_dividend", "per_10_shares": 2.0},
        {"symbol": "600000.SH", "ex_date": pd.Timestamp("2020-07-01"), "action_type": "bonus_share", "per_10_shares": 1.0},
    ]


def test_akshare_sina_hs_source_uses_configured_timeout_for_live_cninfo_requests(monkeypatch):
    observed: dict[str, object] = {}

    def fake_fetch(code: str, *, timeout_seconds: float) -> pd.DataFrame:
        observed.update(code=code, timeout_seconds=timeout_seconds)
        return pd.DataFrame({"除权日": ["2020-07-01"], "派息比例": [2.0]})

    monkeypatch.setattr(akshare_sina_hs_module, "_fetch_cninfo_dividend_records", fake_fetch)

    actions = AkshareSinaHsRawDataSource(cninfo_timeout_seconds=7.5).fetch_cninfo_corporate_actions_for_symbol(
        "600000.SH", "2020-01-01", "2020-12-31"
    )

    assert observed == {"code": "600000", "timeout_seconds": 7.5}
    assert actions["action_type"].tolist() == ["cash_dividend"]


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


def test_csv_source_derives_calendar_from_its_daily_snapshot():
    source = CsvRawDataSource(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ"],
                "trade_date": ["2020-01-02"],
                "open": [10.0],
                "high": [10.5],
                "low": [9.9],
                "close": [10.3],
                "volume": [1000.0],
                "amount": [10300.0],
            }
        ),
        source="snapshot",
    )

    calendar = source.fetch_calendar("2020-01-02", "2020-01-02")

    assert bool(calendar.loc[0, "is_trading_day"]) is True


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
