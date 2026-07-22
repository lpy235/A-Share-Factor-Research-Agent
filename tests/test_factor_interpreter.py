import pandas as pd
import pytest

from app.factor import operators
from app.factor.dsl import FactorSpec
from app.factor.executor import FactorExecutor


def _market_data() -> pd.DataFrame:
    index = pd.MultiIndex.from_product(
        [["000001", "000002"], pd.date_range("2024-01-01", periods=25)],
        names=["symbol", "date"],
    )
    return pd.DataFrame(
        {
            "close": list(range(1, 26)) + list(range(2, 27)),
            "volume": list(range(101, 126)) + list(range(201, 226)),
        },
        index=index,
    )


def _spec(
    formula: str,
    *,
    required_fields: list[str] | None = None,
    lookback: int = 20,
) -> FactorSpec:
    return FactorSpec(
        factor_name="momentum_20",
        hypothesis="Past returns may persist.",
        formula=formula,
        required_fields=["close"] if required_fields is None else required_fields,
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=lookback,
        source_title="test report",
        source_excerpt="Past returns may measure momentum.",
        confidence=0.8,
    )


def test_executor_matches_operator_result_for_valid_formula():
    data = _market_data()

    result = FactorExecutor().execute(_spec("returns(close, 20)"), data)
    expected = operators.returns(data["close"], 20).rename("momentum_20")

    pd.testing.assert_series_equal(result.values, expected)


def test_executor_rejects_formula_that_would_use_forward_data():
    with pytest.raises(ValueError, match="Invalid factor formula"):
        FactorExecutor().execute(_spec("delay(close, -1)"), _market_data())


def test_executor_rejects_non_series_expression():
    with pytest.raises(TypeError, match="Factor formula must return a pandas Series"):
        FactorExecutor().execute(
            _spec("1 + 2", required_fields=[], lookback=1),
            _market_data(),
        )


def test_executor_rejects_misaligned_result_index(monkeypatch):
    data = _market_data()

    def misaligned_rank(values: pd.Series) -> pd.Series:
        return values.iloc[1:]

    monkeypatch.setattr(operators, "rank", misaligned_rank)

    with pytest.raises(ValueError, match="result index must match market data index"):
        FactorExecutor().execute(_spec("rank(close)"), data)
