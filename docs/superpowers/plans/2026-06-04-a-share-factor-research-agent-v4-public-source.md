# A-Share Factor Research Agent V4 Public Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic public-source discovery to `auto` and `hybrid` research runs.

**Architecture:** Keep the V3 graph unchanged. Extend `LoadDocumentsNode` with a public source discovery service that returns parsed source dictionaries compatible with existing chunking and extraction nodes.

**Tech Stack:** Python, FastAPI, LangGraph, source policy filters, deterministic fixture public sources, pytest.

---

## Tasks

### Task 1: Public Source Discovery

- [x] Create `app/sources/discovery.py`.
- [x] Add deterministic public source seeds.
- [x] Apply `SourcePolicy` before returning candidates.
- [x] Add optional live fetch support behind `allow_live_fetch`.

### Task 2: Graph Integration

- [x] Extend `ResearchState` with `max_sources` and `allow_live_fetch`.
- [x] Extend `LoadDocumentsNode` to support `auto` and `hybrid`.
- [x] Record source discovery fallback events.
- [x] Preserve V3 upload behavior.

### Task 3: API and Docs

- [x] Add `max_sources` and `allow_live_fetch` to `ResearchRunRequest`.
- [x] Update README and REPORT with V4 auto-source mode.
- [x] Update harness state.

### Task 4: Tests and Verification

- [x] Add tests for source discovery.
- [x] Add workflow tests for auto and hybrid mode.
- [x] Add API test for auto mode.
- [x] Run `pytest -v`.
- [x] Run `python evals/run_eval.py`.
- [x] Run `python -m compileall app`.
- [x] Commit and push V4.
