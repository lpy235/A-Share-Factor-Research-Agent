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


class FactorSelector:
    """Multi-condition factor selector with OOS-aware thresholds.

    Default thresholds are calibrated for A-share daily factor research:
    - |mean_rank_ic| > 0.02: filters noise-level factors
    - |ICIR| > 0.3: ensures IC stability over time
    - coverage >= 0.8: requires factor to be computable for most stocks
    - OOS decay ratio < 2.0: flags potential overfitting (IS >> OOS)
    """

    def __init__(
        self,
        min_abs_rank_ic: float = 0.02,
        min_abs_icir: float = 0.3,
        min_coverage: float = 0.8,
        max_missing: float = 0.2,
        max_drawdown_limit: float = -0.5,
        max_ic_decay_ratio: float = 2.0,
    ) -> None:
        self.min_abs_rank_ic = min_abs_rank_ic
        self.min_abs_icir = min_abs_icir
        self.min_coverage = min_coverage
        self.max_missing = max_missing
        self.max_drawdown_limit = max_drawdown_limit
        self.max_ic_decay_ratio = max_ic_decay_ratio

    def select(self, scores: list[FactorScore]) -> list[FactorScore]:
        selected: list[FactorScore] = []
        for score in scores:
            if abs(score.mean_rank_ic) < self.min_abs_rank_ic:
                continue
            if abs(score.icir) < self.min_abs_icir:
                continue
            if score.coverage_ratio < self.min_coverage:
                continue
            if score.missing_ratio > self.max_missing:
                continue
            if score.max_drawdown < self.max_drawdown_limit:
                continue
            if (
                score.ic_decay_ratio is not None
                and score.ic_decay_ratio > self.max_ic_decay_ratio
            ):
                continue
            selected.append(score)
        return selected

    def rejection_reasons(self, scores: list[FactorScore]) -> dict[str, list[str]]:
        """Diagnostic: return rejection reasons for each factor score."""
        reasons: dict[str, list[str]] = {}
        for score in scores:
            item_reasons: list[str] = []
            if abs(score.mean_rank_ic) < self.min_abs_rank_ic:
                item_reasons.append(f"|mean_rank_ic|={abs(score.mean_rank_ic):.4f} < {self.min_abs_rank_ic}")
            if abs(score.icir) < self.min_abs_icir:
                item_reasons.append(f"|ICIR|={abs(score.icir):.2f} < {self.min_abs_icir}")
            if score.coverage_ratio < self.min_coverage:
                item_reasons.append(f"coverage={score.coverage_ratio:.2f} < {self.min_coverage}")
            if score.missing_ratio > self.max_missing:
                item_reasons.append(f"missing={score.missing_ratio:.2f} > {self.max_missing}")
            if score.max_drawdown < self.max_drawdown_limit:
                item_reasons.append(f"max_dd={score.max_drawdown:.4f} < {self.max_drawdown_limit}")
            if (
                score.ic_decay_ratio is not None
                and score.ic_decay_ratio > self.max_ic_decay_ratio
            ):
                item_reasons.append(f"ic_decay={score.ic_decay_ratio:.2f} > {self.max_ic_decay_ratio}")
            if item_reasons:
                reasons[score.factor_name] = item_reasons
        return reasons

