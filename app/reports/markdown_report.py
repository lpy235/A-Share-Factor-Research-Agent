from typing import Any


def render_report(
    research_topic: str,
    sources: list[dict[str, Any]],
    factors: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    limitations: list[str],
    source_diagnostics: dict[str, Any] | None = None,
    backtest_assumptions: dict[str, Any] | None = None,
    audit_trail: list[dict[str, Any]] | None = None,
) -> str:
    source_diagnostics = source_diagnostics or {}
    backtest_assumptions = backtest_assumptions or {}
    audit_trail = audit_trail or []
    lines = [
        f"# A 股因子研究报告：{research_topic}",
        "",
        "> 历史回测不构成投资建议。本报告仅用于量化研究流程展示。",
        "",
        "## 1. 资料摘要",
    ]
    for source in sources:
        lines.append(f"- {source.get('source_title')} {source.get('source_url') or ''}".strip())

    lines.extend(["", "## 2. 来源诊断"])
    lines.append(f"- 接受来源数：{source_diagnostics.get('accepted_count', len(sources))}")
    lines.append(f"- 过滤来源数：{source_diagnostics.get('rejected_count', 0)}")
    for item in source_diagnostics.get("rejected", [])[:5]:
        lines.append(f"- 已过滤：{item.get('title')}，原因：{item.get('reason')}")

    lines.extend(["", "## 3. 抽取到的因子公式"])
    for factor in factors:
        lines.append(f"- `{factor.get('factor_name')}`: `{factor.get('formula')}`")
        lines.append(f"  - 假设：{factor.get('hypothesis')}")
        lines.append(f"  - 来源：{factor.get('source_title')}")

    lines.extend(["", "## 4. 回测校验指标"])
    for metric in metrics:
        items = ", ".join(f"{k}={v}" for k, v in metric.items())
        lines.append(f"- {items}")

    lines.extend(["", "## 5. 回测假设"])
    if backtest_assumptions:
        lines.append(f"- 股票池：{backtest_assumptions.get('universe')}")
        lines.append(
            f"- 区间：{backtest_assumptions.get('start_date')} 至 "
            f"{backtest_assumptions.get('end_date')}"
        )
        lines.append(f"- 数据源：{backtest_assumptions.get('data_provider')}")
        lines.append(f"- 调仓频率：{backtest_assumptions.get('rebalance_frequency')}")
        lines.append(f"- 交易成本：{backtest_assumptions.get('transaction_cost_bps')} bps")
        for item in backtest_assumptions.get("bias_notes", []):
            lines.append(f"- {item}")

    lines.extend(["", "## 6. Agent 审计解释"])
    for item in audit_trail:
        lines.append(f"- {item.get('title')}：{item.get('detail')}")

    lines.extend(["", "## 7. 局限性"])
    for item in limitations:
        lines.append(f"- {item}")

    lines.extend(["", "## 8. 可复现性"])
    lines.append("- 默认使用确定性的内置示例数据，除非在运行参数中指定其他行情数据源。")
    lines.append("- LLM 抽取未配置或失败时，会回退到确定性的规则抽取流程。")
    return "\n".join(lines)
