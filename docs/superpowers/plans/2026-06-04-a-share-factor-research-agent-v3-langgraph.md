# A-Share Factor Research Agent V3 LangGraph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the V2 monolithic research workflow with a LangGraph `StateGraph` while preserving the public API and deterministic demo behavior.

**Architecture:** Keep `run_research_workflow(state)` as the compatibility entry point. Move each pipeline stage into a small graph node, wrap node execution with SQLite trace events, and keep heavy runtime objects private in graph state.

**Tech Stack:** Python, FastAPI, LangGraph, Pydantic, pandas, SQLite, pytest.

---

## Files

- Modify `app/agents/state.py`: add intermediate and private graph state fields.
- Create `app/agents/graph_events.py`: node event tracing helper.
- Create `app/agents/graph_nodes.py`: LangGraph node functions.
- Modify `app/agents/graph.py`: build and invoke compiled `StateGraph`.
- Modify `app/api/research.py`: pass `event_db_path` into workflow.
- Create `tests/test_agent_graph.py`: graph compatibility tests.
- Create `tests/test_agent_graph_events.py`: node trace tests.
- Modify `README.md`: document V3 graph/trace behavior.
- Modify `.codex-harness/STATE.md`: record V3 implementation progress.

## Tasks

### Task 1: State and Event Tracing

- [x] Extend `ResearchState` with `hypotheses`, `validation_results`, `market_data_summary`, `errors`, `trace`, `event_db_path`, `_market_data`, and `_factor_values`.
- [x] Add `GraphEventTracer` with `node_started`, `node_completed`, `node_fallback`, and `node_failed` methods.
- [x] Ensure event payloads store summaries only, not full document text or market data.

### Task 2: Graph Nodes

- [x] Create deterministic nodes:
  - `load_documents_node`
  - `retrieve_chunks_node`
  - `extract_hypotheses_node`
  - `generate_factor_dsl_node`
  - `validate_dsl_node`
  - `load_market_data_node`
  - `execute_factors_node`
  - `run_backtest_node`
  - `select_factors_node`
  - `generate_report_node`
- [x] Preserve V2 fallback behavior for missing uploads and no extracted hypothesis.
- [x] Keep V2 metric names and selected factor behavior.

### Task 3: LangGraph Assembly

- [x] Add `build_research_graph()` in `app/agents/graph.py`.
- [x] Wire the linear graph from `START` to `END`.
- [x] Keep `run_research_workflow(state)` as the public entry point.
- [x] Return API-safe state with private objects omitted from normal response use.

### Task 4: Tests

- [x] Add a graph invocation test that verifies uploaded document content still drives the factor source.
- [x] Add an event trace test that verifies node-level events are written in order.
- [x] Add a fallback event test for no-document runs.
- [x] Keep existing V2 tests passing.

### Task 5: Docs and Verification

- [x] Update README with V3 LangGraph trace positioning.
- [x] Run:

```bash
.venv/bin/pytest -v
.venv/bin/python evals/run_eval.py
.venv/bin/python -m compileall app
```

- [x] Commit and push V3 when verification passes.
