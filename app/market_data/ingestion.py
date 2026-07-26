from __future__ import annotations

import time
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
                    "reference_table_partitions": self._manifest_reference_table_partitions(run.data_version),
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

    def _manifest_reference_table_partitions(self, version_id: str) -> dict[str, list[str]]:
        if self._reference_table_partitions:
            return self._reference_table_partitions
        partitions: dict[str, list[str]] = {}
        for table_name in self.reference_tables:
            table_dir = self.store.paths.lake_dir / table_name / f"data_version={version_id}"
            paths = sorted(table_dir.rglob("*.parquet"))
            if paths:
                partitions[table_name] = [
                    str(path.relative_to(self.store.paths.root)) for path in paths
                ]
        return partitions

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
        error, _ = self._fetch_with_retries(run, symbols)
        if error is None:
            return False

        has_failures = False
        for symbol in symbols:
            symbol_error, attempt_count = self._fetch_with_retries(run, [symbol])
            if symbol_error is None:
                continue
            has_failures = True
            self.catalog.record_ingest_error(
                run.ingest_run_id,
                symbol=symbol,
                error_message=str(symbol_error),
                attempt_count=attempt_count,
            )
        return has_failures

    def _fetch_with_retries(self, run: IngestRun, symbols: list[str]) -> tuple[Exception | None, int]:
        for attempt_count in range(1, self.max_retries + 2):
            try:
                bars = self.source.fetch_daily_bars(symbols, run.start_date, run.end_date)
                if not bars.empty:
                    self.store.write_raw_daily_bars(
                        bars, data_version=run.data_version, source=self.source.source_name
                    )
                return None, attempt_count
            except Exception as exc:  # Source errors are retained as research evidence.
                if attempt_count == self.max_retries + 1:
                    return exc, attempt_count
                time.sleep(float(2 ** (attempt_count - 1)))
        raise AssertionError("retry loop must return on the final attempt")


