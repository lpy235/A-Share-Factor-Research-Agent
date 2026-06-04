# Checks

## Stage 0 Checks

```bash
pwd
find .codex-harness -type f | sort
git status --short
git remote -v
```

## Stage 1 Checks

Run from repository root:

```bash
python - <<'PY'
import app
print("ok")
PY
```

```bash
pytest tests/test_source_policy.py -v
pytest tests/test_factor_dsl.py -v
pytest tests/test_factor_operators.py -v
pytest tests/test_metrics.py -v
pytest tests/test_selector.py -v
pytest tests/test_report.py -v
pytest -v
```

```bash
python evals/run_eval.py
```

```bash
uvicorn app.main:app --port 8000
```

API smoke test:

```bash
curl -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload"}'
```

## Stage 2 Checks

```bash
pytest tests/test_storage_events.py -v
pytest tests/test_keyword_retriever.py -v
pytest tests/test_public_source_fetch.py -v
pytest tests/test_extraction_parser.py -v
pytest tests/test_agent_nodes.py -v
pytest tests/test_charts.py -v
pytest -v
```

```bash
python evals/run_eval.py
```

Event API smoke test:

```bash
curl http://127.0.0.1:8000/runs/<run_id>/events
```

## Final Checks

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
git status --short
```

Final push check:

```bash
git remote -v
git branch --show-current
```

