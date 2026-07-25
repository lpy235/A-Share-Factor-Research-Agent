# 正式基线来源元数据 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让正式 CSV 基线导入保存并校验可审计来源元数据。

**Architecture:** 独立 provenance 模块验证本地 JSON；CLI 仅在 `--formal-baseline` 选择时调用它，自动启用参考表门禁，并把验证后的内容与文件哈希交给既有 manifest 发布流程。

**Tech Stack:** Python 3.14, JSON, pandas, pytest, DuckDB/Parquet。

---

### Task 1: 契约与回归测试

**Files:**
- Create: `app/market_data/provenance.py`
- Create: `tests/test_market_data_provenance.py`
- Modify: `tests/test_market_data_cli.py`

- [x] 写出正式模式缺少或不一致 provenance JSON 的失败测试。
- [x] 写出完整 JSON 在发布 manifest 中保留内容与 SHA-256 的成功测试。

### Task 2: CLI 集成

**Files:**
- Modify: `app/market_data/cli.py`

- [x] 添加 `--formal-baseline` 和 `--provenance-json`。
- [x] 正式模式自动要求四类参考表，读取并验证 JSON，再写入 manifest。

### Task 3: 文档与验证

**Files:**
- Modify: `docs/market-data-baseline-runbook.md`
- Modify: `docs/2026-07-25-next-ten-tasks.md`
- Modify: `.codex-harness/STATE.md`

- [x] 给出最小 JSON 示例和正式命令，说明外部许可真实性仍需人工复核。
- [x] 运行全量 pytest、Ruff、compileall、eval 与 diff 检查，然后提交推送。
