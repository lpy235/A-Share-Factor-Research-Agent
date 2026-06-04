import numpy as np
import pandas as pd

from app.backtest.metrics import annualized_return, max_drawdown, sharpe_ratio
from app.backtest.single_factor import compute_rank_ic, grouped_forward_returns


def test_annualized_return_positive_series():
    returns = pd.Series([0.01] * 252)
    assert annualized_return(returns) > 0


def test_max_drawdown_detects_drop():
    returns = pd.Series([0.1, -0.5, 0.1])
    assert max_drawdown(returns) < 0


def test_sharpe_ratio_zero_for_flat_returns():
    returns = pd.Series([0.0] * 252)
    assert sharpe_ratio(returns) == 0.0


def test_compute_rank_ic_returns_series_by_date():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002", "000003"], pd.date_range("2024-01-01", periods=3)],
        names=["symbol", "date"],
    )
    factor = pd.Series(np.arange(len(idx)), index=idx)
    forward_returns = pd.Series(np.arange(len(idx)), index=idx)
    result = compute_rank_ic(factor, forward_returns)
    assert len(result) == 3
    assert result.dropna().iloc[0] == 1.0


def test_grouped_forward_returns_outputs_groups():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002", "000003", "000004", "000005"], [pd.Timestamp("2024-01-01")]],
        names=["symbol", "date"],
    )
    factor = pd.Series([1, 2, 3, 4, 5], index=idx)
    forward_returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05], index=idx)
    result = grouped_forward_returns(factor, forward_returns, groups=5)
    assert set(result.columns) == {1, 2, 3, 4, 5}

