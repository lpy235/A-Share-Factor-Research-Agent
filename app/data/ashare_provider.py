from __future__ import annotations

from typing import Protocol

import pandas as pd

from app.market_data.sources.akshare_raw import AkshareRawDataSource


class DailyBarRawSource(Protocol):
    def fetch_daily_bars(
        self, symbols: list[str], start_date: str, end_date: str
    ) -> pd.DataFrame: ...


class AkshareAshareDataProvider:
    """Compatibility adapter for the legacy research provider interface.

    New warehouse ingestion should use ``AkshareRawDataSource`` directly. This
    adapter remains only while research runs still expect a MultiIndex frame.
    """

    def __init__(self, source: DailyBarRawSource | None = None) -> None:
        self.source = source or AkshareRawDataSource()

    def get_universe(self, universe_name: str, date: str) -> list[str]:
        del universe_name, date
        return ["000001", "000002", "600000", "600519", "300750"]

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        raw_bars = self.source.fetch_daily_bars(symbols, start_date, end_date)
        if raw_bars.empty:
            return _empty_daily_bars()
        frame = raw_bars.rename(columns={"trade_date": "date"}).copy()
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index(["symbol", "date"])[
            ["open", "high", "low", "close", "volume", "amount"]
        ].sort_index()


def _empty_daily_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume", "amount"],
        index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
    )
