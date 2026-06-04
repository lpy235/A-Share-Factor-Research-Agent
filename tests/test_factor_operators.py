import pandas as pd

from app.factor.operators import rank, returns, zscore


def test_returns_calculates_pct_change_by_symbol():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002"], pd.date_range("2024-01-01", periods=3)],
        names=["symbol", "date"],
    )
    close = pd.Series([10, 11, 12, 20, 18, 22], index=idx, name="close")
    result = returns(close, 1)
    assert round(result.loc[("000001", pd.Timestamp("2024-01-02"))], 6) == 0.1
    assert round(result.loc[("000002", pd.Timestamp("2024-01-02"))], 6) == -0.1


def test_cross_sectional_rank_by_date():
    idx = pd.MultiIndex.from_tuples(
        [
            ("000001", pd.Timestamp("2024-01-01")),
            ("000002", pd.Timestamp("2024-01-01")),
            ("000003", pd.Timestamp("2024-01-01")),
        ],
        names=["symbol", "date"],
    )
    values = pd.Series([1.0, 3.0, 2.0], index=idx)
    result = rank(values)
    assert result.loc[("000001", pd.Timestamp("2024-01-01"))] == 1 / 3
    assert result.loc[("000003", pd.Timestamp("2024-01-01"))] == 2 / 3
    assert result.loc[("000002", pd.Timestamp("2024-01-01"))] == 1.0


def test_zscore_by_date_has_zero_mean():
    idx = pd.MultiIndex.from_tuples(
        [
            ("000001", pd.Timestamp("2024-01-01")),
            ("000002", pd.Timestamp("2024-01-01")),
            ("000003", pd.Timestamp("2024-01-01")),
        ],
        names=["symbol", "date"],
    )
    values = pd.Series([1.0, 2.0, 3.0], index=idx)
    result = zscore(values)
    assert round(result.groupby(level="date").mean().iloc[0], 8) == 0

