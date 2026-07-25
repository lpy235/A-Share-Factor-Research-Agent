# Development Guide

## Common Commands

```bash
make test
make eval
make compile
make check
make run
make backfill-raw-ashare START=2016-01-01 END=2026-07-24 DAILY_BARS_CSV=/path/to/raw_daily_bars.csv SOURCE=reviewed_snapshot
make update-raw-ashare TRADE_DATE=2026-07-24 PARENT_VERSION=v20260723_xxxxxxxx DAILY_BARS_CSV=/path/to/latest_snapshot.csv SOURCE=reviewed_snapshot
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

## Market Data Operations

Market-data commands import an explicit local CSV file. They do not fetch online data. The CSV must contain unadjusted `symbol`, `trade_date`, `open`, `high`, `low`, `close`, `volume`, and `amount` columns; source, ingestion time, and data version are assigned by the warehouse.

Use `make resume-raw-ashare RUN_ID=<id> DAILY_BARS_CSV=<path> SOURCE=<name>` after an interrupted import. Published versions are immutable. A failed or incomplete draft remains on disk for diagnosis and resume; do not delete a published version to recover from a bad import.

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
