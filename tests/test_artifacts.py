from app.storage.artifacts import ArtifactStore


def test_artifact_store_writes_manifest_and_downloadable_files(tmp_path):
    store = ArtifactStore(tmp_path)

    artifacts = store.write_run_artifacts(
        "run_demo",
        report_markdown="# 研究报告",
        metrics=[
            {
                "factor_name": "momentum_20",
                "mean_rank_ic": 0.04,
                "icir": 0.6,
                "coverage_ratio": 0.9,
                "missing_ratio": 0.1,
                "max_drawdown": -0.12,
                "sharpe": 1.2,
            }
        ],
        factor_specs=[{"factor_name": "momentum_20", "formula": "rank(returns(close, 20))"}],
        selected_factors=["momentum_20"],
        backtest_series={
            "momentum_20": {
                "rank_ic": [{"date": "2020-01-01", "value": 0.1}],
                "cumulative_rank_ic": [{"date": "2020-01-01", "value": 0.1}],
                "equity_curve": [{"date": "2020-01-01", "value": 1.01}],
                "drawdown": [{"date": "2020-01-01", "value": 0.0}],
                "grouped_returns": [{"date": "2020-01-01", "1": 0.01, "5": 0.03}],
            }
        },
    )

    names = {item["name"] for item in artifacts}
    assert names == {
        "backtest_series.json",
        "bundle.json",
        "cumulative_ic.png",
        "drawdown_curve.png",
        "factor_correlation.json",
        "factor_quality.png",
        "factors.json",
        "grouped_returns.png",
        "ic_decay.png",
        "long_short_equity.png",
        "metric_overview.png",
        "metrics.json",
        "monthly_heatmap.png",
        "oos_metrics.json",
        "rank_ic_timeseries.png",
        "report.md",
        "rolling_sharpe.png",
    }
    assert all(item["size_bytes"] > 0 for item in artifacts)
    assert store.get_artifact_path("run_demo", "report.md").read_text(encoding="utf-8") == "# 研究报告"
    assert store.get_artifact_path("run_demo", "../report.md") is None
