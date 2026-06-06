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
    )

    names = {item["name"] for item in artifacts}
    assert names == {
        "bundle.json",
        "factor_quality.png",
        "factors.json",
        "metric_overview.png",
        "metrics.json",
        "report.md",
    }
    assert all(item["size_bytes"] > 0 for item in artifacts)
    assert store.get_artifact_path("run_demo", "report.md").read_text(encoding="utf-8") == "# 研究报告"
    assert store.get_artifact_path("run_demo", "../report.md") is None
