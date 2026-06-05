# A-Share Factor Research Agent V3 LangGraph Design

## 1. Goal

V3 upgrades the V2 document-driven workflow into a real LangGraph agent workflow with node-level state transitions and trace events.

The user-facing API behavior stays compatible with V2:

- `POST /documents` uploads user materials.
- `GET /documents/{document_id}` returns uploaded document metadata.
- `POST /research/runs` starts a factor research run.
- `GET /runs/{run_id}/events` returns the trace.
- `GET /runs/{run_id}/events/stream` streams the trace.

The internal workflow changes from one large function into a compiled `StateGraph`. Each meaningful research step becomes a node that can be tested, traced, and explained in an technical review.

## 2. Why V3

V2 proves that the pipeline can parse uploaded material, extract a factor idea, execute a restricted factor DSL, backtest it, select a factor, and generate a report.

V3 should make the project look and behave like an agent system:

- The graph shows how the agent reasons through a research task.
- The run trace shows each node's input/output summary.
- Failures are localized to a node instead of hidden inside a monolithic function.
- The implementation is easier to extend later with live public source search, LLM extraction, or human review gates.

## 3. Scope

### In Scope

V3 includes:

- Replace the body of `run_research_workflow()` with a LangGraph `StateGraph`.
- Keep `run_research_workflow(state)` as the public Python entry point for tests and API compatibility.
- Add node modules for the research pipeline.
- Add an event callback/helper that records node start, completion, fallback, and failure events.
- Enrich `ResearchState` with intermediate fields so node outputs are explicit.
- Add tests for graph construction, node ordering, event trace, fallback behavior, and API compatibility.
- Update README/report docs to describe V3 graph execution.

### Out of Scope

V3 does not add:

- Live web search.
- Real LLM calls as the default path.
- Vector database retrieval.
- Live AKShare/Tushare market data as the default path.
- Multi-factor portfolio optimization.
- Auto-trading or stock recommendation.

These are better saved for V4 because V3's main value is agent architecture and observability.

## 4. Architecture

V3 architecture:

```text
FastAPI
-> app.agents.graph.run_research_workflow()
-> compiled LangGraph StateGraph
-> node-level deterministic services
-> Factor DSL validation/execution
-> fixture A-share data provider
-> backtest metrics/selector
-> Markdown report
-> SQLite event trace
```

The graph is deterministic by default. This keeps the demo reliable without network access or API keys. Later versions can replace individual nodes with LLM or live-data implementations without changing the whole pipeline.

## 5. State Schema

`app/agents/state.py` should keep `ResearchState` as the shared graph state.

Required input fields:

```python
run_id: str
research_topic: str
source_mode: Literal["auto", "upload", "hybrid"]
universe: str
start_date: str
end_date: str
```

Optional input fields:

```python
document_paths: list[str]
max_chunks: int
```

Intermediate/output fields:

```python
sources: list[dict]
chunks: list[dict]
hypotheses: list[dict]
factor_specs: list[dict]
validation_results: list[dict]
market_data_summary: dict
metrics: list[dict]
selected_factors: list[str]
report_markdown: str
warnings: list[str]
errors: list[dict]
trace: list[dict]
```

State rules:

- Nodes only write their own outputs and append warnings/errors when needed.
- Nodes should not mutate hidden global workflow state.
- DataFrame-heavy objects can stay internal inside the node where possible. If a later node needs them, store them under private state keys such as `_market_data` or `_factor_values`; API responses must not expose those private fields.
- Public API responses should continue returning selected factors, factor specs, and report markdown.

## 6. Graph Nodes

### 6.1 `LoadDocumentsNode`

Purpose:

- Convert `document_paths` into parsed source documents.
- Use the deterministic demo document when no uploaded documents are provided.

Inputs:

- `research_topic`
- `source_mode`
- `document_paths`

Outputs:

- `sources`
- `warnings`

Fallback:

