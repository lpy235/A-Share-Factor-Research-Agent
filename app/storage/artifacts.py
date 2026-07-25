import json
from pathlib import Path
from typing import Any

from app.reports.charts import (
    save_cumulative_ic_chart,
    save_drawdown_chart,
    save_equity_curve_chart,
    save_factor_correlation_chart,
    save_factor_quality_chart,
    save_grouped_returns_chart,
    save_ic_decay_chart,
    save_metric_overview_chart,
    save_monthly_heatmap,
    save_rank_ic_chart,
    save_rolling_sharpe_chart,
)


ARTIFACT_ROOT = Path("run_artifacts")


class ArtifactStore:
    def __init__(self, root_dir: str | Path = ARTIFACT_ROOT) -> None:
        self.root_dir = Path(root_dir)

    def write_run_artifacts(
        self,
        run_id: str,
        *,
        report_markdown: str,
        metrics: list[dict[str, Any]],
        factor_specs: list[dict[str, Any]],
        selected_factors: list[str],
        backtest_series: dict[str, Any] | None = None,
        oos_metrics: list[dict[str, Any]] | None = None,
        factor_correlation: dict[str, Any] | None = None,
        portfolio_results: dict[str, Any] | None = None,
        backtest_diagnostics: dict[str, Any] | None = None,
        market_data_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        backtest_series = backtest_series or {}
        oos_metrics = oos_metrics or []
        factor_correlation = factor_correlation or {}
        portfolio_results = portfolio_results or {}
        backtest_diagnostics = backtest_diagnostics or {}
        market_data_metadata = market_data_metadata or {}
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        self._write_text(run_dir / "report.md", report_markdown)
        self._write_json(run_dir / "metrics.json", metrics)
        self._write_json(run_dir / "oos_metrics.json", oos_metrics)
        self._write_json(run_dir / "factors.json", factor_specs)
        self._write_json(run_dir / "backtest_series.json", backtest_series)
        self._write_json(run_dir / "factor_correlation.json", factor_correlation)
        self._write_json(run_dir / "portfolio_backtest.json", portfolio_results)
        self._write_json(run_dir / "backtest_diagnostics.json", backtest_diagnostics)
        self._write_json(
            run_dir / "bundle.json",
            {
                "run_id": run_id,
                "selected_factors": selected_factors,
                "factor_specs": factor_specs,
                "metrics": metrics,
                "oos_metrics": oos_metrics,
                "backtest_series": backtest_series,
                "factor_correlation": factor_correlation,
                "portfolio_results": portfolio_results,
                "backtest_diagnostics": backtest_diagnostics,
                "market_data_metadata": market_data_metadata,
                "report_markdown": report_markdown,
            },
        )
        corr_labels = factor_correlation.get("labels", [])
        corr_values = factor_correlation.get("values", [])
        if len(corr_labels) >= 2 and len(corr_values) == len(corr_labels):
            import pandas as pd

            corr_df = pd.DataFrame(corr_values, index=corr_labels, columns=corr_labels)
            save_factor_correlation_chart(corr_df, str(run_dir / "factor_correlation.png"))
        if metrics:
            save_metric_overview_chart(metrics, str(run_dir / "metric_overview.png"))
            save_factor_quality_chart(metrics, str(run_dir / "factor_quality.png"))
        if backtest_series:
            save_rank_ic_chart(backtest_series, str(run_dir / "rank_ic_timeseries.png"))
            save_cumulative_ic_chart(backtest_series, str(run_dir / "cumulative_ic.png"))
            save_equity_curve_chart(backtest_series, str(run_dir / "long_short_equity.png"))
            save_drawdown_chart(backtest_series, str(run_dir / "drawdown_curve.png"))
            save_grouped_returns_chart(backtest_series, str(run_dir / "grouped_returns.png"))
            save_rolling_sharpe_chart(backtest_series, str(run_dir / "rolling_sharpe.png"))
            save_monthly_heatmap(backtest_series, str(run_dir / "monthly_heatmap.png"))
            save_ic_decay_chart(backtest_series, str(run_dir / "ic_decay.png"))

        return self.list_artifacts(run_id)

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return []
        return [
            self._manifest_entry(run_id, path)
            for path in sorted(run_dir.iterdir())
            if path.is_file() and not path.name.startswith(".")
        ]

    def get_artifact_path(self, run_id: str, artifact_name: str) -> Path | None:
        if Path(artifact_name).name != artifact_name:
            return None
        path = self._run_dir(run_id) / artifact_name
        if not path.exists() or not path.is_file():
            return None
        return path

    def _run_dir(self, run_id: str) -> Path:
        return self.root_dir / run_id

    def _write_text(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def _write_json(self, path: Path, content: Any) -> None:
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

    def _manifest_entry(self, run_id: str, path: Path) -> dict[str, Any]:
        return {
            "name": path.name,
            "label": _label_for(path.name),
            "kind": _kind_for(path.suffix),
            "media_type": _media_type_for(path.suffix),
            "size_bytes": path.stat().st_size,
            "url": f"/runs/{run_id}/artifacts/{path.name}",
        }


def _label_for(name: str) -> str:
    labels = {
        "report.md": "研究报告 Markdown",
        "metrics.json": "回测指标 JSON",
        "oos_metrics.json": "样本外指标 JSON",
        "backtest_series.json": "回测序列 JSON",
        "factors.json": "因子公式 JSON",
        "bundle.json": "完整研究包 JSON",
        "metric_overview.png": "指标概览图",
        "factor_quality.png": "因子质量图",
        "rank_ic_timeseries.png": "Rank IC 时间序列",
        "cumulative_ic.png": "累计 Rank IC",
        "long_short_equity.png": "多空净值曲线",
        "drawdown_curve.png": "回撤曲线",
        "grouped_returns.png": "分组收益图",
        "rolling_sharpe.png": "滚动 Sharpe (63日)",
        "monthly_heatmap.png": "月度收益热力图",
        "ic_decay.png": "IC 衰减 (滚动20日)",
        "factor_correlation.png": "因子相关性矩阵",
        "factor_correlation.json": "因子相关性 JSON",
        "portfolio_backtest.json": "可执行多头组合回测 JSON",
        "backtest_diagnostics.json": "交易约束与股票池诊断 JSON",
    }
    return labels.get(name, name)


def _kind_for(suffix: str) -> str:
    if suffix == ".png":
        return "chart"
    if suffix == ".md":
        return "report"
    return "data"


def _media_type_for(suffix: str) -> str:
    if suffix == ".png":
        return "image/png"
    if suffix == ".md":
        return "text/markdown; charset=utf-8"
    return "application/json"
