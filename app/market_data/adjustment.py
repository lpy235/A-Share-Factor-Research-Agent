from __future__ import annotations

import numpy as np
import pandas as pd


PRICE_COLUMNS = ("open", "high", "low", "close")
EVENT_TYPES = ("cash_dividend", "bonus_share", "capitalization")


def apply_corporate_action_adjustment(
    bars: pd.DataFrame, actions: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int | str]]:
    """Derive backward total-return OHLC prices without changing raw bars.

    Each ex-date adjusts prior prices by the cash-and-share entitlement factor
    implied by the prior close. This preserves an ex-date total-return series
    while the source Parquet continues to store unadjusted market prices.
    """
    required_bar_columns = {"symbol", "trade_date", *PRICE_COLUMNS}
    missing_bar_columns = required_bar_columns - set(bars.columns)
    if missing_bar_columns:
        raise ValueError(f"price adjustment requires columns: {sorted(missing_bar_columns)}")

    adjusted = bars.copy()
    adjusted["trade_date"] = pd.to_datetime(adjusted["trade_date"], errors="raise").dt.normalize()
    diagnostics: dict[str, int | str] = {
        "price_adjustment_mode": "corporate_action_total_return",
        "event_count": 0,
        "applied_event_count": 0,
        "skipped_event_count": 0,
    }
    if adjusted.empty or actions.empty:
        return adjusted, diagnostics

    required_action_columns = {"symbol", "ex_date", "action_type", "per_10_shares"}
    missing_action_columns = required_action_columns - set(actions.columns)
    if missing_action_columns:
        raise ValueError(
            "corporate-action price adjustment requires columns: "
            f"{sorted(missing_action_columns)}"
        )

    research_symbols = set(adjusted["symbol"].astype(str))
    normalized = actions.loc[:, list(required_action_columns)].copy()
    normalized["symbol"] = normalized["symbol"].astype(str)
    normalized = normalized.loc[normalized["symbol"].isin(research_symbols)].copy()
    normalized["ex_date"] = pd.to_datetime(normalized["ex_date"], errors="coerce").dt.normalize()
    if normalized["ex_date"].isna().any():
        raise ValueError("corporate-action price adjustment requires valid ex_date values")
    unknown_types = set(normalized["action_type"].dropna().astype(str)) - set(EVENT_TYPES)
    if unknown_types:
        raise ValueError(f"unsupported corporate-action types: {sorted(unknown_types)}")

    start_date = adjusted["trade_date"].min()
    end_date = adjusted["trade_date"].max()
    normalized = normalized.loc[normalized["ex_date"].between(start_date, end_date)].copy()
    diagnostics["event_count"] = int(len(normalized))
    if normalized.empty:
        return adjusted, diagnostics

    normalized["per_10_shares"] = pd.to_numeric(normalized["per_10_shares"], errors="coerce")
    if normalized["per_10_shares"].isna().any() or normalized["per_10_shares"].lt(0).any():
        raise ValueError("corporate-action per_10_shares must be finite and non-negative")

    price_column_positions = [adjusted.columns.get_loc(column) for column in PRICE_COLUMNS]
    symbol_positions = adjusted.groupby(adjusted["symbol"].astype(str), sort=False).indices
    trade_dates = adjusted["trade_date"].to_numpy()
    raw_closes = pd.to_numeric(bars["close"], errors="raise").to_numpy(dtype=float, copy=False)

    for symbol, symbol_actions in normalized.groupby("symbol", sort=False):
        positions = symbol_positions.get(symbol)
        if positions is None:
            continue
        ordered_positions = positions[np.argsort(trade_dates[positions])]
        symbol_dates = pd.DatetimeIndex(trade_dates[ordered_positions])
        ex_date_factors = np.ones(len(ordered_positions), dtype=float)
        applied_for_symbol = False

        for ex_date, event_group in symbol_actions.groupby("ex_date", sort=True):
            date_position = int(symbol_dates.get_indexer([ex_date])[0])
            if date_position <= 0:
                diagnostics["skipped_event_count"] += int(len(event_group))
                continue

            prior_close = float(raw_closes[ordered_positions[date_position - 1]])
            cash_per_share = float(
                event_group.loc[event_group["action_type"].eq("cash_dividend"), "per_10_shares"].sum()
            ) / 10.0
            share_ratio = 1.0 + float(
                event_group.loc[
                    event_group["action_type"].isin({"bonus_share", "capitalization"}),
                    "per_10_shares",
                ].sum()
            ) / 10.0
            factor = (prior_close - cash_per_share) / (prior_close * share_ratio)
            if not pd.notna(factor) or factor <= 0:
                raise ValueError(
                    f"invalid corporate-action adjustment factor for {symbol} on {ex_date.date()}"
                )
            ex_date_factors[date_position] = factor
            diagnostics["applied_event_count"] += int(len(event_group))
            applied_for_symbol = True

        if applied_for_symbol:
            cumulative_factors = np.cumprod(ex_date_factors[::-1])[::-1] / ex_date_factors
            adjusted.iloc[ordered_positions, price_column_positions] = (
                adjusted.iloc[ordered_positions, price_column_positions].to_numpy(
                    dtype=float, copy=True
                )
                * cumulative_factors[:, None]
            )

    return adjusted, diagnostics
