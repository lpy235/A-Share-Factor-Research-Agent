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

## Out Of Scope

- Auto-trading
- Order execution
- Stock recommendations
- Return promises
- Paid/login-required research scraping

