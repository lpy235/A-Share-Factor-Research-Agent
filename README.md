# A股因子研究智能体

A quant strategy / AI Agent research system for A-share factor research.

It reads public or uploaded research material, retrieves factor evidence, extracts factor hypotheses, converts them into a restricted Factor DSL, validates them on A-share daily data, runs factor backtests, selects candidate factors, and renders a traceable research report in a browser dashboard.

## 快速启动

```bash
cd "/Users/brain6/Documents/document/A-Share Factor Research Agent"
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

首页提供三种入口：跑一个示例研究、从主题开始、上传论文/研报。默认示例研究不需要 OpenAI Key、实时行情或实时网页抓取。

## What It Does

```text
public/uploaded research material
-> RAG retrieval
-> schema-validated or rule-based factor extraction
-> restricted Factor DSL
-> fixture or optional AKShare A-share daily data
-> IS/OOS Rank IC, ICIR, grouped returns, diagnostic long-short metrics
-> next-open equal-weight long-only portfolio, turnover, costs, and tradability checks
-> IC decay and factor-correlation diagnostics
-> factor selection with rejection reasons
-> Markdown report + charts + JSON research bundle + LangGraph trace
```

## Demo

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
pytest -v
python evals/run_eval.py
uvicorn app.main:app --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

The dashboard default run is deterministic: no OpenAI key, no live data source, and no live web fetch are required.

## Key Features

- FastAPI dashboard for running research and inspecting results.
- LangGraph workflow with node-level SQLite trace events.
- Markdown/txt/PDF upload plus deterministic public-source discovery.
- Keyword, vector, and hybrid retrieval over research chunks.
- Rule-based extraction by default, with optional schema-validated LLM extraction.
- Restricted Factor DSL with whitelisted fields and operators, strict window semantics, and controlled AST interpretation.
- Deterministic fixture A-share data plus optional AKShare mode and local CSV cache.
- Factor validation, IS/OOS Rank IC, ICIR, grouped returns, diagnostic long-short metrics, and factor selection.
- Next-open equal-weight long-only backtest with configurable commission, sell-side stamp duty, slippage, and turnover.
- Optional ST, listing-age, suspension, price-limit, and registered historical-universe filters with explicit missing-data diagnostics.
- IC decay, factor-correlation matrix, rolling Sharpe, monthly-return heatmap, and downloadable research bundles.
- Deterministic eval runner and 60+ pytest coverage.

Optional embedding backends are separated from the default install:

```bash
pip install -e ".[embedding]"
```

## Safety Boundary

This is a research workflow demo. It does not provide investment advice, stock recommendations, return promises, order execution, or auto-trading.

Model output cannot execute arbitrary Python. It must pass schema validation and produce formulas in a restricted Factor DSL.

The Factor DSL contract is enforced before execution:

- formulas may reference only registered market-data fields and operators;
- rolling and delay windows must be integer constants from `1` through `2520` (`MAX_WINDOW`);
- `required_fields` must exactly match the fields referenced by the formula;
- `lookback` must cover the formula's largest rolling or delay window;
- source length, AST size, call depth, operator signatures, and numeric arguments are bounded;
- invalid formulas are excluded, and workflow fallback formulas must pass the same validator.

Validated formulas run through an in-process controlled AST interpreter. The interpreter supports only the approved names, numeric constants, arithmetic operations, and operator calls; it does not expose Python builtins, attributes, subscripts, or dynamic function lookup. This is a semantic execution boundary, not a process-isolation or resource sandbox. Deployments that accept formulas from untrusted users still need process isolation, timeouts, memory limits, and operating-system-level controls.

## Repository Map

```text
app/api        FastAPI routes for dashboard, documents, universes, runs, and trace events
app/agents     LangGraph workflow, nodes, extraction logic, prompts, schemas
app/backtest   Factor diagnostics, next-open portfolio simulation, costs, and selection
app/data       Fixture data, optional AKShare adapter, daily-bar cache
app/factor     Restricted Factor DSL, validator, operators, executor
app/rag        Chunking, keyword retrieval, hashing embeddings, vector retrieval
app/sources    Public-source policy, discovery, fetching, parsing
app/storage    SQLite events plus uploaded document and historical-universe stores
app/web        Browser dashboard
evals          Deterministic evaluation set
tests          Unit, API, graph, and integration tests
docs           Architecture, API, demo, development, roadmap, and execution archive
```

## Useful Commands

```bash
make test
make eval
make compile
make check
make run
```

Manual verification:

```bash
python -m pytest -q
python evals/run_eval.py
python -m compileall app
```

API smoke test:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","data_provider":"fixture","cache_enabled":true}'
```

## Realistic Backtest Convention

The executable portfolio uses a fixed daily convention:

```text
t close: calculate factor signal
t+1 open: trade into the target portfolio
t+1 open to t+2 open: measure portfolio return
```

The top factor quintile is held as an equal-weight long-only portfolio. Factor direction is applied before ranking. `unknown` direction factors remain available for IC diagnostics but do not produce an executable portfolio. The existing G5-G1 result is retained as a research diagnostic and is not presented as an ordinary A-share short-selling strategy.

Default costs are 3 bps commission on buys and sells, 5 bps stamp duty on sells, and 5 bps slippage on buys and sells. They are request parameters and are displayed in the report. IS and OOS portfolios each start from cash.

Market data may provide `in_universe`, `is_suspended`, `is_st`, `days_since_listing`, `limit_up`, and `limit_down`. Available rules are applied; missing fields are reported rather than assumed. Historical membership CSV files use `date,symbol,in_universe`, are uploaded through `POST /universes`, and are referenced by the returned `historical_universe_id`. Arbitrary server paths are not accepted.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Demo Guide](docs/DEMO.md)
- [Interview Demo Guide](docs/INTERVIEW_DEMO.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Roadmap](docs/ROADMAP.md)
- [Demo Report](REPORT.md)

Detailed historical specs and implementation plans are kept under `docs/superpowers/`.

## Project Summary

> Built an A-share factor research agent with a FastAPI dashboard and LangGraph workflow. The system discovers public A-share research materials or reads uploaded documents, retrieves evidence with hybrid RAG, extracts schema-validated factor hypotheses with deterministic fallback, converts them into a restricted Factor DSL, validates them on cached fixture or optional AKShare daily data, and generates traceable factor research reports with IS/OOS Rank IC, IC decay, factor-correlation diagnostics, grouped returns, long-short backtests, downloadable artifacts, and node-level event traces.
