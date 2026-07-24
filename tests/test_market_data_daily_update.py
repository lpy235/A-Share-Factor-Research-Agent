import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.daily_update import DailyUpdateService
from app.market_data.quality import QualityGateService
from app.market_data.store import MarketDataStore


class DailySource:
    source_name = "fixture"

    def __init__(self, is_trading_day: bool = True, has_bars: bool = True) -> None:
        self.is_trading_day = is_trading_day
        self.has_bars = has_bars
        self.fetch_calls = 0

    def list_securities(self, as_of_date):
        return pd.DataFrame({"symbol": ["000001.SZ"]})

    def fetch_calendar(self, start_date, end_date):
        return pd.DataFrame({"trade_date": [start_date], "is_trading_day": [self.is_trading_day]})

    def fetch_daily_bars(self, symbols, start_date, end_date):
        self.fetch_calls += 1
        if not self.has_bars:
            return pd.DataFrame()
        return pd.DataFrame(
            {"symbol": symbols, "trade_date": [start_date], "open": [10.0], "high": [10.5], "low": [9.9], "close": [10.3], "volume": [1000.0], "amount": [10300.0]}
        )


def _published_parent(catalog):
    draft = catalog.create_draft(source="fixture", as_of_date="2020-01-01")
    return catalog.publish(draft.version_id, manifest={"tables": {}})


def test_daily_update_skips_non_trading_day_without_source_request(tmp_path):
    catalog = DataCatalog(tmp_path)
    source = DailySource(is_trading_day=False)
    service = DailyUpdateService(catalog, MarketDataStore(tmp_path), source, QualityGateService(catalog))

    result = service.run("2020-01-02", _published_parent(catalog).version_id)

    assert result.status == "skipped"
    assert source.fetch_calls == 0


def test_daily_update_publishes_child_once_and_is_idempotent(tmp_path):
    catalog = DataCatalog(tmp_path)
    source = DailySource()
    service = DailyUpdateService(catalog, MarketDataStore(tmp_path), source, QualityGateService(catalog))
    parent = _published_parent(catalog)

    first = service.run("2020-01-02", parent.version_id)
    second = service.run("2020-01-02", parent.version_id)

    assert first.status == "published"
    assert second.status == "already_published"
    assert source.fetch_calls == 1


def test_daily_update_keeps_incomplete_data_as_draft(tmp_path):
    catalog = DataCatalog(tmp_path)
    source = DailySource(has_bars=False)
    service = DailyUpdateService(catalog, MarketDataStore(tmp_path), source, QualityGateService(catalog))

    result = service.run("2020-01-02", _published_parent(catalog).version_id)

    assert result.status == "incomplete"
    assert catalog.get_version(result.data_version).status == "draft"
