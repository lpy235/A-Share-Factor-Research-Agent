from typing import Literal

from pydantic import BaseModel, Field


Direction = Literal["positive", "negative", "unknown"]


class FactorSpec(BaseModel):
    factor_name: str
    hypothesis: str
    formula: str
    required_fields: list[str]
    direction: Direction
    category: str
    frequency: Literal["daily"] = "daily"
    lookback: int = Field(ge=1)
    source_title: str
    source_url: str | None = None
    source_excerpt: str
    confidence: float = Field(ge=0.0, le=1.0)

