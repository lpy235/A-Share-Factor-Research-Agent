# Roadmap

## Current State

The project is a working MVP:

- FastAPI dashboard and JSON APIs
- LangGraph factor research workflow
- Public/uploaded source ingestion
- Keyword, vector, and hybrid retrieval
- Schema-validated LLM extraction path with deterministic fallback
- Restricted Factor DSL validation and execution
- Fixture and optional AKShare data providers
- IC, RankIC, grouped returns, long-short backtest metrics
- Node-level SQLite trace events
- Deterministic test and eval suite

## High-Value Next Steps

1. Add richer backtest artifacts: equity curve, grouped return chart, IC time series, and downloadable report bundle.
2. Add real public search integration while preserving source policy filters.
3. Add experiment persistence so past runs can be reopened from the dashboard.
4. Add model-backed embeddings as an optional retrieval backend.
5. Add stronger A-share universe/date handling and survivorship-bias notes.

## Completion Route

### V9 Research Artifacts

Make each run produce a visible artifact set: charts, metrics JSON, factor JSON, Markdown report, and a downloadable bundle. Add artifact list/download APIs and surface them in the dashboard.

V14 extends this artifact layer with real backtest series: Rank IC time series, cumulative IC, long-short equity, drawdown, grouped returns, and `backtest_series.json`.

### V10 Experiment History

Persist completed runs with configuration, response payload, timestamps, and status. Add recent-run listing and reopening from the dashboard.

### V11 Public Source Discovery

Connect optional live public search behind source-policy gates. Preserve deterministic fallback sources and expose accepted/rejected source diagnostics.

### V12 A-Share Backtest Assumptions

Add explicit universe/date diagnostics, transaction-cost and rebalance assumptions, stronger data-provider notes, and bias warnings for fixture and public data providers.

### V13 Agent Audit Trail

Turn raw workflow events into readable explanations: why sources were used, why factors were extracted, why factors passed or failed selection, and where fallbacks occurred.

## Out Of Scope

- Auto-trading
- Order execution
- Stock recommendations
- Return promises
- Paid/login-required research scraping
