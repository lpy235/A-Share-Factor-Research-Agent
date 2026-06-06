import json
from pathlib import Path
from typing import Any

from app.reports.charts import save_factor_quality_chart, save_metric_overview_chart


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
    ) -> list[dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        self._write_text(run_dir / "report.md", report_markdown)
        self._write_json(run_dir / "metrics.json", metrics)
        self._write_json(run_dir / "factors.json", factor_specs)
        self._write_json(
            run_dir / "bundle.json",
            {
                "run_id": run_id,
                "selected_factors": selected_factors,
                "factor_specs": factor_specs,
                "metrics": metrics,
                "report_markdown": report_markdown,
            },
        )
        if metrics:
            save_metric_overview_chart(metrics, str(run_dir / "metric_overview.png"))
            save_factor_quality_chart(metrics, str(run_dir / "factor_quality.png"))

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
        "factors.json": "因子公式 JSON",
        "bundle.json": "完整研究包 JSON",
        "metric_overview.png": "指标概览图",
        "factor_quality.png": "因子质量图",
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
