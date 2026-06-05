# A-Share Factor Research Agent

A resume-ready quant strategy / AI Agent project for A-share factor research.

It reads public or uploaded research material, retrieves factor evidence, extracts factor hypotheses, converts them into a restricted Factor DSL, validates them on A-share daily data, runs factor backtests, selects candidate factors, and renders a traceable research report in a browser dashboard.

## What It Does

```text
public/uploaded research material
-> RAG retrieval
-> schema-validated or rule-based factor extraction
-> restricted Factor DSL
-> fixture or optional AKShare A-share daily data
-> IC / RankIC / grouped returns / long-short metrics
-> factor selection
-> Markdown report + LangGraph trace
```

## Demo

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install pandas numpy scipy fastapi pydantic pydantic-settings python-dotenv requests beautifulsoup4 matplotlib pytest uvicorn openai pypdf langgraph python-multipart
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
- Restricted Factor DSL with whitelisted fields and operators.
- Deterministic fixture A-share data plus optional AKShare mode and local CSV cache.
- Factor validation, IC/RankIC, grouped returns, long-short metrics, and factor selection.
- Deterministic eval runner and 60+ pytest coverage.

## Safety Boundary

This is a research workflow demo. It does not provide investment advice, stock recommendations, return promises, order execution, or auto-trading.

Model output cannot execute arbitrary Python. It must pass schema validation and produce formulas in a restricted Factor DSL.

## Repository Map

```text
app/api        FastAPI routes for dashboard, documents, runs, and trace events
app/agents     LangGraph workflow, nodes, extraction logic, prompts, schemas
app/backtest   Factor metrics and selection
app/data       Fixture data, optional AKShare adapter, daily-bar cache
app/factor     Restricted Factor DSL, validator, operators, executor
app/rag        Chunking, keyword retrieval, hashing embeddings, vector retrieval
app/sources    Public-source policy, discovery, fetching, parsing
app/storage    SQLite event store and uploaded document store
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

API smoke test:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","data_provider":"fixture","cache_enabled":true}'
```

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Demo Guide](docs/DEMO.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Roadmap](docs/ROADMAP.md)
- [Demo Report](REPORT.md)

Detailed historical specs and implementation plans are kept under `docs/superpowers/`.

## Resume Positioning

> Built an A-share factor research agent with a FastAPI dashboard and LangGraph workflow. The system discovers public A-share research materials or reads uploaded documents, retrieves evidence with hybrid RAG, extracts schema-validated factor hypotheses with deterministic fallback, converts them into a restricted Factor DSL, validates them on cached fixture or optional AKShare daily data, and generates traceable factor research reports with IC/RankIC, grouped returns, long-short backtests, and node-level event traces.
