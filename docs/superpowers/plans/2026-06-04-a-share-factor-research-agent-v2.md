# A-Share Factor Research Agent V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade V1 from a fixed demo workflow into a user-document-driven factor research agent.

**Architecture:** V2 adds a document upload API and filesystem-backed document registry. The research workflow accepts `document_ids`, parses uploaded Markdown/text/PDF files, chunks them, retrieves relevant chunks by topic, extracts factor hypotheses, generates Factor DSL, and runs the existing deterministic validation/backtest/report pipeline.

**Tech Stack:** FastAPI, UploadFile, python-multipart, Pydantic, filesystem document registry, existing parser/chunker/retriever/factor/backtest modules.

---

## V2 Scope

In scope:

```text
POST /documents
GET /documents/{document_id}
POST /research/runs with document_ids
uploaded Markdown/txt/PDF parsing
topic-based chunk retrieval
factor extraction from uploaded content
event trace for document-driven runs
README/REPORT update
tests for document store, upload API, and workflow
```

Out of scope for this version:

```text
embedding-backed vector DB
live LLM extraction
real public web search
full LangGraph StateGraph
large-scale A-share live data demo
```

## Implementation Tasks

### Task 1: Document Store

Create `app/storage/documents.py`.

Responsibilities:

```text
save uploaded file bytes
assign document_id
persist index.json
resolve document_id to path
return metadata for API
```

### Task 2: Document API

Create `app/api/documents.py`.

Endpoints:

```text
POST /documents
GET /documents/{document_id}
```

### Task 3: Research API Upgrade

Modify `app/api/research.py`.

Add:

```text
document_ids: list[str] = []
max_chunks: int = 5
```

Resolve `document_ids` through `DocumentStore` and pass `document_paths` into workflow state.

### Task 4: Workflow Uses Uploaded Documents

Modify `app/agents/graph.py`.

Flow:

```text
if document_paths:
  parse files
  chunk files
  retrieve top chunks by research_topic
else:
  use deterministic demo chunk
```

Then continue existing factor extraction, DSL generation, factor execution, metrics, selection, and report.

### Task 5: Tests

Add tests:

```text
test_document_store.py
test_document_api.py
test_workflow_documents.py
```

### Task 6: Final Verification

Run:

```bash
pytest -v
python evals/run_eval.py
python -m compileall app
```

Smoke test:

```bash
uvicorn app.main:app --port 8000
curl -F "file=@fixture_docs/demo_factor_note.md" http://127.0.0.1:8000/documents
curl -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload","document_ids":["<id>"]}'
```

