# A-Share Factor Research Agent V8 Dashboard Design

## Goal

Build a research dashboard for running and reviewing the A-share factor research agent from the browser.

## Scope

V8 adds a lightweight FastAPI-served UI. It does not add a separate frontend framework, user login, async job queue, database schema changes, or trading/recommendation features.

## User Experience

The first screen is the research workspace:

- A compact run configuration panel for topic, source mode, retrieval mode, extraction mode, data provider, date range, and safety toggles.
- Optional document upload before a run.
- A result area with selected factors, generated Factor DSL, validation/backtest metrics when visible in the report, the Markdown report, and node-level trace events.
- Status and error states for pending, running, completed, and failed runs.

The UI should feel like a quant research workbench, not a landing page. It should be dense, readable, and calm enough for repeated use in an research review.

## Architecture

Static assets live under `app/web`. FastAPI serves `app/web/index.html` at `/` and mounts static assets at `/static`.

The browser calls existing backend APIs:

```text
POST /documents
POST /research/runs
GET /runs/{run_id}/events
GET /health
```

No API contract change is required for V8. The UI derives displayed factor formulas from `factor_specs`, selected factor chips from `selected_factors`, report text from `report_markdown`, and trace details from `/runs/{run_id}/events`.

## Files

```text
app/api/ui.py
app/web/index.html
app/web/static/styles.css
app/web/static/app.js
tests/test_ui.py
README.md
REPORT.md
.codex-harness/STATE.md
```

## Safety and Defaults

Default UI values must keep the workflow deterministic:

```text
source_mode = auto
retrieval_mode = hybrid
extraction_mode = rule
enable_llm_extraction = false
data_provider = fixture
cache_enabled = true
fallback_to_fixture = true
allow_live_fetch = false
```

The UI must not present trading actions, stock recommendations, or return promises.

## Testing

Automated tests should verify:

- `/` returns the dashboard HTML.
- Static CSS and JS are served.
- The HTML includes the research form and references static assets.
- Existing API tests still pass.

Manual/browser verification should run the local FastAPI server, open `/`, start a deterministic fixture run, and confirm that selected factors and trace events render.

