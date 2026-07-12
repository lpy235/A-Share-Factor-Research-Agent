from typing import Any


def render_report(
    research_topic: str,
    sources: list[dict[str, Any]],
    factors: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    limitations: list[str],
    oos_metrics: list[dict[str, Any]] | None = None,
    factor_correlation: dict[str, Any] | None = None,
    source_diagnostics: dict[str, Any] | None = None,
    backtest_assumptions: dict[str, Any] | None = None,
    audit_trail: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> str:
    oos_metrics = oos_metrics or []
    factor_correlation = factor_correlation or {}
    source_diagnostics = source_diagnostics or {}
    backtest_assumptions = backtest_assumptions or {}
    audit_trail = audit_trail or []
    warnings = warnings or []
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
    if not metrics:
        lines.append("- 暂无可展示指标。")
    else:
        lines.append("| 因子 | IS Rank IC | OOS Rank IC | ICIR | IC 衰减 | 覆盖率 | 缺失率 | Sharpe |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for metric in metrics:
            lines.append(
                "| "
                f"{metric.get('factor_name', '')} | "
                f"{_fmt(metric.get('mean_rank_ic'))} | "
                f"{_fmt(metric.get('mean_rank_ic_oos'))} | "
                f"{_fmt(metric.get('icir'))} | "
                f"{_fmt(metric.get('ic_decay_ratio'))} | "
                f"{_fmt(metric.get('coverage_ratio'))} | "
                f"{_fmt(metric.get('missing_ratio'))} | "
                f"{_fmt(metric.get('sharpe'))} |"
            )
        lines.append("")
        lines.append(
            "- IS 为样本内回测，OOS 为日期后 30% 样本外检验；"
            "IC 衰减越大，越需要警惕样本内过拟合。"
        )

    if oos_metrics:
        lines.extend(["", "### OOS 明细"])
        for metric in oos_metrics:
            factor_name = metric.get("factor_name_oos", metric.get("factor_name", ""))
            lines.append(
                f"- {factor_name}: Rank IC={_fmt(metric.get('mean_rank_ic_oos'))}, "
                f"ICIR={_fmt(metric.get('icir_oos'))}, "
                f"Sharpe={_fmt(metric.get('sharpe_oos'))}"
            )

    corr_labels = factor_correlation.get("labels", [])
    corr_values = factor_correlation.get("values", [])
    if len(corr_labels) >= 2 and len(corr_values) == len(corr_labels):
        lines.extend(["", "### 因子相关性"])
        max_pair = _max_abs_corr_pair(corr_labels, corr_values)
        if max_pair:
            left, right, value = max_pair
            lines.append(f"- 最高绝对相关因子对：{left} / {right}，相关系数={value:.3f}。")
        lines.append("- 相关性矩阵已写入 `factor_correlation.json`，图表见 artifact。")

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
        lines.append(f"- 样本内/外切分：{backtest_assumptions.get('oos_split_ratio')}")
        lines.append(f"- OOS 起始日期：{backtest_assumptions.get('oos_split_date')}")
        for item in backtest_assumptions.get("bias_notes", []):
            lines.append(f"- {item}")

    lines.extend(["", "## 6. Agent 审计解释"])
    for item in audit_trail:
        lines.append(f"- {item.get('title')}：{item.get('detail')}")

    if warnings:
        lines.extend(["", "## 7. 风险提示与筛选原因"])
        for item in warnings:
            lines.append(f"- {item}")

    lines.extend(["", "## 8. 局限性"])
    for item in limitations:
        lines.append(f"- {item}")

    lines.extend(["", "## 9. 可复现性"])
    lines.append("- 默认使用确定性的内置示例数据，除非在运行参数中指定其他行情数据源。")
    lines.append("- LLM 抽取未配置或失败时，会回退到确定性的规则抽取流程。")
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _max_abs_corr_pair(
    labels: list[str],
    values: list[list[float]],
) -> tuple[str, str, float] | None:
    best: tuple[str, str, float] | None = None
    for row_index, row in enumerate(values):
        for col_index, value in enumerate(row):
            if col_index <= row_index or value is None:
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            if best is None or abs(numeric_value) > abs(best[2]):
                best = (labels[row_index], labels[col_index], numeric_value)
    return best
