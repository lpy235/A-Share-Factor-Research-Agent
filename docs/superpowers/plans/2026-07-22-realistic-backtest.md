# Realistic A-Share Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a next-open, cost-aware, tradability-aware A-share portfolio backtest while preserving the existing Rank IC and G5-G1 diagnostics.

**Architecture:** Keep cross-sectional factor diagnostics in `single_factor.py` and add a focused stateful portfolio engine in `portfolio.py`. Validate request configuration at the FastAPI boundary, resolve historical membership only through a controlled CSV store, and pass typed configuration and diagnostics through LangGraph state. Existing response fields remain unchanged; executable portfolio fields are additive and are persisted in dedicated artifacts.

**Tech Stack:** Python 3.11+, Pandas, NumPy, Pydantic v2, FastAPI, LangGraph, Pytest, vanilla JavaScript.

---

## File Map

- Create `app/backtest/config.py`: immutable validated portfolio-backtest configuration.
- Create `app/backtest/portfolio.py`: next-open portfolio construction, position carry, costs, metrics, and diagnostics.
- Create `app/storage/universes.py`: controlled CSV historical-universe registry and schema validation.
- Create `app/api/universes.py`: upload endpoint returning an opaque `historical_universe_id`.
- Modify `app/main.py`: register the universe API router.
- Modify `app/api/research.py`: validate backtest request fields and expose additive result objects.
- Modify `app/agents/state.py`: declare configuration, portfolio result, and diagnostic state fields.
- Modify `app/agents/graph_nodes.py`: resolve membership, execute independent IS/OOS portfolios from flat, and serialize outputs.
- Modify `app/data/fixture_provider.py`: provide deterministic optional tradability fields.
- Modify `app/storage/artifacts.py`: persist portfolio series, metrics, and diagnostics.
- Modify `app/reports/markdown_report.py`: disclose timing, costs, tradability coverage, universe limitations, and net results.
- Modify `app/web/index.html` and `app/web/static/app.js`: accept cost/filter inputs and display portfolio output.
- Create `tests/test_portfolio_backtest.py`: deterministic engine behavior tests.
- Create `tests/test_universe_store.py`: controlled store and malformed CSV tests.
- Modify `tests/test_research_api.py`, `tests/test_agent_graph.py`, `tests/test_artifacts.py`, `tests/test_report.py`, and `tests/test_ui.py`: integration and compatibility tests.

### Task 1: Validated Backtest Configuration

**Files:**
- Create: `app/backtest/config.py`
- Modify: `app/api/research.py`
- Modify: `app/agents/state.py`
- Test: `tests/test_research_api.py`

- [x] **Step 1: Write failing API validation tests**

```python
def test_research_api_validates_realistic_backtest_configuration():
    client = TestClient(app)
    payload = {
        "research_topic": "A股量价类动量因子",
        "execution_mode": "next_open_to_next_open",
        "commission_bps": 3,
        "stamp_duty_bps": 5,
        "slippage_bps": 5,
        "exclude_st": True,
        "min_listing_days": 60,
    }
    response = client.post("/research/runs", json=payload)
    assert response.status_code == 200
    assumptions = response.json()["backtest_assumptions"]
    assert assumptions["execution_mode"] == "next_open_to_next_open"
    assert assumptions["commission_bps"] == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [("commission_bps", -1), ("stamp_duty_bps", -1),
     ("slippage_bps", -1), ("min_listing_days", -1),
     ("execution_mode", "same_close")],
)
def test_research_api_rejects_invalid_backtest_configuration(field, value):
    response = TestClient(app).post(
        "/research/runs",
        json={"research_topic": "test", field: value},
    )
    assert response.status_code == 422
```

- [x] **Step 2: Run the focused tests and verify they fail**

Run: `.venv/bin/pytest tests/test_research_api.py -k 'realistic_backtest or invalid_backtest' -v`

