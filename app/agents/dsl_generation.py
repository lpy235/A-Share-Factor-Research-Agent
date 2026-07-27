from app.agents.schemas import FactorHypothesis
from app.factor.dsl import FactorSpec


class FactorDslGenerationService:
    def generate_fallback(self, hypothesis: FactorHypothesis) -> FactorSpec:
        text = f"{hypothesis.factor_name} {hypothesis.hypothesis} {hypothesis.evidence}"
        fields = set(hypothesis.required_fields)
        lowered = text.lower()

        if "volume" in fields and "close" in fields:
            formula = "rank(returns(close, 20) * ts_mean(volume, 20) / ts_mean(volume, 60))"
            lookback = 60
            category = "volume_price"
        elif "波动" in text or "volatility" in lowered:
            formula = "rank(ts_std(returns(close, 1), 20))"
            lookback = 20
            category = "volatility"
        elif "反转" in text or "contrarian" in lowered or hypothesis.category == "reversal":
            formula = "rank(-returns(close, 20))"
            lookback = 20
            category = "reversal"
        else:
            formula = "rank(returns(close, 20))"
            lookback = 20
            category = hypothesis.category or "momentum"

        return FactorSpec(
            factor_name=hypothesis.factor_name,
            hypothesis=hypothesis.hypothesis,
            formula=formula,
            required_fields=sorted(fields or {"close"}),
            direction="positive",
            category=category,
            frequency="daily",
            lookback=lookback,
            source_title=hypothesis.source_title,
            source_url=hypothesis.source_url,
            source_excerpt=hypothesis.evidence,
            confidence=hypothesis.confidence,
        )
