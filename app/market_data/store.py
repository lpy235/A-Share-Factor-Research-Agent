from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from app.market_data.paths import MarketDataPaths
from app.market_data.schemas import (
    LINEAGE_COLUMNS,
    RAW_DAILY_BAR_COLUMNS,
    validate_event_table,
    validate_raw_daily_bars,
)


class MarketDataStore:
    """Immutable, version-addressed Parquet storage for raw A-share market data."""

    def __init__(self, root: str | Path = "market_data") -> None:
        self.paths = MarketDataPaths(root)

    def write_raw_daily_bars(
        self, frame: pd.DataFrame, *, data_version: str, source: str
    ) -> list[Path]:
        if not data_version.strip():
            raise ValueError("data_version is required")
        if not source.strip():
            raise ValueError("source is required")

        bars = validate_raw_daily_bars(frame)
        if bars.empty:
            raise ValueError("raw daily bars must not be empty")
        bars["source"] = source
        bars["ingested_at"] = datetime.now(UTC).isoformat()
        bars["data_version"] = data_version
        bars["adjustment"] = "none"

        paths: list[Path] = []
        for year, partition in bars.groupby(bars["trade_date"].dt.year, sort=True):
            path = self.paths.raw_daily_bar_partition(data_version, int(year), _part_name())
            if path.exists():
                raise ValueError(f"raw daily bar partition is immutable: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            ordered = partition.loc[:, (*RAW_DAILY_BAR_COLUMNS, *LINEAGE_COLUMNS)]
            ordered.to_parquet(path, index=False, engine="pyarrow")
            paths.append(path)
        return paths

    def read_raw_daily_bars(
        self, data_version: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        if start > end:
            raise ValueError("start_date must not be after end_date")

        version_dir = self.paths.lake_dir / "raw_daily_bars" / f"data_version={data_version}"
        parquet_paths = sorted(version_dir.glob("year=*/part-*.parquet"))
        if not parquet_paths:
            return pd.DataFrame(columns=(*RAW_DAILY_BAR_COLUMNS, *LINEAGE_COLUMNS))
        # Read files individually: Hive-style path inference would otherwise add a
        # second data_version column that conflicts with the lineage column in file.
        bars = pd.concat(
            [pd.read_parquet(path, engine="pyarrow") for path in parquet_paths],
            ignore_index=True,
        )
        bars["trade_date"] = pd.to_datetime(bars["trade_date"])
        filtered = bars.loc[bars["trade_date"].between(start, end)].copy()
        return filtered.sort_values(["trade_date", "symbol"], ignore_index=True)

    def read_effective_raw_daily_bars(
        self, catalog, data_version: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Read a published child version together with all of its parent deltas."""
        version_chain = self._version_chain(catalog, data_version)
        frames = [self.read_raw_daily_bars(version_id, start_date, end_date) for version_id in version_chain]
        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame(columns=(*RAW_DAILY_BAR_COLUMNS, *LINEAGE_COLUMNS))
        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates(["symbol", "trade_date"], keep="last")
        return merged.sort_values(["trade_date", "symbol"], ignore_index=True)

    def read_corporate_actions(self, data_version: str) -> pd.DataFrame:
        actions = self._read_event_table("corporate_actions", data_version)
        if actions.empty:
            return pd.DataFrame(columns=("symbol", "ex_date", "action_type", *LINEAGE_COLUMNS))
        actions["ex_date"] = pd.to_datetime(actions["ex_date"])
        return actions.sort_values(["ex_date", "symbol", "action_type"], ignore_index=True)

    def read_effective_corporate_actions(self, catalog, data_version: str) -> pd.DataFrame:
        frames = [self.read_corporate_actions(version_id) for version_id in self._version_chain(catalog, data_version)]
        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame(columns=("symbol", "ex_date", "action_type", *LINEAGE_COLUMNS))
        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates(["symbol", "ex_date", "action_type"], keep="last")
        return merged.sort_values(["ex_date", "symbol", "action_type"], ignore_index=True)

    def read_security_master(self, data_version: str) -> pd.DataFrame:
        master = self._read_event_table("security_master", data_version)
        if master.empty:
            return pd.DataFrame(columns=("symbol", "exchange", "security_name", "listing_date", *LINEAGE_COLUMNS))
        master["listing_date"] = pd.to_datetime(master["listing_date"], errors="coerce")
        return master.sort_values("symbol", ignore_index=True)

    def read_trading_calendar(self, data_version: str) -> pd.DataFrame:
        calendar = self._read_event_table("trading_calendar", data_version)
        if calendar.empty:
            return pd.DataFrame(columns=("exchange", "trade_date", "is_trading_day", *LINEAGE_COLUMNS))
        calendar["trade_date"] = pd.to_datetime(calendar["trade_date"], errors="coerce")
        return calendar.sort_values(["trade_date", "exchange"], ignore_index=True)

    def read_security_status(self, data_version: str) -> pd.DataFrame:
        status = self._read_event_table("security_status", data_version)
        if status.empty:
            return pd.DataFrame(
                columns=("symbol", "trade_date", "is_st", "is_suspended", *LINEAGE_COLUMNS)
            )
        status["trade_date"] = pd.to_datetime(status["trade_date"], errors="coerce")
        return status.sort_values(["trade_date", "symbol"], ignore_index=True)

    def read_effective_security_master(self, catalog, data_version: str) -> pd.DataFrame:
        return self._read_effective_reference_table(
            catalog, data_version, self.read_security_master, ("symbol",)
        )

    def read_effective_trading_calendar(self, catalog, data_version: str) -> pd.DataFrame:
        return self._read_effective_reference_table(
            catalog, data_version, self.read_trading_calendar, ("exchange", "trade_date")
        )

    def read_effective_security_status(self, catalog, data_version: str) -> pd.DataFrame:
        return self._read_effective_reference_table(
            catalog, data_version, self.read_security_status, ("symbol", "trade_date")
        )

    def write_security_master(
        self, frame: pd.DataFrame, *, data_version: str, source: str
    ) -> Path:
        return self._write_event_table(
            "security_master",
            frame,
            data_version=data_version,
            source=source,
            required_columns=("symbol", "exchange", "security_name", "listing_date"),
            natural_key=("symbol",),
        )[0]

    def write_trading_calendar(
        self, frame: pd.DataFrame, *, data_version: str, source: str
    ) -> Path:
        return self._write_event_table(
            "trading_calendar",
            frame,
            data_version=data_version,
            source=source,
            required_columns=("exchange", "trade_date", "is_trading_day"),
            natural_key=("exchange", "trade_date"),
        )[0]

    def write_corporate_actions(
        self, frame: pd.DataFrame, *, data_version: str, source: str
    ) -> list[Path]:
        return self._write_event_table(
            "corporate_actions",
            frame,
            data_version=data_version,
            source=source,
            required_columns=("symbol", "ex_date", "action_type"),
            natural_key=("symbol", "ex_date", "action_type"),
            partition_date_column="ex_date",
        )

    def write_security_status(
        self, frame: pd.DataFrame, *, data_version: str, source: str
    ) -> list[Path]:
        return self._write_event_table(
            "security_status",
            frame,
            data_version=data_version,
            source=source,
            required_columns=("symbol", "trade_date", "is_st", "is_suspended"),
            natural_key=("symbol", "trade_date"),
            partition_date_column="trade_date",
        )

    def _write_event_table(
        self,
        table_name: str,
        frame: pd.DataFrame,
        *,
        data_version: str,
        source: str,
        required_columns: tuple[str, ...],
        natural_key: tuple[str, ...],
        partition_date_column: str | None = None,
    ) -> list[Path]:
        self._validate_lineage_arguments(data_version, source)
        events = validate_event_table(
            frame, required_columns=required_columns, natural_key=natural_key
        )
        if events.empty:
            raise ValueError(f"{table_name} must not be empty")
        if partition_date_column:
            events[partition_date_column] = pd.to_datetime(
                events[partition_date_column], errors="coerce"
            )
            if events[partition_date_column].isna().any():
                raise ValueError(f"{partition_date_column} must be a valid date")
            partitions = events.groupby(events[partition_date_column].dt.year, sort=True)
        else:
            partitions = [(None, events)]

        paths: list[Path] = []
        for year, partition in partitions:
            path = self.paths.table_partition(table_name, data_version, year=year, part_name=_part_name())
            if path.exists():
                raise ValueError(f"{table_name} partition is immutable: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            saved = partition.copy()
            saved["source"] = source
            saved["ingested_at"] = datetime.now(UTC).isoformat()
            saved["data_version"] = data_version
            saved.to_parquet(path, index=False, engine="pyarrow")
            paths.append(path)
        return paths

    def _read_event_table(self, table_name: str, data_version: str) -> pd.DataFrame:
        table_dir = self.paths.lake_dir / table_name / f"data_version={data_version}"
        parquet_paths = sorted(table_dir.rglob("part-*.parquet"))
        if not parquet_paths:
            return pd.DataFrame()
        return pd.concat([pd.read_parquet(path, engine="pyarrow") for path in parquet_paths], ignore_index=True)

    def _read_effective_reference_table(self, catalog, data_version: str, reader, natural_key: tuple[str, ...]) -> pd.DataFrame:
        frames = [reader(version_id) for version_id in self._version_chain(catalog, data_version)]
        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame()
        merged = pd.concat(frames, ignore_index=True)
        merged = merged.drop_duplicates(list(natural_key), keep="last")
        return merged.sort_values(list(natural_key), ignore_index=True)

    @staticmethod
    def _validate_lineage_arguments(data_version: str, source: str) -> None:
        if not data_version.strip():
            raise ValueError("data_version is required")
        if not source.strip():
            raise ValueError("source is required")

    @staticmethod
    def _version_chain(catalog, data_version: str) -> list[str]:
        chain: list[str] = []
        seen: set[str] = set()
        current = data_version
        while current:
            if current in seen:
                raise ValueError(f"data-version manifest cycle detected: {current}")
            seen.add(current)
            chain.append(current)
            manifest = catalog.get_manifest(current)
            current = manifest.get("manifest", {}).get("parent_version_id")
        return list(reversed(chain))


def _part_name() -> str:
    return f"part-{uuid4().hex}"
