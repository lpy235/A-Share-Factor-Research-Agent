# Development Guide

## Common Commands

```bash
make test
make eval
make compile
make check
make run
```

Equivalent direct commands:

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
git diff --check
uvicorn app.main:app --port 8000
```

## Local Files

These are generated locally and ignored by git:

```text
.venv/
.pytest_cache/
runs.db
uploaded_docs/
data_cache/
logs/
demo_artifacts/*.png
__pycache__/
```

## Environment

Copy `.env.example` if live services are needed:

```bash
cp .env.example .env
```

The default project path does not require an OpenAI key, AKShare connectivity, or live source fetching.

## Verification Policy

Before pushing a milestone, run:

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
git diff --check
```

For UI changes, also start the server and run one deterministic dashboard workflow from `/`.

## Development History

Detailed implementation specs and plans live under:

```text
docs/superpowers/specs/
docs/superpowers/plans/
```

Those files are retained as an execution archive. For current usage, prefer the top-level README and the concise docs in `docs/`.

