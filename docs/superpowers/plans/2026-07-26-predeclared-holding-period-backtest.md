# Predeclared Holding-Period Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support a predeclared holding period that controls both factor forward-return evaluation and portfolio rebalance frequency, then replay the approved A-share momentum paper for 5, 10, and 15 trading days on one fixed data version.

**Architecture:** Add one validated `holding_period_days` integer to the research request and workflow state. The graph uses it for `compute_forward_returns` and passes it through `BacktestConfig`; the portfolio rebalances only at that interval while retaining daily open-to-open valuation. The value is persisted in events, run config, assumptions, reports, and the dashboard payload.

**Tech Stack:** FastAPI/Pydantic, LangGraph state, pandas backtests, pytest, vanilla JavaScript.

---

### Task 1: Add failing holding-period tests

**Files:**
- Modify: `tests/test_portfolio_backtest.py`
- Modify: `tests/test_research_api.py`
- Modify: `tests/test_agent_graph.py`

- [x] **Step 1: Write the portfolio regression test**

```python
def test_portfolio_rebalances_only_after_the_predeclared_holding_period():
    config = BacktestConfig(holding_period_days=2, commission_bps=0, stamp_duty_bps=0, slippage_bps=0, min_listing_days=0)
    result = run_long_only_backtest(factor, data, direction="positive", config=config)
    assert result.weights[pd.Timestamp("2024-01-03")] == {"A": 1.0}
    assert result.diagnostics["daily"][1]["rebalanced"] is False
    assert result.costs.loc[pd.Timestamp("2024-01-03"), "total_cost"] == 0
```

- [x] **Step 2: Write API validation and audit assertions**

```python
response = TestClient(app).post("/research/runs", json={"research_topic": "A股量价类动量因子", "holding_period_days": 5})
assert response.status_code == 200
assert response.json()["backtest_assumptions"]["holding_period_days"] == 5
assert response.json()["backtest_assumptions"]["forward_return_period"] == "5 trading days"

response = TestClient(app).post("/research/runs", json={"research_topic": "test", "holding_period_days": 0})
assert response.status_code == 422
```

- [x] **Step 3: Run the focused tests to verify they fail**

Run: `.venv/bin/pytest -q tests/test_portfolio_backtest.py tests/test_research_api.py tests/test_agent_graph.py`

Expected: failure because `BacktestConfig` and `ResearchRunRequest` do not yet accept `holding_period_days`.

### Task 2: Propagate the declared period through the research contract

**Files:**
- Modify: `app/api/research.py`
- Modify: `app/agents/state.py`
- Modify: `app/agents/graph.py`

- [x] **Step 1: Add validated request and state fields**

```python
holding_period_days: int = Field(default=1, ge=1, le=60)
```

Add the field to `ResearchState`, `_build_workflow_state`, and `_build_run_started_payload` so it is present in persisted configuration and event audit payloads.

- [x] **Step 2: Add the default graph state value**

```python
"holding_period_days": 1,
```

- [x] **Step 3: Run API-focused tests**

Run: `.venv/bin/pytest -q tests/test_research_api.py`

Expected: request validation passes and response assertions remain pending until Task 3 publishes assumptions.

### Task 3: Use the period for evaluation and executable portfolio turnover

**Files:**
- Modify: `app/backtest/config.py`
- Modify: `app/backtest/portfolio.py`
- Modify: `app/agents/graph_nodes.py`

- [x] **Step 1: Extend `BacktestConfig`**

```python
holding_period_days: int = 1

if self.holding_period_days < 1:
    raise ValueError("holding_period_days must be at least 1")
```

- [x] **Step 2: Apply interval rebalancing in the portfolio loop**

Use the existing `signal_date -> execution_date -> valuation_date` loop. On the first execution date and every `holding_period_days` thereafter, construct targets with the existing eligibility and cost rules. On intervening dates, retain `previous_weights`, create zero-turnover costs, and record `rebalanced: False` in daily diagnostics. Continue daily open-to-open valuation in both cases.

- [x] **Step 3: Apply the same period to factor evaluation**

```python
holding_period_days = state.get("holding_period_days", 1)
forward_returns_is = compute_forward_returns(data_is["close"], periods=holding_period_days)
forward_returns_oos = compute_forward_returns(data_oos["close"], periods=holding_period_days)
```

Pass the value to `BacktestConfig`, and disclose `holding_period_days`, `forward_return_period`, and rebalance frequency in `_build_backtest_assumptions`.

- [x] **Step 4: Run the focused test set**

Run: `.venv/bin/pytest -q tests/test_portfolio_backtest.py tests/test_research_api.py tests/test_agent_graph.py`

Expected: PASS.

### Task 4: Expose and document the declared period

**Files:**
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Modify: `app/reports/markdown_report.py`
- Modify: `docs/API.md`

- [x] **Step 1: Add a constrained dashboard number input**

```html
<input id="holding-period-days" type="number" min="1" max="60" step="1" value="1" />
```

Include `holding_period_days: numberOf("#holding-period-days")` in the request payload and render the response assumption.

- [x] **Step 2: Add report and API disclosure**

Render both the holding period and evaluation horizon in the Markdown report. Document `holding_period_days` as a 1-60 trading-day value that changes both forward-return evaluation and portfolio rebalance interval.

- [x] **Step 3: Run relevant report and API tests**

Run: `.venv/bin/pytest -q tests/test_report.py tests/test_research_api.py`

Expected: PASS.

### Task 5: Execute the preregistered research replay

**Files:**
- Modify: `docs/2026-07-25-next-ten-tasks.md`
- Modify: `.codex-harness/STATE.md`

- [x] **Step 1: Start three isolated research runs**

Use the verified public-paper topic, `data_provider="warehouse"`, `data_version="v20260724_de5cde1b"`, `fallback_to_fixture=False`, range `2016-01-01` through `2024-12-31`, and `holding_period_days` exactly `5`, `10`, and `15`.

- [x] **Step 2: Record every outcome**

For each run, record the run ID, selected factors, IS/OOS Rank IC, ICIR, drawdown, Walk-forward result, manifest hash, and whether a subsequent registry/experiment action is eligible. Never alter thresholds, dates, source, or holding period after results are known.

- [x] **Step 3: Run verification**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check app tests && .venv/bin/python -m compileall -q app && git diff --check`

Expected: all tests pass, lint has no violations, compilation succeeds, and no whitespace errors exist.

- [x] **Step 4: Commit only the scoped code and documentation files**

```bash
git add app/api/research.py app/agents/state.py app/agents/graph.py app/agents/graph_nodes.py app/backtest/config.py app/backtest/portfolio.py app/reports/markdown_report.py app/web/index.html app/web/static/app.js docs/API.md docs/2026-07-25-next-ten-tasks.md .codex-harness/STATE.md tests/test_portfolio_backtest.py tests/test_research_api.py tests/test_agent_graph.py
git commit -m "feat: add predeclared holding-period backtests"
```

Do not stage unrelated market-data changes already present in the worktree.
