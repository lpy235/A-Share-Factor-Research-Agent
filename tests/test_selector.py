from app.backtest.selector import FactorScore, FactorSelector


def test_selector_accepts_stable_factor():
    scores = [
        FactorScore("momentum_20", mean_rank_ic=0.04, icir=0.6, coverage_ratio=0.9, missing_ratio=0.1, max_drawdown=-0.12)
    ]
    selected = FactorSelector().select(scores)
    assert [x.factor_name for x in selected] == ["momentum_20"]


def test_selector_rejects_low_coverage_factor():
    scores = [
        FactorScore("bad_factor", mean_rank_ic=0.08, icir=1.0, coverage_ratio=0.5, missing_ratio=0.5, max_drawdown=-0.12)
    ]
    assert FactorSelector().select(scores) == []

