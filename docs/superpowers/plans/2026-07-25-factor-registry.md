# 因子库第一期 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist selected research factors as versioned candidates and require explicit human decisions before approval.

**Architecture:** Add a focused SQLite `FactorRegistryStore` beside the run store. A small API reads completed-run payloads, registers only selected factors, and appends decisions without modifying the research workflow.

**Tech Stack:** Python, SQLite, FastAPI, Pydantic, pytest.

---

### Task 1: Registry Store

**Files:** Create `app/storage/factor_registry.py`; modify `app/storage/db.py`; test `tests/test_factor_registry.py`.

- [ ] Write failing tests for candidate registration, version retrieval and append-only approval/rejection decisions.
- [ ] Implement `factor_versions` and `factor_decisions` SQLite tables; store specs, evidence, metrics and data lineage as JSON.
- [ ] Validate statuses against `candidate`, `approved`, `rejected`, `retired`.
- [ ] Run `.venv/bin/pytest tests/test_factor_registry.py -q`.

### Task 2: Registry API

**Files:** Create `app/api/factor_registry.py`; modify `app/main.py`; test `tests/test_factor_registry_api.py`.

- [ ] Add `POST /factor-registry/from-run/{run_id}` that rejects unknown/incomplete/no-selection runs and maps only selected specs into candidates.
- [ ] Add listing and explicit decision endpoints; require decision maker and reason.
- [ ] Verify that response lineage contains the original research run and market-data version.
- [ ] Run focused storage and API tests.

### Task 3: Governance And Verification

**Files:** Modify `docs/research-governance.md`, `README.md`, `.codex-harness/STATE.md`.

- [ ] Document that candidate registration is not approval and decisions remain human-attributable.
- [ ] Run full pytest, Ruff, compileall and diff checks.
- [ ] Commit as `feat: add auditable factor registry`.