Expected: FAIL because the request model does not expose or validate the new fields.

- [x] **Step 3: Add the configuration model and request fields**

```python
# app/backtest/config.py
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BacktestConfig:
    execution_mode: str = "next_open_to_next_open"
    commission_bps: float = 3.0
    stamp_duty_bps: float = 5.0
    slippage_bps: float = 5.0
    exclude_st: bool = True
    min_listing_days: int = 60

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
```

In `ResearchRunRequest`, use Pydantic constraints and a literal execution mode:

```python
execution_mode: Literal["next_open_to_next_open"] = "next_open_to_next_open"
commission_bps: float = Field(default=3.0, ge=0)
stamp_duty_bps: float = Field(default=5.0, ge=0)
slippage_bps: float = Field(default=5.0, ge=0)
exclude_st: bool = True
min_listing_days: int = Field(default=60, ge=0)
historical_universe_id: str | None = None
```

Copy these fields into the initial workflow state and declare them in `ResearchState`.

- [x] **Step 4: Run the focused tests and verify they pass**

Run: `.venv/bin/pytest tests/test_research_api.py -k 'realistic_backtest or invalid_backtest' -v`

Expected: PASS.

- [x] **Step 5: Commit the configuration boundary**

```bash
git add app/backtest/config.py app/api/research.py app/agents/state.py tests/test_research_api.py
git commit -m "feat: validate realistic backtest configuration"
```

### Task 2: Next-Open Portfolio Engine

**Files:**
- Create: `app/backtest/portfolio.py`
- Create: `tests/test_portfolio_backtest.py`

- [x] **Step 1: Write failing timing and direction tests**

```python
def test_portfolio_uses_signal_t_and_open_t_plus_1_to_t_plus_2_return():
    data, factor = make_market_fixture()
    result = run_long_only_backtest(factor, data, direction="positive", config=zero_cost_config())
    assert result.gross_returns.index.tolist() == [pd.Timestamp("2024-01-02")]
    assert result.gross_returns.iloc[0] == pytest.approx(0.10)


def test_negative_direction_inverts_ranking_and_unknown_is_diagnostic_only():
    data, factor = make_market_fixture()
    negative = run_long_only_backtest(factor, data, direction="negative", config=zero_cost_config())
    unknown = run_long_only_backtest(factor, data, direction="unknown", config=zero_cost_config())
    assert negative.selected_symbols[pd.Timestamp("2024-01-02")] == ["B"]
    assert unknown.gross_returns.empty
    assert unknown.diagnostics["executable"] is False
```

The fixture must have three dates and five symbols so the top quintile selects exactly one symbol. Put factor values only on the signal date, and set distinct next two opens so a same-close or close-to-close implementation cannot accidentally pass.

- [x] **Step 2: Run timing and direction tests and verify they fail**

Run: `.venv/bin/pytest tests/test_portfolio_backtest.py -k 'signal or direction' -v`

Expected: FAIL with import error for `app.backtest.portfolio`.

- [x] **Step 3: Implement the typed result and execution loop**

```python
@dataclass
class PortfolioBacktestResult:
    gross_returns: pd.Series
    net_returns: pd.Series
    turnover: pd.Series
    costs: pd.DataFrame
    weights: dict[pd.Timestamp, dict[str, float]]
    selected_symbols: dict[pd.Timestamp, list[str]]
    diagnostics: dict[str, Any]


def run_long_only_backtest(
    factor: pd.Series,
    market_data: pd.DataFrame,
    *,
    direction: str,
    config: BacktestConfig,
) -> PortfolioBacktestResult:
    if direction == "unknown":
        return _empty_result("factor_direction_unknown")
    scores = factor if direction == "positive" else -factor
    dates = sorted(pd.DatetimeIndex(market_data.index.get_level_values("date")).unique())
    # signal_dates[:-2] map t -> t+1 execution -> t+2 valuation
    # Build equal weights over the highest ceil(n / 5) eligible scores,
    # apply execution constraints, calculate open-to-open gross return,
    # and carry the resulting positions to the next rebalance.
```