- If no documents are provided, create the existing demo source about A-share volume-price momentum.
- If a document cannot be parsed, record a warning and continue with parseable documents.
- If all documents fail, use the demo source.

### 6.2 `RetrieveChunksNode`

Purpose:

- Chunk parsed sources and retrieve chunks relevant to the research topic.

Inputs:

- `sources`
- `research_topic`
- `max_chunks`

Outputs:

- `chunks`

Fallback:

- If keyword retrieval returns no result, use the first `max_chunks` chunks.
- If no chunks exist, create a fallback chunk with the existing volume-price momentum note.

### 6.3 `ExtractHypothesesNode`

Purpose:

- Extract factor hypotheses from retrieved chunks.

Inputs:

- `research_topic`
- `chunks`

Outputs:

- `hypotheses`

Fallback:

- If no hypothesis is extracted, add the existing deterministic fallback hypothesis.

### 6.4 `GenerateFactorDSLNode`

Purpose:

- Convert factor hypotheses into restricted Factor DSL specs.

Inputs:

- `hypotheses`

Outputs:

- `factor_specs`

Fallback:

- Use the existing deterministic DSL generation service.

### 6.5 `ValidateDSLNode`

Purpose:

- Validate each Factor DSL spec before execution.

Inputs:

- `factor_specs`

Outputs:

- `validation_results`
- filtered `factor_specs`
- `warnings`

Behavior:

- Invalid specs are excluded from execution.
- Validation failures are visible in trace events and report warnings.
- If all specs are invalid, create a fallback volume-price momentum spec and validate it.

### 6.6 `LoadMarketDataNode`

Purpose:

- Load A-share daily bar data for the configured universe and date range.

Inputs:

- `universe`
- `start_date`
- `end_date`

Outputs:

- private `_market_data`
- `market_data_summary`

Behavior:

- Continue using `FixtureAshareDataProvider` as the deterministic default.
- Limit demo universe size to the current first 20 symbols unless the existing provider changes.

### 6.7 `ExecuteFactorsNode`

Purpose:

- Execute validated factor specs on market data.

Inputs:

- `factor_specs`
- private `_market_data`

Outputs:

- private `_factor_values`
- `warnings`

Behavior:

- Record factor-level execution failures.
- Continue with successfully executed factors.

### 6.8 `RunBacktestNode`

Purpose:

- Compute RankIC, ICIR, grouped returns, long-short metrics, max drawdown, Sharpe, coverage, and missing ratio.

Inputs:

- private `_market_data`
- private `_factor_values`

Outputs:

- `metrics`

Behavior:

- Preserve V2 metric names so existing tests and demo output remain stable.

### 6.9 `SelectFactorsNode`

Purpose:

- Select factors using the existing `FactorSelector`.

Inputs:

- `metrics`

Outputs:

- `selected_factors`

Behavior:

- Keep V2 selector thresholds unless tests show a deterministic fixture regression.

### 6.10 `GenerateReportNode`

Purpose:

- Render the final Markdown report.

Inputs:

- `research_topic`
- `hypotheses`
- `factor_specs`
- `metrics`
- `selected_factors`
- `warnings`

Outputs:

- `report_markdown`

Behavior:

- Preserve V2 report content.
- Add a short "Agent Trace Summary" section only if it can be done without making the report noisy.

## 7. Graph Edges

The V3 graph is a linear graph for reliability:

```text
START
-> LoadDocumentsNode
-> RetrieveChunksNode
-> ExtractHypothesesNode
-> GenerateFactorDSLNode
-> ValidateDSLNode
-> LoadMarketDataNode
-> ExecuteFactorsNode
-> RunBacktestNode
-> SelectFactorsNode
-> GenerateReportNode
-> END
```

Conditional branches are intentionally deferred. A linear graph is easier to test and still demonstrates real agent state orchestration. Future versions can add branches such as "ask user for review before execution" or "search public sources when upload evidence is weak."

## 8. Event Trace

Every node records events to SQLite through `EventStore`.

Event types:

