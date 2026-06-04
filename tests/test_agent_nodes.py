from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.rag.chunker import DocumentChunk


def test_extract_hypotheses_from_chunks_rule_based():
    chunks = [
        DocumentChunk("c1", "demo report", "user_upload", "成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。")
    ]
    result = extract_hypotheses_from_chunks("A股量价动量因子", chunks)
    assert len(result) >= 1
    assert result[0].required_fields == ["close", "volume"]


def test_generate_factor_specs_from_hypotheses():
    chunks = [
        DocumentChunk("c1", "demo report", "user_upload", "成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。")
    ]
    hypotheses = extract_hypotheses_from_chunks("A股量价动量因子", chunks)
    specs = generate_factor_specs(hypotheses)
    assert len(specs) >= 1
    assert "volume" in specs[0].formula

