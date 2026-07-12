# Demo Guide

## Fast Path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
pytest -v
python evals/run_eval.py
uvicorn app.main:app --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

Click `Run research` with the default settings.

## Review Checklist

1. The dashboard starts from a realistic quant research topic: `A股量价类动量因子`.
2. The run uses public or uploaded source material and retrieves evidence.
3. Extracted hypotheses become restricted Factor DSL formulas.
4. The workflow validates formulas before execution.
5. Backtest metrics separate IS and OOS Rank IC and show IC decay.
6. The artifact list includes report Markdown, metrics JSON, factor-correlation JSON, and PNG charts.
7. The trace tab shows every LangGraph node and fallback decision.

## API-Only Demo

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","data_provider":"fixture","cache_enabled":true}'
```

Then inspect events:

```bash
curl -s http://127.0.0.1:8000/runs/<run_id>/events
```

## Uploaded Document Demo

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -F "file=@fixture_docs/demo_factor_note.md"
```

Use the returned `document_id`:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload","document_ids":["<document_id>"]}'
```

## Safety Notes

- No auto-trading or order execution.
- No stock recommendations or return promises.
- Model output is constrained to schema-validated hypotheses and a whitelisted Factor DSL.
- Live LLM calls, public fetching, and AKShare data are explicit opt-ins with deterministic fallbacks.
