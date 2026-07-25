# Raw A-Share Daily Data Warehouse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, versioned warehouse for 8-10 years of full A-share unadjusted daily market data, with daily incremental updates and fixed data versions for every backtest.

**Architecture:** Store immutable version manifests and operational metadata in DuckDB, and store large market tables as date-partitioned Parquet files. Every raw row carries `source`, `ingested_at`, and `data_version`; a published data version is immutable and its manifest pins the exact partitions used by research and backtests. Data-source adapters implement one contract so an initial AKShare unadjusted source can later be replaced by an authorized team CSV/API adapter without changing the warehouse or research layers.

**Source priority (updated):** Prefer one internally exported file or one manually reviewed GitHub snapshot imported as local CSV/Parquet with repository revision and file checksum recorded. 第一版不使用在线接口补数；数据不完整时直接标记覆盖缺口，不混入不同口径的临时拉取结果。

**Tech Stack:** Python 3.14, pandas, PyArrow, DuckDB, Parquet, FastAPI, pytest, existing AkShare optional adapter.

---

## Non-Negotiable Data Rules

- Raw prices are stored with `adjustment = "none"`. No qfq, hfq, or vendor-adjusted close can enter `raw_daily_bars`.
- Corporate actions are stored as independent source events. A later research-price transform must declare its corporate-action rule and data version; it must never overwrite raw prices.
- A backtest accepts a published `data_version`, never a mutable "latest" directory.
- A data version is published only after row-count, uniqueness, calendar, OHLC, and continuity checks pass.
- Source records remain attributable even after a newer version supersedes them.

## Execution Order

1. Define the warehouse contract and version manifest before downloading any history.
2. Build the local storage, query, and immutable publication mechanics using small fixtures.
3. Add security master, exchange calendar, raw daily bars, corporate actions, and trading status ingestion.
4. Import and validate 一份 reviewed 8-10 year full-universe snapshot, then publish the first baseline version. 覆盖缺口保留在质量报告中，待后续统一替换快照，不使用在线补数。
5. Add daily incremental collection, quality gates, and operational alert output.
6. Change research runs to require and record a published data version.
7. Add historical index membership and point-in-time financial data as subsequent data domains.

## Target Layout

```text
market_data/
  warehouse.duckdb
  manifests/
    v20260724_001.json
  lake/
    raw_daily_bars/data_version=v20260724_001/year=2020/part-000.parquet
    corporate_actions/data_version=v20260724_001/year=2020/part-000.parquet
    security_master/data_version=v20260724_001/part-000.parquet
    trading_calendar/data_version=v20260724_001/part-000.parquet
    security_status/data_version=v20260724_001/year=2020/part-000.parquet
```

Each Parquet row includes `source`, `ingested_at`, and `data_version`. The DuckDB metadata tables include `data_versions`, `ingest_runs`, `quality_results`, and `version_partitions`.

### Task 1: Warehouse Contract and Metadata Registry (Completed: `8fc4be7`)

**Files:**
- Create: `app/market_data/models.py`
- Create: `app/market_data/catalog.py`
- Create: `app/market_data/paths.py`
- Create: `tests/test_market_data_catalog.py`
- Modify: `pyproject.toml`

- [x] **Step 1: Add failing metadata tests**

