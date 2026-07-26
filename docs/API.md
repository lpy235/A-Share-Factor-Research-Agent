# API Reference

## Health

```http
GET /health
```

Returns:

```json
{"status": "ok"}
```

## Upload Document

```http
POST /documents
```

Multipart form field:

```text
file: Markdown, txt, or PDF research material
```

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -F "file=@fixture_docs/demo_factor_note.md"
```

## Create Research Run

```http
POST /research/runs
```

Deterministic demo request:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "research_topic": "A股量价类动量因子",
    "source_mode": "auto",
    "retrieval_mode": "hybrid",
    "extraction_mode": "rule",
    "data_provider": "fixture",
    "cache_enabled": true
  }'
```

Important request fields:

```text
research_topic: required natural-language research question
source_mode: upload | auto | hybrid
document_ids: uploaded document ids for upload or hybrid mode
retrieval_mode: keyword | vector | hybrid
extraction_mode: rule | llm | hybrid
enable_llm_extraction: explicit LLM opt-in
data_provider: fixture | akshare | warehouse
cache_enabled: enable local daily-bar CSV cache
fallback_to_fixture: use fixture data if live provider fails
allow_live_fetch: explicit public URL fetch opt-in
execution_mode: next_open_to_next_open
commission_bps: bilateral commission, default 3
stamp_duty_bps: sell-side stamp duty, default 5
slippage_bps: bilateral slippage, default 5
exclude_st: exclude ST stocks when the field is available
min_listing_days: minimum listing age, default 60
holding_period_days: 1-60 trading days, used for both forward-return evaluation and portfolio rebalance interval, default 1
price_adjustment_mode: raw | corporate_action_total_return; the latter is the default and derives research prices from corporate-action events without overwriting raw daily bars
max_universe_size: optional positive cap; warehouse uses every available symbol when omitted, fixture and live-demo providers default to 20
historical_universe_id: optional id returned by POST /universes
async_run: if true, return immediately with {run_id, status:"running"} and run the workflow in a background worker; poll GET /runs/{run_id} until status is completed or failed (default false, synchronous)
```

Response fields:

```text
run_id
status
selected_factors
factor_specs
metrics
oos_metrics
factor_correlation
backtest_series
gross_backtest_series
net_backtest_series
turnover_series
cost_series
long_only_metrics
tradability_diagnostics
universe_diagnostics
report_markdown
artifacts
source_diagnostics
backtest_assumptions
audit_trail
combination_backtest
```

## Upload Historical Universe

```http
POST /universes
```

Upload a CSV multipart field named `file` with the exact columns:

```csv
date,symbol,in_universe
2024-01-02,000001,true
```

The response contains an opaque `historical_universe_id`. Research runs accept that id only; arbitrary filesystem paths and unknown ids return `422`.

## List Runs

```http
GET /runs
```

Returns recent completed runs with topic, status, selected-factor count, factor count, and timestamps.

## Get Run

```http
GET /runs/{run_id}
```

Returns the saved run metadata, original config, and full response payload so the dashboard can reopen historical experiments.

## List Trace Events

```http
GET /runs/{run_id}/events
```

Returns node-level LangGraph events ordered by insertion id.

## 因子库与实验

```http
POST /factor-registry/from-run/{run_id}
GET  /factor-registry
POST /factor-registry/{version_id}/decisions
POST /factor-registry/{version_id}/recommendations
POST /research-experiments/from-run/{run_id}
GET  /research-experiments/{experiment_id}
```

`from-run` 只登记已完成运行中的 `selected_factors`，初始状态始终为 `candidate`。`decisions` 是人工追加记录；PM recommendation 仅保存 `approve`、`reject` 或 `continue_research` 建议，不会改变因子状态。

实验请求体可以设置 `max_candidates`、`max_variation_rounds` 和 `max_backtests`。实验只接受 `warehouse` 数据源且绑定 `data_version` 的运行，并将预算、父因子、变形原因、指标和淘汰原因保存到 SQLite。

## Stream Trace Events

```http
GET /runs/{run_id}/events/stream
```

Returns server-sent event frames for simple live trace inspection.

## List Run Artifacts

```http
GET /runs/{run_id}/artifacts
```

Returns downloadable artifacts for the run, including Markdown report, JSON data files, and PNG charts.

## Download Run Artifact

```http
GET /runs/{run_id}/artifacts/{artifact_name}
```

Supported artifact names include:

```text
report.md
metrics.json
oos_metrics.json
backtest_series.json
portfolio_backtest.json
backtest_diagnostics.json
factor_correlation.json
factors.json
bundle.json
metric_overview.png
factor_quality.png
rank_ic_timeseries.png
cumulative_ic.png
long_short_equity.png
drawdown_curve.png
grouped_returns.png
rolling_sharpe.png
monthly_heatmap.png
ic_decay.png
factor_correlation.png
```

## Dashboard

```http
GET /
```

Serves the browser research workbench. Static assets are served from:

```http
GET /static/styles.css
GET /static/app.js
```
