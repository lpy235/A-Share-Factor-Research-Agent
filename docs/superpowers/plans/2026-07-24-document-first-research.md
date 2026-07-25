# Document-First Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make report upload work without a manually entered research topic.

**Architecture:** Remove the dashboard textarea's seeded sample text while retaining the sample action's explicit topic assignment. The existing upload-mode API contract derives a title from the uploaded filename, so no backend behavior changes are required.

**Tech Stack:** HTML, browser JavaScript, FastAPI, pytest.

---

### Task 1: Remove the Seeded Topic and Add a UI Regression Test

**Files:**
- Modify: `app/web/index.html:41-49`
- Modify: `tests/test_ui.py`

- [x] **Step 1: Add a markup test**

Assert that the topic textarea exists, retains the upload-oriented placeholder, and does not contain `A股量价类动量因子` as initial content.

- [x] **Step 2: Run the focused UI test**

Run: `.venv/bin/pytest tests/test_ui.py -q`

Expected: FAIL because the dashboard seeds the sample topic.

- [x] **Step 3: Remove only the initial textarea content**

Keep the `<textarea>` identifier, name, rows, and placeholder unchanged. Remove its inner sample text so `valueOf("#research-topic")` produces an empty value until the user types or clicks the sample action.

- [x] **Step 4: Verify UI and API behavior**

Run: `.venv/bin/pytest tests/test_ui.py tests/test_research_api.py -q`

Expected: PASS; upload-only requests still derive the document title and sample research still receives its explicit topic.

- [x] **Step 5: Restart and smoke-test the local server**

Run the local Uvicorn server on `127.0.0.1:8000`, then verify `GET /health` returns `{"status":"ok"}`.
