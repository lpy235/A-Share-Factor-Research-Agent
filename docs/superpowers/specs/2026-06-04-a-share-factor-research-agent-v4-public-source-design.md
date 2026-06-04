# A-Share Factor Research Agent V4 Public Source Design

## Goal

V4 adds public-source discovery to the existing LangGraph workflow.

The agent should be able to start from a research topic, find allowed public materials, convert them into parsed source documents, and continue through the existing RAG, factor extraction, DSL validation, backtest, selection, and report nodes.

## Scope

In scope:

- Support `source_mode="auto"` for public-source-only runs.
- Support `source_mode="hybrid"` for uploaded documents plus public sources.
- Keep `source_mode="upload"` behavior unchanged.
- Add deterministic public source seeds so tests and demos work offline.
- Apply `SourcePolicy` before any public source is used.
- Add optional live fetch support behind an explicit request flag.
- Add source-discovery trace metadata.

Out of scope:

- Real search-engine API integration.
- Embedding-backed retrieval.
- LLM-based source summarization.
- Paywalled or login-required scraping.

## Data Flow

```text
LoadDocumentsNode
-> parse uploaded files when mode is upload/hybrid
-> discover public sources when mode is auto/hybrid
-> filter candidates with SourcePolicy
-> use embedded public source text by default
-> optionally fetch public URLs when allow_live_fetch=true
-> emit sources into existing RetrieveChunksNode
```

## API Additions

`POST /research/runs` gains:

```python
max_sources: int = 3
allow_live_fetch: bool = False
```

Defaults preserve deterministic execution.

## Public Source Discovery

Create `app/sources/discovery.py`.

Responsibilities:

- Hold deterministic public source seeds.
- Score candidates by topic tokens.
- Apply source policy.
- Return compact `DiscoveredSource` objects.
- Optionally fetch live text for candidates when explicitly enabled.

## Success Criteria

- `source_mode="auto"` produces a factor from public source material without uploads.
- `source_mode="hybrid"` combines uploaded documents and public sources.
- Disallowed URLs are filtered before use.
- Existing V3 tests still pass.
- New tests cover auto source discovery, hybrid source merging, and API compatibility.

