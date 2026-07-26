import pandas as pd

import app.market_data.ingestion as ingestion_module
from app.market_data.catalog import DataCatalog
from app.market_data.ingestion import BackfillService, CorporateActionBackfillService
from app.market_data.quality import QualityGateService
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


class BatchFailureSource(FakeSource):
    """Simulates a batch transport failure with one genuinely broken symbol."""

    def fetch_daily_bars(self, symbols, start_date, end_date):
        if len(symbols) > 1:
            raise TimeoutError("batch transport failure")
        if symbols == ["000002.SZ"]:
            raise ValueError("malformed source response")
        return super().fetch_daily_bars(symbols, start_date, end_date)


class RecoveringSource(FakeSource):
    def __init__(self) -> None:
        self.calls = 0

    def fetch_daily_bars(self, symbols, start_date, end_date):
        self.calls += 1
        if self.calls < 3:
            raise TimeoutError("proxy temporarily unavailable")
        return super().fetch_daily_bars(symbols, start_date, end_date)


class CorporateActionSource:
    source_name = "cninfo_fixture"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_cninfo_corporate_actions_for_symbol(self, symbol, start_date, end_date):
        self.calls.append(symbol)
        return pd.DataFrame(
            {
                "symbol": [symbol],
                "ex_date": ["2020-07-01"],
                "action_type": ["cash_dividend"],
                "per_10_shares": [1.0],
            }
        )


class RecoveringCorporateActionSource(CorporateActionSource):
    def __init__(self) -> None:
        super().__init__()
        self.failed_once = False

    def fetch_cninfo_corporate_actions_for_symbol(self, symbol, start_date, end_date):
        self.calls.append(symbol)
        if symbol == "600000.SH" and not self.failed_once:
            self.failed_once = True
            raise TimeoutError("temporary CNInfo outage")
        return pd.DataFrame(
            {
                "symbol": [symbol],
                "ex_date": ["2020-07-01"],
                "action_type": ["cash_dividend"],
                "per_10_shares": [1.0],
            }
        )


def _published_parent_with_master(catalog: DataCatalog, store: MarketDataStore) -> str:
    parent = catalog.create_draft(source="parent_fixture", as_of_date="2020-01-31")
    store.write_raw_daily_bars(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600000.SH"], "trade_date": ["2020-01-02", "2020-01-02"],
                "open": [10.0, 20.0], "high": [10.5, 20.5], "low": [9.8, 19.8],
                "close": [10.2, 20.2], "volume": [1000.0, 2000.0], "amount": [10200.0, 40400.0],
            }
        ),
        data_version=parent.version_id,
        source="parent_fixture",
    )
    store.write_security_master(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600000.SH"], "exchange": ["SZ", "SH"],
                "security_name": ["SZ", "SH"], "listing_date": ["1991-04-03", "1999-11-10"],
            }
        ),
        data_version=parent.version_id,
        source="parent_fixture",
    )
    store.write_trading_calendar(
        pd.DataFrame({"exchange": ["CN"], "trade_date": ["2020-01-02"], "is_trading_day": [True]}),
        data_version=parent.version_id,
        source="parent_fixture",
    )
    catalog.publish(parent.version_id, manifest={})
    return parent.version_id


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


def test_backfill_isolates_a_batch_failure_to_the_actual_bad_symbol(tmp_path):
    catalog = DataCatalog(tmp_path)
    store = MarketDataStore(tmp_path)
    service = BackfillService(catalog, store, BatchFailureSource(), max_retries=0)

    result = service.run("2020-01-01", "2020-01-31", batch_size=2)

    errors = catalog.list_ingest_errors(result.ingest_run_id)
    stored = store.read_raw_daily_bars(result.data_version, "2020-01-01", "2020-01-31")
    assert result.status == "completed_with_errors"
    assert [error.symbol for error in errors] == ["000002.SZ"]
    assert errors[0].error_message == "malformed source response"
    assert sorted(stored["symbol"].unique()) == ["000001.SZ", "600000.SH", "600519.SH"]


def test_backfill_uses_increasing_delay_between_transient_source_retries(tmp_path, monkeypatch):
    delays: list[float] = []
    monkeypatch.setattr(ingestion_module.time, "sleep", delays.append)
    service = BackfillService(DataCatalog(tmp_path), MarketDataStore(tmp_path), RecoveringSource(), max_retries=2)

    result = service.run("2020-01-01", "2020-01-31", batch_size=4)

    assert result.status == "completed"
    assert delays == [1.0, 2.0]


