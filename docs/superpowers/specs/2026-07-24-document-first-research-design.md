# Document-First Research Design

## Goal

Allow a user to upload a research report and run factor research directly without entering a research topic.

## Scope

The dashboard's topic field starts empty. The sample-research action continues to fill its predefined topic. When a report is selected, the dashboard selects upload-only source mode and sends `research_topic: null` unless the user entered their own topic.

The existing API behavior remains the source of truth: an upload-only request with a document and no topic derives the run title from the document filename and extracts hypotheses from document chunks. Topic-only automatic research still requires a topic.

## Boundaries

This change does not generate a separate LLM summary title, alter RAG ranking, or erase user-entered topic text. A topic supplied by the user remains an optional retrieval and extraction hint for uploaded reports.

## Tests

Frontend markup tests will assert that the topic textarea has no prefilled content and keeps its upload-oriented placeholder. Existing API coverage continues to verify that upload-only research succeeds without a topic and that empty automatic research is rejected.

## Acceptance Criteria

1. Opening the dashboard does not insert a default research topic into an upload request.
2. Selecting a report uses upload-only mode.
3. An uploaded report can complete a run with no topic, named from its filename.
4. The sample action still supplies its explicit sample topic.