```python
def test_catalog_publishes_immutable_version(tmp_path):
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="akshare", as_of_date="2026-07-24")
    catalog.publish(version.version_id, manifest={"tables": {"raw_daily_bars": 10}})
    assert catalog.get_version(version.version_id).status == "published"
    with pytest.raises(ValueError, match="immutable"):
        catalog.publish(version.version_id, manifest={"tables": {"raw_daily_bars": 11}})
```

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_market_data_catalog.py -q`

Expected: FAIL because `DataCatalog` does not exist.

- [x] **Step 3: Add explicit models and DuckDB registry**

Define `DataVersion`, `IngestRun`, and `QualityResult` dataclasses. `DataCatalog` creates the metadata schema, creates draft versions, records partition manifests and quality results, and allows a one-way `draft -> published` transition. Add `duckdb` and `pyarrow` to project dependencies.

- [x] **Step 4: Run the focused test and commit**

Run: `.venv/bin/pytest tests/test_market_data_catalog.py -q`

Expected: PASS.

Commit: `feat: add versioned market data catalog`

### Task 2: Immutable Parquet Tables and Schema Validation (Completed: `8fc4be7`)

**Files:**
- Create: `app/market_data/schemas.py`
- Create: `app/market_data/store.py`
- Create: `tests/test_market_data_store.py`

- [x] **Step 1: Write failing raw-bar storage tests**

```python
def test_store_writes_unadjusted_daily_bars_with_lineage(tmp_path, raw_bars):
    store = MarketDataStore(tmp_path)
    path = store.write_raw_daily_bars(raw_bars, data_version="v1", source="fixture")
    loaded = store.read_raw_daily_bars("v1", "2020-01-01", "2020-01-31")
    assert path.exists()
    assert {"source", "ingested_at", "data_version", "adjustment"} <= set(loaded.columns)
    assert loaded["adjustment"].eq("none").all()
```

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_market_data_store.py -q`

Expected: FAIL because `MarketDataStore` does not exist.

- [x] **Step 3: Implement schema validation and partitioned writes**

Require `symbol`, `trade_date`, `open`, `high`, `low`, `close`, `volume`, and `amount` for raw daily bars. Reject adjusted input, duplicate `(symbol, trade_date)` rows, non-positive prices, invalid OHLC bounds, and a caller-supplied lineage column. Add lineage internally, write year partitions, and read only by explicit data version.

- [x] **Step 4: Add event-table schemas**

Implement independent writers for `security_master`, `trading_calendar`, `corporate_actions`, and `security_status`. Each validates its natural key and includes lineage columns. Do not derive adjusted prices in this task.

- [x] **Step 5: Run focused tests and commit**

Run: `.venv/bin/pytest tests/test_market_data_store.py -q`

Expected: PASS.

Commit: `feat: add immutable raw A-share data store`

### Task 3: Source Adapter Boundary and Unadjusted AKShare Adapter (Completed: `8099b5b`)

**Files:**
- Create: `app/market_data/sources/base.py`
- Create: `app/market_data/sources/akshare_raw.py`
- Create: `app/market_data/sources/csv_import.py`
- Create: `tests/test_market_data_sources.py`
- Modify: `app/data/ashare_provider.py`

- [x] **Step 1: Write adapter-contract tests**

Test an in-memory source against `RawMarketDataSource`. Test that the AKShare request is constructed with `adjust=""`, and that a normalized result has no adjusted-price field. Test that the CSV adapter rejects missing source metadata and duplicate raw-bar keys.

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_market_data_sources.py -q`

Expected: FAIL because the raw-source contract and adapters do not exist.

- [x] **Step 3: Implement source adapters**

Define `list_securities(as_of_date)`, `fetch_daily_bars(symbols, start_date, end_date)`, `fetch_corporate_actions(start_date, end_date)`, `fetch_calendar(start_date, end_date)`, and `fetch_security_status(start_date, end_date)`. The AKShare adapter must request unadjusted prices only; unavailable domains must return an explicit capability error rather than fabricating status. The CSV adapter is the future team-data entry point and maps documented columns into the same normalized schemas.

- [x] **Step 4: Replace the current five-symbol AKShare universe shortcut**

Keep `AkshareAshareDataProvider` only as a temporary compatibility wrapper. Make it delegate to the normalized raw source and return an explicit limitation until the baseline full-universe version is published.

- [x] **Step 5: Run focused tests and commit**

Run: `.venv/bin/pytest tests/test_market_data_sources.py tests/test_data_provider_factory.py -q`

Expected: PASS.

Commit: `feat: add raw market data source adapters`

### Task 4: Historical Backfill and Resumable Ingestion (In Progress: `3f212ef`)

**Files:**
- Create: `app/market_data/ingestion.py`
- Create: `scripts/backfill_raw_ashare.py`
- Create: `tests/test_market_data_ingestion.py`
- Modify: `Makefile`

- [x] **Step 1: Write resumability tests**

```python
def test_backfill_resumes_from_completed_symbols(tmp_path, fake_source):
    service = BackfillService(catalog, store, fake_source)
    first = service.run("2016-01-01", "2026-07-24", batch_size=2, stop_after_batches=1)
    second = service.resume(first.ingest_run_id)
    assert second.status == "completed"
    assert second.completed_symbol_count == 4