Use `max(1, math.ceil(len(candidates) / 5))` for the top quintile. The result date is the execution date `t+1`; the last date without `t+2` open is excluded.

- [x] **Step 4: Run timing and direction tests and verify they pass**

Run: `.venv/bin/pytest tests/test_portfolio_backtest.py -k 'signal or direction' -v`

Expected: PASS.

- [x] **Step 5: Write failing turnover and cost tests**

```python
def test_costs_apply_commission_and_slippage_both_sides_and_stamp_only_to_sells():
    data, factor = make_two_rebalance_fixture()
    config = BacktestConfig(commission_bps=3, stamp_duty_bps=5, slippage_bps=5)
    result = run_long_only_backtest(factor, data, direction="positive", config=config)
    second = result.costs.iloc[1]
    assert second["commission"] == pytest.approx(result.turnover.iloc[1] * 3 / 10_000)
    assert second["slippage"] == pytest.approx(result.turnover.iloc[1] * 5 / 10_000)
    assert second["stamp_duty"] == pytest.approx(second["sell_turnover"] * 5 / 10_000)
    assert result.net_returns.iloc[1] == pytest.approx(
        result.gross_returns.iloc[1] - second["total_cost"]
    )


def test_zero_cost_net_equals_gross():
    data, factor = make_two_rebalance_fixture()
    result = run_long_only_backtest(factor, data, direction="positive", config=zero_cost_config())
    pd.testing.assert_series_equal(result.net_returns, result.gross_returns, check_names=False)
```

- [x] **Step 6: Implement turnover and cost accounting**

For each execution date calculate:

```python
symbols = set(previous_weights) | set(target_weights)
buy_turnover = sum(max(target_weights.get(s, 0) - previous_weights.get(s, 0), 0) for s in symbols)
sell_turnover = sum(max(previous_weights.get(s, 0) - target_weights.get(s, 0), 0) for s in symbols)
turnover = buy_turnover + sell_turnover
commission = turnover * config.commission_bps / 10_000
slippage = turnover * config.slippage_bps / 10_000
stamp_duty = sell_turnover * config.stamp_duty_bps / 10_000
total_cost = commission + slippage + stamp_duty
```

- [x] **Step 7: Run all portfolio engine tests**

Run: `.venv/bin/pytest tests/test_portfolio_backtest.py -v`

Expected: PASS.

- [x] **Step 8: Commit the engine**

```bash
git add app/backtest/portfolio.py tests/test_portfolio_backtest.py
git commit -m "feat: add next-open portfolio backtest engine"
```

### Task 3: Tradability Rules and Diagnostics

**Files:**
- Modify: `app/backtest/portfolio.py`
- Modify: `app/data/fixture_provider.py`
- Modify: `tests/test_portfolio_backtest.py`
- Test: `tests/test_data_provider_factory.py`

- [x] **Step 1: Write failing rule tests**

```python
@pytest.mark.parametrize("column", ["in_universe", "is_suspended", "is_st", "days_since_listing", "limit_up"])
def test_candidate_filters_use_available_signal_or_execution_fields(column):
    data, factor = make_status_fixture(blocking_column=column)
    result = run_long_only_backtest(factor, data, direction="positive", config=zero_cost_config())
    assert "A" not in result.selected_symbols[pd.Timestamp("2024-01-02")]


@pytest.mark.parametrize("column", ["is_suspended", "limit_down"])
def test_blocked_sell_carries_existing_position(column):
    data, factor = make_carry_fixture(blocking_column=column)
    result = run_long_only_backtest(factor, data, direction="positive", config=zero_cost_config())
    assert result.weights[pd.Timestamp("2024-01-03")]["A"] > 0
    assert result.diagnostics["blocked_sells"] >= 1


def test_missing_optional_fields_are_disclosed_not_claimed():
    data, factor = make_market_fixture()
    data = data[["open", "close"]]
    result = run_long_only_backtest(factor, data, direction="positive", config=zero_cost_config())
    assert set(result.diagnostics["missing_fields"]) == {
        "in_universe", "is_suspended", "is_st", "days_since_listing", "limit_up", "limit_down"
    }
    assert result.diagnostics["applied_rules"] == []
```

