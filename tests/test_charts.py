import pandas as pd

from app.reports.charts import (
    save_equity_curve,
    save_factor_quality_chart,
    save_metric_overview_chart,
)


def test_save_equity_curve_creates_png(tmp_path):
    returns = pd.Series([0.01, -0.02, 0.03], index=pd.date_range("2024-01-01", periods=3))
    path = tmp_path / "curve.png"
    save_equity_curve(returns, str(path), title="demo")
    assert path.exists()
    assert path.stat().st_size > 0


def test_metric_artifact_charts_create_pngs(tmp_path):
    metrics = [
        {
            "factor_name": "momentum_20",
            "mean_rank_ic": 0.04,
            "icir": 0.6,
            "coverage_ratio": 0.9,
            "missing_ratio": 0.1,
            "max_drawdown": -0.12,
            "sharpe": 1.2,
        }
    ]
    overview_path = tmp_path / "overview.png"
    quality_path = tmp_path / "quality.png"

    save_metric_overview_chart(metrics, str(overview_path))
    save_factor_quality_chart(metrics, str(quality_path))

    assert overview_path.exists()
    assert overview_path.stat().st_size > 0
    assert quality_path.exists()
    assert quality_path.stat().st_size > 0
