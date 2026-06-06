from typing import Any


def build_audit_trail(state: dict[str, Any]) -> list[dict[str, str]]:
    selected = set(state.get("selected_factors", []))
    metrics_by_factor = {item.get("factor_name"): item for item in state.get("metrics", [])}
    entries = [
        {
            "title": "资料选择",
            "detail": _source_detail(state),
        },
        {
            "title": "因子抽取",
            "detail": (
                f"系统从 {len(state.get('chunks', []))} 个资料片段中抽取 "
                f"{len(state.get('hypotheses', []))} 条因子假设。"
            ),
        },
        {
            "title": "DSL 校验",
            "detail": (
                f"{len(state.get('factor_specs', []))} 个公式通过受限 Factor DSL 校验，"
                "只允许白名单字段和运算符执行。"
            ),
        },
        {
            "title": "回测筛选",
            "detail": _selection_detail(selected, metrics_by_factor),
        },
    ]
    if state.get("warnings"):
        entries.append({"title": "运行警示", "detail": "；".join(state.get("warnings", []))})
    return entries


def _source_detail(state: dict[str, Any]) -> str:
    diagnostics = state.get("source_diagnostics", {})
    accepted = diagnostics.get("accepted_count", len(state.get("sources", [])))
    rejected = diagnostics.get("rejected_count", 0)
    return (
        f"资料模式为 {state.get('source_mode', 'upload')}，"
        f"接受 {accepted} 个公开或上传来源，过滤 {rejected} 个不符合策略的来源。"
    )


def _selection_detail(selected: set[str], metrics_by_factor: dict[str, dict[str, Any]]) -> str:
    if not metrics_by_factor:
        return "没有可用于筛选的回测指标。"
    if not selected:
        return "本次候选因子未通过覆盖率、缺失率和稳定性筛选。"
    descriptions = []
    for factor_name in sorted(selected):
        metric = metrics_by_factor.get(factor_name, {})
        descriptions.append(
            f"{factor_name} 入选，Rank IC={metric.get('mean_rank_ic')}，"
            f"覆盖率={metric.get('coverage_ratio')}。"
        )
    return " ".join(descriptions)
