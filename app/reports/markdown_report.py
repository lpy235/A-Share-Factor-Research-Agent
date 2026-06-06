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
        "## 1. 资料摘要",
    ]
    for source in sources:
        lines.append(f"- {source.get('source_title')} {source.get('source_url') or ''}".strip())

    lines.extend(["", "## 2. 抽取到的因子公式"])
    for factor in factors:
        lines.append(f"- `{factor.get('factor_name')}`: `{factor.get('formula')}`")
        lines.append(f"  - 假设：{factor.get('hypothesis')}")
        lines.append(f"  - 来源：{factor.get('source_title')}")

    lines.extend(["", "## 3. 回测校验指标"])
    for metric in metrics:
        items = ", ".join(f"{k}={v}" for k, v in metric.items())
        lines.append(f"- {items}")

    lines.extend(["", "## 4. 局限性"])
    for item in limitations:
        lines.append(f"- {item}")

    lines.extend(["", "## 5. 可复现性"])
    lines.append("- 默认使用确定性的内置示例数据，除非在运行参数中指定其他行情数据源。")
    lines.append("- LLM 抽取未配置或失败时，会回退到确定性的规则抽取流程。")
    return "\n".join(lines)
