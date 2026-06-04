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

## V2 Document-Driven Demo

V2 upgrades the project from a fixed demo note to user-provided research material.

New workflow:

```text
POST /documents
-> save Markdown/txt/PDF material
-> return document_id
-> POST /research/runs with document_ids
-> parse uploaded document
-> chunk and retrieve relevant content
-> extract factor hypothesis from uploaded text
-> generate Factor DSL
-> validate and backtest
-> return report and events
```

Smoke test result:

```text
uploaded file: fixture_docs/demo_factor_note.md
selected factor: volume_price_momentum
source title in factor spec: demo_factor_note.md
```

## Verification

The current version is expected to pass:

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
```

Latest verified result:

```text
pytest -v                 30 passed
python evals/run_eval.py  accuracy 1.0
python -m compileall app  passed
V2 API smoke test         passed
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
- Add real public source search integration.
- Add real AKShare demo mode and data caching.
