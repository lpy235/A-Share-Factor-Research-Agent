from app.agents.portfolio_manager import PortfolioManagerAgent


def test_portfolio_manager_recommends_without_changing_factor_status():
    recommendation = PortfolioManagerAgent().recommend(
        metrics={"mean_rank_ic": 0.03, "mean_rank_ic_oos": 0.02, "walk_forward_positive_ratio": 0.8, "walk_forward_sign_consistent": True},
        long_only_metrics={"cumulative_cost": 0.01, "max_drawdown": -0.2},
        data_version="v1",
        manifest_hash="a" * 64,
    )

    assert recommendation.recommendation == "approve"


def test_portfolio_manager_requires_more_research_for_unstable_oos():
    recommendation = PortfolioManagerAgent().recommend(
        metrics={"mean_rank_ic": 0.03, "mean_rank_ic_oos": 0.001, "walk_forward_positive_ratio": 0.4, "walk_forward_sign_consistent": False},
        long_only_metrics={},
        data_version="v1",
        manifest_hash="a" * 64,
    )

    assert recommendation.recommendation == "continue_research"
