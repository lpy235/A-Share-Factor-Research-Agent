# Demo Report

## Project

A-Share Factor Research Agent is a quant strategy / AI Agent internship portfolio project.

It demonstrates a controlled research loop:

```text
factor idea extraction
-> safe Factor DSL
-> deterministic factor execution
-> IC / RankIC validation
-> grouped return and long-short backtest
-> factor selection
-> traceable Markdown report
```

## First-Version Demo

The first version runs offline with fixture A-share data and deterministic factor extraction.

Default demo topic:

```text
A股量价类动量因子
```

Extracted factor:

```text
volume_price_momentum
```

Formula:

```text
rank(returns(close, 20) * ts_mean(volume, 20) / ts_mean(volume, 60))
```

## Verification

The first version is expected to pass:

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
```

## Limitations

- Fixture data is used for deterministic demo execution.
- Live AKShare data is implemented as an adapter but not required by tests.
- LLM extraction is represented by deterministic fallback rules so the project works without API keys.
- Historical backtests are research artifacts and do not constitute investment advice.

## Next Steps

- Replace deterministic workflow with full LangGraph `StateGraph`.
- Add embedding-backed RAG retrieval.
- Add live structured LLM extraction with schema validation and retry.
- Add document upload endpoint.
- Add real public source search integration.
