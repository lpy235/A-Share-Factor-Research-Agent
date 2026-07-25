# 正式基线参考表门禁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让正式全市场 CSV 导入在四类参考表不完整时不能发布。

**Architecture:** CLI 的显式开关传入 `BackfillService`，后者在发布时传入 `QualityGateService`。质量服务将策略转换为质量结果与 manifest 字段；默认策略保持演练行为。

**Tech Stack:** Python 3.14, pandas, pytest, DuckDB/Parquet 数据仓。

---

### Task 1: 质量服务门禁

**Files:**
- Modify: `app/market_data/quality.py`
- Test: `tests/test_market_data_quality.py`

- [x] 编写缺表时必须产生硬失败并保留 draft 的回归测试。
- [x] 向 `publish_if_valid()` 与 `evaluate_reference_tables()` 增加 `required_reference_tables=False`。
- [x] 对每个缺失且必需的表记录 `QualityCheck(f"{name}_required", False, 1)`。
- [x] 将策略值写入发布 manifest 的 `reference_tables_required`。

### Task 2: 导入链路与 CLI

**Files:**
- Modify: `app/market_data/ingestion.py`
- Modify: `app/market_data/cli.py`
- Test: `tests/test_market_data_cli.py`

- [x] 让 `BackfillService` 保存并透传策略。
- [x] 添加 `--require-reference-tables` 开关。
- [x] 验证四表齐全时发布，只有日线和日历时返回 1 且版本保持 draft。

### Task 3: 操作说明与验证

**Files:**
- Modify: `docs/market-data-baseline-runbook.md`
- Modify: `docs/2026-07-25-next-ten-tasks.md`
- Modify: `.codex-harness/STATE.md`

- [x] 在正式基线命令、验收清单和任务状态中记录强制开关与演练边界。
- [x] 运行全量 pytest、Ruff、compileall、eval 和 diff 检查，再提交推送。
