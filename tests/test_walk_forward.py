import pandas as pd

from app.backtest.walk_forward import walk_forward_ic


def test_walk_forward_ic_returns_windows_and_stability():
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    ic = pd.Series([0.05] * 60 + [0.03] * 40, index=dates)
    result = walk_forward_ic(ic, n_windows=5)
    assert len(result["windows"]) == 5
    assert result["stability"]["window_count"] == 5
    assert result["stability"]["positive_ratio"] == 1.0
    assert result["stability"]["sign_consistent"] is True
    assert result["windows"][0]["start_date"]
    assert result["windows"][0]["end_date"]


def test_walk_forward_ic_handles_insufficient_data():
    ic = pd.Series([0.01, 0.02, 0.03])
    result = walk_forward_ic(ic, n_windows=5)
    assert result["windows"] == []
    assert result["stability"]["insufficient_data"] is True


def test_walk_forward_ic_detects_inconsistent_sign():
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    ic = pd.Series([0.05] * 50 + [-0.05] * 50, index=dates)
    result = walk_forward_ic(ic, n_windows=5)
    assert result["stability"]["sign_consistent"] is False
    assert result["stability"]["positive_ratio"] < 1.0
