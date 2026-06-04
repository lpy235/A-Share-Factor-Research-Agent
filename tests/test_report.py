from app.reports.markdown_report import render_report


def test_report_contains_disclaimer_and_sections():
    report = render_report(
        research_topic="A股量价类动量因子",
        sources=[{"source_title": "demo report", "source_url": "https://example.com"}],
        factors=[{"factor_name": "momentum_20", "formula": "rank(returns(close, 20))"}],
        metrics=[{"factor_name": "momentum_20", "mean_rank_ic": 0.04, "icir": 0.6}],
        limitations=["fixture data only"],
    )
    assert "A股量价类动量因子" in report
    assert "历史回测不构成投资建议" in report
    assert "momentum_20" in report

