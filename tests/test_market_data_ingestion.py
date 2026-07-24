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
