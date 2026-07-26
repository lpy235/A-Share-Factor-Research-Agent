# 研究价格与回填恢复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make fixed-version research use auditable corporate-action-adjusted prices and make market-data backfills recover correctly across parent-child versions.

**Architecture:** Keep raw Parquet bars immutable. A dedicated market-data adjustment module derives research OHLC prices from effective corporate-action events at provider-read time. The research graph samples IC statistics at the same signal cadence as the portfolio. Catalog progress becomes the source of truth for unresolved failures, while store readers resolve all reference tables through the manifest parent chain.

**Tech Stack:** Python 3, pandas, DuckDB, FastAPI/Pydantic, pytest, Ruff.

---

### Task 1: Versioned Corporate-Action Price Transform

**Files:**
- Create: `app/market_data/adjustment.py`
- Modify: `app/data/warehouse_provider.py`
- Test: `tests/test_market_data_adjustment.py`
- Test: `tests/test_warehouse_provider.py`

- [ ] **Step 1: Write failing tests for backward total-return adjustment**

```python
adjusted, diagnostics = apply_corporate_action_adjustment(bars, actions)
assert adjusted.loc[0, "close"] == pytest.approx(90.0)
assert adjusted.loc[1, "close"] == pytest.approx(90.0)
assert bars.loc[0, "close"] == 100.0
assert diagnostics["applied_event_count"] == 1
```

Include grouped cash-dividend, bonus-share, and capitalization events on one ex-date, an event before the requested price window, and an in-window event without `per_10_shares` that raises `ValueError`.

- [ ] **Step 2: Run the new tests and confirm failure**

Run: `.venv/bin/pytest -q tests/test_market_data_adjustment.py tests/test_warehouse_provider.py`

Expected: FAIL because the adjustment module and provider mode do not exist.

- [ ] **Step 3: Implement a pure adjustment module**

```python
def apply_corporate_action_adjustment(
    bars: pd.DataFrame, actions: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int | str]]:
    # For each ex-date, factor earlier OHLC prices by
    # (previous_close - cash_per_share) / (previous_close * share_ratio).
```

Require `symbol`, `trade_date`, and OHLC columns; only use events in the requested observation window; aggregate same-day event types; reject missing/non-positive adjustment factors; change only `open`, `high`, `low`, and `close` on a copy.

- [ ] **Step 4: Integrate with the warehouse provider**

Add `price_adjustment_mode` with `raw` and `corporate_action_total_return` modes. In adjusted mode, load effective events, call the pure function before setting the MultiIndex, and update provider diagnostics with adjustment mode, event counts, and applied/skipped counts.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/pytest -q tests/test_market_data_adjustment.py tests/test_warehouse_provider.py`

Expected: PASS.

### Task 2: Declare the Research Price Mode

**Files:**
- Modify: `app/data/provider_factory.py`
- Modify: `app/api/research.py`
- Modify: `app/agents/state.py`
- Modify: `app/agents/graph.py`
- Modify: `app/agents/graph_nodes.py`
- Modify: `app/reports/markdown_report.py`
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Modify: `docs/API.md`
- Test: `tests/test_research_api.py`
- Test: `tests/test_report.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write failing API, report, and UI tests**

```python
response = client.post("/research/runs", json={"price_adjustment_mode": "raw"})
assert response.status_code == 200
assert response.json()["backtest_assumptions"]["price_adjustment_mode"] == "raw"
```

Also assert the default warehouse mode is `corporate_action_total_return`, invalid modes return 422, report output names the selected rule, and the dashboard payload contains the selector value.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `.venv/bin/pytest -q tests/test_research_api.py tests/test_report.py tests/test_ui.py`

Expected: FAIL because request/state/report/UI do not expose the price mode.

- [ ] **Step 3: Propagate and disclose the mode**

