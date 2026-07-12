from app.reports.markdown_report import render_report


def test_report_contains_disclaimer_and_sections():
    report = render_report(
        research_topic="A股量价类动量因子",
        sources=[{"source_title": "demo report", "source_url": "https://example.com"}],
        factors=[{"factor_name": "momentum_20", "formula": "rank(returns(close, 20))"}],
        metrics=[
            {
                "factor_name": "momentum_20",
                "mean_rank_ic": 0.04,
                "mean_rank_ic_oos": 0.03,
                "icir": 0.6,
                "ic_decay_ratio": 1.33,
            }
        ],
        oos_metrics=[
            {"factor_name_oos": "momentum_20", "mean_rank_ic_oos": 0.03, "icir_oos": 0.4}
        ],
        factor_correlation={"labels": ["momentum_20", "value_20"], "values": [[1, 0.2], [0.2, 1]]},
        limitations=["fixture data only"],
    )
    assert "A股量价类动量因子" in report
    assert "历史回测不构成投资建议" in report
    assert "资料摘要" in report
    assert "来源诊断" in report
    assert "回测校验指标" in report
    assert "回测假设" in report
    assert "Agent 审计解释" in report
    assert "可复现性" in report
    assert "OOS 明细" in report
    assert "因子相关性" in report
    assert "momentum_20" in report
