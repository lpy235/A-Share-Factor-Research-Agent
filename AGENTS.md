# Agent Execution Rules

This repository is the workspace for the A-Share Factor Research Agent project.

## Mission

Build and submit the project to:

```text
https://github.com/lpy235/A-Share-Factor-Research-Agent
```

The project must become a reproducible quant strategy / AI Agent research system.

## Execution Mode

Use automatic execution mode:

1. Keep implementing without stopping for ordinary decisions.
2. Prefer deterministic fallbacks over blocking on external services.
3. Update `.codex-harness/STATE.md` after every meaningful task.
4. Run the relevant checks after each task.
5. If a check fails, diagnose and attempt repairs before moving on.
6. Do not stop because LLM keys, live market data, or public source fetching are unavailable.
7. Use fixture data, deterministic extraction, and local test documents when external systems fail.
8. Commit at stable milestones.
9. Push to the target GitHub repository only after tests pass.

## Project Scope

The system is an A-share factor research agent:

```text
public/uploaded sources
-> factor hypothesis extraction
-> restricted Factor DSL
-> A-share daily data
-> factor validation
-> backtest
-> factor selection
-> traceable research report
```

The project is not an auto-trading system and must not provide trading advice, order execution, or return promises.

## Recovery

When context is lost, read these files first:

```text
.codex-harness/GOAL.md
.codex-harness/STATE.md
.codex-harness/RUNBOOK.md
.codex-harness/CHECKS.md
docs/superpowers/specs/2026-06-04-a-share-factor-research-agent-design.md
docs/superpowers/plans/2026-06-04-a-share-factor-research-agent.md
docs/superpowers/plans/2026-06-04-a-share-factor-research-agent-stage-2.md
```

Then continue from the next incomplete item in `.codex-harness/STATE.md`.

