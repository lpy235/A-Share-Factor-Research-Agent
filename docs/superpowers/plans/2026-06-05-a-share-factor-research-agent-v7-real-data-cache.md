# A-Share Factor Research Agent V7 Real Data Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional real A-share data mode with local CSV caching while preserving deterministic fixture defaults.

**Architecture:** Introduce a provider factory and cache wrapper in `app/data`. `LoadMarketDataNode` selects the configured provider, records market data diagnostics, and falls back to fixture data when live data fails and fallback is enabled.

**Tech Stack:** Python, pandas, AkShare adapter, filesystem CSV cache, FastAPI, LangGraph, pytest.

---

## Tasks

### Task 1: Data Cache and Provider Selection

- [x] Create `app/data/cache.py`.
- [x] Create `app/data/provider_factory.py`.
- [x] Implement per-symbol CSV cache keys.
- [x] Wrap providers with cache support.
- [x] Add fixture fallback support.

### Task 2: Graph and API Integration

- [x] Extend `ResearchState` with `data_provider`, `cache_enabled`, `fallback_to_fixture`, `market_data_cache_dir`, and `market_data_diagnostics`.
- [x] Add these fields to `ResearchRunRequest`.
- [x] Update `LoadMarketDataNode` to use provider factory.
- [x] Add provider/cache/fallback diagnostics to trace summaries.

### Task 3: Tests and Docs

- [x] Add data cache tests.
- [x] Add provider factory tests with fake providers.
- [x] Add workflow/API tests for fixture defaults and provider fields.
- [x] Update README, REPORT, and harness state.

### Task 4: Verification

- [x] Run `pytest -v`.
- [x] Run `python evals/run_eval.py`.
- [x] Run `python -m compileall app`.
- [ ] Commit and push V7.
