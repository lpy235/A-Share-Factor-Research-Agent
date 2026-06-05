from app.agents.extraction import StructuredFactorExtractor, parse_factor_extraction_response
from app.rag.chunker import DocumentChunk


def test_parse_factor_extraction_response():
    text = """
    {
      "factors": [
        {
          "factor_name": "volume_price_momentum",
          "hypothesis": "量价齐升可能代表趋势延续",
          "evidence": "成交量放大且价格上涨",
          "source_title": "demo report",
          "source_url": null,
          "category": "volume_price",
          "required_fields": ["close", "volume"],
          "confidence": 0.76
        }
      ]
    }
    """
    result = parse_factor_extraction_response(text)
    assert len(result) == 1
    assert result[0].factor_name == "volume_price_momentum"
    assert result[0].required_fields == ["close", "volume"]


def test_parse_factor_extraction_response_strips_markdown_fence():
    text = """
    ```json
    {
      "factors": [
        {
          "factor_name": "momentum_20",
          "hypothesis": "过去收益率较高的股票可能存在趋势延续",
          "evidence": "过去收益率和动量效应相关",
          "source_title": "demo report",
          "source_url": null,
          "category": "momentum",
          "required_fields": ["close"],
          "confidence": 0.7
        }
      ]
    }
    ```
    """
    result = parse_factor_extraction_response(text)
    assert result[0].factor_name == "momentum_20"


class FakeLlmClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def text(self, prompt: str) -> str:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def test_structured_extractor_uses_valid_llm_json():
    client = FakeLlmClient(
        [
            """
            {
              "factors": [
                {
                  "factor_name": "volume_price_momentum",
                  "hypothesis": "成交量放大且价格上涨可能代表趋势延续",
                  "evidence": "成交量放大且价格上涨",
                  "source_title": "demo report",
                  "source_url": null,
                  "category": "volume_price",
                  "required_fields": ["close", "volume"],
                  "confidence": 0.8
                }
              ]
            }
            """
        ]
    )
    chunks = [
        DocumentChunk("c1", "demo report", "public_article", "成交量放大且价格上涨，可构造量价动量因子。")
    ]

    result = StructuredFactorExtractor(client).extract(
        "A股量价类动量因子",
        chunks,
        extraction_mode="llm",
    )

    assert result.hypotheses[0].factor_name == "volume_price_momentum"
    assert result.diagnostics["llm_attempted"] is True
    assert result.diagnostics["fallback_used"] is False


def test_structured_extractor_repairs_invalid_llm_json():
    client = FakeLlmClient(
        [
            "not json",
            """
            {
              "factors": [
                {
                  "factor_name": "volume_price_momentum",
                  "hypothesis": "成交量放大且价格上涨可能代表趋势延续",
                  "evidence": "成交量放大且价格上涨",
                  "source_title": "demo report",
                  "source_url": null,
                  "category": "volume_price",
                  "required_fields": ["close", "volume"],
                  "confidence": 0.8
                }
              ]
            }
            """,
        ]
    )
    chunks = [
        DocumentChunk("c1", "demo report", "public_article", "成交量放大且价格上涨，可构造量价动量因子。")
    ]

    result = StructuredFactorExtractor(client).extract(
        "A股量价类动量因子",
        chunks,
        extraction_mode="llm",
        llm_retry_count=1,
    )

    assert result.hypotheses[0].factor_name == "volume_price_momentum"
    assert result.diagnostics["llm_retry_count"] == 1


def test_structured_extractor_falls_back_after_invalid_llm_output():
    client = FakeLlmClient(["not json", '{"factors": []}'])
    chunks = [
        DocumentChunk("c1", "demo report", "public_article", "成交量放大且价格上涨，可构造量价动量因子。")
    ]

    result = StructuredFactorExtractor(client).extract(
        "A股量价类动量因子",
        chunks,
        extraction_mode="llm",
        llm_retry_count=1,
    )

    assert result.hypotheses[0].factor_name == "volume_price_momentum"
    assert result.diagnostics["fallback_used"] is True
    assert result.diagnostics["fallback_reason"] == "llm_invalid_output"
