# Recovery Prompts

## Resume Prompt

Use this when context is lost:

```text
Continue building A-Share Factor Research Agent in automatic execution mode.
Read AGENTS.md and .codex-harness/STATE.md first.
Continue from the first incomplete task.
Use fixture data and deterministic fallbacks instead of blocking on external APIs.
Update STATE.md after each meaningful task.
```

## Stage 1 Prompt

```text
Implement Stage 1 from docs/superpowers/plans/2026-06-04-a-share-factor-research-agent.md.
Use the current workspace root, not the old A-Share Factor Research Agent path.
After each task, run the listed test and update .codex-harness/STATE.md.
```

## Stage 2 Prompt

```text
Implement Stage 2 from docs/superpowers/plans/2026-06-04-a-share-factor-research-agent-stage-2.md.
Keep live LLM and live data optional.
Prioritize passing deterministic tests, event trace, API smoke tests, and eval runner.
```

## Finalization Prompt

```text
Finalize the repository for GitHub submission.
Run pytest -v, python evals/run_eval.py, and python -m compileall app.
Update README.md and REPORT.md.
Commit stable changes.
Push to https://github.com/lpy235/A-Share-Factor-Research-Agent.git if auth allows.
```

