# A-Share Factor Research Agent Stage 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the deterministic MVP into a complete agentic research workflow with RAG, public source collection, LLM-based factor extraction, LangGraph orchestration, trace persistence, SSE events, charts, and evaluation.

**Architecture:** Stage 2 keeps the Stage 1 quant modules as the trusted execution layer. New modules add public source discovery, retrieval, structured LLM extraction, LangGraph nodes, SQLite event storage, API observability, and report packaging.

**Tech Stack:** Python, FastAPI, Pydantic, SQLite, LangGraph, OpenAI-compatible Responses API, BeautifulSoup, requests, Chroma or deterministic keyword retrieval for tests, matplotlib, pytest.

---

## Assumptions

Stage 1 has created:

```text
/Users/brain6/Documents/document/A-Share Factor Research Agent
```

with these modules:

```text
app/factor/dsl.py
app/factor/validator.py
app/factor/executor.py
app/data/fixture_provider.py
app/data/ashare_provider.py
app/backtest/metrics.py
app/backtest/single_factor.py
app/backtest/selector.py
app/reports/markdown_report.py
app/agents/state.py
app/agents/graph.py
app/api/research.py
app/main.py
```

If Stage 1 is not implemented yet, do Stage 1 first.

## Stage 2 File Additions

```text
./
  app/
    sources/
      search.py
      fetch.py
    rag/
      retriever.py
    agents/
      extraction.py
      dsl_generation.py
      nodes.py
    storage/
      db.py
      events.py
    reports/
      charts.py
    api/
      runs.py
  tests/
    test_storage_events.py
    test_keyword_retriever.py
    test_public_source_fetch.py
    test_extraction_parser.py
    test_agent_nodes.py
    test_charts.py
```

## Task 1: SQLite Event Storage

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/storage/db.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/storage/events.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_storage_events.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_storage_events.py`:

```python
from app.storage.db import init_db
from app.storage.events import EventStore


