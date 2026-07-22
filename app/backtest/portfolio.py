from dataclasses import dataclass
import math
from typing import Any

import pandas as pd

from app.backtest.config import BacktestConfig


OPTIONAL_STATUS_FIELDS = (
    "in_universe",
    "is_suspended",
    "is_st",
    "days_since_listing",
    "limit_up",
    "limit_down",
)
COST_COLUMNS = (
    "buy_turnover",
    "sell_turnover",
    "commission",
    "slippage",
    "stamp_duty",
    "total_cost",
    "cumulative_cost",
)


@dataclass
class PortfolioBacktestResult:
    gross_returns: pd.Series
    net_returns: pd.Series
    turnover: pd.Series
    costs: pd.DataFrame
    weights: dict[pd.Timestamp, dict[str, float]]
    selected_symbols: dict[pd.Timestamp, list[str]]
    diagnostics: dict[str, Any]


def run_long_only_backtest(
    factor: pd.Series,
    market_data: pd.DataFrame,
    *,
    direction: str,
    config: BacktestConfig,
) -> PortfolioBacktestResult:
    _validate_inputs(factor, market_data)
    if direction == "unknown":
        return _empty_result("factor_direction_unknown")
    if direction not in {"positive", "negative"}:
        raise ValueError(f"Unsupported factor direction: {direction}")

    available_fields = [field for field in OPTIONAL_STATUS_FIELDS if field in market_data]
    diagnostics: dict[str, Any] = {
        "executable": True,
        "execution_mode": config.execution_mode,
        "missing_fields": [field for field in OPTIONAL_STATUS_FIELDS if field not in market_data],
        "applied_rules": _applied_rules(available_fields, config),
        "blocked_buys": 0,
        "blocked_sells": 0,
        "empty_candidate_dates": 0,
        "missing_valuation_opens": 0,
        "daily": [],
    }
    scores = factor if direction == "positive" else -factor
    dates = sorted(pd.DatetimeIndex(market_data.index.get_level_values("date")).unique())
    previous_weights: dict[str, float] = {}
    gross_values: dict[pd.Timestamp, float] = {}
    net_values: dict[pd.Timestamp, float] = {}
    turnover_values: dict[pd.Timestamp, float] = {}
    cost_rows: list[dict[str, float | pd.Timestamp]] = []
    weights: dict[pd.Timestamp, dict[str, float]] = {}
    selected_symbols: dict[pd.Timestamp, list[str]] = {}
    cumulative_cost = 0.0

    for signal_date, execution_date, valuation_date in zip(dates, dates[1:], dates[2:]):
        signal_bars = _date_frame(market_data, signal_date)
        execution_bars = _date_frame(market_data, execution_date)
        valuation_bars = _date_frame(market_data, valuation_date)
        daily_scores = _date_series(scores, signal_date)
        candidates, excluded_count = _eligible_candidates(
            daily_scores, signal_bars, config
        )
        if candidates.empty:
            diagnostics["empty_candidate_dates"] += 1
            ranked_targets: list[str] = []
        else:
            target_count = max(1, math.ceil(len(candidates) / 5))
            ranked_targets = [str(symbol) for symbol in candidates.nlargest(target_count).index]

        blocked_weights = _blocked_existing_weights(previous_weights, execution_bars)
        diagnostics["blocked_sells"] += len(blocked_weights)
        buyable_targets: list[str] = []
        blocked_buy_count = 0
        for symbol in ranked_targets:
            if symbol in blocked_weights:
                continue
            if _is_limit_up(symbol, execution_bars):
                if previous_weights.get(symbol, 0.0) > 0:
                    blocked_weights[symbol] = previous_weights[symbol]
                else:
                    blocked_buy_count += 1
                continue
            if _can_hold_or_buy(symbol, execution_bars):
                buyable_targets.append(symbol)
            else:
                blocked_buy_count += 1
        diagnostics["blocked_buys"] += blocked_buy_count

        target_weights = dict(blocked_weights)
        allocatable_weight = max(0.0, 1.0 - sum(blocked_weights.values()))
        if buyable_targets:
            equal_weight = allocatable_weight / len(buyable_targets)
            target_weights.update({symbol: equal_weight for symbol in buyable_targets})

        cost = _calculate_costs(previous_weights, target_weights, config)
        cumulative_cost += cost["total_cost"]
        cost["cumulative_cost"] = cumulative_cost
        gross_return, missing_valuation_opens = _portfolio_return(
            target_weights, execution_bars, valuation_bars
        )
        net_return = gross_return - cost["total_cost"]

        gross_values[execution_date] = gross_return
        net_values[execution_date] = net_return
        turnover_values[execution_date] = cost["buy_turnover"] + cost["sell_turnover"]
        cost_rows.append({"date": execution_date, **cost})
        weights[execution_date] = target_weights
        selected_symbols[execution_date] = buyable_targets
        diagnostics["missing_valuation_opens"] += missing_valuation_opens
        diagnostics["daily"].append(
            {
                "signal_date": str(signal_date.date()),
                "execution_date": str(execution_date.date()),
                "valuation_date": str(valuation_date.date()),
                "candidate_count": int(len(candidates)),
                "excluded_count": excluded_count,
                "selected_count": len(buyable_targets),
                "blocked_buy_count": blocked_buy_count,
                "blocked_sell_count": len(blocked_weights),
            }
        )
        previous_weights = target_weights

    return PortfolioBacktestResult(
        gross_returns=pd.Series(gross_values, dtype=float),
        net_returns=pd.Series(net_values, dtype=float),
        turnover=pd.Series(turnover_values, dtype=float),
        costs=_cost_frame(cost_rows),
        weights=weights,
        selected_symbols=selected_symbols,
        diagnostics=diagnostics,
    )


