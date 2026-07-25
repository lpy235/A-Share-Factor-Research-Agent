from dataclasses import dataclass


@dataclass(frozen=True)
class FactorScore:
    factor_name: str
    mean_rank_ic: float
    icir: float
    coverage_ratio: float
    missing_ratio: float
    max_drawdown: float
    mean_rank_ic_oos: float | None = None
    ic_decay_ratio: float | None = None
    walk_forward_positive_ratio: float | None = None
    walk_forward_sign_consistent: bool | None = None
    walk_forward_insufficient_data: bool = True


class FactorSelector:
    """Multi-condition factor selector with OOS-aware thresholds.

    Default thresholds are calibrated for A-share daily factor research:
    - |mean_rank_ic| > 0.02: filters noise-level factors
    - |ICIR| > 0.3: ensures IC stability over time
    - coverage >= 0.8: requires factor to be computable for most stocks
    - OOS Rank IC >= 0.01 and aligned with IS: requires out-of-sample validity
    - OOS decay ratio < 2.0: flags potential overfitting (IS >> OOS)
    - walk-forward positive ratio >= 0.6 and consistent sign: requires stability
    """

    def __init__(
        self,
        min_abs_rank_ic: float = 0.02,
        min_abs_icir: float = 0.3,
        min_coverage: float = 0.8,
        max_missing: float = 0.2,
        max_drawdown_limit: float = -0.5,
        min_abs_rank_ic_oos: float = 0.01,
        max_ic_decay_ratio: float = 2.0,
        min_walk_forward_positive_ratio: float = 0.6,
    ) -> None:
        self.min_abs_rank_ic = min_abs_rank_ic
        self.min_abs_icir = min_abs_icir
        self.min_coverage = min_coverage
        self.max_missing = max_missing
        self.max_drawdown_limit = max_drawdown_limit
        self.min_abs_rank_ic_oos = min_abs_rank_ic_oos
        self.max_ic_decay_ratio = max_ic_decay_ratio
        self.min_walk_forward_positive_ratio = min_walk_forward_positive_ratio

    def select(self, scores: list[FactorScore]) -> list[FactorScore]:
        selected: list[FactorScore] = []
        for score in scores:
            if not self._rejection_reasons(score):
                selected.append(score)
        return selected

    def rejection_reasons(self, scores: list[FactorScore]) -> dict[str, list[str]]:
        """Diagnostic: return rejection reasons for each factor score."""
        reasons: dict[str, list[str]] = {}
        for score in scores:
            item_reasons = self._rejection_reasons(score)
            if item_reasons:
                reasons[score.factor_name] = item_reasons
        return reasons

    def _rejection_reasons(self, score: FactorScore) -> list[str]:
        reasons: list[str] = []
        if abs(score.mean_rank_ic) < self.min_abs_rank_ic:
            reasons.append(f"|mean_rank_ic|={abs(score.mean_rank_ic):.4f} < {self.min_abs_rank_ic}")
        if abs(score.icir) < self.min_abs_icir:
            reasons.append(f"|ICIR|={abs(score.icir):.2f} < {self.min_abs_icir}")
        if score.coverage_ratio < self.min_coverage:
            reasons.append(f"coverage={score.coverage_ratio:.2f} < {self.min_coverage}")
        if score.missing_ratio > self.max_missing:
            reasons.append(f"missing={score.missing_ratio:.2f} > {self.max_missing}")
        if score.max_drawdown < self.max_drawdown_limit:
            reasons.append(f"max_dd={score.max_drawdown:.4f} < {self.max_drawdown_limit}")
        if score.mean_rank_ic_oos is None:
            reasons.append("oos_rank_ic_missing")
        elif abs(score.mean_rank_ic_oos) < self.min_abs_rank_ic_oos:
            reasons.append(
                f"abs_oos_rank_ic={abs(score.mean_rank_ic_oos):.4f} < {self.min_abs_rank_ic_oos}"
            )
        elif score.mean_rank_ic * score.mean_rank_ic_oos <= 0:
            reasons.append("oos_direction_mismatch")
        if (
            score.ic_decay_ratio is not None
            and score.ic_decay_ratio > self.max_ic_decay_ratio
        ):
            reasons.append(f"ic_decay={score.ic_decay_ratio:.2f} > {self.max_ic_decay_ratio}")
        if score.walk_forward_insufficient_data:
            reasons.append("walk_forward_insufficient_data")
        elif score.walk_forward_sign_consistent is not True:
            reasons.append("walk_forward_sign_inconsistent")
        elif score.walk_forward_positive_ratio is None:
            reasons.append("walk_forward_positive_ratio_missing")
        elif score.walk_forward_positive_ratio < self.min_walk_forward_positive_ratio:
            reasons.append(
                "walk_forward_positive_ratio="
                f"{score.walk_forward_positive_ratio:.2f} < "
                f"{self.min_walk_forward_positive_ratio}"
            )
        return reasons
