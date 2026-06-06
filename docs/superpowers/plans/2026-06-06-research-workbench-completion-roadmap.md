# Research Workbench Completion Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current end-to-end factor research workflow into a fuller research workbench with richer artifacts, resumable experiments, stronger source discovery, more rigorous A-share assumptions, and explainable agent decisions.

**Architecture:** Keep the existing FastAPI + LangGraph + static dashboard architecture. Add thin, testable modules around artifacts, run persistence, source connectors, market assumptions, and audit summaries rather than rewriting the workflow.

**Tech Stack:** FastAPI, LangGraph, SQLite, pandas, matplotlib, static HTML/CSS/JavaScript, pytest.

---

## Version Sequence

### V9: Research Artifacts and Downloadable Report Bundle

**Purpose:** Make each run produce inspectable research artifacts, not only tables and Markdown text.

**Files:**
- Create: `app/storage/artifacts.py`
- Modify: `app/reports/charts.py`
- Modify: `app/api/research.py`
- Modify: `app/api/runs.py`
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Modify: `app/web/static/styles.css`
- Test: `tests/test_artifacts.py`
- Test: `tests/test_research_api.py`
- Test: `tests/test_ui.py`

**Deliverables:**
- Artifact manifest per run.
- Downloadable `report.md`, `metrics.json`, `factors.json`, and `bundle.json`.
- PNG charts for metric overview and selected factor quality.
- `GET /runs/{run_id}/artifacts`
- `GET /runs/{run_id}/artifacts/{artifact_name}`
- Dashboard section for charts and report bundle downloads.

**Verification:**
- `pytest tests/test_artifacts.py tests/test_research_api.py tests/test_ui.py -v`
- `pytest -v`
- `python evals/run_eval.py`
- HTTP smoke test for artifact list and download.

### V10: Experiment History and Reopenable Runs

**Purpose:** Let users reopen past research runs instead of losing context after each execution.

**Files:**
- Create: `app/storage/runs.py`
- Modify: `app/storage/db.py`
- Modify: `app/api/research.py`
- Modify: `app/api/runs.py`
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Test: `tests/test_run_store.py`
- Test: `tests/test_research_api.py`

**Deliverables:**
- SQLite `runs` table with run id, topic, config JSON, response JSON, status, timestamps.
- `GET /runs`
- `GET /runs/{run_id}`
- Dashboard history panel with recent runs and reopen action.

**Verification:**
- Create two runs, list them, reopen each run, and verify stable response payloads.

### V11: Real Public Source Discovery with Policy Gates

**Purpose:** Improve automatic material discovery while preserving public-source boundaries.

**Files:**
- Modify: `app/sources/search.py`
- Modify: `app/sources/discovery.py`
- Modify: `app/sources/source_policy.py`
- Modify: `app/agents/graph_nodes.py`
- Test: `tests/test_public_source_fetch.py`
- Test: `tests/test_source_discovery.py`
- Test: `tests/test_source_policy.py`

**Deliverables:**
- Optional live public search connector.
- URL policy checks before fetch.
- Source diagnostics explaining accepted, rejected, and fallback sources.
- Evidence snippets linked to extracted factors.

**Verification:**
- Mock live search responses.
- Confirm login-required, paid, CNKI, and unsupported sources are rejected.
- Confirm seed fallback remains deterministic.

### V12: A-Share Data and Backtest Assumption Panel

**Purpose:** Make the research output honest about A-share data assumptions and backtest limitations.

**Files:**
- Modify: `app/data/ashare_provider.py`
- Modify: `app/data/provider_factory.py`
- Modify: `app/backtest/single_factor.py`
- Modify: `app/backtest/metrics.py`
- Modify: `app/agents/graph_nodes.py`
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Test: `tests/test_metrics.py`
- Test: `tests/test_research_api.py`

**Deliverables:**
- Explicit universe and date diagnostics.
- Trading assumptions in API response and dashboard.
- Turnover, transaction cost, and rebalance frequency fields.
- Bias notes for fixture, AKShare, and future real providers.

**Verification:**
- Fixture runs include deterministic assumptions.
- AKShare fallback explains provider failure without hiding it.

### V13: Agent Audit and Decision Explanation

**Purpose:** Upgrade trace events from raw logs into a readable research audit trail.

**Files:**
- Create: `app/agents/audit.py`
- Modify: `app/agents/graph_nodes.py`
- Modify: `app/reports/markdown_report.py`
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Test: `tests/test_agent_audit.py`
- Test: `tests/test_report.py`

**Deliverables:**
- Per-node explanation summaries.
- Source selection rationale.
- Factor selection/rejection reasons.
- Fallback and confidence notes.
- Dashboard audit panel and report section.

**Verification:**
- Runs expose non-empty audit entries.
- Report includes audit summary.
- UI shows audit entries without requiring raw JSON inspection.

## Current Execution Focus

Start with V9. It creates the visible product lift needed before deeper data and discovery work.

