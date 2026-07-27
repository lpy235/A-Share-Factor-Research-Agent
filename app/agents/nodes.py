from app.agents.dsl_generation import FactorDslGenerationService
from app.agents.schemas import FactorHypothesis
from app.factor.dsl import FactorSpec
from app.rag.chunker import DocumentChunk


def extract_hypotheses_from_chunks(
    research_topic: str,
    chunks: list[DocumentChunk],
) -> list[FactorHypothesis]:
    hypotheses: list[FactorHypothesis] = []
    for chunk in chunks:
        text = chunk.text
        lowered = text.lower()
        if "量价" in text or ("成交量" in text and "价格" in text):
            hypotheses.append(
                FactorHypothesis(
                    factor_name="volume_price_momentum",
                    hypothesis="成交量放大且价格上涨可能代表趋势延续。",
                    evidence=text[:200],
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    category="volume_price",
                    required_fields=["close", "volume"],
                    confidence=0.75,
                )
            )
        elif "反转" in text or "contrarian" in lowered:
            hypotheses.append(
                FactorHypothesis(
                    factor_name="contrarian_loser_20",
                    hypothesis="过去收益最低的股票可能在后续期间出现横截面反转。",
                    evidence=text[:200],
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    category="reversal",
                    required_fields=["close"],
                    confidence=0.75,
                )
            )
        elif "动量" in text or "过去收益" in text or "momentum" in lowered:
            hypotheses.append(
                FactorHypothesis(
                    factor_name="momentum_20",
                    hypothesis="过去收益率较高的股票可能存在短期趋势延续。",
                    evidence=text[:200],
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    category="momentum",
                    required_fields=["close"],
                    confidence=0.7,
                )
            )
        elif "波动" in text:
            hypotheses.append(
                FactorHypothesis(
                    factor_name="volatility_20",
                    hypothesis="短期波动率可能刻画风险补偿或拥挤交易。",
                    evidence=text[:200],
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    category="volatility",
                    required_fields=["close"],
                    confidence=0.65,
                )
            )
    return hypotheses


def generate_factor_specs(hypotheses: list[FactorHypothesis]) -> list[FactorSpec]:
    service = FactorDslGenerationService()
    return [service.generate_fallback(item) for item in hypotheses]
