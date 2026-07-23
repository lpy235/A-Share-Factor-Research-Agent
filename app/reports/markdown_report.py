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
    long_only_metrics: list[dict[str, Any]] | None = None,
    tradability_diagnostics: dict[str, Any] | None = None,
    universe_diagnostics: dict[str, Any] | None = None,
) -> str:
    oos_metrics = oos_metrics or []
    factor_correlation = factor_correlation or {}
    source_diagnostics = source_diagnostics or {}
    backtest_assumptions = backtest_assumptions or {}
    audit_trail = audit_trail or []
    warnings = warnings or []
    long_only_metrics = long_only_metrics or []
    tradability_diagnostics = tradability_diagnostics or {}
    universe_diagnostics = universe_diagnostics or {}
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

    if long_only_metrics:
        lines.extend(["", "### 可执行多头组合"])
        lines.append("| 因子 | 年化收益 | 超额年化 | Beta | IR | 跟踪误差 | 最大回撤 | 相对回撤 | 累计成本 |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for metric in long_only_metrics:
            lines.append(
                "| "
                f"{metric.get('factor_name', '')} | "
                f"{_fmt(metric.get('annualized_return'))} | "
                f"{_fmt(metric.get('excess_annualized_return'))} | "
                f"{_fmt(metric.get('benchmark_beta'))} | "
                f"{_fmt(metric.get('information_ratio'))} | "
                f"{_fmt(metric.get('tracking_error'))} | "
                f"{_fmt(metric.get('max_drawdown'))} | "
                f"{_fmt(metric.get('relative_max_drawdown'))} | "
                f"{_fmt(metric.get('cumulative_cost'))} |"
            )
        lines.append("- 组合时序：t 日收盘计算，t+1 日开盘成交，持有至 t+2 日开盘。")
        lines.append("- G5-G1 仅为研究诊断，不代表普通 A 股账户可执行的自由卖空策略。")
        benchmark_note = backtest_assumptions.get("benchmark_note")
        if benchmark_note:
            lines.append(f"- 基准：{benchmark_note}")

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
        lines.append(f"- 执行模式：{backtest_assumptions.get('execution_mode')}")
        lines.append(f"- 佣金：{backtest_assumptions.get('commission_bps')} bps（买卖双边）")
        lines.append(f"- 印花税：{backtest_assumptions.get('stamp_duty_bps')} bps（仅卖出）")
        lines.append(f"- 滑点：{backtest_assumptions.get('slippage_bps')} bps（买卖双边）")
        lines.append(f"- 样本内/外切分：{backtest_assumptions.get('oos_split_ratio')}")
        lines.append(f"- OOS 起始日期：{backtest_assumptions.get('oos_split_date')}")
        lines.append(f"- 基准：{backtest_assumptions.get('benchmark', '未指定')}")
        for item in backtest_assumptions.get("bias_notes", []):
            lines.append(f"- {item}")
    for factor_name, diagnostics in tradability_diagnostics.items():
        applied = ", ".join(diagnostics.get("applied_rules", [])) or "无"
        missing = ", ".join(diagnostics.get("missing_fields", [])) or "无"
        lines.append(f"- {factor_name} 已应用交易状态：{applied}")
        lines.append(f"- {factor_name} 未应用字段：{missing}")
    if universe_diagnostics.get("warning"):
        lines.append(f"- {universe_diagnostics['warning']}")

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
