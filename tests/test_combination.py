import pandas as pd

from app.backtest.combination import combine_factor_values


def _make_factor_series(symbol_values: dict[str, list[float]]) -> pd.Series:
    dates = pd.date_range("2020-01-01", periods=len(next(iter(symbol_values.values()))), freq="B")
    rows = []
    for symbol, values in symbol_values.items():
        for date, value in zip(dates, values):
            rows.append((symbol, date, value))
    idx = pd.MultiIndex.from_tuples([(s, d) for s, d, _ in rows], names=["symbol", "date"])
    return pd.Series([v for _, _, v in rows], index=idx)


def test_combine_equal_weight_returns_series():
    f1 = _make_factor_series({"001": [1, 2, 3, 4, 5], "002": [2, 3, 4, 5, 6]})
    f2 = _make_factor_series({"001": [5, 4, 3, 2, 1], "002": [4, 3, 2, 1, 0]})
    combined = combine_factor_values({"f1": f1, "f2": f2}, ["f1", "f2"], method="equal_weight")
    assert not combined.empty
    assert len(combined) == 10


def test_combine_empty_when_no_selected():
    f1 = _make_factor_series({"001": [1, 2, 3]})
    combined = combine_factor_values({"f1": f1}, [], method="equal_weight")
    assert combined.empty


def test_combine_ic_weight_uses_weights():
    f1 = _make_factor_series({"001": [1, 2, 3, 4, 5]})
    f2 = _make_factor_series({"001": [5, 4, 3, 2, 1]})
    combined = combine_factor_values(
        {"f1": f1, "f2": f2}, ["f1", "f2"], method="ic_weight", ic_weights={"f1": 0.1, "f2": 0.3}
    )
    assert not combined.empty
    assert len(combined) == 5


def test_combine_risk_parity_returns_series():
    f1 = _make_factor_series({"001": [1.0, 1.0, 1.0, 1.0, 1.0]})
    f2 = _make_factor_series({"001": [1.0, 2.0, 1.0, 2.0, 1.0]})
    combined = combine_factor_values({"f1": f1, "f2": f2}, ["f1", "f2"], method="risk_parity")
    assert not combined.empty
    assert len(combined) == 5


def test_combine_skips_unavailable_factors():
    f1 = _make_factor_series({"001": [1, 2, 3]})
    combined = combine_factor_values({"f1": f1}, ["f1", "missing"], method="equal_weight")
    assert not combined.empty
    assert len(combined) == 3
