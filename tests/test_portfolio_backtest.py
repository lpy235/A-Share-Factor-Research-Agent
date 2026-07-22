import pandas as pd
import pytest

from app.backtest.config import BacktestConfig
from app.backtest.portfolio import run_long_only_backtest


SYMBOLS = ["A", "B", "C", "D", "E"]


def _market_data(dates: list[str], opens: dict[str, list[float]]) -> pd.DataFrame:
    index = pd.MultiIndex.from_product(
        [SYMBOLS, pd.to_datetime(dates)], names=["symbol", "date"]
    )
    frame = pd.DataFrame(index=index)
    for symbol in SYMBOLS:
        frame.loc[(symbol, slice(None)), "open"] = opens[symbol]
    frame["close"] = frame["open"]
    return frame.astype(float)


def _factor(dates: list[str], daily_order: list[list[float]]) -> pd.Series:
    index = pd.MultiIndex.from_product(
        [SYMBOLS, pd.to_datetime(dates)], names=["symbol", "date"]
    )
    values: list[float] = []
    for symbol_index in range(len(SYMBOLS)):
        values.extend(day[symbol_index] for day in daily_order)
    return pd.Series(values, index=index, dtype=float)


def _zero_cost_config() -> BacktestConfig:
    return BacktestConfig(
        commission_bps=0,
        stamp_duty_bps=0,
        slippage_bps=0,
        min_listing_days=0,
    )


def test_portfolio_uses_signal_t_and_open_t_plus_1_to_t_plus_2_return():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = _market_data(
        dates,
        {
            "A": [8, 10, 11],
            "B": [8, 10, 10],
            "C": [8, 10, 10],
            "D": [8, 10, 10],
            "E": [8, 10, 10],
        },
    )
    factor = _factor(dates, [[5, 4, 3, 2, 1], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])

    result = run_long_only_backtest(
        factor, data, direction="positive", config=_zero_cost_config()
    )

    assert result.gross_returns.index.tolist() == [pd.Timestamp("2024-01-02")]
    assert result.gross_returns.iloc[0] == pytest.approx(0.10)
    assert result.selected_symbols[pd.Timestamp("2024-01-02")] == ["A"]


def test_negative_direction_inverts_ranking_and_unknown_is_diagnostic_only():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = _market_data(dates, {symbol: [10, 10, 10] for symbol in SYMBOLS})
    factor = _factor(dates, [[5, 1, 2, 3, 4], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])

    negative = run_long_only_backtest(
        factor, data, direction="negative", config=_zero_cost_config()
    )
    unknown = run_long_only_backtest(
        factor, data, direction="unknown", config=_zero_cost_config()
    )

    assert negative.selected_symbols[pd.Timestamp("2024-01-02")] == ["B"]
    assert unknown.gross_returns.empty
    assert unknown.diagnostics["executable"] is False
    assert unknown.diagnostics["reason"] == "factor_direction_unknown"


def test_costs_apply_bilateral_fees_and_sell_side_stamp_duty():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
    data = _market_data(dates, {symbol: [10, 10, 10, 10] for symbol in SYMBOLS})
    factor = _factor(
        dates,
        [
            [5, 4, 3, 2, 1],
            [1, 5, 4, 3, 2],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ],
    )
    config = BacktestConfig(
        commission_bps=3,
        stamp_duty_bps=5,
        slippage_bps=5,
        min_listing_days=0,
    )

    result = run_long_only_backtest(factor, data, direction="positive", config=config)

    second = result.costs.iloc[1]
    assert result.turnover.iloc[1] == pytest.approx(2.0)
    assert second["sell_turnover"] == pytest.approx(1.0)
    assert second["commission"] == pytest.approx(2 * 3 / 10_000)
    assert second["slippage"] == pytest.approx(2 * 5 / 10_000)
    assert second["stamp_duty"] == pytest.approx(1 * 5 / 10_000)
    assert result.net_returns.iloc[1] == pytest.approx(
        result.gross_returns.iloc[1] - second["total_cost"]
    )


def test_zero_cost_net_equals_gross():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = _market_data(dates, {symbol: [10, 10, 11] for symbol in SYMBOLS})
    factor = _factor(dates, [[5, 4, 3, 2, 1], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])

    result = run_long_only_backtest(
        factor, data, direction="positive", config=_zero_cost_config()
    )

    pd.testing.assert_series_equal(result.net_returns, result.gross_returns)


@pytest.mark.parametrize(
    ("column", "value", "execution_field"),
    [
        ("in_universe", False, False),
        ("is_st", True, False),
        ("days_since_listing", 10, False),
        ("is_suspended", True, True),
        ("limit_up", True, True),
    ],
)
def test_available_status_fields_filter_candidates(
    column: str, value: bool | int, execution_field: bool
):
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = _market_data(dates, {symbol: [10, 10, 10] for symbol in SYMBOLS})
    data["in_universe"] = True
    data["is_st"] = False
    data["days_since_listing"] = 365
    data["is_suspended"] = False
    data["limit_up"] = False
    target_date = dates[1] if execution_field else dates[0]
    data.loc[("A", pd.Timestamp(target_date)), column] = value
    factor = _factor(dates, [[5, 4, 3, 2, 1], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])

    result = run_long_only_backtest(
        factor, data, direction="positive", config=BacktestConfig(min_listing_days=60)
    )

    assert "A" not in result.selected_symbols[pd.Timestamp("2024-01-02")]


@pytest.mark.parametrize("column", ["is_suspended", "limit_down"])
def test_blocked_sell_carries_existing_position(column: str):
    dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
    data = _market_data(dates, {symbol: [10, 10, 10, 10] for symbol in SYMBOLS})
    data["is_suspended"] = False
    data["limit_down"] = False
    data.loc[("A", pd.Timestamp("2024-01-03")), column] = True
    factor = _factor(
        dates,
        [
            [5, 4, 3, 2, 1],
            [1, 5, 4, 3, 2],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ],
    )

    result = run_long_only_backtest(
        factor, data, direction="positive", config=_zero_cost_config()
    )

    assert result.weights[pd.Timestamp("2024-01-03")]["A"] == pytest.approx(1.0)
    assert result.diagnostics["blocked_sells"] == 1


def test_missing_optional_fields_are_disclosed_not_claimed():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = _market_data(dates, {symbol: [10, 10, 10] for symbol in SYMBOLS})
    factor = _factor(dates, [[5, 4, 3, 2, 1], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])

    result = run_long_only_backtest(
        factor, data, direction="positive", config=_zero_cost_config()
    )

    assert set(result.diagnostics["missing_fields"]) == {
        "in_universe",
        "is_suspended",
        "is_st",
        "days_since_listing",
        "limit_up",
        "limit_down",
    }
    assert result.diagnostics["applied_rules"] == []


def test_no_eligible_candidates_produces_zero_return_and_diagnostic():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    data = _market_data(dates, {symbol: [10, 10, 10] for symbol in SYMBOLS})
    data["in_universe"] = False
    factor = _factor(dates, [[5, 4, 3, 2, 1], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])

    result = run_long_only_backtest(
        factor, data, direction="positive", config=_zero_cost_config()
    )

    assert result.gross_returns.iloc[0] == 0
    assert result.diagnostics["empty_candidate_dates"] == 1
