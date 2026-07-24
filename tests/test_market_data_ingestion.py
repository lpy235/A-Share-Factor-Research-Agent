import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.ingestion import BackfillService
from app.market_data.store import MarketDataStore


class FakeSource:
    source_name = "fixture"

    def list_securities(self, as_of_date):
        return pd.DataFrame({"symbol": ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH"]})

    def fetch_daily_bars(self, symbols, start_date, end_date):
        return pd.DataFrame(
            {
                "symbol": symbols,
                "trade_date": ["2020-01-02"] * len(symbols),
                "open": [10.0] * len(symbols),
                "high": [10.5] * len(symbols),
                "low": [9.9] * len(symbols),
                "close": [10.3] * len(symbols),
                "volume": [1000.0] * len(symbols),
                "amount": [10300.0] * len(symbols),
            }
        )


class FlakySource(FakeSource):
    def __init__(self) -> None:
        self.calls = 0

    def fetch_daily_bars(self, symbols, start_date, end_date):
        self.calls += 1
        if symbols == ["000002.SZ"]:
            raise TimeoutError("snapshot unavailable")
        return super().fetch_daily_bars(symbols, start_date, end_date)


def test_backfill_resumes_from_completed_symbol_batches(tmp_path):
    catalog = DataCatalog(tmp_path)
    store = MarketDataStore(tmp_path)
    service = BackfillService(catalog, store, FakeSource())

    first = service.run("2020-01-01", "2020-01-31", batch_size=2, stop_after_batches=1)
    second = service.resume(first.ingest_run_id)

    assert first.status == "paused"
    assert first.completed_symbol_count == 2
    assert second.status == "completed"
    assert second.completed_symbol_count == 4
    assert catalog.get_version(second.data_version).status == "draft"
    assert len(store.read_raw_daily_bars(second.data_version, "2020-01-01", "2020-01-31")) == 4


def test_backfill_retries_then_records_failed_symbols_and_continues(tmp_path):
    catalog = DataCatalog(tmp_path)
    service = BackfillService(catalog, MarketDataStore(tmp_path), FlakySource(), max_retries=1)

    result = service.run("2020-01-01", "2020-01-31", batch_size=1)

    assert result.status == "completed_with_errors"
    assert result.completed_symbol_count == 4
    errors = catalog.list_ingest_errors(result.ingest_run_id)
    assert errors[0].symbol == "000002.SZ"
    assert errors[0].attempt_count == 2