def test_corporate_action_backfill_recovers_replayed_batch_and_publishes_child(tmp_path):
    catalog = DataCatalog(tmp_path)
    store = MarketDataStore(tmp_path)
    parent_version_id = _published_parent_with_master(catalog, store)
    source = CorporateActionSource()
    service = CorporateActionBackfillService(catalog, store, source, max_retries=0)

    first = service.run(
        parent_version_id=parent_version_id,
        start_date="2020-01-01",
        end_date="2020-12-31",
        batch_size=1,
        stop_after_batches=1,
    )
    assert first.status == "paused"
    assert catalog.list_ingest_symbol_progress(first.ingest_run_id)[0].symbol == "000001.SZ"

    # Simulate a crash after a Parquet write but before its DuckDB checkpoint.
    replay_child = catalog.create_draft(source="cninfo_fixture", as_of_date="2020-12-31")
    replay_run = catalog.create_ingest_run(
        replay_child.version_id,
        parent_version_id=parent_version_id,
        start_date="2020-01-01",
        end_date="2020-12-31",
        batch_size=1,
        symbols=["000001.SZ", "600000.SH"],
    )
    store.write_corporate_actions(
        source.fetch_cninfo_corporate_actions_for_symbol("000001.SZ", "2020-01-01", "2020-12-31"),
        data_version=replay_child.version_id,
        source=source.source_name,
    )

    resumed = service.resume(replay_run.ingest_run_id)
    actions = store.read_corporate_actions(replay_child.version_id)
    assert resumed.status == "completed"
    assert not actions.duplicated(["symbol", "ex_date", "action_type"]).any()
    assert len(catalog.list_ingest_symbol_progress(replay_run.ingest_run_id)) == 2

    published = service.publish(replay_run.ingest_run_id)
    manifest = catalog.get_manifest(published.data_version)["manifest"]
    assert published.status == "published"
    assert manifest["parent_version_id"] == parent_version_id
    assert manifest["corporate_actions_source"] == source.source_name


def test_corporate_action_backfill_retries_only_failed_symbols_and_keeps_failure_history(tmp_path):
    catalog = DataCatalog(tmp_path)
    store = MarketDataStore(tmp_path)
    parent_version_id = _published_parent_with_master(catalog, store)
    source = RecoveringCorporateActionSource()
    service = CorporateActionBackfillService(catalog, store, source, max_retries=0)

    first = service.run(
        parent_version_id=parent_version_id,
        start_date="2020-01-01",
        end_date="2020-12-31",
        batch_size=2,
    )
    recovered = service.resume(first.ingest_run_id)
    published = service.publish(recovered.ingest_run_id)
    progress = catalog.list_ingest_symbol_progress(recovered.ingest_run_id)

    assert first.status == "completed_with_errors"
    assert recovered.status == "completed"
    assert published.status == "published"
    assert source.calls == ["000001.SZ", "600000.SH", "600000.SH"]
    assert [item.status for item in progress] == ["completed", "completed"]
    assert len(catalog.list_ingest_errors(recovered.ingest_run_id)) == 1


def test_corporate_action_child_reads_reference_tables_from_a_parent_chain(tmp_path):
    catalog = DataCatalog(tmp_path)
    store = MarketDataStore(tmp_path)
    base_version_id = _published_parent_with_master(catalog, store)
    intermediate = catalog.create_draft(source="daily_delta", as_of_date="2020-02-01")
    catalog.publish(intermediate.version_id, manifest={"parent_version_id": base_version_id})

    service = CorporateActionBackfillService(catalog, store, CorporateActionSource(), max_retries=0)
    completed = service.run(
        parent_version_id=intermediate.version_id,
        start_date="2020-01-01",
        end_date="2020-12-31",
        batch_size=2,
    )
    published = service.publish(completed.ingest_run_id)

    assert completed.status == "completed"
    assert published.status == "published"
    assert catalog.get_manifest(published.data_version)["manifest"]["parent_version_id"] == intermediate.version_id


def test_backfill_publishes_only_when_quality_gate_passes(tmp_path):
    catalog = DataCatalog(tmp_path)
    service = BackfillService(
        catalog,
        MarketDataStore(tmp_path),
        FakeSource(),
        quality_gate=QualityGateService(catalog),
        expected_trading_dates=["2020-01-02"],
    )

    result = service.run("2020-01-01", "2020-01-31", batch_size=2)

    assert result.status == "published"
    assert catalog.get_version(result.data_version).status == "published"
    assert service.resume(result.ingest_run_id).status == "published"


def test_backfill_keeps_draft_when_failed_symbol_ratio_exceeds_threshold(tmp_path):
    catalog = DataCatalog(tmp_path)
    service = BackfillService(
        catalog,
        MarketDataStore(tmp_path),
        FlakySource(),
        max_retries=0,
        quality_gate=QualityGateService(catalog),
        expected_trading_dates=["2020-01-02"],
        max_failed_symbol_ratio=0.0,
    )

    result = service.run("2020-01-01", "2020-01-31", batch_size=1)

    assert result.status == "quality_failed"
    assert catalog.get_version(result.data_version).status == "draft"
