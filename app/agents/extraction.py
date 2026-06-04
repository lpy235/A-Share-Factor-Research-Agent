import json

from app.agents.schemas import FactorHypothesis


def parse_factor_extraction_response(text: str) -> list[FactorHypothesis]:
    data = json.loads(text)
    return [FactorHypothesis(**item) for item in data.get("factors", [])]

