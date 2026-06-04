# A-Share-Factor-Research-Agent

An A-share factor research agent that extracts factor ideas from public or uploaded research materials, converts them into a safe Factor DSL, validates them on A-share daily data, and produces traceable research reports.

This repository is being built as a quant strategy / AI Agent internship portfolio project.

## What It Does

```text
public/uploaded research material
-> factor hypothesis extraction
-> restricted Factor DSL
-> A-share daily data
-> IC / RankIC / grouped returns / long-short backtest
-> factor selection
-> traceable Markdown report
```

The first version is intentionally deterministic: it can run without an LLM key or live market data by using rule-based extraction and fixture A-share data. Live LLM extraction and AKShare data adapters are included as extension points.

## Safety Boundary

This project is a research workflow demo. It does not provide investment advice, stock recommendations, return promises, or trading execution.

The LLM is not allowed to execute arbitrary Python. It can only produce a restricted Factor DSL using whitelisted fields and operators.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install pandas numpy fastapi pydantic pydantic-settings python-dotenv requests beautifulsoup4 matplotlib pytest uvicorn openai pypdf langgraph
pytest -v
python evals/run_eval.py
```

Run the API:

```bash
uvicorn app.main:app --port 8000
```

Smoke test:

```bash
curl -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload"}'
```

## Current MVP

- Restricted Factor DSL validation
- Safe formula execution with whitelisted operators
- Deterministic A-share fixture data provider
- Document upload API for Markdown/txt/PDF materials
- Public-source discovery for `auto` and `hybrid` research modes
- Document-driven chunk retrieval before factor extraction
- LangGraph research workflow with explicit agent nodes
- Node-level SQLite trace for every research run
- Rule-based factor hypothesis extraction fallback
- Factor validation and long-short backtest metrics
- SQLite event trace
- FastAPI research endpoint
- Deterministic eval runner

## V3 LangGraph Agent Workflow

The research run is now executed by a LangGraph `StateGraph`:

```text
LoadDocuments
-> RetrieveChunks
-> ExtractHypotheses
-> GenerateFactorDSL
-> ValidateDSL
-> LoadMarketData
-> ExecuteFactors
-> RunBacktest
-> SelectFactors
-> GenerateReport
```

Each node writes compact events to SQLite, so `/runs/{run_id}/events` can show how the agent moved from source material to factor selection and report generation.

## V4 Public-Source Discovery

Research runs now support three source modes:

```text
upload: use uploaded Markdown/txt/PDF materials
auto: discover allowed public research sources from the topic
hybrid: combine uploaded materials with discovered public sources
```

The default public-source discovery path is deterministic and offline-friendly. It uses a curated seed set of public A-share factor papers/articles, filters candidates through `SourcePolicy`, and only fetches live URL content when `allow_live_fetch=true`.

Auto-source demo:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","max_sources":2}'
```

## V2 Document-Driven Demo

Upload a document:

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -F "file=@fixture_docs/demo_factor_note.md"
```

Run research with the returned `document_id`:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload","document_ids":["<document_id>"]}'
```

## Resume Positioning

> Built an A-share factor research agent that discovers public A-share research materials or reads uploaded documents, extracts factor hypotheses, converts them into a restricted Factor DSL, validates them on daily A-share data, and generates traceable factor research reports with IC/RankIC, grouped returns, long-short backtests, and selection rules.
