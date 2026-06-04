# A-Share Factor Research Agent V5 Embedding RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline deterministic embedding-backed retrieval for document chunks.

**Architecture:** Add a local hashing embedder and vector retriever under `app/rag`. Update `RetrieveChunksNode` to support `keyword`, `vector`, and `hybrid` retrieval modes while preserving source discovery and existing factor extraction.

**Tech Stack:** Python, NumPy, LangGraph, FastAPI, pytest.

---

## Tasks

### Task 1: Embedding and Vector Retrieval

- [x] Create `app/rag/embeddings.py`.
- [x] Create `app/rag/vector_retriever.py`.
- [x] Implement deterministic normalized hashing embeddings.
- [x] Implement cosine vector search.
- [x] Implement hybrid keyword/vector retrieval with deduplication.

### Task 2: Graph and API Integration

- [x] Extend `ResearchState` with `retrieval_mode`, `embedding_dim`, and `retrieval_diagnostics`.
- [x] Add `retrieval_mode` and `embedding_dim` to `ResearchRunRequest`.
- [x] Update `RetrieveChunksNode` to choose keyword/vector/hybrid retrieval.
- [x] Add retrieval diagnostics to trace summaries.

### Task 3: Tests and Docs

- [x] Add tests for embeddings and vector retrieval.
- [x] Add workflow tests for vector and hybrid modes.
- [x] Add API test for `retrieval_mode=vector`.
- [x] Update README, REPORT, and harness state.

### Task 4: Verification

- [x] Run `pytest -v`.
- [x] Run `python evals/run_eval.py`.
- [x] Run `python -m compileall app`.
- [x] Commit and push V5.