```

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_market_data_ingestion.py -q`

Expected: FAIL because `BackfillService` does not exist.

- [ ] **Step 3: Implement bounded historical ingestion**

Current status: bounded batches, resumable cursor, draft-only writes, finite retries and per-symbol error records are complete. Period-sensitive universe snapshots remain; for the first local snapshot import, this will be derived from the supplied security-master fields rather than an online query.

Fetch the security universe as of each relevant period, split symbols into bounded batches, persist the completed batch cursor after every successful write, retry transient source failures with a finite retry count, and record errors per symbol. Never publish the draft data version during this step.

- [x] **Step 4: Add the operator command**

Add `make backfill-raw-ashare START=2016-01-01 END=2026-07-24` calling the script. The script must print the draft version, ingest run id, completed-symbol count, failed-symbol count, and next resume command.

- [x] **Step 5: Run focused tests and commit**

Run: `.venv/bin/pytest tests/test_market_data_ingestion.py -q`

Expected: PASS.

Commit: `feat: add resumable raw A-share backfill`

### Task 5: Quality Gates and Version Publication (In Progress)

**Files:**
- Create: `app/market_data/quality.py`
- Create: `tests/test_market_data_quality.py`
- Modify: `app/market_data/ingestion.py`

- [x] **Step 1: Write failing quality-gate tests**

Test duplicate keys, invalid OHLC relations, missing exchange trading dates, unexpectedly large price gaps, missing lineage, and failed symbols above a configured threshold. Assert that a failing check leaves the version in `draft` status.

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_market_data_quality.py -q`

Expected: FAIL because no quality-gate service exists.

- [ ] **Step 3: Implement quality report and publish gate**

Current status: raw-bar lineage, uniqueness, OHLC, unadjusted flag, expected-date coverage and failed-symbol thresholds are persisted. Completed ingestion automatically publishes only a passing draft. Unexpected price-gap detection and richer quality samples remain.

Create a deterministic `QualityReport` with check name, severity, affected count, sample keys, and pass status. Publish only when hard checks pass; persist the report in DuckDB and the immutable version manifest. A failed backfill remains resumable and queryable only as draft data.

- [x] **Step 4: Run focused tests and commit**

Run: `.venv/bin/pytest tests/test_market_data_quality.py -q`

Expected: PASS.

Commit: `feat: gate data version publication on quality checks`

### Task 6: Daily Incremental Update and Operations (Completed)

**Files:**
- Create: `app/market_data/daily_update.py`
- Create: `scripts/update_raw_ashare.py`
- Create: `tests/test_market_data_daily_update.py`
- Modify: `Makefile`
- Modify: `docs/DEVELOPMENT.md`

- [x] **Step 1: Write daily-update tests**

Test that a non-trading day performs no source request, a successful trading day creates a child draft version, repeated execution is idempotent, and an incomplete update remains unpublished.

- [x] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_market_data_daily_update.py -q`

Expected: FAIL because `DailyUpdateService` does not exist.

- [x] **Step 3: Implement one-version-per-successful-update semantics**

Current status: child-version creation, non-trading-day skip, incomplete-draft behavior, idempotency, parent-chain reads and local CSV calendar integration are complete.

