from __future__ import annotations

import math

import pandas as pd


RAW_DAILY_BAR_COLUMNS = (
    "symbol",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
)
LINEAGE_COLUMNS = ("source", "ingested_at", "data_version", "adjustment")
EVENT_LINEAGE_COLUMNS = ("source", "ingested_at", "data_version")


def validate_raw_daily_bars(frame: pd.DataFrame) -> pd.DataFrame:
    """Return normalized raw daily bars after enforcing the warehouse contract."""
    missing = set(RAW_DAILY_BAR_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"raw daily bars missing required columns: {sorted(missing)}")
    supplied_lineage = set(LINEAGE_COLUMNS) & set(frame.columns)
    if supplied_lineage:
        raise ValueError("caller-supplied lineage columns are not allowed")

    bars = frame.loc[:, RAW_DAILY_BAR_COLUMNS].copy()
    bars["symbol"] = bars["symbol"].astype("string")
    if bars["symbol"].isna().any() or bars["symbol"].str.strip().eq("").any():
        raise ValueError("symbol must be non-empty")

    bars["trade_date"] = pd.to_datetime(bars["trade_date"], errors="coerce")
    if bars["trade_date"].isna().any():
        raise ValueError("trade_date must be a valid date")
    if bars.duplicated(["symbol", "trade_date"]).any():
        raise ValueError("duplicate raw daily bar keys")

    numeric_columns = ("open", "high", "low", "close", "volume", "amount")
    for column in numeric_columns:
        bars[column] = pd.to_numeric(bars[column], errors="coerce")
    if bars.loc[:, numeric_columns].isna().any().any():
        raise ValueError("raw daily bars contain non-numeric values")
    if not bars.loc[:, numeric_columns].map(math.isfinite).all().all():
        raise ValueError("raw daily bars contain non-finite values")
    if (bars.loc[:, ("open", "high", "low", "close")] <= 0).any().any():
        raise ValueError("raw daily bar prices must be positive")
    if (bars.loc[:, ("volume", "amount")] < 0).any().any():
        raise ValueError("volume and amount must be non-negative")

    price_high = bars.loc[:, ("open", "low", "close")].max(axis=1)
    price_low = bars.loc[:, ("open", "high", "close")].min(axis=1)
    if (bars["high"] < price_high).any() or (bars["low"] > price_low).any():
        raise ValueError("invalid OHLC bounds")
    return bars


def validate_event_table(
    frame: pd.DataFrame, *, required_columns: tuple[str, ...], natural_key: tuple[str, ...]
) -> pd.DataFrame:
    missing = set(required_columns) - set(frame.columns)
    if missing:
        raise ValueError(f"event table missing required columns: {sorted(missing)}")
    supplied_lineage = set(EVENT_LINEAGE_COLUMNS) & set(frame.columns)
    if supplied_lineage:
        raise ValueError("caller-supplied lineage columns are not allowed")
    event_frame = frame.copy()
    if event_frame.loc[:, natural_key].isna().any().any():
        raise ValueError("event table natural key must not contain nulls")
    if event_frame.duplicated(list(natural_key)).any():
        raise ValueError("duplicate event table natural keys")
    return event_frame