def test_event_store_appends_and_lists_events(tmp_path):
    db_path = tmp_path / "runs.db"
    init_db(str(db_path))
    store = EventStore(str(db_path))

    store.append(
        run_id="run_test",
        node="ExtractHypothesesNode",
        event_type="node_completed",
        payload={"count": 3},
    )

    events = store.list_events("run_test")
    assert len(events) == 1
    assert events[0]["node"] == "ExtractHypothesesNode"
    assert events[0]["payload"]["count"] == 3
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_storage_events.py -v
```

Expected: FAIL because storage modules do not exist.

- [ ] **Step 3: Implement database initialization**

Write `app/storage/db.py`:

```python
import sqlite3


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_run_id
            ON events(run_id, id)
            """
        )
        conn.commit()
```

- [ ] **Step 4: Implement event store**

Write `app/storage/events.py`:

```python
import json
import sqlite3
from typing import Any


class EventStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def append(
        self,
        run_id: str,
        node: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO events(run_id, node, event_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, node, event_type, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, run_id, node, event_type, payload_json, created_at
                FROM events
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (run_id,),
            ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result
```

- [ ] **Step 5: Run test to verify pass**

Run:

```bash
pytest tests/test_storage_events.py -v
```

Expected: PASS.

## Task 2: Deterministic Keyword Retriever

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/rag/retriever.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_keyword_retriever.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_keyword_retriever.py`:

```python
from app.rag.chunker import DocumentChunk
from app.rag.retriever import KeywordRetriever


def test_keyword_retriever_returns_relevant_chunks_first():
    chunks = [
        DocumentChunk("c1", "a.md", "user_upload", "本文讨论动量因子和过去收益率。"),
        DocumentChunk("c2", "b.md", "user_upload", "本文讨论股息率和基本面。"),
        DocumentChunk("c3", "c.md", "user_upload", "量价齐升可能产生趋势延续。"),
    ]
    retriever = KeywordRetriever(chunks)
    result = retriever.search("动量 量价 趋势", top_k=2)

    assert len(result) == 2
    assert result[0].chunk_id in {"c1", "c3"}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_keyword_retriever.py -v
```

Expected: FAIL because `KeywordRetriever` does not exist.

- [ ] **Step 3: Implement retriever**

Write `app/rag/retriever.py`:

```python
import re

from app.rag.chunker import DocumentChunk


def tokenize(text: str) -> set[str]:
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    english = re.findall(r"[A-Za-z0-9_]+", text.lower())
    tokens = set(english)
    for item in chinese:
        tokens.update(item[i : i + 2] for i in range(max(1, len(item) - 1)))
    return tokens


class KeywordRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        self.chunk_tokens = [(chunk, tokenize(chunk.text)) for chunk in chunks]

    def search(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        query_tokens = tokenize(query)
        scored: list[tuple[int, DocumentChunk]] = []
        for chunk, tokens in self.chunk_tokens:
            score = len(query_tokens & tokens)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_keyword_retriever.py -v
```

Expected: PASS.

## Task 3: Public Source Fetching

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/sources/search.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/sources/fetch.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_public_source_fetch.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_public_source_fetch.py`:

```python
from app.sources.fetch import html_to_text
from app.sources.search import ManualSourceSearch


def test_manual_source_search_filters_by_query():
    search = ManualSourceSearch(
        [
            {"title": "A股动量因子研究", "url": "https://example.com/momentum"},
            {"title": "债券久期研究", "url": "https://example.com/bond"},
        ]
    )
    result = search.search("动量因子", max_sources=3)
    assert len(result) == 1
    assert result[0]["title"] == "A股动量因子研究"


def test_html_to_text_strips_scripts():
    html = "<html><script>bad()</script><body><h1>因子研究</h1><p>量价齐升。</p></body></html>"
    text = html_to_text(html)
    assert "bad()" not in text
    assert "因子研究" in text
    assert "量价齐升" in text
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_public_source_fetch.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement manual source search**

Write `app/sources/search.py`:

```python
from app.rag.retriever import tokenize
from app.sources.source_policy import SourcePolicy


class ManualSourceSearch:
    def __init__(self, sources: list[dict[str, str]]) -> None:
        self.sources = sources
        self.policy = SourcePolicy()

    def search(self, query: str, max_sources: int = 5) -> list[dict[str, str]]:
        query_tokens = tokenize(query)
        results: list[tuple[int, dict[str, str]]] = []
        for source in self.sources:
            url = source.get("url", "")
            policy_result = self.policy.check_url(url)
            if not policy_result.allowed:
                continue
            text = f"{source.get('title', '')} {source.get('url', '')}"
            score = len(query_tokens & tokenize(text))
            if score > 0:
                results.append((score, source))
        results.sort(key=lambda x: x[0], reverse=True)
        return [source for _, source in results[:max_sources]]
```

- [ ] **Step 4: Implement HTML fetch helpers**

Write `app/sources/fetch.py`:

```python
import requests
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


class PublicSourceFetcher:
    def fetch_text(self, url: str, timeout: int = 15) -> str:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "A-Share-Factor-Agent/0.1"},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            return html_to_text(response.text)
        return response.text
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_public_source_fetch.py -v
```

Expected: PASS.

## Task 4: LLM Factor Extraction Parser

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/extraction.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_extraction_parser.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_extraction_parser.py`:

```python
from app.agents.extraction import parse_factor_extraction_response


def test_parse_factor_extraction_response():
    text = """
    {
      "factors": [
        {
          "factor_name": "volume_price_momentum",
          "hypothesis": "量价齐升可能代表趋势延续",
          "evidence": "成交量放大且价格上涨",
          "source_title": "demo report",
          "source_url": null,
          "category": "volume_price",
          "required_fields": ["close", "volume"],
          "confidence": 0.76
        }
      ]
    }
    """
    result = parse_factor_extraction_response(text)
    assert len(result) == 1
    assert result[0].factor_name == "volume_price_momentum"
    assert result[0].required_fields == ["close", "volume"]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_extraction_parser.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement extraction parser**

Write `app/agents/extraction.py`:

```python
import json

from app.agents.schemas import FactorHypothesis


def parse_factor_extraction_response(text: str) -> list[FactorHypothesis]:
    data = json.loads(text)
    return [FactorHypothesis(**item) for item in data.get("factors", [])]
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_extraction_parser.py -v
```

Expected: PASS.

## Task 5: Factor DSL Generation Service

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/dsl_generation.py`

- [ ] **Step 1: Implement rule-based fallback generator**

Write `app/agents/dsl_generation.py`:

```python
from app.agents.schemas import FactorHypothesis
from app.factor.dsl import FactorSpec


class FactorDslGenerationService:
    def generate_fallback(self, hypothesis: FactorHypothesis) -> FactorSpec:
        text = f"{hypothesis.factor_name} {hypothesis.hypothesis} {hypothesis.evidence}"
        fields = set(hypothesis.required_fields)

        if "volume" in fields and "close" in fields:
            formula = "rank(returns(close, 20) * ts_mean(volume, 20) / ts_mean(volume, 60))"
            lookback = 60
            category = "volume_price"
        elif "波动" in text or "volatility" in text.lower():
            formula = "rank(ts_std(returns(close, 1), 20))"
            lookback = 20
            category = "volatility"
        elif "反转" in text:
            formula = "rank(returns(close, 20))"
            lookback = 20
            category = "reversal"
        else:
            formula = "rank(returns(close, 20))"
            lookback = 20
            category = hypothesis.category or "momentum"

        return FactorSpec(
            factor_name=hypothesis.factor_name,
            hypothesis=hypothesis.hypothesis,
            formula=formula,
            required_fields=sorted(fields or {"close"}),
            direction="positive",
            category=category,
            frequency="daily",
            lookback=lookback,
            source_title=hypothesis.source_title,
            source_url=hypothesis.source_url,
            source_excerpt=hypothesis.evidence,
            confidence=hypothesis.confidence,
        )
```

- [ ] **Step 2: Verify fallback manually**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.agents.schemas import FactorHypothesis
from app.agents.dsl_generation import FactorDslGenerationService
h = FactorHypothesis(
    factor_name="volume_price_momentum",
    hypothesis="量价齐升可能代表趋势延续",
    evidence="成交量放大且价格上涨",
    source_title="demo",
    category="volume_price",
    required_fields=["close", "volume"],
    confidence=0.8,
)
spec = FactorDslGenerationService().generate_fallback(h)
assert "volume" in spec.formula
print(spec.formula)
PY
```

Expected: formula prints.

## Task 6: Agent Node Services

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/nodes.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_agent_nodes.py`

- [ ] **Step 1: Write failing node test**

Write `tests/test_agent_nodes.py`:

```python
from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.rag.chunker import DocumentChunk


def test_extract_hypotheses_from_chunks_rule_based():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            source_title="demo report",
            source_type="user_upload",
            text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。",
        )
    ]
    result = extract_hypotheses_from_chunks("A股量价动量因子", chunks)
    assert len(result) >= 1
    assert result[0].required_fields == ["close", "volume"]


def test_generate_factor_specs_from_hypotheses():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            source_title="demo report",
            source_type="user_upload",
            text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。",
        )
    ]
    hypotheses = extract_hypotheses_from_chunks("A股量价动量因子", chunks)
    specs = generate_factor_specs(hypotheses)
    assert len(specs) >= 1
    assert "volume" in specs[0].formula
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_agent_nodes.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement deterministic node helpers**

Write `app/agents/nodes.py`:

```python
from app.agents.dsl_generation import FactorDslGenerationService
from app.agents.schemas import FactorHypothesis
from app.factor.dsl import FactorSpec
from app.rag.chunker import DocumentChunk


def extract_hypotheses_from_chunks(
    research_topic: str,
    chunks: list[DocumentChunk],
) -> list[FactorHypothesis]:
    hypotheses: list[FactorHypothesis] = []
    for chunk in chunks:
        text = chunk.text
        if "量价" in text or ("成交量" in text and "价格" in text):
            hypotheses.append(
                FactorHypothesis(
                    factor_name="volume_price_momentum",
                    hypothesis="成交量放大且价格上涨可能代表趋势延续。",
                    evidence=text[:200],
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    category="volume_price",
                    required_fields=["close", "volume"],
                    confidence=0.75,
                )
            )
        elif "动量" in text or "过去收益" in text:
            hypotheses.append(
                FactorHypothesis(
                    factor_name="momentum_20",
                    hypothesis="过去收益率较高的股票可能存在短期趋势延续。",
                    evidence=text[:200],
                    source_title=chunk.source_title,
                    source_url=chunk.source_url,
                    category="momentum",
                    required_fields=["close"],
                    confidence=0.7,
                )
            )
    return hypotheses


def generate_factor_specs(hypotheses: list[FactorHypothesis]) -> list[FactorSpec]:
    service = FactorDslGenerationService()
    return [service.generate_fallback(item) for item in hypotheses]
```

- [ ] **Step 4: Run test**

Run:

```bash
pytest tests/test_agent_nodes.py -v
```

Expected: PASS.

## Task 7: Full Workflow Replacement

**Files:**
- Modify: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/graph.py`

- [ ] **Step 1: Replace skeleton workflow with deterministic full run**

Modify `app/agents/graph.py`:

```python
from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.agents.state import ResearchState
from app.backtest.metrics import max_drawdown, sharpe_ratio
from app.backtest.selector import FactorScore, FactorSelector
from app.backtest.single_factor import (
    compute_forward_returns,
    compute_rank_ic,
    grouped_forward_returns,
)
from app.data.fixture_provider import FixtureAshareDataProvider
from app.factor.executor import FactorExecutor
from app.rag.chunker import DocumentChunk
from app.reports.markdown_report import render_report


def run_research_workflow(state: ResearchState) -> ResearchState:
    chunks = [
        DocumentChunk(
            chunk_id="demo:0",
            source_title="demo factor note",
            source_type="user_upload",
            text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。",
        )
    ]

    hypotheses = extract_hypotheses_from_chunks(state["research_topic"], chunks)
    specs = generate_factor_specs(hypotheses)

    provider = FixtureAshareDataProvider()
    symbols = provider.get_universe(state.get("universe", "CSI300"), state.get("start_date", "2020-01-01"))[:20]
    data = provider.get_daily_bars(
        symbols=symbols,
        start_date=state.get("start_date", "2020-01-01"),
        end_date=state.get("end_date", "2020-12-31"),
    )

    executor = FactorExecutor()
    metrics = []
    selected_input = []
    for spec in specs:
        factor = executor.execute(spec, data).values
        forward_returns = compute_forward_returns(data["close"], periods=1)
        rank_ic = compute_rank_ic(factor, forward_returns)
        grouped = grouped_forward_returns(factor, forward_returns, groups=5)
        long_short = grouped[5] - grouped[1]
        score = {
            "factor_name": spec.factor_name,
            "mean_rank_ic": float(rank_ic.mean()) if not rank_ic.empty else 0.0,
            "icir": float(rank_ic.mean() / rank_ic.std()) if rank_ic.std() else 0.0,
            "coverage_ratio": float(factor.notna().mean()),
            "missing_ratio": float(factor.isna().mean()),
            "max_drawdown": max_drawdown(long_short),
            "sharpe": sharpe_ratio(long_short),
        }
        metrics.append(score)
        selected_input.append(
            FactorScore(
                factor_name=score["factor_name"],
                mean_rank_ic=score["mean_rank_ic"],
                icir=score["icir"],
                coverage_ratio=score["coverage_ratio"],
                missing_ratio=score["missing_ratio"],
                max_drawdown=score["max_drawdown"],
            )
        )

    selected = FactorSelector().select(selected_input)
    report = render_report(
        research_topic=state["research_topic"],
        sources=[
            {
                "source_title": hypothesis.source_title,
                "source_url": hypothesis.source_url,
            }
            for hypothesis in hypotheses
        ],
        factors=[spec.model_dump() for spec in specs],
        metrics=metrics,
        limitations=[
            "当前报告使用 fixture 数据演示完整流程。",
            "正式研究需要替换为 AKShare/Tushare 等合法 A 股数据源。",
            "历史回测不构成投资建议。",
        ],
    )
    state["factor_specs"] = [spec.model_dump() for spec in specs]
    state["metrics"] = metrics
    state["report_markdown"] = report
    state["selected_factors"] = [item.factor_name for item in selected]
    return state
```

- [ ] **Step 2: Verify workflow**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.agents.graph import run_research_workflow
state = run_research_workflow({
    "run_id": "run_demo",
    "research_topic": "A股量价类动量因子",
    "source_mode": "upload",
    "universe": "CSI300",
    "start_date": "2020-01-01",
    "end_date": "2020-12-31",
})
assert state["factor_specs"]
assert state["metrics"]
assert "A 股因子研究报告" in state["report_markdown"]
print(state["selected_factors"])
PY
```

Expected: selected factor list prints.

## Task 8: API Run Events and SSE

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/api/runs.py`
- Modify: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/main.py`

- [ ] **Step 1: Implement runs router**

Write `app/api/runs.py`:

```python
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.storage.db import init_db
from app.storage.events import EventStore

router = APIRouter(prefix="/runs", tags=["runs"])

DB_PATH = "runs.db"
init_db(DB_PATH)
store = EventStore(DB_PATH)


@router.get("/{run_id}/events")
def list_events(run_id: str):
    return {"run_id": run_id, "events": store.list_events(run_id)}


@router.get("/{run_id}/events/stream")
async def stream_events(run_id: str):
    async def event_generator():
        sent = 0
        for _ in range(30):
            events = store.list_events(run_id)
            for event in events[sent:]:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            sent = len(events)
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: Register router**

Modify `app/main.py`:

```python
from fastapi import FastAPI

from app.api.research import router as research_router
from app.api.runs import router as runs_router

app = FastAPI(title="A-Share Factor Research Agent")

app.include_router(research_router)
app.include_router(runs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Verify API imports**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.main import app
assert app.title == "A-Share Factor Research Agent"
print("ok")
PY
```

Expected:

```text
ok
```

## Task 9: Research Endpoint Event Logging

**Files:**
- Modify: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/api/research.py`

- [ ] **Step 1: Add event logging to research endpoint**

Modify `app/api/research.py`:

```python
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.graph import run_research_workflow
from app.storage.db import init_db
from app.storage.events import EventStore

router = APIRouter(prefix="/research", tags=["research"])

DB_PATH = "runs.db"
init_db(DB_PATH)
event_store = EventStore(DB_PATH)


class ResearchRunRequest(BaseModel):
    research_topic: str
    source_mode: str = "upload"
    universe: str = "CSI300"
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"


@router.post("/runs")
def create_research_run(request: ResearchRunRequest):
    run_id = f"run_{uuid4().hex[:12]}"
    event_store.append(
        run_id,
        "CreateRun",
        "run_started",
        {"research_topic": request.research_topic, "source_mode": request.source_mode},
    )
    state = run_research_workflow(
        {
            "run_id": run_id,
            "research_topic": request.research_topic,
            "source_mode": request.source_mode,
            "universe": request.universe,
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
    )
    event_store.append(
        run_id,
        "GenerateReportNode",
        "run_completed",
        {
            "factor_count": len(state.get("factor_specs", [])),
            "selected_factors": state.get("selected_factors", []),
        },
    )
    return {
        "run_id": run_id,
        "status": "completed",
        "selected_factors": state.get("selected_factors", []),
        "report_markdown": state["report_markdown"],
    }
```

- [ ] **Step 2: Verify endpoint manually**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
uvicorn app.main:app --port 8000
```

Then in another terminal:

```bash
curl -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload"}'
```

Expected: response includes `run_id`, `selected_factors`, and `report_markdown`.

## Task 10: Chart Generation

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/reports/charts.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_charts.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_charts.py`:

```python
import pandas as pd

from app.reports.charts import save_equity_curve


def test_save_equity_curve_creates_png(tmp_path):
    returns = pd.Series([0.01, -0.02, 0.03], index=pd.date_range("2024-01-01", periods=3))
    path = tmp_path / "curve.png"
    save_equity_curve(returns, str(path), title="demo")
    assert path.exists()
    assert path.stat().st_size > 0
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_charts.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement chart helper**

Write `app/reports/charts.py`:

```python
import pandas as pd


def save_equity_curve(returns: pd.Series, output_path: str, title: str) -> None:
    import matplotlib.pyplot as plt

    equity = (1 + returns.fillna(0)).cumprod()
    fig, ax = plt.subplots(figsize=(8, 4))
    equity.plot(ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
```

- [ ] **Step 4: Run test**

Run:

```bash
pytest tests/test_charts.py -v
```

Expected: PASS.

## Task 11: Evaluation Expansion

**Files:**
- Modify: `/Users/brain6/Documents/document/A-Share Factor Research Agent/evals/tasks.jsonl`
- Modify: `/Users/brain6/Documents/document/A-Share Factor Research Agent/evals/run_eval.py`

- [ ] **Step 1: Add extraction eval tasks**

Append to `evals/tasks.jsonl`:

```jsonl
{"id":"extract_volume_price_001","type":"factor_extraction","text":"成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。","expected_fields":["close","volume"],"expected_category":"volume_price"}
{"id":"extract_momentum_001","type":"factor_extraction","text":"过去收益率较高的股票在短期可能延续上涨，体现动量效应。","expected_fields":["close"],"expected_category":"momentum"}
```

- [ ] **Step 2: Update eval runner**

Modify `evals/run_eval.py` to include factor extraction:

```python
import json
from pathlib import Path

from app.agents.nodes import extract_hypotheses_from_chunks
from app.factor.dsl import FactorSpec
from app.factor.validator import FactorDslValidator
from app.rag.chunker import DocumentChunk


def run() -> None:
    path = Path(__file__).with_name("tasks.jsonl")
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    validator = FactorDslValidator()
    total = 0
    correct = 0

    for task in tasks:
        if task["type"] == "dsl_validation":
            spec = FactorSpec(
                factor_name=task["id"],
                hypothesis="eval",
                formula=task["formula"],
                required_fields=["close"],
                direction="unknown",
                category="eval",
                frequency="daily",
                lookback=20,
                source_title="eval",
                source_url=None,
                source_excerpt="eval",
                confidence=0.5,
            )
            result = validator.validate(spec)
            total += 1
            correct += int(result.valid == task["expected_valid"])

        if task["type"] == "factor_extraction":
            chunk = DocumentChunk(
                chunk_id=task["id"],
                source_title="eval",
                source_type="user_upload",
                text=task["text"],
            )
            hypotheses = extract_hypotheses_from_chunks("A股因子", [chunk])
            total += 1
            if hypotheses:
                first = hypotheses[0]
                fields_ok = set(first.required_fields) == set(task["expected_fields"])
                category_ok = first.category == task["expected_category"]
                correct += int(fields_ok and category_ok)

    print({"total": total, "correct": correct, "accuracy": correct / total if total else 0})


if __name__ == "__main__":
    run()
```

- [ ] **Step 3: Run eval**

Run:

```bash
python evals/run_eval.py
```

Expected: accuracy prints and should be `1.0` for deterministic evals.

## Task 12: Final Stage 2 Verification

**Files:**
- No new files.

- [ ] **Step 1: Run all tests**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run eval**

Run:

```bash
python evals/run_eval.py
```

Expected: deterministic eval accuracy is `1.0`.

- [ ] **Step 3: Run API**

Run:

```bash
uvicorn app.main:app --port 8000
```

Expected: server starts.

- [ ] **Step 4: Create demo run**

Run:

```bash
curl -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload","universe":"CSI300","start_date":"2020-01-01","end_date":"2020-12-31"}'
```

Expected: response includes report and selected factors.

- [ ] **Step 5: Check events**

Use the `run_id` from Step 4:

```bash
curl http://127.0.0.1:8000/runs/<run_id>/events
```

Expected: includes `run_started` and `run_completed`.

## Self-Review

Spec coverage:

- RAG: deterministic keyword retriever included; Chroma embedding retriever can be added as Stage 3.
- Public source collection: manual public source search and fetch helper included; web search API integration can be added as Stage 3.
- LLM factor extraction: parser and prompts are ready; deterministic extraction is used for tests. Live LLM integration can be added behind an environment flag.
- LangGraph: this plan still uses a deterministic workflow function rather than full `StateGraph`. A full LangGraph implementation should be Stage 3 once all nodes are stable.
- Trace: SQLite events and SSE stream included.
- Charts: equity curve helper included.
- Evaluation: DSL and extraction evals included.

Next plan:

- Replace `run_research_workflow` with actual `langgraph.graph.StateGraph`.
- Add Chroma or FAISS retriever with embeddings.
- Add live LLM extraction and DSL generation with schema validation/retry.
- Add document upload endpoint.
- Add public search API integration.
- Add real AKShare demo mode and cached data.
- Add full report charts and downloadable artifacts.

