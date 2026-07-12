import pandas as pd

from app.backtest.correlation import compute_factor_correlation_matrix, deduplicate_by_correlation


def _factor(values: list[float]) -> pd.Series:
    index = pd.MultiIndex.from_product(
        [["000001", "000002", "000003"], pd.date_range("2024-01-01", periods=2)],
        names=["symbol", "date"],
    )
    return pd.Series(values, index=index)


def test_compute_factor_correlation_matrix_averages_daily_cross_sections():
    factor_a = _factor([1, 2, 2, 4, 3, 6])
    factor_b = _factor([10, 20, 20, 40, 30, 60])
    factor_c = _factor([30, 60, 20, 40, 10, 20])

    corr = compute_factor_correlation_matrix(
        {
            "factor_a": factor_a,
            "factor_b": factor_b,
            "factor_c": factor_c,
        }
    )

    assert corr.loc["factor_a", "factor_a"] == 1.0
    assert corr.loc["factor_a", "factor_b"] == 1.0
    assert corr.loc["factor_b", "factor_a"] == 1.0
    assert corr.loc["factor_a", "factor_c"] == -1.0


def test_compute_factor_correlation_matrix_requires_multiple_factors():
    assert compute_factor_correlation_matrix({"factor_a": _factor([1, 2, 3, 4, 5, 6])}).empty


def test_deduplicate_by_correlation_keeps_higher_quality_factor():
    factor_a = _factor([1, 2, 2, 4, 3, 6])
    factor_b = _factor([10, 20, 20, 40, 30, 60])

    kept, removed = deduplicate_by_correlation(
        {"factor_a": factor_a, "factor_b": factor_b},
        corr_threshold=0.9,
        quality_scores={"factor_a": 0.1, "factor_b": 0.3},
    )

    assert kept == ["factor_b"]
    assert "factor_a" in removed
