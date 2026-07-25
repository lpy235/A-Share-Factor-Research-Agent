from app.backtest.selector import FactorScore, FactorSelector


def _passing_score(**overrides):
    values = {
        "factor_name": "momentum_20",
        "mean_rank_ic": 0.04,
        "icir": 0.6,
        "coverage_ratio": 0.9,
        "missing_ratio": 0.1,
        "max_drawdown": -0.12,
        "mean_rank_ic_oos": 0.03,
        "walk_forward_positive_ratio": 1.0,
        "walk_forward_sign_consistent": True,
        "walk_forward_insufficient_data": False,
    }
    values.update(overrides)
    return FactorScore(**values)


def test_selector_accepts_stable_factor():
    scores = [_passing_score()]
    selected = FactorSelector().select(scores)
    assert [x.factor_name for x in selected] == ["momentum_20"]


def test_selector_rejects_low_coverage_factor():
    scores = [
        FactorScore("bad_factor", mean_rank_ic=0.08, icir=1.0, coverage_ratio=0.5, missing_ratio=0.5, max_drawdown=-0.12)
    ]
    assert FactorSelector().select(scores) == []


def test_selector_rejects_opposite_oos_direction():
    score = _passing_score(mean_rank_ic_oos=-0.03)
    assert FactorSelector().select([score]) == []
    assert "oos_direction_mismatch" in FactorSelector().rejection_reasons([score])["momentum_20"]


def test_selector_rejects_small_oos_rank_ic():
    score = _passing_score(mean_rank_ic_oos=0.009)
    assert FactorSelector().select([score]) == []
    assert "abs_oos_rank_ic" in FactorSelector().rejection_reasons([score])["momentum_20"][0]


def test_selector_rejects_insufficient_walk_forward_data():
    score = _passing_score(walk_forward_insufficient_data=True)
    assert FactorSelector().select([score]) == []
    assert "walk_forward_insufficient_data" in FactorSelector().rejection_reasons([score])["momentum_20"]


def test_selector_rejects_inconsistent_walk_forward_direction():
    score = _passing_score(walk_forward_sign_consistent=False)
    assert FactorSelector().select([score]) == []
    assert "walk_forward_sign_inconsistent" in FactorSelector().rejection_reasons([score])["momentum_20"]


def test_selector_rejects_too_few_positive_walk_forward_windows():
    score = _passing_score(walk_forward_positive_ratio=0.4)
    assert FactorSelector().select([score]) == []
    assert "walk_forward_positive_ratio" in FactorSelector().rejection_reasons([score])["momentum_20"][0]