Use a Pydantic literal field, pass it through `select_data_provider`, persist it in run-start events and graph state, include provider adjustment diagnostics in report assumptions, and provide a compact advanced-settings select control.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/pytest -q tests/test_research_api.py tests/test_report.py tests/test_ui.py`

Expected: PASS.

### Task 3: Align IC Sampling With Holding Periods

**Files:**
- Modify: `app/agents/graph_nodes.py`
- Test: `tests/test_agent_graph.py`

- [ ] **Step 1: Write a failing cadence test**

```python
state = run_research_workflow({... , "holding_period_days": 5})
rank_ic = state["backtest_series"]["volume_price_momentum"]["rank_ic"]
assert all((later - earlier).days >= 5 for earlier, later in adjacent_dates(rank_ic))
```

The test must also assert the diagnostic `factor_evaluation_frequency` is `every 5 trading days` and that the daily setting retains all available dates.

- [ ] **Step 2: Run the test and confirm failure**

Run: `.venv/bin/pytest -q tests/test_agent_graph.py::test_workflow_samples_factor_metrics_on_holding_period_signal_dates`

Expected: FAIL because the current Rank IC series contains every trading day.

- [ ] **Step 3: Sample factor and forward returns before metric calculation**

```python
def _sample_holding_period_signals(
    factor: pd.Series, forward_returns: pd.Series, holding_period_days: int
) -> tuple[pd.Series, pd.Series]:
    # Keep every Nth common date beginning at the segment's first date.
```

Pass the sampled data to `_backtest_single_factor`, Walk-forward, grouped returns, and selection metrics; retain the daily portfolio valuation unchanged; add cadence and sample-count diagnostics to assumptions.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/pytest -q tests/test_agent_graph.py tests/test_portfolio_backtest.py`

Expected: PASS.

### Task 4: Retry Failed Symbols and Inherit Reference Tables

**Files:**
- Modify: `app/market_data/catalog.py`
- Modify: `app/market_data/store.py`
- Modify: `app/market_data/ingestion.py`
- Test: `tests/test_market_data_ingestion.py`
- Test: `tests/test_market_data_store.py`

- [ ] **Step 1: Write failing recovery and inheritance tests**

```python
failed = service.run(...)
recovered = service.resume(failed.ingest_run_id)
assert recovered.status == "completed"
assert service.publish(recovered.ingest_run_id).status == "published"
assert source.calls.count("000002.SZ") == 2
```

Create a base version with reference tables, publish an intermediate child with only a parent pointer, then prove a corporate-action child can be created from that intermediate version.

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv/bin/pytest -q tests/test_market_data_ingestion.py tests/test_market_data_store.py`

Expected: FAIL because failed symbols are not retried and master/calendar do not resolve through parents.

- [ ] **Step 3: Implement latest-status recovery semantics**

Add catalog methods to list unresolved failed progress and clear their active failure records on successful retry. `CorporateActionBackfillService.resume` must process failed symbols first, update their progress to completed, then continue unfinished sequential batches. `publish` must consult unresolved failures rather than historical error rows.

- [ ] **Step 4: Implement effective reference-table readers**

Add `read_effective_security_master`, `read_effective_trading_calendar`, and `read_effective_security_status`, deduplicating each table by its natural key with child rows winning. Use effective master/calendar in corporate-action run and publication checks.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/pytest -q tests/test_market_data_ingestion.py tests/test_market_data_store.py tests/test_market_data_cli.py`

Expected: PASS.

### Task 5: Verify and Reproduce Fixed-Version Research

**Files:**
- Modify: `docs/2026-07-25-next-ten-tasks.md`
- Modify: `.codex-harness/STATE.md`

- [ ] **Step 1: Run static and full-suite verification**

Run: `.venv/bin/pytest -q`, `.venv/bin/ruff check app tests`, `.venv/bin/python -m compileall -q app`, and `git diff --check`.

Expected: all commands exit 0.

- [ ] **Step 2: Run the three immutable replays**

Use the public-paper source, `warehouse`, `v20260724_de5cde1b`, `fallback_to_fixture=false`, range `2016-01-01` through `2024-12-31`, `price_adjustment_mode=corporate_action_total_return`, and each holding period `5`, `10`, and `15`.

- [ ] **Step 3: Record replacement evidence**

Append new run IDs, data version, manifest hash, price-adjustment diagnostics, non-overlapping evaluation cadence, metrics, and selection result. Preserve prior runs as superseded by the corrected statistical/pricing methodology.

- [ ] **Step 4: Commit only the scoped remediation**

```bash
git add app/data app/market_data app/api/research.py app/agents app/backtest app/reports app/web docs/API.md docs/2026-07-25-next-ten-tasks.md .codex-harness/STATE.md tests
git commit -m "fix: align research prices and recoverable backfills"
```

Do not stage pre-existing unrelated market-data edits; stage each intended file explicitly after inspecting `git diff --name-only`.