Read the latest published version, obtain the next trading date from the versioned calendar, ingest only that date's raw bars and events, run the same quality gates, write a child manifest referencing unchanged parent partitions, then publish the child version atomically.

- [x] **Step 4: Add operator commands and recovery documentation**

Add `make update-raw-ashare` and `make resume-raw-ashare RUN_ID=<id>`. Document disk location, expected runtime, source failure behavior, retry policy, and how to archive a bad draft version without deleting published versions.

- [x] **Step 5: Run focused tests and commit**

Run: `.venv/bin/pytest tests/test_market_data_daily_update.py -q`

Expected: PASS.

Commit: `feat: add daily raw A-share update pipeline`

### Task 7: Freeze Market Data for Research and Backtests

**Files:**
- Modify: `app/api/research.py`
- Modify: `app/agents/state.py`
- Modify: `app/agents/graph_nodes.py`
- Modify: `app/data/provider_factory.py`
- Modify: `app/reports/markdown_report.py`
- Modify: `app/storage/artifacts.py`
- Create: `tests/test_versioned_market_data_research.py`

- [ ] **Step 1: Write failing API and graph tests**

Test that a production-market-data request rejects a missing `data_version`, resolves only a published version, stores the selected version in run configuration and artifacts, and reproduces the same market-data hash when rerun with the same version.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `.venv/bin/pytest tests/test_versioned_market_data_research.py -q`

Expected: FAIL because research runs do not accept or record `data_version`.

- [ ] **Step 3: Add version-pinned provider selection**

Introduce `data_version: str | None` into the research request and state. Fixture mode remains allowed for deterministic unit tests; all warehouse-backed data requires a published version. Include the manifest hash and source summary in `market_data_diagnostics`, report assumptions, run configuration, and research bundle.

- [ ] **Step 4: Keep raw and research-price layers separate**

Do not silently replace raw fields with adjusted prices. Any future corporate-action transform must expose its transform id and parent raw `data_version`; this task only passes raw daily bars into the existing research pipeline and reports the limitation.

- [ ] **Step 5: Run focused tests and commit**

Run: `.venv/bin/pytest tests/test_versioned_market_data_research.py tests/test_research_api.py -q`

Expected: PASS.

Commit: `feat: pin research runs to market data versions`

### Task 8: Baseline Full-Universe Publication and Acceptance Audit

**Files:**
- Create: `docs/market-data-baseline-runbook.md`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Run a small two-symbol rehearsal version**

Run the backfill for two symbols and one calendar year. Verify manifest immutability, data lineage, quality-report persistence, resume behavior, and version-pinned research before collecting the full universe.

- [ ] **Step 2: Run the 8-10 year full-universe backfill**

Start a dated draft version with the approved source. Resume until all intended symbols complete. Retain failed-symbol records and do not substitute fixture data in this command.

- [ ] **Step 3: Review the publication audit**

Require: all hard quality checks pass, a manifest hash exists, raw bars show `adjustment="none"`, every table exposes source/ingested_at/data_version, and the versioned symbol/date coverage is documented.

- [ ] **Step 4: Publish the baseline and run a fixed-version research replay**

Publish only after the audit. Execute one research run against the new version, retain its report and bundle, then rerun with the identical `data_version` and confirm matching market-data manifest hash.

- [ ] **Step 5: Run the full regression suite and commit**

Run: `.venv/bin/pytest -q`

Expected: PASS.

Commit: `docs: publish raw A-share data warehouse runbook`

## Cost and Time Controls

- Use a local data lake and batch updates; do not introduce a cloud database before disk capacity or collaboration requires it.
- Begin all development against synthetic fixtures and a two-symbol rehearsal. Do not spend provider request quota on untested ingestion code.
- The historical backfill is resumable, so network interruptions do not waste completed work.
- Keep the source adapter boundary from day one; professional data access changes the adapter and licensing configuration, not the warehouse contract.
- Do not start point-in-time financial statements, industry-history reconstruction, alternative data, or intraday data until Task 8 establishes a trusted raw daily baseline.
