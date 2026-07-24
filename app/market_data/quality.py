from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.models import DataVersion


@dataclass(frozen=True)
class QualityCheck:
    check_name: str
    passed: bool
    affected_count: int
    severity: str = "hard"


class QualityGateService:
    """Evaluates deterministic hard gates before a data version is published."""

    def __init__(self, catalog: DataCatalog) -> None:
        self.catalog = catalog

    def publish_if_valid(
        self,
        version_id: str,
        bars: pd.DataFrame,
        *,
        expected_trading_dates: Iterable[str],
        failed_symbol_count: int = 0,
        total_symbol_count: int = 0,
        max_failed_symbol_ratio: float = 0.0,
    ) -> DataVersion:
        checks = self.evaluate_raw_daily_bars(
            bars,
            expected_trading_dates,
            failed_symbol_count=failed_symbol_count,
            total_symbol_count=total_symbol_count,
            max_failed_symbol_ratio=max_failed_symbol_ratio,
        )
        for check in checks:
            self.catalog.record_quality_result(
                version_id,
                check_name=check.check_name,
                passed=check.passed,
                affected_count=check.affected_count,
                severity=check.severity,
            )
        failures = [check for check in checks if check.severity == "hard" and not check.passed]
        if failures:
            names = ", ".join(check.check_name for check in failures)
            raise ValueError(f"quality gates failed: {names}")
        return self.catalog.publish(
            version_id,
            manifest={"quality_checks": [asdict(check) for check in checks]},
        )

    def evaluate_raw_daily_bars(
        self,
        bars: pd.DataFrame,
        expected_trading_dates: Iterable[str],
        *,
        failed_symbol_count: int = 0,
        total_symbol_count: int = 0,
        max_failed_symbol_ratio: float = 0.0,
    ) -> list[QualityCheck]:
        required = {
            "symbol",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "source",
            "ingested_at",
            "data_version",
            "adjustment",
        }
        missing_columns = required - set(bars.columns)
        lineage_missing = (
            len(bars)
            if missing_columns
            else int(bars.loc[:, sorted(required)].isna().any(axis=1).sum())
        )
        duplicate_count = (
            len(bars) if {"symbol", "trade_date"} - set(bars.columns) else int(bars.duplicated(["symbol", "trade_date"]).sum())
        )
        ohlc_invalid = self._invalid_ohlc_count(bars)
        adjustment_invalid = (
            len(bars) if "adjustment" not in bars else int(bars["adjustment"].ne("none").sum())
        )
        actual_dates = set(pd.to_datetime(bars.get("trade_date", []), errors="coerce").dropna().dt.normalize())
        expected_dates = set(pd.to_datetime(list(expected_trading_dates)).normalize())
        calendar_missing = len(expected_dates - actual_dates)
        failed_ratio = failed_symbol_count / total_symbol_count if total_symbol_count else 0.0
        return [
            QualityCheck("raw_daily_bar_lineage", lineage_missing == 0, lineage_missing),
            QualityCheck("raw_daily_bar_uniqueness", duplicate_count == 0, duplicate_count),
            QualityCheck("raw_daily_bar_ohlc", ohlc_invalid == 0, ohlc_invalid),
            QualityCheck("raw_daily_bar_unadjusted", adjustment_invalid == 0, adjustment_invalid),
            QualityCheck("raw_daily_bar_calendar_coverage", calendar_missing == 0, calendar_missing),
            QualityCheck(
                "raw_daily_bar_failed_symbol_ratio",
                failed_ratio <= max_failed_symbol_ratio,
                failed_symbol_count,
            ),
        ]

    @staticmethod
    def _invalid_ohlc_count(bars: pd.DataFrame) -> int:
        required = {"open", "high", "low", "close"}
        if required - set(bars.columns):
            return len(bars)
        numeric = bars.loc[:, ["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
        invalid = numeric.isna().any(axis=1) | (numeric <= 0).any(axis=1)
        invalid |= numeric["high"] < numeric.loc[:, ["open", "low", "close"]].max(axis=1)
        invalid |= numeric["low"] > numeric.loc[:, ["open", "high", "close"]].min(axis=1)
        return int(invalid.sum())
