from __future__ import annotations

from typing import Protocol

import pandas as pd


class SourceCapabilityError(RuntimeError):
    """Raised when a source does not expose a required raw-data domain."""


class RawMarketDataSource(Protocol):
    source_name: str

    def list_securities(self, as_of_date: str) -> pd.DataFrame: ...

    def fetch_daily_bars(
        self, symbols: list[str], start_date: str, end_date: str
    ) -> pd.DataFrame: ...

    def fetch_corporate_actions(self, start_date: str, end_date: str) -> pd.DataFrame: ...

    def fetch_calendar(self, start_date: str, end_date: str) -> pd.DataFrame: ...

    def fetch_security_status(self, start_date: str, end_date: str) -> pd.DataFrame: ...
