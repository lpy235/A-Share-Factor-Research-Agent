# A-Share Factor Research Agent V6 Structured LLM Extraction Design

## Goal

V6 adds structured LLM-based factor hypothesis extraction while preserving deterministic offline execution.

The agent should be able to use retrieved evidence chunks, ask an LLM for candidate factor hypotheses, validate the JSON response with `FactorHypothesis`, and fall back to rule-based extraction if the LLM is unavailable or returns invalid output.

## Scope

In scope:

- Add `extraction_mode` with `rule`, `llm`, and `hybrid`.
- Add `enable_llm_extraction` as an explicit API switch.
- Add an extraction service that validates LLM JSON with Pydantic.
- Add one retry/repair attempt for malformed JSON.
- Store extraction diagnostics in graph state and trace summaries.
- Preserve deterministic fallback behavior.

Out of scope:

- LLM-generated arbitrary Python.
- LLM-generated Factor DSL execution without validation.
- Multi-turn human review.
- Model-specific prompt tuning beyond a compact structured extraction prompt.

## Behavior

```text
rule: use deterministic extraction only
llm: try LLM extraction first, fall back to rule extraction on failure
hybrid: try LLM only when enable_llm_extraction=true, otherwise use rules
```

Defaults:

```text
extraction_mode = "hybrid"
enable_llm_extraction = false
llm_retry_count = 1
```

This keeps API demos stable without API keys.

## Data Flow

```text
retrieved chunks
-> StructuredFactorExtractor
-> LLM JSON prompt when enabled
-> parse JSON
-> validate FactorHypothesis list
-> fallback rule extraction when needed
-> extraction diagnostics
-> Factor DSL generation
```

## Success Criteria

- Existing V5 tests continue to pass.
- Rule mode preserves current behavior.
- LLM mode can be tested with a fake client returning valid JSON.
- Invalid LLM output triggers fallback and diagnostics.
- API accepts extraction controls.
- Events include extraction method and fallback reason.