- [x] **Step 2: Run rule tests and verify they fail**

Run: `.venv/bin/pytest tests/test_portfolio_backtest.py -k 'filter or blocked_sell or optional_fields' -v`

Expected: FAIL because status rules are not implemented.

- [x] **Step 3: Apply candidate and execution rules**

At signal date, restrict `in_universe`, `is_st`, and `days_since_listing` only when present. At execution date, exclude missing `open`, suspended names, and limit-up buys. Before setting final weights, preserve previous weights for names whose sale is blocked by `is_suspended` or `limit_down`, then allocate only the remaining weight to buyable target names. Record per-date counts plus aggregate `missing_fields`, `applied_rules`, `blocked_buys`, `blocked_sells`, and `empty_candidate_dates`.

- [x] **Step 4: Add deterministic status columns to fixture data**

```python
df["in_universe"] = True
df["is_suspended"] = False
df["is_st"] = False
df["days_since_listing"] = (
    df.groupby(level="symbol").cumcount().to_numpy() + 365
)
df["limit_up"] = False
df["limit_down"] = False
```

- [x] **Step 5: Run portfolio and provider tests**

Run: `.venv/bin/pytest tests/test_portfolio_backtest.py tests/test_data_provider_factory.py -v`

Expected: PASS.

- [x] **Step 6: Commit tradability support**

```bash
git add app/backtest/portfolio.py app/data/fixture_provider.py tests/test_portfolio_backtest.py tests/test_data_provider_factory.py
git commit -m "feat: enforce available tradability constraints"
```

### Task 4: Controlled Historical Universe Store

**Files:**
- Create: `app/storage/universes.py`
- Create: `app/api/universes.py`
- Modify: `app/main.py`
- Create: `tests/test_universe_store.py`

- [x] **Step 1: Write failing store tests**

```python
def test_universe_store_registers_and_loads_valid_csv(tmp_path):
    store = HistoricalUniverseStore(tmp_path)
    universe_id = store.register(
        b"date,symbol,in_universe\n2024-01-02,000001,true\n2024-01-02,000002,false\n"
    )
    loaded = store.load(universe_id)
    assert loaded.loc[(pd.Timestamp("2024-01-02"), "000001")] is True


@pytest.mark.parametrize(
    "content",
    [b"date,symbol\n2024-01-02,000001\n", b"date,symbol,in_universe\nbad,000001,true\n"],
)
def test_universe_store_rejects_malformed_csv(tmp_path, content):
    with pytest.raises(ValueError):
        HistoricalUniverseStore(tmp_path).register(content)


def test_universe_store_rejects_path_like_identifier(tmp_path):
    with pytest.raises(ValueError):
        HistoricalUniverseStore(tmp_path).load("../membership.csv")
```

- [x] **Step 2: Run store tests and verify they fail**

Run: `.venv/bin/pytest tests/test_universe_store.py -v`

Expected: FAIL with import error for `app.storage.universes`.

- [x] **Step 3: Implement opaque-ID storage and strict CSV parsing**