def _validate_inputs(factor: pd.Series, market_data: pd.DataFrame) -> None:
    if not isinstance(factor.index, pd.MultiIndex) or not {"symbol", "date"}.issubset(
        factor.index.names
    ):
        raise ValueError("Factor must use a MultiIndex with symbol and date levels")
    if not isinstance(market_data.index, pd.MultiIndex) or not {
        "symbol",
        "date",
    }.issubset(market_data.index.names):
        raise ValueError("Market data must use a MultiIndex with symbol and date levels")
    if "open" not in market_data:
        raise ValueError("Market data must contain open prices")


def _date_frame(frame: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    try:
        result = frame.xs(date, level="date").copy()
    except KeyError:
        return frame.iloc[0:0].droplevel("date")
    result.index = result.index.astype(str)
    return result


def _date_series(series: pd.Series, date: pd.Timestamp) -> pd.Series:
    try:
        result = series.xs(date, level="date").copy()
    except KeyError:
        return pd.Series(dtype=float)
    result.index = result.index.astype(str)
    return result


def _eligible_candidates(
    scores: pd.Series,
    signal_bars: pd.DataFrame,
    config: BacktestConfig,
) -> tuple[pd.Series, int]:
    candidates = scores.dropna()
    initial_count = len(candidates)
    common = candidates.index.intersection(signal_bars.index)
    candidates = candidates.loc[common]
    bars = signal_bars.loc[common]
    if "in_universe" in bars:
        candidates = candidates.loc[bars["in_universe"].fillna(False).astype(bool)]
        bars = bars.loc[candidates.index]
    if config.exclude_st and "is_st" in bars:
        candidates = candidates.loc[~bars["is_st"].fillna(True).astype(bool)]
        bars = bars.loc[candidates.index]
    if "days_since_listing" in bars:
        listing_days = pd.to_numeric(bars["days_since_listing"], errors="coerce")
        candidates = candidates.loc[listing_days.ge(config.min_listing_days).fillna(False)]
    return candidates, initial_count - len(candidates)


def _blocked_existing_weights(
    previous_weights: dict[str, float], execution_bars: pd.DataFrame
) -> dict[str, float]:
    blocked: dict[str, float] = {}
    for symbol, weight in previous_weights.items():
        if symbol not in execution_bars.index:
            blocked[symbol] = weight
            continue
        row = execution_bars.loc[symbol]
        suspended = bool(row.get("is_suspended", False))
        limit_down = bool(row.get("limit_down", False))
        missing_open = pd.isna(row.get("open")) or float(row.get("open", 0)) <= 0
        if suspended or limit_down or missing_open:
            blocked[symbol] = weight
    return blocked


def _can_hold_or_buy(
    symbol: str,
    execution_bars: pd.DataFrame,
) -> bool:
    if symbol not in execution_bars.index:
        return False
    row = execution_bars.loc[symbol]
    if pd.isna(row.get("open")) or float(row.get("open", 0)) <= 0:
        return False
    if bool(row.get("is_suspended", False)):
        return False
    return True


def _is_limit_up(symbol: str, execution_bars: pd.DataFrame) -> bool:
    if symbol not in execution_bars.index:
        return False
    return bool(execution_bars.loc[symbol].get("limit_up", False))


def _calculate_costs(
    previous_weights: dict[str, float],
    target_weights: dict[str, float],
    config: BacktestConfig,
) -> dict[str, float]:
    symbols = set(previous_weights) | set(target_weights)
    buy_turnover = sum(
        max(target_weights.get(symbol, 0.0) - previous_weights.get(symbol, 0.0), 0.0)
        for symbol in symbols
    )
    sell_turnover = sum(
        max(previous_weights.get(symbol, 0.0) - target_weights.get(symbol, 0.0), 0.0)
        for symbol in symbols
    )
    turnover = buy_turnover + sell_turnover
    commission = turnover * config.commission_bps / 10_000
    slippage = turnover * config.slippage_bps / 10_000
    stamp_duty = sell_turnover * config.stamp_duty_bps / 10_000
    return {
        "buy_turnover": float(buy_turnover),
        "sell_turnover": float(sell_turnover),
        "commission": float(commission),
        "slippage": float(slippage),
        "stamp_duty": float(stamp_duty),
        "total_cost": float(commission + slippage + stamp_duty),
    }


def _portfolio_return(
    weights: dict[str, float],
    execution_bars: pd.DataFrame,
    valuation_bars: pd.DataFrame,
) -> tuple[float, int]:
    gross_return = 0.0
    missing_opens = 0
    for symbol, weight in weights.items():
        if symbol not in execution_bars.index or symbol not in valuation_bars.index:
            missing_opens += 1
            continue
        start_open = execution_bars.loc[symbol].get("open")
        end_open = valuation_bars.loc[symbol].get("open")
        if pd.isna(start_open) or pd.isna(end_open) or float(start_open) <= 0:
            missing_opens += 1
            continue
        gross_return += weight * (float(end_open) / float(start_open) - 1.0)
    return float(gross_return), missing_opens


def _applied_rules(available_fields: list[str], config: BacktestConfig) -> list[str]:
    rules = []
    for field in available_fields:
        if field == "is_st" and not config.exclude_st:
            continue
        rules.append(field)
    return rules


def _cost_frame(rows: list[dict[str, float | pd.Timestamp]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COST_COLUMNS, dtype=float)
    return pd.DataFrame(rows).set_index("date").loc[:, COST_COLUMNS]


def _empty_result(reason: str) -> PortfolioBacktestResult:
    return PortfolioBacktestResult(
        gross_returns=pd.Series(dtype=float),
        net_returns=pd.Series(dtype=float),
        turnover=pd.Series(dtype=float),
        costs=pd.DataFrame(columns=COST_COLUMNS, dtype=float),
        weights={},
        selected_symbols={},
        diagnostics={"executable": False, "reason": reason},
    )
