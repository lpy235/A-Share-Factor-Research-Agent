# State

## Current Phase

```text
Stage 2 realistic A-share backtesting complete
```

## Workspace

```text
/Users/brain6/Documents/document/A-Share Factor Research Agent
```

## Remote

```text
https://github.com/lpy235/A-Share-Factor-Research-Agent.git
```

## Completed

- [x] Project idea selected: A-share factor research agent.
- [x] Scope narrowed to quant strategy factor research.
- [x] Source policy selected: public sources and user-provided materials only.
- [x] Design document written.
- [x] Stage 1 implementation plan written.
- [x] Stage 2 implementation plan written.
- [x] Workspace moved to `/Users/brain6/Documents/document/A-Share Factor Research Agent`.
- [x] Automatic execution harness requested.
- [x] Automatic execution harness files created.
- [x] Git repository initialized.
- [x] GitHub remote connected.
- [x] Remote repository inspected.
- [x] Remote README/LICENSE incorporated locally.
- [x] Implementation plan paths reconciled with the new workspace path.
- [x] Stage 1 deterministic core modules implemented.
- [x] Stage 2 deterministic workflow/API/event/eval skeleton implemented.
- [x] Test suite added.
- [x] Local virtual environment created.
- [x] Minimal runtime/test dependencies installed.
- [x] `pytest -v` passed with 26 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed.
- [x] FastAPI smoke test passed.
- [x] Run events endpoint passed.
- [x] README and REPORT updated.
- [x] V2 implementation plan written.
- [x] Document upload API implemented.
- [x] Filesystem-backed document store implemented.
- [x] Research runs now accept `document_ids`.
- [x] Workflow now parses uploaded documents, chunks content, retrieves relevant chunks, and extracts factors from uploaded material.
- [x] V2 tests added and passed.
- [x] `pytest -v` passed with 30 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V2.
- [x] V2 upload-document smoke test passed.
- [x] V2 committed and pushed.
- [x] V3 direction selected: LangGraph agentization and complete node-level trace.
- [x] V3 LangGraph design spec written.
- [x] V3 implementation plan written.
- [x] LangGraph package installed in local virtual environment.
- [x] Research graph nodes and event tracer implemented.
- [x] V3 LangGraph workflow implemented.
- [x] V3 graph/event/API tests added.
- [x] `pytest -v` passed with 36 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V3.
- [x] V3 committed and pushed.
- [x] V4 public-source discovery design spec written.
- [x] V4 public-source implementation plan written.
- [x] Deterministic public-source discovery service implemented.
- [x] `auto` and `hybrid` source modes integrated into `LoadDocumentsNode`.
- [x] Research API accepts `max_sources` and `allow_live_fetch`.
- [x] V4 source discovery, workflow, and API tests added.
- [x] `pytest -v` passed with 42 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V4.
- [x] V4 committed and pushed.
- [x] V5 embedding RAG design spec written.
- [x] V5 embedding RAG implementation plan written.
- [x] Deterministic hashing embedder implemented.
- [x] Vector and hybrid retrievers implemented.
- [x] `retrieval_mode` and `embedding_dim` integrated into graph/API.
- [x] V5 embedding/vector workflow/API tests added.
- [x] `pytest -v` passed with 47 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V5.
- [x] V5 committed and pushed.
- [x] V6 structured LLM extraction design spec written.
- [x] V6 structured LLM extraction implementation plan written.
- [x] Structured factor extraction service implemented.
- [x] LLM JSON parsing, schema validation, repair, and fallback implemented.
- [x] `extraction_mode`, `enable_llm_extraction`, and `llm_retry_count` integrated into graph/API.
- [x] V6 extraction service, workflow, and API tests added.
- [x] `pytest -v` passed with 53 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V6.
- [x] V6 committed and pushed.
- [x] V7 real A-share data/cache design spec written.
- [x] V7 real A-share data/cache implementation plan written.
- [x] Daily bar CSV cache implemented.
- [x] Data provider factory and cached provider wrapper implemented.
- [x] `data_provider`, `cache_enabled`, `fallback_to_fixture`, and `market_data_cache_dir` integrated into graph/API.
- [x] Market data diagnostics integrated into LangGraph node summaries.
- [x] V7 cache/provider/workflow/API tests added.
- [x] `pytest -v` passed with 60 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V7.
- [x] `git diff --check` passed after V7.
- [x] V7 committed and pushed.
- [x] V8 dashboard design spec written.
- [x] V8 dashboard implementation plan written.
- [x] FastAPI dashboard route and static asset mount implemented.
- [x] Browser dashboard HTML/CSS/JS implemented.
- [x] Dashboard tests added.
- [x] README and REPORT updated for V8 dashboard usage.
- [x] `pytest -v` passed with 62 tests.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] `python -m compileall app` passed after V8.
- [x] `git diff --check` passed after V8.
- [x] Browser dashboard verification passed with deterministic run, 2 selected factors, and 22 trace events.
- [x] V8 committed and pushed.
- [x] Repository structure audited.
- [x] Repository organization docs drafted.
- [x] Makefile helper commands added.
- [x] README simplified into a project entry point.
- [x] Documentation index added.
- [x] `.gitignore` expanded for common local artifacts.
- [x] `pytest -v` passed with 62 tests after repository cleanup.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0 after repository cleanup.
- [x] `python -m compileall app` passed after repository cleanup.
- [x] `git diff --check` passed after repository cleanup.
- [x] Repository cleanup committed and pushed.
- [x] Public-facing wording cleaned to remove career-application framing.
- [x] `pytest -v` passed with 62 tests after wording cleanup.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0 after wording cleanup.
- [x] `python -m compileall app` passed after wording cleanup.
- [x] Career-framing keyword scan passed after wording cleanup.
- [x] Wording cleanup committed and pushed.
- [x] Factor DSL safety and correctness design and implementation plan written.
- [x] Strict Factor DSL window, signature, complexity, and metadata validation implemented.
- [x] Direct Factor DSL eval replaced with a controlled AST interpreter.
- [x] Negative-window fallback, interpreter regression, and validator tests added.
- [x] README and architecture docs updated with the strict DSL contract.
- [x] Full pytest, eval, compileall, Ruff, diff-check, and API smoke verification passed.
- [x] Realistic A-share backtest design spec and TDD implementation plan written.
- [x] Next-open equal-weight long-only portfolio engine implemented.
- [x] Configurable commission, sell-side stamp duty, slippage, and turnover implemented.
- [x] ST, listing-age, suspension, limit-up, limit-down, and missing-field diagnostics implemented.
- [x] Controlled historical-universe CSV registration and opaque-ID resolution implemented.
- [x] Independent flat-start IS/OOS portfolio integration and additive API outputs implemented.
- [x] Portfolio artifacts, report disclosures, dashboard controls, and documentation updated.
- [x] `pytest -v` passed with 139 tests after realistic backtest implementation.
- [x] `python evals/run_eval.py` passed with 5/5 correct and accuracy 1.0.
- [x] Compileall, Ruff, JavaScript syntax, diff-check, and API smoke verification passed.
- [x] Dashboard LLM provider/model/Base URL/API Key configuration restored with masked run-history persistence.
- [x] LLM configuration regression verified with 142 tests, 5/5 eval, browser interaction, and zero console errors.
- [x] Async research runs: POST /research/runs accepts async_run=true, returns immediately, background worker writes run_completed/run_failed events; frontend polls GET /runs/{id}.
- [x] Backtest benchmark comparison: long_only_metrics now include benchmark_beta, information_ratio, tracking_error, excess_annualized_return, relative_max_drawdown; report adds benchmark columns; assumptions record benchmark source.
- [x] Full pytest (143), eval (5/5), compileall, ruff verification passed after async + benchmark changes.
- [x] Walk-forward stability: rolling-window IC analysis (5 windows) with positive_ratio / sign_consistent / cross-window stats; report adds WF columns.
- [x] Multi-factor combination optimization: equal_weight / ic_weight / risk_parity composite factors backtested with benchmark-relative metrics; report adds combination section.
- [x] Full pytest (151), eval (5/5), compileall, ruff verification passed after walk-forward + combination changes.
- [x] Optional research_topic: upload mode runs without a topic (skips retrieval, derives topic from filename); auto mode without topic or documents returns 422.
- [x] Full pytest (153), eval (5/5), ruff verification passed after optional research_topic changes.

