import pytest

from app.factor.dsl import FactorSpec
from app.factor.validator import (
    MAX_WINDOW,
    FactorDslValidator,
    FormulaMetadata,
)


def _spec(
    formula: str,
    *,
    required_fields: list[str] | None = None,
    lookback: int = 20,
) -> FactorSpec:
    return FactorSpec(
        factor_name="test_factor",
        hypothesis="A testable factor hypothesis.",
        formula=formula,
        required_fields=["close"] if required_fields is None else required_fields,
        direction="positive",
        category="test",
        frequency="daily",
        lookback=lookback,
        source_title="test source",
        source_url=None,
        source_excerpt="test evidence",
        confidence=0.8,
    )


@pytest.mark.parametrize(
    ("formula", "error_code"),
    [
        ("returns(close, 0)", "invalid_window:returns"),
        ("returns(close, -1)", "invalid_window:returns"),
        ("returns(close, 1.5)", "invalid_window:returns"),
        ("returns(close, True)", "invalid_window:returns"),
        ("returns(close, 1 + 1)", "invalid_window:returns"),
        (
            f"returns(close, {MAX_WINDOW + 1})",
            "window_exceeds_max:returns",
        ),
    ],
)
def test_invalid_window_is_rejected(formula: str, error_code: str):
    result = FactorDslValidator().validate(
        _spec(formula, lookback=MAX_WINDOW + 1)
    )

    assert result.valid is False
    assert error_code in result.errors


@pytest.mark.parametrize(
    "formula",
    [
        "returns(close)",
        "rank(close, 20)",
        "neutralize(close)",
        "ts_mean(close, 20, 60)",
        "rank(x=close)",
    ],
)
def test_invalid_operator_signature_is_rejected(formula: str):
    result = FactorDslValidator().validate(_spec(formula))

    assert result.valid is False
    assert any(error.startswith("invalid_signature:") for error in result.errors)


@pytest.mark.parametrize(
    "formula",
    [
        "winsorize(close)",
        "winsorize(close, 0.05)",
        "winsorize(close, 0.05, 0.95)",
    ],
)
def test_winsorize_supported_signatures_remain_valid(formula: str):
    result = FactorDslValidator().validate(_spec(formula))

    assert result.valid is True
    assert result.errors == []


@pytest.mark.parametrize(
    "formula",
    [
        "winsorize(close, -0.1, 0.9)",
        "winsorize(close, 0.1, 1.1)",
        "winsorize(close, 0.9, 0.1)",
        "winsorize(close, close, 0.9)",
    ],
)
def test_invalid_winsorize_bounds_are_rejected(formula: str):
    result = FactorDslValidator().validate(_spec(formula))

    assert result.valid is False
    assert "invalid_parameter:winsorize" in result.errors


def test_formula_fields_must_equal_declared_required_fields():
    result = FactorDslValidator().validate(
        _spec(
            "rank(returns(close, 20))",
            required_fields=["volume"],
        )
    )

    assert result.valid is False
    assert "required_fields_mismatch" in result.errors
    assert result.metadata == FormulaMetadata(frozenset({"close"}), 20)


def test_lookback_must_cover_largest_formula_window():
    result = FactorDslValidator().validate(
        _spec("rank(returns(close, 60))", lookback=20)
    )

    assert result.valid is False
    assert "lookback_too_small" in result.errors
    assert result.metadata == FormulaMetadata(frozenset({"close"}), 60)


def test_volume_price_formula_derives_both_fields_and_largest_window():
    formula = (
        "rank(returns(close, 20) * ts_mean(volume, 20) "
        "/ ts_mean(volume, 60))"
    )
    result = FactorDslValidator().validate(
        _spec(
            formula,
            required_fields=["volume", "close"],
            lookback=60,
        )
    )

    assert result.valid is True
    assert result.errors == []
    assert result.metadata == FormulaMetadata(
        frozenset({"close", "volume"}),
        60,
    )


def test_formula_length_limit_is_rejected():
    result = FactorDslValidator().validate(_spec(" " * 513 + "close"))

    assert result.valid is False
    assert "formula_too_long" in result.errors


def test_formula_ast_complexity_limit_is_rejected():
    formula = "close" + " + close" * 40
    result = FactorDslValidator().validate(_spec(formula))

    assert result.valid is False
    assert "ast_too_complex" in result.errors


def test_call_depth_limit_is_rejected():
    formula = "rank(" * 17 + "close" + ")" * 17
    result = FactorDslValidator().validate(_spec(formula))

    assert result.valid is False
    assert "call_depth_exceeded" in result.errors


@pytest.mark.parametrize(
    ("formula", "error_code"),
    [
        ("close[0]", "unsupported_ast:Subscript"),
        ("[close for _ in close]", "unsupported_ast:ListComp"),
        ("(lambda x: x)(close)", "unsafe_call"),
        ("missing", "unknown_name:missing"),
        ("unknown(close)", "unknown_operator:unknown"),
    ],
)
def test_unsupported_expression_is_rejected(formula: str, error_code: str):
    result = FactorDslValidator().validate(_spec(formula))

    assert result.valid is False
    assert error_code in result.errors


def test_validation_error_order_is_stable_and_deduplicated():
    result = FactorDslValidator().validate(
        _spec("returns(missing, -1)", required_fields=["bad_field"])
    )

    assert result.errors == sorted(set(result.errors))
    assert "invalid_window:returns" in result.errors
    assert "unknown_field:bad_field" in result.errors
    assert "unknown_name:missing" in result.errors
