# Architecture

## Purpose

This project is an A-share factor research agent for quant strategy research workflows. It turns public or uploaded research material into factor hypotheses, validates the hypotheses through a restricted Factor DSL, runs backtests on A-share daily data, and produces traceable reports.

It is intentionally safe and reproducible by default: fixture market data, rule-based extraction, deterministic hashing embeddings, and curated public sources keep the demo runnable without live services.

## End-to-End Flow

```text
public/uploaded research material
-> document parsing and chunking
-> keyword/vector/hybrid retrieval
-> rule or schema-validated LLM factor extraction
-> restricted Factor DSL generation
-> DSL validation
-> fixture、演示性 AKShare 或固定版本的本地原始日频数据
-> factor execution
-> IC / RankIC / grouped returns / diagnostic long-short metrics
-> next-open long-only portfolio / turnover / transaction costs
-> factor selection
-> Markdown report and LangGraph event trace
```

## LangGraph Nodes

```text
LoadDocumentsNode
RetrieveChunksNode
ExtractHypothesesNode
GenerateFactorDSLNode
ValidateDSLNode
LoadMarketDataNode
ExecuteFactorsNode
RunBacktestNode
SelectFactorsNode
GenerateReportNode
```

Each node writes compact SQLite events through `EventStore`. The dashboard reads those events from `GET /runs/{run_id}/events`.

## Module Map

```text
app/api        FastAPI routers for UI, document/universe upload, research runs, trace events
app/agents     LangGraph workflow, node implementations, extraction schemas/prompts
app/backtest   IC diagnostics, next-open portfolio simulation, costs, selection, and risk metrics
app/data       Fixture data, optional AKShare adapter, local daily-bar cache
app/market_data Versioned DuckDB catalog, Parquet raw daily-bar lake, import and quality gates
app/factor     Restricted Factor DSL, strict validator, operators, controlled AST interpreter
app/llm        OpenAI-compatible client wrapper
app/rag        Chunking, keyword retrieval, hashing embeddings, vector/hybrid retrieval
app/reports    Markdown report and chart helpers
app/sources    Public-source policy, discovery, fetching, parsing
app/storage    SQLite events and controlled document/historical-universe storage
app/web        FastAPI-served dashboard assets
evals          Deterministic evaluation tasks
fixture_docs   Demo research note
tests          Unit, API, graph, and integration tests
```

## Safety Defaults

```text
source_mode = auto
retrieval_mode = hybrid
extraction_mode = rule
enable_llm_extraction = false
data_provider = fixture
cache_enabled = true
fallback_to_fixture = true
allow_live_fetch = false
```

The system does not execute arbitrary model-generated Python. Factor formulas are validated against a restricted DSL with whitelisted fields and operators.

## Versioned Raw Daily Data Warehouse

Production-oriented research uses `data_provider=warehouse` with a required, already-published `data_version`. The warehouse keeps metadata in DuckDB (`market_data/warehouse.duckdb`) and raw daily bars in Parquet (`market_data/lake/`), with a JSON manifest and content hash for every published version. Each raw bar carries `source`, `ingested_at`, `data_version`, and `adjustment`; quality publication requires `adjustment="none"`.

Published versions are immutable. Daily updates are child versions containing only the new trading-day delta; their manifests point to `parent_version_id`, and the provider resolves the complete parent-child chain when loading a research run. Warehouse loading never falls back to fixture data. The selected version, manifest hash, and source are stored in the report assumptions and artifact bundle so a research run can be replayed against the same input snapshot.

The current baseline runbook is [market-data-baseline-runbook.md](market-data-baseline-runbook.md). It deliberately requires a small, auditable CSV rehearsal before a full-universe historical backfill.

## Factor DSL Contract

`FactorDslValidator` is the mandatory boundary between generated `FactorSpec` objects and factor execution. It parses each formula as an expression AST and enforces all of the following before a factor can run:

```text
field names          registered market-data fields only
operator calls       registered operators with explicit signatures only
window arguments     integer constants in 1..2520 (MAX_WINDOW)
required_fields      exactly equal to fields derived from the formula AST
lookback             greater than or equal to the largest derived window
formula complexity   bounded source length, AST node count, and call depth
```

Negative, zero, non-integer, and oversized windows are rejected. This prevents formulas such as `delay(close, -1)` from requesting forward data through a time-series operator. Validation results use stable error codes so `ValidateDSLNode` can exclude invalid candidates, record actionable warnings, and expose the decision in the workflow trace. When every candidate is invalid, the deterministic fallback factor is accepted only if it passes this same contract.

## Controlled Factor Execution

`FactorExecutor` does not evaluate formula strings as general Python. After validation, it passes the parsed expression tree to an in-process controlled AST interpreter. The interpreter resolves field names from the market-data environment and operator names from the registry, and implements only approved numeric constants, arithmetic nodes, unary negation, and calls. Attributes, subscripts, comprehensions, lambdas, imports, builtins, and dynamic lookup are outside the executable surface. The returned value must be a Pandas `Series` whose index matches the input market-data index.

The interpreter is an application-level semantic boundary, not a resource sandbox. It runs in the API/worker process and does not by itself provide CPU, memory, wall-clock, or operating-system isolation. A production deployment that accepts untrusted formulas should add process isolation, execution timeouts, memory limits, and workload quotas around this layer.

## Backtest Semantics

The legacy single-factor layer computes close-to-next-close forward returns for Rank IC and G5-G1 diagnostics. It remains unchanged for compatibility. The executable portfolio layer is separate and uses:

```text
signal at t close -> execution at t+1 open -> valuation at t+2 open
```

`BacktestConfig` validates the execution mode, commission, sell-side stamp duty, slippage, ST filter, and minimum listing age. `run_long_only_backtest` ranks the direction-normalized factor, holds the top quintile at equal weight, checks execution-date suspension and price limits, carries positions that cannot be sold, and returns gross/net returns, turnover, component costs, weights, and diagnostics. IS and OOS data slices invoke the engine independently so both segments begin flat.

Optional market-data fields are applied only when present:

```text
in_universe is_suspended is_st days_since_listing limit_up limit_down
```

Missing fields appear in `tradability_diagnostics`; the system never claims an unavailable rule was enforced. Historical membership is registered through `POST /universes` as a strict `date,symbol,in_universe` CSV and resolved only by an opaque `historical_universe_id`. Without it, the fixed provider universe is retained with an explicit survivorship-bias warning.
