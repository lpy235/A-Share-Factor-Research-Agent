# A-Share Factor Research Agent V6 Structured LLM Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add schema-validated LLM factor hypothesis extraction with deterministic fallback.

**Architecture:** Add a structured extraction service under `app/agents/extraction.py`. `ExtractHypothesesNode` chooses rule/LLM/hybrid extraction based on state flags, validates all LLM outputs with `FactorHypothesis`, records diagnostics, and falls back to rule extraction when needed.

**Tech Stack:** Python, Pydantic, existing OpenAI client wrapper, LangGraph, pytest.

---

## Tasks

### Task 1: Extraction Service

- [x] Extend `app/agents/extraction.py` with `StructuredFactorExtractor`.
- [x] Add LLM prompt rendering using retrieved chunks.
- [x] Parse top-level `{"factors": [...]}` JSON.
- [x] Validate each item with `FactorHypothesis`.
- [x] Return extraction diagnostics.

### Task 2: Graph and API Integration

- [x] Extend `ResearchState` with `extraction_mode`, `enable_llm_extraction`, `llm_retry_count`, and `extraction_diagnostics`.
- [x] Add these fields to `ResearchRunRequest`.
- [x] Update `ExtractHypothesesNode` to use the structured extractor.
- [x] Add extraction diagnostics to trace summaries.

### Task 3: Tests and Docs

- [x] Add tests for valid LLM extraction with a fake client.
- [x] Add tests for invalid LLM output fallback.
- [x] Add workflow/API tests for extraction controls.
- [x] Update README, REPORT, and harness state.

### Task 4: Verification

- [x] Run `pytest -v`.
- [x] Run `python evals/run_eval.py`.
- [x] Run `python -m compileall app`.
- [x] Commit and push V6.
