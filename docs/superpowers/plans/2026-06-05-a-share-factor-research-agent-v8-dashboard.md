# A-Share Factor Research Agent V8 Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FastAPI-served portfolio dashboard for running and reviewing agent research runs.

**Architecture:** Serve static HTML/CSS/JS from `app/web`, expose the dashboard at `/`, and use existing JSON APIs for document upload, research runs, and LangGraph event trace retrieval.

**Tech Stack:** FastAPI, Starlette static files, vanilla HTML/CSS/JavaScript, pytest, in-app browser verification.

---

## Tasks

### Task 1: Dashboard Route and Assets

- [x] Create `app/api/ui.py`.
- [x] Mount `/static` and route `/` in `app/main.py`.
- [x] Create `app/web/index.html`.
- [x] Create `app/web/static/styles.css`.
- [x] Create `app/web/static/app.js`.

### Task 2: Browser Workflow

- [x] Implement document upload through `POST /documents`.
- [x] Implement research run submission through `POST /research/runs`.
- [x] Implement event loading through `GET /runs/{run_id}/events`.
- [x] Render selected factors, formulas, report, and trace events.
- [x] Add loading and error states.

### Task 3: Tests and Documentation

- [x] Add `tests/test_ui.py`.
- [x] Update README with V8 dashboard usage.
- [x] Update REPORT with V8 dashboard notes.
- [x] Update `.codex-harness/STATE.md`.

### Task 4: Verification

- [x] Run `pytest -v`.
- [x] Run `python evals/run_eval.py`.
- [x] Run `python -m compileall app`.
- [x] Run `git diff --check`.
- [x] Start local server and inspect `/` in browser.
- [ ] Commit and push V8.
