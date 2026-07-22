from app.agents.graph_nodes import validate_dsl_node
from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.factor.dsl import FactorSpec
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


def test_validate_dsl_node_excludes_negative_window_and_validates_fallback():
    invalid_spec = FactorSpec(
        factor_name="forward_delay",
        hypothesis="测试负窗口不得进入执行流程。",
        formula="delay(close, -1)",
        required_fields=["close"],
        direction="positive",
        category="test",
        frequency="daily",
        lookback=20,
        source_title="test report",
        source_excerpt="测试负窗口。",
        confidence=0.5,
    )

    result = validate_dsl_node(
        {
            "factor_specs": [invalid_spec.model_dump()],
            "warnings": [],
        }
    )

    first_validation = result["validation_results"][0]
    assert first_validation["factor_name"] == "forward_delay"
    assert first_validation["valid"] is False
    assert "invalid_window:delay" in first_validation["errors"]
    assert result["factor_specs"]
    assert result["validation_results"][-1]["valid"] is True
    assert result["factor_specs"][0]["formula"] != invalid_spec.formula
    assert any("forward_delay" in warning for warning in result["warnings"])
    assert any(
        event["event_type"] == "node_fallback"
        and event["payload"]["reason"] == "no_valid_specs"
        for event in result["trace"]
    )
