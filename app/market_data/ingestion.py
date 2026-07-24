from __future__ import annotations

from app.market_data.catalog import DataCatalog
from app.market_data.models import IngestRun
from app.market_data.sources.base import RawMarketDataSource
from app.market_data.store import MarketDataStore


class BackfillService:
    """Bounded, resumable ingestion of raw daily bars into a draft version."""

    def __init__(self, catalog: DataCatalog, store: MarketDataStore, source: RawMarketDataSource) -> None:
        self.catalog = catalog
        self.store = store
        self.source = source

    def run(
        self, start_date: str, end_date: str, *, batch_size: int, stop_after_batches: int | None = None
    ) -> IngestRun:
        symbols = self.source.list_securities(end_date)["symbol"].astype(str).tolist()
        version = self.catalog.create_draft(source=self.source.source_name, as_of_date=end_date)
        run = self.catalog.create_ingest_run(
            version.version_id, start_date=start_date, end_date=end_date, batch_size=batch_size, symbols=symbols
        )
        return self._process(run, stop_after_batches)

    def resume(self, ingest_run_id: str, *, stop_after_batches: int | None = None) -> IngestRun:
        run = self.catalog.get_ingest_run(ingest_run_id)
        if run.status == "completed":
            return run
        return self._process(run, stop_after_batches)

    def _process(self, run: IngestRun, stop_after_batches: int | None) -> IngestRun:
        completed_batches = 0
        index = run.next_symbol_index
        while index < len(run.symbols):
            if stop_after_batches is not None and completed_batches >= stop_after_batches:
                return self.catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=index, status="paused")
            symbols = list(run.symbols[index : index + run.batch_size])
            bars = self.source.fetch_daily_bars(symbols, run.start_date, run.end_date)
            if not bars.empty:
                self.store.write_raw_daily_bars(bars, data_version=run.data_version, source=self.source.source_name)
            index += len(symbols)
            completed_batches += 1
            run = self.catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=index, status="running")
        return self.catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=index, status="completed")