class CorporateActionBackfillService:
    """Resumable, symbol-by-symbol CNInfo corporate-action ingestion."""

    def __init__(
        self,
        catalog: DataCatalog,
        store: MarketDataStore,
        source,
        *,
        max_retries: int = 2,
        quality_gate: QualityGateService | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self.catalog = catalog
        self.store = store
        self.source = source
        self.max_retries = max_retries
        self.quality_gate = quality_gate or QualityGateService(catalog)

    def run(
        self,
        *,
        parent_version_id: str,
        start_date: str,
        end_date: str,
        batch_size: int,
        stop_after_batches: int | None = None,
    ) -> IngestRun:
        self._require_published_parent(parent_version_id)
        master = self.store.read_effective_security_master(self.catalog, parent_version_id)
        if master.empty:
            raise ValueError("parent version has no security_master reference table")
        symbols = master["symbol"].dropna().astype(str).drop_duplicates().tolist()
        version = self.catalog.create_draft(source=self._source_name, as_of_date=end_date)
        run = self.catalog.create_ingest_run(
            version.version_id,
            parent_version_id=parent_version_id,
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            symbols=symbols,
        )
        return self._process(run, stop_after_batches)

    def resume(
        self,
        ingest_run_id: str,
        *,
        parent_version_id: str | None = None,
        stop_after_batches: int | None = None,
    ) -> IngestRun:
        run = self.catalog.get_ingest_run(ingest_run_id)
        if run.status == "published":
            return run
        if parent_version_id is not None:
            run = self.catalog.set_ingest_run_parent(ingest_run_id, parent_version_id)
        if run.parent_version_id is None:
            raise ValueError("resuming a corporate-action run requires parent_version_id")
        self._require_published_parent(run.parent_version_id)
        run = self._restore_missing_progress(run)
        run = self._retry_failed_symbols(run)
        return self._process(run, stop_after_batches)

    def publish(self, ingest_run_id: str) -> IngestRun:
        run = self.catalog.get_ingest_run(ingest_run_id)
        if run.status == "published":
            return run
        if run.parent_version_id is None:
            raise ValueError("corporate-action child version requires parent_version_id")
        if run.next_symbol_index != len(run.symbols):
            raise ValueError("corporate-action backfill is not complete")
        failed_symbols = self.catalog.list_failed_ingest_symbol_progress(ingest_run_id)
        if failed_symbols:
            raise ValueError("corporate-action backfill has unresolved symbol errors")
        self._require_published_parent(run.parent_version_id)
        child = self.catalog.get_version(run.data_version)
        if child.status != "draft":
            raise ValueError("corporate-action child version must be a draft before publication")

        actions = self.store.read_corporate_actions(run.data_version)
        master = self.store.read_effective_security_master(self.catalog, run.parent_version_id)
        calendar = self.store.read_effective_trading_calendar(self.catalog, run.parent_version_id)
        expected_dates = calendar.loc[
            calendar["is_trading_day"].astype(bool), "trade_date"
        ].dt.strftime("%Y-%m-%d").tolist()
        child_bars = self.store.read_raw_daily_bars(run.data_version, run.start_date, run.end_date)
        self.quality_gate.publish_reference_child_if_valid(
            run.data_version,
            expected_trading_dates=expected_dates,
            reference_tables={
                "security_master": master,
                "trading_calendar": calendar,
                "corporate_actions": actions,
            },
            child_raw_daily_bar_count=len(child_bars),
            manifest_context={
                "parent_version_id": run.parent_version_id,
                "corporate_actions_source": self._source_name,
                "corporate_actions_range": [run.start_date, run.end_date],
                "corporate_actions_ingest_run_id": run.ingest_run_id,
                "corporate_actions_symbol_count": len(run.symbols),
                "corporate_actions_event_count": len(actions),
            },
        )
        return self.catalog.update_ingest_run(
            run.ingest_run_id,
            next_symbol_index=run.next_symbol_index,
            status="published",
        )

    @property
    def _source_name(self) -> str:
        return str(getattr(self.source, "corporate_actions_source_name", self.source.source_name))

    def _process(self, run: IngestRun, stop_after_batches: int | None) -> IngestRun:
        completed_batches = 0
        index = run.next_symbol_index
        existing_keys = set(self._action_keys(self.store.read_corporate_actions(run.data_version)))
        while index < len(run.symbols):
            if stop_after_batches is not None and completed_batches >= stop_after_batches:
                return self.catalog.update_ingest_run(
                    run.ingest_run_id, next_symbol_index=index, status="paused"
                )
            symbols = list(run.symbols[index : index + run.batch_size])
            frames: list[pd.DataFrame] = []
            progress: list[tuple[str, int, str, int]] = []
            errors: list[tuple[str, str, int]] = []
            for offset, symbol in enumerate(symbols):
                try:
                    actions, attempt_count = self._fetch_with_retries(run, symbol)
                    frames.append(actions)
                    progress.append((symbol, index + offset, "completed", len(actions)))
                except Exception as exc:
                    errors.append((symbol, str(exc), self.max_retries + 1))
                    progress.append((symbol, index + offset, "failed", 0))

            existing_keys = self._write_new_actions(run, frames, existing_keys)
            index += len(symbols)
            completed_batches += 1
            run = self.catalog.complete_ingest_batch(
                run.ingest_run_id,
                next_symbol_index=index,
                symbol_progress=progress,
                errors=errors,
                status="running_with_errors" if errors else "running",
            )

        status = (
            "completed_with_errors"
            if self.catalog.list_failed_ingest_symbol_progress(run.ingest_run_id)
            else "completed"
        )
        return self.catalog.update_ingest_run(
            run.ingest_run_id, next_symbol_index=index, status=status
        )

    def _retry_failed_symbols(self, run: IngestRun) -> IngestRun:
        failed = self.catalog.list_failed_ingest_symbol_progress(run.ingest_run_id)
        if not failed:
            return run
        existing_keys = set(self._action_keys(self.store.read_corporate_actions(run.data_version)))
        frames: list[pd.DataFrame] = []
        progress: list[tuple[str, int, str, int]] = []
        errors: list[tuple[str, str, int]] = []
        for checkpoint in failed:
            try:
                actions, attempt_count = self._fetch_with_retries(run, checkpoint.symbol)
                frames.append(actions)
                progress.append(
                    (checkpoint.symbol, checkpoint.symbol_index, "completed", len(actions))
                )
            except Exception as exc:
                errors.append((checkpoint.symbol, str(exc), self.max_retries + 1))
                progress.append((checkpoint.symbol, checkpoint.symbol_index, "failed", 0))
        self._write_new_actions(run, frames, existing_keys)
        return self.catalog.complete_ingest_batch(
            run.ingest_run_id,
            next_symbol_index=run.next_symbol_index,
            symbol_progress=progress,
            errors=errors,
            status="running_with_errors" if errors else "running",
        )

    def _write_new_actions(
        self, run: IngestRun, frames: list[pd.DataFrame], existing_keys: set[tuple[str, str, str]]
    ) -> set[tuple[str, str, str]]:
        if not frames:
            return existing_keys
        batch_actions = pd.concat(frames, ignore_index=True)
        batch_actions = batch_actions.drop_duplicates(["symbol", "ex_date", "action_type"])
        new_actions = batch_actions.loc[
            [key not in existing_keys for key in self._action_keys(batch_actions)]
        ].copy()
        if not new_actions.empty:
            self.store.write_corporate_actions(
                new_actions, data_version=run.data_version, source=self._source_name
            )
            existing_keys.update(self._action_keys(new_actions))
        return existing_keys

    def _fetch_with_retries(self, run: IngestRun, symbol: str) -> tuple[pd.DataFrame, int]:
        for attempt_count in range(1, self.max_retries + 2):
            try:
                return (
                    self.source.fetch_cninfo_corporate_actions_for_symbol(
                        symbol, run.start_date, run.end_date
                    ),
                    attempt_count,
                )
            except Exception:
                if attempt_count == self.max_retries + 1:
                    raise
                time.sleep(float(2 ** (attempt_count - 1)))
        raise AssertionError("retry loop must return on the final attempt")

    def _require_published_parent(self, parent_version_id: str) -> None:
        if self.catalog.get_version(parent_version_id).status != "published":
            raise ValueError("parent version must be published")

    def _restore_missing_progress(self, run: IngestRun) -> IngestRun:
        """Backfill symbol checkpoints for runs created before per-symbol progress existed."""
        existing_symbols = {
            item.symbol for item in self.catalog.list_ingest_symbol_progress(run.ingest_run_id)
        }
        missing = [
            (symbol, index)
            for index, symbol in enumerate(run.symbols[: run.next_symbol_index])
            if symbol not in existing_symbols
        ]
        if not missing:
            return run
        actions = self.store.read_corporate_actions(run.data_version)
        action_counts = actions.groupby("symbol").size().to_dict() if not actions.empty else {}
        return self.catalog.complete_ingest_batch(
            run.ingest_run_id,
            next_symbol_index=run.next_symbol_index,
            symbol_progress=[
                (symbol, index, "completed", int(action_counts.get(symbol, 0)))
                for symbol, index in missing
            ],
            errors=[],
            status=run.status,
        )

    @staticmethod
    def _action_keys(frame: pd.DataFrame) -> list[tuple[str, str, str]]:
        if frame.empty:
            return []
        return [
            (str(symbol), pd.Timestamp(ex_date).strftime("%Y-%m-%d"), str(action_type))
            for symbol, ex_date, action_type in frame.loc[:, ["symbol", "ex_date", "action_type"]].itertuples(index=False)
        ]