```python
REQUIRED_COLUMNS = ["date", "symbol", "in_universe"]


class HistoricalUniverseStore:
    def register(self, content: bytes) -> str:
        frame = pd.read_csv(io.BytesIO(content), dtype={"symbol": str})
        if list(frame.columns) != REQUIRED_COLUMNS:
            raise ValueError("Historical universe CSV must contain date,symbol,in_universe")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise")
        frame["in_universe"] = frame["in_universe"].map(_parse_bool)
        universe_id = f"universe_{uuid4().hex[:12]}"
        frame.to_csv(self.root_dir / f"{universe_id}.csv", index=False)
        return universe_id

    def load(self, universe_id: str) -> pd.Series:
        if not re.fullmatch(r"universe_[0-9a-f]{12}", universe_id):
            raise ValueError("Invalid historical universe id")
        # Read only root_dir / f"{universe_id}.csv" and return a boolean
        # Series indexed by (date, symbol).
```

- [x] **Step 4: Add the multipart upload endpoint**

```python
@router.post("")
async def upload_historical_universe(file: UploadFile) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Historical universe must be a CSV file")
    try:
        universe_id = universe_store.register(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"historical_universe_id": universe_id}
```

Register the router under `/universes` in `app/main.py`.

- [x] **Step 5: Run store and API tests**

Run: `.venv/bin/pytest tests/test_universe_store.py -v`

Expected: PASS.

- [x] **Step 6: Commit the controlled store**

```bash
git add app/storage/universes.py app/api/universes.py app/main.py tests/test_universe_store.py
git commit -m "feat: register historical universe artifacts"
```

### Task 5: Workflow Integration and Flat IS/OOS Segments

**Files:**
- Modify: `app/agents/graph_nodes.py`
- Modify: `app/agents/state.py`
- Modify: `app/api/research.py`
- Modify: `tests/test_agent_graph.py`
- Modify: `tests/test_research_api.py`

- [x] **Step 1: Write failing workflow tests**

```python
def test_workflow_exposes_cost_aware_long_only_outputs(tmp_path):
    state = run_research_workflow(make_fixture_state(tmp_path))
    factor = "volume_price_momentum"
    assert state["gross_backtest_series"][factor]
    assert state["net_backtest_series"][factor]
    assert state["turnover_series"][factor]
    assert state["cost_series"][factor]
    assert state["long_only_metrics"][0]["factor_name"] == factor
    assert state["tradability_diagnostics"][factor]["executable"] is True


def test_is_and_oos_portfolios_each_start_flat(tmp_path):
    state = run_research_workflow(make_fixture_state(tmp_path))
    factor = "volume_price_momentum"
    assert state["cost_series"][factor]["is"][0]["sell_turnover"] == 0
    assert state["cost_series"][factor]["oos"][0]["sell_turnover"] == 0
```

- [x] **Step 2: Run workflow tests and verify they fail**

Run: `.venv/bin/pytest tests/test_agent_graph.py -k 'cost_aware or start_flat' -v`

Expected: FAIL because portfolio state fields do not exist.

- [x] **Step 3: Resolve membership and merge it into market data**

In `_load_market_data`, load `historical_universe_id` through `HistoricalUniverseStore`; join membership on `(date, symbol)` into `in_universe`. If no ID is supplied, set:

```python
state["universe_diagnostics"] = {
    "source": "fixed_provider_universe",
    "historical_membership_applied": False,
    "warning": "未提供历史成分股，结果可能存在生存者偏差。",
}
```

An unknown ID or malformed stored file must raise before backtesting.

- [x] **Step 4: Run the portfolio independently for IS and OOS**

Build a `factor_name -> direction` map from `factor_specs`. In `_run_backtest`, preserve the existing diagnostic calculations, then call `run_long_only_backtest` separately on `data_is` and `data_oos`. This ensures each segment starts with `{}` previous weights. Merge serialized segment series only for the full response while retaining `is` and `oos` detail in `cost_series`.

Compute additive metrics from net returns:

```python
{
    "factor_name": factor_name,
    "annualized_return": round(annualized_return(net_returns), 6),
    "sharpe": round(sharpe_ratio(net_returns), 6),
    "max_drawdown": round(max_drawdown(net_returns), 6),
    "cumulative_cost": round(float(costs["total_cost"].sum()), 8),
}
```

