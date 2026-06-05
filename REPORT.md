# Demo Report

## Project

A-Share Factor Research Agent is a quant strategy / AI Agent internship portfolio project.

It demonstrates a controlled research loop:

```text
factor idea extraction
-> safe Factor DSL
-> deterministic factor execution
-> IC / RankIC validation
-> grouped return and long-short backtest
-> factor selection
-> traceable Markdown report
```

## First-Version Demo

The first version runs offline with fixture A-share data and deterministic factor extraction.

Default demo topic:

```text
A股量价类动量因子
```

Extracted factor:

```text
volume_price_momentum
```

Formula:

```text
rank(returns(close, 20) * ts_mean(volume, 20) / ts_mean(volume, 60))
```

## V2 Document-Driven Demo

V2 upgrades the project from a fixed demo note to user-provided research material.

New workflow:

```text
POST /documents
-> save Markdown/txt/PDF material
-> return document_id
-> POST /research/runs with document_ids
-> parse uploaded document
-> chunk and retrieve relevant content
-> extract factor hypothesis from uploaded text
-> generate Factor DSL
-> validate and backtest
-> return report and events
```

Smoke test result:

```text
uploaded file: fixture_docs/demo_factor_note.md
selected factor: volume_price_momentum
source title in factor spec: demo_factor_note.md
```

## Verification

The current version is expected to pass:

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
```

Latest verified result:

```text
pytest -v                 53 passed
python evals/run_eval.py  accuracy 1.0
python -m compileall app  passed
```

## V3 LangGraph Agent Workflow

V3 replaces the monolithic workflow with a LangGraph `StateGraph`.

Graph nodes:

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

Each node records compact SQLite events, including start, completion, fallback, and failure events. This makes `/runs/{run_id}/events` a full agent trace rather than only a run-level log.

## V4 Public-Source Discovery

V4 adds `auto` and `hybrid` source modes.

Source modes:

```text
upload: parse uploaded documents only
auto: discover allowed public sources from the research topic
hybrid: combine uploaded documents and public sources
```

The public-source path is deterministic by default. It uses a curated seed set of public A-share factor research pages, applies `SourcePolicy`, and avoids live fetching unless `allow_live_fetch=true`.

Example request:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","max_sources":2}'
```

## V5 Embedding RAG

V5 replaces keyword-only retrieval with an embedding-backed retrieval layer.

Retrieval modes:

```text
keyword: existing token-overlap retrieval
vector: cosine similarity over deterministic hashing embeddings
hybrid: combine keyword and vector scores, then deduplicate chunks
```

The default is `hybrid`. This keeps the demo offline and deterministic while making the RAG architecture explicit and extensible.

Example request:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","retrieval_mode":"vector","embedding_dim":128}'
```

## V6 Structured LLM Extraction

V6 adds schema-validated LLM factor extraction while preserving offline deterministic fallback.

Extraction modes:

```text
rule: deterministic rule extraction only
llm: try LLM extraction, then fall back to rules
hybrid: use rules unless enable_llm_extraction=true
```

The LLM response must validate as a top-level `{"factors": [...]}` JSON object where each item matches `FactorHypothesis`. Invalid JSON or schema failures get one repair attempt, then the workflow falls back to rule extraction and records extraction diagnostics in the graph trace.

Example request:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"auto","extraction_mode":"rule"}'
```

## Limitations

- Fixture data is used for deterministic demo execution.
- Live AKShare data is implemented as an adapter but not required by tests.
- Public-source discovery uses curated deterministic seeds by default; live fetch is optional.
- Embeddings use a deterministic hashing backend by default; model-backed embeddings are deferred.
- LLM extraction is optional and schema-validated; deterministic fallback keeps the project working without API keys.
- Historical backtests are research artifacts and do not constitute investment advice.

## Next Steps

- Replace hashing embeddings with optional sentence-transformers or ChromaDB.
- Replace curated public-source seeds with a real search API integration.
- Add real AKShare demo mode and data caching.
