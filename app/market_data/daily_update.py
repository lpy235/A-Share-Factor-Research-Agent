from __future__ import annotations

from dataclasses import dataclass

from app.market_data.catalog import DataCatalog
from app.market_data.quality import QualityGateService
from app.market_data.store import MarketDataStore


@dataclass(frozen=True)
class DailyUpdateResult:
    status: str
    data_version: str | None = None


class DailyUpdateService:
    """Creates one quality-gated child version for one trading-day delta."""

    def __init__(self, catalog: DataCatalog, store: MarketDataStore, source, quality_gate: QualityGateService) -> None:
        self.catalog = catalog
        self.store = store
        self.source = source
        self.quality_gate = quality_gate

    def run(self, trade_date: str, parent_version_id: str) -> DailyUpdateResult:
        parent = self.catalog.get_version(parent_version_id)
        if parent.status != "published":
            raise ValueError("parent data version must be published")
        if self.catalog.has_published_child(parent_version_id, trade_date):
            return DailyUpdateResult("already_published")
        calendar = self.source.fetch_calendar(trade_date, trade_date)
        if calendar.empty or not bool(calendar.iloc[0]["is_trading_day"]):
            return DailyUpdateResult("skipped")

        draft = self.catalog.create_draft(source=self.source.source_name, as_of_date=trade_date)
        symbols = self.source.list_securities(trade_date)["symbol"].astype(str).tolist()
        bars = self.source.fetch_daily_bars(symbols, trade_date, trade_date)
        if bars.empty:
            return DailyUpdateResult("incomplete", draft.version_id)
        self.store.write_raw_daily_bars(bars, data_version=draft.version_id, source=self.source.source_name)
        stored = self.store.read_raw_daily_bars(draft.version_id, trade_date, trade_date)
        try:
            self.quality_gate.publish_if_valid(
                draft.version_id,
                stored,
                expected_trading_dates=[trade_date],
                total_symbol_count=len(symbols),
                manifest_context={"parent_version_id": parent_version_id, "update_date": trade_date},
            )
        except ValueError:
            return DailyUpdateResult("quality_failed", draft.version_id)
        return DailyUpdateResult("published", draft.version_id)
