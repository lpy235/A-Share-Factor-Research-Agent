# API Reference

## Health

```http
GET /health
```

Returns:

```json
{"status": "ok"}
```

## Upload Document

```http
POST /documents
```

Multipart form field:

```text
file: Markdown, txt, or PDF research material
```

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -F "file=@fixture_docs/demo_factor_note.md"
```

## Create Research Run

```http
POST /research/runs
```

Deterministic demo request:

```bash
curl -s -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "research_topic": "A股量价类动量因子",
    "source_mode": "auto",
    "retrieval_mode": "hybrid",
    "extraction_mode": "rule",
    "data_provider": "fixture",
    "cache_enabled": true
  }'
```

Important request fields:

```text
research_topic: required natural-language research question
source_mode: upload | auto | hybrid
document_ids: uploaded document ids for upload or hybrid mode
retrieval_mode: keyword | vector | hybrid
extraction_mode: rule | llm | hybrid
enable_llm_extraction: explicit LLM opt-in
data_provider: fixture | akshare
cache_enabled: enable local daily-bar CSV cache
fallback_to_fixture: use fixture data if live provider fails
allow_live_fetch: explicit public URL fetch opt-in
```

Response fields:

```text
run_id
status
selected_factors
factor_specs
report_markdown
```

## List Trace Events

```http
GET /runs/{run_id}/events
```

Returns node-level LangGraph events ordered by insertion id.

## Stream Trace Events

```http
GET /runs/{run_id}/events/stream
```

Returns server-sent event frames for simple live trace inspection.

## Dashboard

```http
GET /
```

Serves the browser research workbench. Static assets are served from:

```http
GET /static/styles.css
GET /static/app.js
```

