from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.models import IngestRun
from app.market_data.quality import QualityGateService
from app.market_data.sources.base import RawMarketDataSource
from app.market_data.store import MarketDataStore


class BackfillService:
    """Bounded, resumable ingestion of raw daily bars into a draft version."""

    def __init__(
        self,
        catalog: DataCatalog,
        store: MarketDataStore,
        source: RawMarketDataSource,
        max_retries: int = 2,
        quality_gate: QualityGateService | None = None,
        expected_trading_dates: list[str] | None = None,
        max_failed_symbol_ratio: float = 0.0,
        manifest_context: dict | None = None,
        reference_tables: dict[str, pd.DataFrame] | None = None,
        required_reference_tables: bool = False,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if not 0 <= max_failed_symbol_ratio <= 1:
            raise ValueError("max_failed_symbol_ratio must be between zero and one")
        self.catalog = catalog
        self.store = store
        self.source = source
        self.max_retries = max_retries
        self.quality_gate = quality_gate
        self.expected_trading_dates = expected_trading_dates
        self.max_failed_symbol_ratio = max_failed_symbol_ratio
        self.manifest_context = manifest_context
        self.reference_tables = reference_tables or {}
        self.required_reference_tables = required_reference_tables
        self._reference_table_partitions: dict[str, list[str]] = {}

    def run(
        self, start_date: str, end_date: str, *, batch_size: int, stop_after_batches: int | None = None
    ) -> IngestRun:
        symbols = self.source.list_securities(end_date)["symbol"].astype(str).tolist()
        version = self.catalog.create_draft(source=self.source.source_name, as_of_date=end_date)
        self._write_reference_tables(version.version_id)
        run = self.catalog.create_ingest_run(
            version.version_id, start_date=start_date, end_date=end_date, batch_size=batch_size, symbols=symbols
        )
        return self._process(run, stop_after_batches)

    def resume(self, ingest_run_id: str, *, stop_after_batches: int | None = None) -> IngestRun:
        run = self.catalog.get_ingest_run(ingest_run_id)
        if run.status in {"completed", "completed_with_errors", "published", "quality_failed"}:
            return run
        return self._process(run, stop_after_batches)

    def _process(self, run: IngestRun, stop_after_batches: int | None) -> IngestRun:
        completed_batches = 0
        index = run.next_symbol_index
        while index < len(run.symbols):
            if stop_after_batches is not None and completed_batches >= stop_after_batches:
                return self.catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=index, status="paused")
            symbols = list(run.symbols[index : index + run.batch_size])
            error = self._fetch_and_write(run, symbols)
            index += len(symbols)
            completed_batches += 1
            status = "running_with_errors" if error else "running"
            run = self.catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=index, status=status)
        errors = self.catalog.list_ingest_errors(run.ingest_run_id)
        status = "completed_with_errors" if errors else "completed"
        run = self.catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=index, status=status)
        return self._publish_if_configured(run)

    def _publish_if_configured(self, run: IngestRun) -> IngestRun:
        if self.quality_gate is None or self.expected_trading_dates is None:
            return run
        errors = self.catalog.list_ingest_errors(run.ingest_run_id)
        bars = self.store.read_raw_daily_bars(run.data_version, run.start_date, run.end_date)
        try:
            self.quality_gate.publish_if_valid(
                run.data_version,
                bars,
                expected_trading_dates=self.expected_trading_dates,
                failed_symbol_count=len(errors),
                total_symbol_count=len(run.symbols),
                max_failed_symbol_ratio=self.max_failed_symbol_ratio,
                manifest_context={
                    **(self.manifest_context or {}),
                    "reference_table_partitions": self._reference_table_partitions,
                },
                reference_tables=self.reference_tables,
                required_reference_tables=self.required_reference_tables,
            )
        except ValueError:
            return self.catalog.update_ingest_run(
                run.ingest_run_id, next_symbol_index=run.next_symbol_index, status="quality_failed"
            )
        return self.catalog.update_ingest_run(
            run.ingest_run_id, next_symbol_index=run.next_symbol_index, status="published"
        )

    def _write_reference_tables(self, version_id: str) -> None:
        writers = {
            "security_master": self.store.write_security_master,
            "trading_calendar": self.store.write_trading_calendar,
            "security_status": self.store.write_security_status,
            "corporate_actions": self.store.write_corporate_actions,
        }
        for table_name, frame in self.reference_tables.items():
            if table_name not in writers:
                raise ValueError(f"unsupported reference table: {table_name}")
            written = writers[table_name](
                frame, data_version=version_id, source=self.source.source_name
            )
            paths = written if isinstance(written, list) else [written]
            self._reference_table_partitions[table_name] = [
                str(Path(path).relative_to(self.store.paths.root)) for path in paths
            ]

    def _fetch_and_write(self, run: IngestRun, symbols: list[str]) -> bool:
        for attempt_count in range(1, self.max_retries + 2):
            try:
                bars = self.source.fetch_daily_bars(symbols, run.start_date, run.end_date)
                if not bars.empty:
                    self.store.write_raw_daily_bars(
                        bars, data_version=run.data_version, source=self.source.source_name
                    )
                return False
            except Exception as exc:  # Source errors are retained as research evidence.
                if attempt_count == self.max_retries + 1:
                    for symbol in symbols:
                        self.catalog.record_ingest_error(
                            run.ingest_run_id,
                            symbol=symbol,
                            error_message=str(exc),
                            attempt_count=attempt_count,
                        )
                    return True
        return True
