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
-> fixture or AKShare A-share daily data
-> factor execution
-> IC / RankIC / grouped returns / long-short metrics
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
app/api        FastAPI routers for UI, document upload, research runs, trace events
app/agents     LangGraph workflow, node implementations, extraction schemas/prompts
app/backtest   IC, grouped return, selection, and risk metrics
app/data       Fixture data, optional AKShare adapter, local daily-bar cache
app/factor     Restricted Factor DSL, validator, operators, executor
app/llm        OpenAI-compatible client wrapper
app/rag        Chunking, keyword retrieval, hashing embeddings, vector/hybrid retrieval
app/reports    Markdown report and chart helpers
app/sources    Public-source policy, discovery, fetching, parsing
app/storage    SQLite event storage and filesystem document storage
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

