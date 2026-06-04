from dataclasses import dataclass


@dataclass(frozen=True)
class FactorScore:
    factor_name: str
    mean_rank_ic: float
    icir: float
    coverage_ratio: float
    missing_ratio: float
    max_drawdown: float


class FactorSelector:
    def __init__(
        self,
        min_abs_rank_ic: float = 0.02,
        min_abs_icir: float = 0.3,
        min_coverage: float = 0.8,
        max_missing: float = 0.2,
        max_drawdown_limit: float = -0.5,
    ) -> None:
        self.min_abs_rank_ic = min_abs_rank_ic
        self.min_abs_icir = min_abs_icir
        self.min_coverage = min_coverage
        self.max_missing = max_missing
        self.max_drawdown_limit = max_drawdown_limit

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
            selected.append(score)
        return selected

