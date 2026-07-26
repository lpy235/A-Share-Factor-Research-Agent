# AKShare 新浪沪深研究基线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以可审计、可暂停方式导入 AKShare 新浪沪深在市 A 股原始不复权日线。

**Architecture:** 独立新浪源负责代码映射、日线与日历；CLI 创建或恢复既有 `BackfillService`。manifest 披露来源版本和缺北京/退市证券的范围限制。

**Tech Stack:** Python 3.14, AKShare, pandas, DuckDB, Parquet, pytest。

---

### Task 1: 新浪沪深源

**Files:**
- Create: `app/market_data/sources/akshare_sina_hs.py`
- Test: `tests/test_market_data_sources.py`

- [x] 写出代码映射、`adjust=""`、列规范化和日历的失败测试。
- [x] 实现只选择沪深 A 股前缀的新浪源，不支持的参考表显式报 capability error。

### Task 2: 回填 CLI

**Files:**
- Modify: `app/market_data/cli.py`
- Test: `tests/test_market_data_cli.py`

- [x] 添加创建或恢复新浪回填运行的命令、批次大小与暂停参数。
- [x] 将 AKShare 版本、通道、证券范围和限制写入 manifest。

### Task 3: 范围披露与真实运行

**Files:**
- Modify: `docs/market-data-baseline-runbook.md`
- Modify: `docs/market-data-source-decision.md`
- Modify: `.codex-harness/STATE.md`

- [x] 明确这不是全 A 股或正式授权基线。
- [ ] 运行测试、静态检查和一个真实暂停批次，检查恢复信息后继续回填。
