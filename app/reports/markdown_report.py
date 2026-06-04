from typing import Any


def render_report(
    research_topic: str,
    sources: list[dict[str, Any]],
    factors: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    limitations: list[str],
) -> str:
    lines = [
        f"# A 股因子研究报告：{research_topic}",
        "",
        "> 历史回测不构成投资建议。本报告仅用于量化研究流程展示。",
        "",
        "## 1. Source Summary",
    ]
    for source in sources:
        lines.append(f"- {source.get('source_title')} {source.get('source_url') or ''}".strip())

    lines.extend(["", "## 2. Extracted Factor Formulas"])
    for factor in factors:
        lines.append(f"- `{factor.get('factor_name')}`: `{factor.get('formula')}`")
        lines.append(f"  - hypothesis: {factor.get('hypothesis')}")
        lines.append(f"  - source: {factor.get('source_title')}")

    lines.extend(["", "## 3. Validation Metrics"])
    for metric in metrics:
        items = ", ".join(f"{k}={v}" for k, v in metric.items())
        lines.append(f"- {items}")

    lines.extend(["", "## 4. Limitations"])
    for item in limitations:
        lines.append(f"- {item}")

    lines.extend(["", "## 5. Reproducibility"])
    lines.append("- Data provider defaults to deterministic fixture data unless configured otherwise.")
    lines.append("- LLM extraction has deterministic fallback rules for offline demos.")
    return "\n".join(lines)

