from app.agents.extraction import parse_factor_extraction_response


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

