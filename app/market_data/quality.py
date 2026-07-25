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
        manifest_context: dict | None = None,
        reference_tables: dict[str, pd.DataFrame] | None = None,
    ) -> DataVersion:
        checks = self.evaluate_raw_daily_bars(
            bars,
            expected_trading_dates,
            failed_symbol_count=failed_symbol_count,
            total_symbol_count=total_symbol_count,
            max_failed_symbol_ratio=max_failed_symbol_ratio,
        )
        checks.extend(
            self.evaluate_reference_tables(
                reference_tables or {}, expected_trading_dates=expected_trading_dates
            )
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
            manifest={**(manifest_context or {}), "quality_checks": [asdict(check) for check in checks]},
        )

    def evaluate_reference_tables(
        self, tables: dict[str, pd.DataFrame], *, expected_trading_dates: Iterable[str]
    ) -> list[QualityCheck]:
        """Check optional reference-table contracts before publishing a version.

        Security master and trading calendar are required for a production
        baseline, but are warnings for the current bars-only CSV entry point.
        Once provided, malformed reference data is a hard publication failure.
        """
        checks: list[QualityCheck] = []
        security_master = tables.get("security_master")
        calendar = tables.get("trading_calendar")
        status = tables.get("security_status")
        actions = tables.get("corporate_actions")
        checks.append(self._optional_table_check("security_master", security_master, self._security_master_invalid))
        checks.append(
            self._optional_table_check(
                "trading_calendar",
                calendar,
                lambda frame: self._calendar_invalid(frame, expected_trading_dates),
            )
        )
        checks.append(self._optional_table_check("security_status", status, self._security_status_invalid))
        checks.append(self._optional_table_check("corporate_actions", actions, self._corporate_actions_invalid))
        if security_master is not None and status is not None:
            master_symbols = set(security_master.get("symbol", pd.Series(dtype="string")).dropna().astype(str))
            status_symbols = set(status.get("symbol", pd.Series(dtype="string")).dropna().astype(str))
            unknown = len(status_symbols - master_symbols)
            checks.append(QualityCheck("security_status_master_coverage", unknown == 0, unknown))
        return checks

    @staticmethod
    def _optional_table_check(name: str, frame: pd.DataFrame | None, validator) -> QualityCheck:
        if frame is None:
            return QualityCheck(f"{name}_contract", True, 0, severity="warning")
        invalid = validator(frame)
        return QualityCheck(f"{name}_contract", invalid == 0, invalid)

    @staticmethod
    def _security_master_invalid(frame: pd.DataFrame) -> int:
        required = {"symbol", "exchange", "security_name", "listing_date"}
        if required - set(frame.columns):
            return len(frame) or 1
        invalid = frame.loc[:, sorted(required)].isna().any(axis=1)
        invalid |= frame["symbol"].astype("string").str.strip().eq("")
        listing = pd.to_datetime(frame["listing_date"], errors="coerce")
        invalid |= listing.isna()
        invalid |= frame.duplicated(["symbol"], keep=False)
        if "delisting_date" in frame:
            delisting = pd.to_datetime(frame["delisting_date"], errors="coerce")
            invalid |= delisting.notna() & (delisting < listing)
        return int(invalid.sum())

    @staticmethod
    def _calendar_invalid(frame: pd.DataFrame, expected_trading_dates: Iterable[str]) -> int:
        required = {"trade_date", "is_trading_day"}
        if required - set(frame.columns):
            return len(frame) or 1
        dates = pd.to_datetime(frame["trade_date"], errors="coerce")
        invalid = dates.isna() | frame["is_trading_day"].isna()
        if "exchange" in frame:
            invalid |= frame.duplicated(["exchange", "trade_date"], keep=False)
        else:
            invalid |= frame.duplicated(["trade_date"], keep=False)
        actual = set(dates[frame["is_trading_day"].astype(bool)].dropna().dt.normalize())
        expected = set(pd.to_datetime(list(expected_trading_dates)).normalize())
        return int(invalid.sum()) + len(expected - actual)

    @staticmethod
    def _security_status_invalid(frame: pd.DataFrame) -> int:
        required = {"symbol", "trade_date", "is_st", "is_suspended"}
        if required - set(frame.columns):
            return len(frame) or 1
        invalid = frame.loc[:, sorted(required)].isna().any(axis=1)
        invalid |= pd.to_datetime(frame["trade_date"], errors="coerce").isna()
        invalid |= frame.duplicated(["symbol", "trade_date"], keep=False)
        invalid |= ~frame["is_st"].isin([True, False])
        invalid |= ~frame["is_suspended"].isin([True, False])
        return int(invalid.sum())

    @staticmethod
    def _corporate_actions_invalid(frame: pd.DataFrame) -> int:
        required = {"symbol", "ex_date", "action_type"}
        if required - set(frame.columns):
            return len(frame) or 1
        invalid = frame.loc[:, sorted(required)].isna().any(axis=1)
        invalid |= pd.to_datetime(frame["ex_date"], errors="coerce").isna()
        invalid |= frame["action_type"].astype("string").str.strip().eq("")
        invalid |= frame.duplicated(["symbol", "ex_date", "action_type"], keep=False)
        return int(invalid.sum())

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
