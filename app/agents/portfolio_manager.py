"""Deterministic, non-authoritative factor review recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Recommendation = Literal["approve", "reject", "continue_research"]


@dataclass(frozen=True)
class PortfolioManagerRecommendation:
    recommendation: Recommendation
    reasons: list[str]
    evidence: dict[str, Any]


class PortfolioManagerAgent:
    """Applies disclosed review rules and never changes a registry decision."""

    def recommend(
        self,
        *,
        metrics: dict[str, Any],
        long_only_metrics: dict[str, Any] | None,
        data_version: str | None,
        manifest_hash: str | None,
        similarity: float | None = None,
    ) -> PortfolioManagerRecommendation:
        reasons: list[str] = []
        oos_ic = _number(metrics.get("mean_rank_ic_oos"))
        is_ic = _number(metrics.get("mean_rank_ic"))
        positive_ratio = _number(metrics.get("walk_forward_positive_ratio"))
        consistent = metrics.get("walk_forward_sign_consistent") is True
        drawdown = _number((long_only_metrics or {}).get("max_drawdown"))
        cost = _number((long_only_metrics or {}).get("cumulative_cost"))

        if not data_version or not manifest_hash:
            reasons.append("缺少固定数据版本或 manifest 哈希，不能进入批准建议。")
        if oos_ic is None or abs(oos_ic) < 0.01:
            reasons.append("OOS Rank IC 未达到 0.01 的最低绝对值。")
        if is_ic is not None and oos_ic is not None and is_ic * oos_ic <= 0:
            reasons.append("IS/OOS Rank IC 方向不一致。")
        if positive_ratio is None or positive_ratio < 0.6 or not consistent:
            reasons.append("Walk-forward 稳定性未达到正 IC 比例 60% 且方向一致的门槛。")
        if similarity is not None and similarity >= 0.9:
            reasons.append("与已登记因子相似度过高，需要比较增量价值。")
        if drawdown is not None and drawdown < -0.5:
            reasons.append("净组合最大回撤低于 -50%，需要拒绝。")

        hard_reject = drawdown is not None and drawdown < -0.5
        if hard_reject:
            decision: Recommendation = "reject"
        elif not reasons and (cost is None or cost >= 0):
            decision = "approve"
            reasons.append("OOS、Walk-forward、成本与数据谱系均满足当前建议规则。")
        else:
            decision = "continue_research"
        return PortfolioManagerRecommendation(
            recommendation=decision,
            reasons=reasons,
            evidence={
                "mean_rank_ic": is_ic,
                "mean_rank_ic_oos": oos_ic,
                "walk_forward_positive_ratio": positive_ratio,
                "walk_forward_sign_consistent": consistent,
                "cumulative_cost": cost,
                "max_drawdown": drawdown,
                "similarity": similarity,
                "data_version": data_version,
                "manifest_hash": manifest_hash,
            },
        )


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
