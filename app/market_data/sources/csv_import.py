from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.market_data.schemas import validate_raw_daily_bars
from app.market_data.sources.base import SourceCapabilityError


class CsvRawDataSource:
    """Controlled CSV entry point for authorized team-provided raw daily bars."""

    def __init__(self, daily_bars: pd.DataFrame, *, source: str) -> None:
        if not source.strip():
            raise ValueError("source metadata is required")
        self.source_name = source
        self._daily_bars = validate_raw_daily_bars(daily_bars)

    @classmethod
    def from_daily_bars_csv(cls, path: str | Path, *, source: str) -> "CsvRawDataSource":
        return cls(pd.read_csv(path), source=source)

    def list_securities(self, as_of_date: str) -> pd.DataFrame:
        del as_of_date
        return pd.DataFrame({"symbol": sorted(self._daily_bars["symbol"].unique())})

    def fetch_daily_bars(
        self, symbols: list[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        return self._daily_bars.loc[
            self._daily_bars["symbol"].isin(symbols)
            & self._daily_bars["trade_date"].between(start, end)
        ].copy()

    def fetch_corporate_actions(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("CSV source contains daily bars only")

    def fetch_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("CSV source contains daily bars only")

    def fetch_security_status(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("CSV source contains daily bars only")
