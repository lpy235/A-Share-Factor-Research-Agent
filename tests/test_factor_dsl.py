import pandas as pd

from app.factor.dsl import FactorSpec
from app.factor.executor import FactorExecutor
from app.factor.validator import FactorDslValidator


def _spec(formula: str, name: str = "momentum_20") -> FactorSpec:
    return FactorSpec(
        factor_name=name,
        hypothesis="过去20日收益率较高的股票可能延续上涨。",
        formula=formula,
        required_fields=["close"],
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=20,
        source_title="example report",
        source_url="https://example.com/report.pdf",
        source_excerpt="过去20日收益率可衡量短期动量。",
        confidence=0.8,
    )


def test_valid_formula_passes():
    result = FactorDslValidator().validate(_spec("rank(returns(close, 20))"))
    assert result.valid is True
    assert result.errors == []


def test_unknown_operator_fails():
    result = FactorDslValidator().validate(_spec("evil(close, 20)", "bad_factor"))
    assert result.valid is False
    assert "unknown_operator:evil" in result.errors


def test_malicious_formula_fails():
    result = FactorDslValidator().validate(
        _spec("__import__('os').system('rm -rf /')", "malicious")
    )
    assert result.valid is False
    assert "unsafe_token" in result.errors


def test_executor_computes_valid_formula():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002"], pd.date_range("2024-01-01", periods=25)],
        names=["symbol", "date"],
    )
    data = pd.DataFrame(index=idx)
    data["close"] = list(range(1, 26)) + list(range(2, 27))

    result = FactorExecutor().execute(_spec("rank(returns(close, 20))"), data)
    assert result.name == "momentum_20"
    assert not result.values.dropna().empty

