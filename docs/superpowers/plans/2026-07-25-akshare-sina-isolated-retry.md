# AKShare Sina Isolated Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent a transient batch failure from incorrectly recording every symbol in that batch as failed.

**Architecture:** Keep the existing batch request and retry path. When it exhausts retries, retry every member of that failed batch individually, write successful responses, and record only individual failures. The current failed draft remains unmodified as audit evidence; the corrected logic is used by a new run.

**Tech Stack:** Python 3.14, pandas, DuckDB, Parquet, pytest.

---

### Task 1: Cover batch failure isolation

**Files:**
- Modify: `tests/test_market_data_ingestion.py`

- [x] Add a source double that fails a multi-symbol request but succeeds for every singleton except `000002.SZ`.
- [x] Assert that only `000002.SZ` is recorded, and successful peers are persisted.

### Task 2: Isolate failures after bounded batch retries

**Files:**
- Modify: `app/market_data/ingestion.py`

- [ ] Extract the existing bounded fetch-and-write retry loop into a helper that returns the final exception and attempt count.
- [ ] On a batch failure, call that helper for each singleton and only record singleton failures.

### Task 3: Verify and run a fresh baseline ingest

**Files:**
- Test: `tests/test_market_data_ingestion.py`

- [ ] Run the new regression test red then green, followed by the market-data tests and static checks.
- [ ] Start a new AKShare Sina run; do not resume the draft that contains false error records.

### Task 4: Space transient source retries

**Files:**
- Modify: `app/market_data/ingestion.py`
- Modify: `tests/test_market_data_ingestion.py`

- [x] Add a recovering source test that asserts 1-second then 2-second delays between retries.
- [ ] Apply those bounded delays before retrying a failed source request.
