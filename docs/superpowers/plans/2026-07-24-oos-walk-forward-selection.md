# OOS and Walk-Forward Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent factors with weak, inverted, or unstable out-of-sample performance from entering `selected_factors` or multi-factor combinations.

**Architecture:** Extend `FactorScore` with the walk-forward diagnostics already produced during backtesting. Centralize OOS and walk-forward gate checks in `FactorSelector`, then map the metric fields in `SelectFactorsNode`; the response remains backward compatible because all new fields already exist in metric output.

**Tech Stack:** Python 3.14, pandas, FastAPI, LangGraph, pytest.

---

### Task 1: Specify OOS and Stability Inputs

**Files:**
- Modify: `app/backtest/selector.py:4-85`
- Test: `tests/test_selector.py`

- [x] **Step 1: Write failing selector tests**

```python
def test_selector_rejects_opposite_oos_direction():
    score = FactorScore(
        "unstable", 0.04, 0.6, 0.9, 0.1, -0.12,
        mean_rank_ic_oos=-0.03,
        walk_forward_positive_ratio=1.0,
        walk_forward_sign_consistent=True,
        walk_forward_insufficient_data=False,
    )
    assert FactorSelector().select([score]) == []
```

Add analogous tests for `abs(mean_rank_ic_oos) < 0.01`, insufficient walk-forward data, inconsistent signs, and a positive ratio below `0.6`. Update the existing accepted-factor fixture to provide passing OOS and walk-forward values.

- [x] **Step 2: Run the focused tests and confirm failure**

Run: `.venv/bin/pytest tests/test_selector.py -q`

Expected: FAIL because `FactorScore` does not accept the new walk-forward fields and the selector has no OOS gate.

- [x] **Step 3: Extend the score model and selector gates**

Add OOS and walk-forward fields to `FactorScore`, then add defaults for `min_abs_rank_ic_oos=0.01` and `min_walk_forward_positive_ratio=0.6` to `FactorSelector`. Share the gate logic between `select()` and `rejection_reasons()`: OOS must exist, meet magnitude, and match the IS direction; walk-forward must have data, consistent direction, and a sufficient positive-window ratio.

- [x] **Step 4: Run focused tests**

Run: `.venv/bin/pytest tests/test_selector.py -q`

Expected: PASS.

### Task 2: Carry Backtest Diagnostics Into Factor Selection

**Files:**
- Modify: `app/agents/graph_nodes.py:709-712`
- Modify: `app/agents/graph_nodes.py:940-960`
- Test: `tests/test_agent_graph.py`

- [x] **Step 1: Write a graph-level regression test**

Create a deterministic metric/state fixture where a factor has acceptable IS statistics but a negative OOS IC or insufficient walk-forward diagnostics. Assert it is absent from `selected_factors` and `combination_backtest` is empty.

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_agent_graph.py -q`

Expected: FAIL because `_select_factors()` does not map the walk-forward diagnostic fields.

- [x] **Step 3: Persist stable walk-forward fields in each metric**

Store `walk_forward_insufficient_data` alongside the existing positive ratio and sign-consistency fields. Pass it, the existing OOS IC, and both stability values when constructing each `FactorScore` in `_select_factors()`.

- [x] **Step 4: Run focused tests**

Run: `.venv/bin/pytest tests/test_agent_graph.py tests/test_selector.py -q`

Expected: PASS.

### Task 3: Verify API Compatibility and Full Regression Suite

**Files:**
- Modify: `tests/test_research_api.py`

- [x] **Step 1: Add API assertions for the new metric field**

Assert that the first metric contains a boolean `walk_forward_insufficient_data` field.

- [x] **Step 2: Run the API test**

Run: `.venv/bin/pytest tests/test_research_api.py -q`

Expected: PASS and response compatibility remains unchanged apart from the additional field.

- [x] **Step 3: Run all regression tests**

Run: `.venv/bin/pytest -q`

Expected: PASS.

- [x] **Step 4: Review the diff**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; changes limited to the selector, graph metric mapping, tests, and this plan.