- [x] **Step 5: Extend the API response without removing legacy fields**

Add `gross_backtest_series`, `net_backtest_series`, `turnover_series`, `cost_series`, `long_only_metrics`, `tradability_diagnostics`, and `universe_diagnostics`. Assert all old keys from `test_research_api_returns_v2_compatible_response_and_node_trace` still exist.

- [x] **Step 6: Run focused workflow and API tests**

Run: `.venv/bin/pytest tests/test_agent_graph.py tests/test_research_api.py -v`

Expected: PASS.

- [x] **Step 7: Commit workflow integration**

```bash
git add app/agents/graph_nodes.py app/agents/state.py app/api/research.py tests/test_agent_graph.py tests/test_research_api.py
git commit -m "feat: integrate realistic portfolio results"
```

### Task 6: Artifacts and Research Report

**Files:**
- Modify: `app/storage/artifacts.py`
- Modify: `app/api/research.py`
- Modify: `app/reports/markdown_report.py`
- Modify: `app/agents/graph_nodes.py`
- Modify: `tests/test_artifacts.py`
- Modify: `tests/test_report.py`

- [x] **Step 1: Write failing artifact and report tests**

```python
def test_artifacts_persist_realistic_backtest_payloads(tmp_path):
    artifacts = ArtifactStore(tmp_path).write_run_artifacts(
        "run_demo",
        report_markdown="# report",
        metrics=[], factor_specs=[], selected_factors=[],
        portfolio_results={"gross_backtest_series": {"factor": []}},
    )
    names = {item["name"] for item in artifacts}
    assert "portfolio_backtest.json" in names
    assert "backtest_diagnostics.json" in names


def test_report_discloses_timing_costs_and_universe_limitations():
    report = render_report(
        research_topic="test", sources=[], factors=[], metrics=[], limitations=[],
        backtest_assumptions={
            "execution_mode": "next_open_to_next_open",
            "commission_bps": 3, "stamp_duty_bps": 5, "slippage_bps": 5,
        },
        long_only_metrics=[{"factor_name": "f", "sharpe": 1.0, "cumulative_cost": 0.01}],
        universe_diagnostics={"warning": "未提供历史成分股，结果可能存在生存者偏差。"},
    )
    assert "t 日收盘计算，t+1 日开盘成交" in report
    assert "印花税：5 bps" in report
    assert "生存者偏差" in report
```

- [x] **Step 2: Run tests and verify they fail**

Run: `.venv/bin/pytest tests/test_artifacts.py tests/test_report.py -v`

Expected: FAIL because the signatures and files are not implemented.

- [x] **Step 3: Persist portfolio payloads and diagnostics**

Extend `write_run_artifacts` with `portfolio_results` and `backtest_diagnostics`. Write `portfolio_backtest.json` and `backtest_diagnostics.json`, and include both in `bundle.json`. Add human-readable labels in `_label_for`.

- [x] **Step 4: Render executable metrics and explicit assumptions**

Add a “可执行多头组合” table with annualized return, Sharpe, max drawdown, and cumulative cost. Replace the legacy zero-cost line with the configured commission, sell-side stamp duty, and slippage values. Add applied/missing tradability rules and the historical-universe warning.

- [x] **Step 5: Run artifact and report tests**

Run: `.venv/bin/pytest tests/test_artifacts.py tests/test_report.py -v`

Expected: PASS.

- [x] **Step 6: Commit persisted outputs**

```bash
git add app/storage/artifacts.py app/api/research.py app/reports/markdown_report.py app/agents/graph_nodes.py tests/test_artifacts.py tests/test_report.py
git commit -m "feat: report realistic backtest results"
```

### Task 7: Dashboard Controls and Results

**Files:**
- Modify: `app/web/index.html`
- Modify: `app/web/static/app.js`
- Modify: `app/web/static/styles.css`
- Modify: `tests/test_ui.py`

