from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.store import MarketDataStore


class WarehouseAshareDataProvider:
    """Read raw daily bars from one immutable, published market-data version."""

    def __init__(self, data_version: str, *, warehouse_root: str | Path = "market_data") -> None:
        self.catalog = DataCatalog(warehouse_root)
        self.store = MarketDataStore(warehouse_root)
        self.version = self.catalog.get_version(data_version)
        if self.version.status != "published":
            raise ValueError("warehouse data_version must be published")
        self.data_version = data_version
        self.diagnostics = {
            "provider": "warehouse",
            "data_version": data_version,
            "manifest_hash": self.version.manifest_hash,
            "source": self.version.source,
        }

    def get_universe(self, universe_name: str, date: str) -> list[str]:
        del universe_name
        bars = self.store.read_effective_raw_daily_bars(
            self.catalog, self.data_version, "1900-01-01", date
        )
        return sorted(bars["symbol"].unique().tolist())

    def get_daily_bars(
        self, symbols: list[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        bars = self.store.read_effective_raw_daily_bars(
            self.catalog, self.data_version, start_date, end_date
        )
        bars = bars.loc[bars["symbol"].isin(symbols)].copy()
        if bars.empty:
            return _empty_daily_bars()
        bars = bars.rename(columns={"trade_date": "date"})
        return bars.set_index(["symbol", "date"])[
            ["open", "high", "low", "close", "volume", "amount"]
        ].sort_index()


def _empty_daily_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume", "amount"],
        index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
    )