## In Progress

- [x] 阶段 0：日频因子研究治理基线与资源预算；已固化研究边界、数据和入库规则、成本上限、磁盘与时间预算、停止条件。
- [ ] 阶段 1：版本化 A 股原始日频数据仓；已完成版本目录、Parquet 表存取、未复权数据源适配、可恢复采集、质量发布联动、父子版本链读取、CSV 运维入口、研究任务固定绑定已发布数据版本、证券主表/交易日历/证券状态/公司行为的同版本 CSV 导入与质量契约、正式基线的四类参考表强制门禁、两标的一年本地授权演练及两次固定版本复跑、基线验收运行手册、公开候选源决策记录及可审计本地 CSV 发布命令；待取得全市场生产数据快照。

## Next Queue

- [ ] 因子库、受限 DSL 变形、固定版本实验编排和 PM 建议闭环已完成；两标的一年本地授权演练已完成；全市场回填仅在取得明确授权快照后执行。

## Known Risks

```text
1. GitHub push may require authentication.
2. Live AKShare and LLM calls may be unavailable.
3. The workspace path contains spaces, so shell commands must quote paths.
4. Public-source discovery currently uses deterministic curated seeds; live search API integration is deferred.
5. V6 keeps LLM extraction optional and falls back deterministically when keys/output are unavailable.
6. V7 keeps AKShare optional and falls back to fixture data when configured.
```

## Recovery Note

If this file is being read after context loss, continue with:

```text
1. Confirm current git status.
2. If V9 is not committed, run full verification and commit/push it.
3. Keep fixture and deterministic fallbacks available for offline demos.
```
