# Automatic Execution Runbook

## Startup Sequence

At the beginning of every continued execution:

1. Confirm the current working directory:

```bash
pwd
```

Expected:

```text
/Users/brain6/Documents/document/A-Share Factor Research Agent
```

2. Read state:

```bash
sed -n '1,240p' .codex-harness/STATE.md
```

3. Check git state:

```bash
git status --short
git remote -v
```

4. Continue from the first incomplete task in `.codex-harness/STATE.md`.

## Execution Loop

For each task:

```text
1. Read the relevant plan section.
2. Make the smallest useful implementation change.
3. Run the task-specific check.
4. If it fails, inspect the error and repair.
5. Retry up to 3 focused repair attempts.
6. If still failing, apply the failure policy.
7. Update STATE.md.
8. Commit when a milestone is stable.
```

## Implementation Order

Primary order:

```text
Stage 0: Harness and repository setup
Stage 1: Deterministic core MVP
Stage 2: Workflow, RAG, trace, API events
Stage 3: Real LangGraph, live LLM extraction, real source search, real A-share demo
Stage 4: README, REPORT, documentation, final verification, push
```

## Commit Policy

Commit after stable milestones:

```text
docs: add execution harness
feat: scaffold factor research agent
feat: add factor dsl and validation
feat: add factor execution and backtest metrics
feat: add research workflow api
feat: add trace and evaluation harness
docs: add demo report and project summary
```

Do not commit broken code unless the commit is explicitly a work-in-progress checkpoint needed for recovery.

## External Dependency Policy

If external systems fail:

```text
LLM unavailable -> use deterministic factor extraction fallback
AKShare unavailable -> use FixtureAshareDataProvider
public source fetching unavailable -> use local fixture documents
embedding model unavailable -> use KeywordRetriever
GitHub push unavailable -> keep local commits and record blocker in STATE.md
```

## Stop Conditions

Do not stop for:

```text
ordinary implementation choices
minor test failures
missing live API keys
live data source outages
public search source failures
style cleanup
```

Only stop for:

```text
missing user credential required for GitHub push
destructive git conflict requiring user choice
legal/compliance uncertainty about a data source
repeated same blocker after 3 repair attempts
```
