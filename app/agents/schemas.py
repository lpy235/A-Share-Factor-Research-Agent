from pydantic import BaseModel, Field


class FactorHypothesis(BaseModel):
    factor_name: str
    hypothesis: str
    evidence: str
    source_title: str
    source_url: str | None = None
    category: str
    required_fields: list[str]
    confidence: float = Field(ge=0.0, le=1.0)