- [x] **Step 1: Write failing UI contract tests**

```python
def test_dashboard_exposes_realistic_backtest_controls_and_results():
    response = TestClient(app).get("/")
    assert 'id="commission-bps"' in response.text
    assert 'id="stamp-duty-bps"' in response.text
    assert 'id="slippage-bps"' in response.text
    assert 'id="exclude-st"' in response.text
    assert 'id="min-listing-days"' in response.text
    assert 'id="long-only-metrics"' in response.text
    assert 'id="tradability-diagnostics"' in response.text
```

- [x] **Step 2: Run UI tests and verify they fail**

Run: `.venv/bin/pytest tests/test_ui.py -v`

Expected: FAIL because the controls are absent.

- [x] **Step 3: Add compact controls and renderers**

Use number inputs with `min="0"` for the three bps fields and listing days, and a checkbox for ST exclusion. Include these values in `buildPayload()`. Add unframed result sections for long-only metrics and tradability/universe diagnostics; render gross/net distinction and do not label the G5-G1 curve executable.

- [x] **Step 4: Run UI tests**

Run: `.venv/bin/pytest tests/test_ui.py -v`

Expected: PASS.

- [x] **Step 5: Commit the dashboard update**

```bash
git add app/web/index.html app/web/static/app.js app/web/static/styles.css tests/test_ui.py
git commit -m "feat: expose realistic backtest controls"
```

### Task 8: Documentation, State, and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `.codex-harness/STATE.md`

- [x] **Step 1: Document the execution convention and limitations**

Add the exact `t close -> t+1 open -> t+2 open` convention, default cost rates, optional status fields, controlled historical-universe upload flow, and the distinction between executable top-quintile long-only results and diagnostic G5-G1 results.

- [x] **Step 2: Run the full test suite**

Run: `.venv/bin/pytest -v`

Expected: all tests pass.

- [x] **Step 3: Run deterministic eval and static checks**

Run: `.venv/bin/python evals/run_eval.py`

Expected: `accuracy: 1.0` and `5/5` cases correct.

Run: `.venv/bin/python -m compileall app`

Expected: exit code 0.

Run: `.venv/bin/ruff check app tests`

Expected: `All checks passed!`.

Run: `git diff --check`

Expected: no output and exit code 0.

- [x] **Step 4: Run an API smoke test**

```bash
.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

response = TestClient(app).post("/research/runs", json={"research_topic": "A股量价类动量因子"})
response.raise_for_status()
body = response.json()
assert body["gross_backtest_series"]
assert body["net_backtest_series"]
assert body["backtest_assumptions"]["execution_mode"] == "next_open_to_next_open"
print(body["status"], len(body["long_only_metrics"]))
PY
```

Expected: `completed 1` or another positive factor count.

- [x] **Step 5: Update harness state and commit the milestone**

Mark Stage 2 realistic backtesting complete in `.codex-harness/STATE.md`, record verification evidence, and set the next queue item to the versioned factor registry.

```bash
git add README.md docs/ARCHITECTURE.md .codex-harness/STATE.md
git commit -m "docs: document realistic A-share backtesting"
```

## Self-Review

- Spec coverage: Tasks 1-7 cover request validation, next-open timing, direction, long-only construction, costs, tradability, historical membership, independent IS/OOS portfolios, additive API fields, artifacts, report, and dashboard. Task 8 covers all acceptance checks.
- Compatibility: existing `metrics`, `oos_metrics`, `backtest_series`, Rank IC, grouped returns, and factor-selection inputs remain unchanged.
- Type consistency: `BacktestConfig`, `PortfolioBacktestResult`, and the seven additive response names are used consistently across engine, state, API, artifacts, and tests.
- Scope boundary: no order matching, intraday simulator, portfolio optimizer, arbitrary path input, or factor registry is included.
