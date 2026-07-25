from app.factor.dsl import FactorSpec
from app.factor.variation import FactorVariationEngine


def _spec() -> FactorSpec:
    return FactorSpec(
        factor_name="volume_momentum",
        hypothesis="volume momentum",
        formula="rank(ts_mean(volume, 5)) + rank(returns(close, 20))",
        required_fields=["close", "volume"],
        direction="positive",
        category="volume_price",
        lookback=20,
        source_title="report",
        source_excerpt="evidence",
        confidence=0.8,
    )


def test_variation_engine_only_emits_valid_bounded_dsl_variants():
    variants = FactorVariationEngine(allowed_windows=(5, 10, 20)).generate(_spec(), max_variants=3)

    assert variants
    assert len(variants) <= 3
    assert all(item.spec.factor_name.startswith("volume_momentum_") for item in variants)
    assert all(item.parent_factor_names == ("volume_momentum",) for item in variants)
    assert all("import" not in item.spec.formula for item in variants)


def test_variation_engine_combines_two_valid_specs_with_explicit_lineage():
    left = _spec()
    right = left.model_copy(update={"factor_name": "close_mean", "formula": "rank(ts_mean(close, 10))", "required_fields": ["close"], "lookback": 10})

    combined = FactorVariationEngine().combine(left, right)

    assert combined.parent_factor_names == ("volume_momentum", "close_mean")
    assert combined.spec.required_fields == ["close", "volume"]
    assert "rank(" in combined.spec.formula