```text
node_started
node_completed
node_fallback
node_failed
run_started
run_completed
```

Minimum event payload fields:

```json
{
  "run_id": "run_xxx",
  "node": "ExtractHypothesesNode",
  "event_type": "node_completed",
  "payload": {
    "input_summary": {},
    "output_summary": {},
    "warnings": []
  }
}
```

Payload rules:

- Do not store full market data frames.
- Do not store full uploaded document text.
- Store counts, names, source titles, selected factor names, and compact error messages.
- Keep payloads deterministic for tests.

Expected trace for a normal uploaded run:

```text
CreateRun/run_started
LoadDocumentsNode/node_started
LoadDocumentsNode/node_completed
RetrieveChunksNode/node_started
RetrieveChunksNode/node_completed
ExtractHypothesesNode/node_started
ExtractHypothesesNode/node_completed
GenerateFactorDSLNode/node_started
GenerateFactorDSLNode/node_completed
ValidateDSLNode/node_started
ValidateDSLNode/node_completed
LoadMarketDataNode/node_started
LoadMarketDataNode/node_completed
ExecuteFactorsNode/node_started
ExecuteFactorsNode/node_completed
RunBacktestNode/node_started
RunBacktestNode/node_completed
SelectFactorsNode/node_started
SelectFactorsNode/node_completed
GenerateReportNode/node_started
GenerateReportNode/node_completed
GenerateReportNode/run_completed
```

## 9. Error Handling

V3 should prefer graceful degradation over hard failure for demo reliability.

Hard failures:

- Missing `research_topic`.
- Missing `run_id`.
- No executable factor after fallback validation.
- No market data returned by the fixture provider.

Soft failures:

- One uploaded document cannot be parsed.
- One factor DSL spec is invalid.
- One factor execution fails.
- Retrieval returns no chunks.
- Hypothesis extraction returns no factors.

Soft failures produce warnings and `node_fallback` events. Hard failures produce `node_failed` events and should raise an API-level error.

## 10. Compatibility

V3 must preserve:

- `run_research_workflow(state)` import path.
- `ResearchState` typed-dict style.
- `POST /research/runs` request shape from V2.
- `POST /research/runs` response keys:
  - `run_id`
  - `status`
  - `selected_factors`
  - `factor_specs`
  - `report_markdown`
- V2 tests for uploaded document content.
- Offline deterministic test behavior.

## 11. Testing Plan

Add or update tests:

```text
tests/test_agent_graph.py
tests/test_agent_graph_events.py
tests/test_workflow_documents.py
tests/test_research_api.py
```

Required assertions:

- `build_research_graph()` returns a compiled graph that can invoke a minimal state.
- A document-driven workflow still selects `volume_price_momentum`.
- The event store receives node-level events in graph order.
- Fallback events are recorded when no document is provided or extraction returns no hypothesis.
- API response remains compatible with V2.
- Full verification still passes:
  - `pytest -v`
  - `python evals/run_eval.py`
  - `python -m compileall app`

## 12. Implementation Notes

Recommended file layout:

```text
app/agents/graph.py
app/agents/graph_events.py
app/agents/graph_nodes.py
app/agents/state.py
tests/test_agent_graph.py
tests/test_agent_graph_events.py
```

`app/agents/graph.py` should be responsible for graph assembly and the public workflow entry point.

`app/agents/graph_nodes.py` should hold node functions. Node functions should stay small and call existing services from `app.rag`, `app.sources`, `app.factor`, `app.backtest`, and `app.reports`.

`app/agents/graph_events.py` should hold event tracing helpers so node code does not duplicate SQLite append logic.

## 13. Success Criteria

V3 is complete when:

- The research workflow runs through a LangGraph `StateGraph`.
- Each graph node records start and completion events.
- Fallback paths record fallback events.
- V2 API behavior still works.
- Tests pass locally.
- README/report clearly state that V3 is an agent graph with traceable nodes.
- The project remains deterministic without external API keys.

