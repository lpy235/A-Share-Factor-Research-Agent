# A 股原始日频数据基线运行手册

本手册用于建立和验收研究用的 A 股原始日频数据基线。范围仅限日频研究与回测，不包含交易、下单或实时行情。

## 目标与边界

第一版的目标是保存近 8 至 10 年的全 A 股原始不复权日线，并让每个研究任务固定引用一个已经发布的数据版本。

当前仓库已经提供本地数据仓、质量门禁、可恢复导入、日增量子版本和研究任务版本绑定；仓库中**没有**真实全市场历史数据，也不应把 fixture 或公开接口的临时响应当作生产基线。

当前候选数据源的核对结论见 [数据源决策记录](market-data-source-decision.md)。

数据仓根目录默认为 `market_data/`：

```text
market_data/
  warehouse.duckdb                 元数据、导入运行、失败记录、质量结果
  manifests/<version_id>.json      已发布版本的不可变清单与哈希
  lake/raw_daily_bars/...parquet   原始日线，按版本和年份分区
```

用 DBeaver 查看元数据时，连接本地 DuckDB 文件 `market_data/warehouse.duckdb`。行情明细保存在 Parquet，而不是 DuckDB 表中；这是为了让全市场多年日线和版本增量保持较低的磁盘与维护成本。

## 数据快照准入

优先使用公司内部授权导出或人工复核的 GitHub Release/提交快照。每个快照在导入前必须记录：

- 数据来源名称、URL，以及仓库提交哈希或 Release 标签；
- 文件 SHA-256、许可证或授权说明；
- 覆盖起止日期、标的范围和字段定义；
- 复权口径，必须明确为原始不复权；
- 人工复核人和复核日期。

这些信息应作为 `source` 名称和版本发布时的 manifest 上下文保存。没有授权或无法复核口径的快照只能用于开发演练，不能作为研究基线。

## CSV 合约

第一阶段使用受控本地 CSV 导入。CSV 至少需要以下列：

```text
symbol,trade_date,open,high,low,close,volume,amount
```

`symbol` 使用固定证券代码格式，例如 `000001.SZ`、`600000.SH`；`trade_date` 使用 `YYYY-MM-DD`。价格、成交量和成交额必须是可解析的非负数，且每个 `symbol + trade_date` 只能出现一次。

导入器在写入时补齐以下血缘字段：

```text
source,ingested_at,data_version,adjustment
```

其中 `adjustment` 固定为 `none`。不要在原始表中写入前复权、后复权或除权价格；后续如需研究价格层，必须单独定义变换编号及其父原始版本。

交易日历 CSV 必须包含 `trade_date`；可选的 `is_trading_day` 列可标记非交易日。正式导入通过以下本地命令执行，命令会将行情文件、交易日历文件的 SHA-256 与 `snapshot_ref` 写入版本 manifest：

```bash
python -m app.market_data.cli import-csv \
  --csv /absolute/path/raw_daily_bars.csv \
  --calendar-csv /absolute/path/trading_calendar.csv \
  --security-master-csv /absolute/path/security_master.csv \
  --security-status-csv /absolute/path/security_status.csv \
  --corporate-actions-csv /absolute/path/corporate_actions.csv \
  --require-reference-tables \
  --source internal_authorized_export \
  --snapshot-ref internal-export-2026-07-25 \
  --start-date 2020-01-01 \
  --end-date 2020-12-31 \
  --warehouse-root market_data
```

命令只接受本地文件，质量门禁未通过时返回非零状态且保留草稿版本供排查；不会调用网络或用 fixture 填补缺失数据。

`--require-reference-tables` 是正式全市场基线的强制开关。启用后，证券主表、交易日历、证券状态和公司行为四张表必须全部存在；任一缺失都会以硬质量门禁阻止发布，版本和已写入的 Parquet 保持草稿，供审计与排查。该策略同时写入 manifest 的 `reference_tables_required`。

两标的一年本地演练可不使用该开关，以保留仅验证日线导入和复现能力的入口；这绝不等同于正式全市场基线。

`--security-master-csv`、`--security-status-csv`、`--corporate-actions-csv` 是正式全市场基线必须提供的参考文件。字段合约如下：

```text
security_master:    symbol,exchange,security_name,listing_date[,delisting_date]
security_status:    symbol,trade_date,is_st,is_suspended
corporate_actions:  symbol,ex_date,action_type
trading_calendar:   trade_date,is_trading_day[,exchange]
```

导入器将交易日历写入 `trading_calendar` 表；缺少 `exchange` 时使用 `--calendar-exchange`（默认 `CN`）。参考表与日线共享相同 `data_version`、`source` 和 `ingested_at`，其 CSV SHA-256 及写入的 Parquet 分区路径会写入 manifest。参考文件一旦提供，其数据契约错误将阻止版本发布。

## 两只股票、一年演练

在下载全市场数据前，先用来源明确的两只股票、一个完整自然年 CSV 演练。通过标准是流程完整可重复，而不是收益表现：

1. 记录快照来源和文件哈希，确认 CSV 只包含原始不复权日线。
2. 用 `CsvRawDataSource`、`BackfillService`、`QualityGateService` 导入到一个新的草稿版本；导入按小批次执行，运行中断后使用同一 `ingest_run_id` 恢复。
3. 质量门禁必须全部通过：血缘字段、`symbol + trade_date` 唯一性、OHLC 合理性、`adjustment=none`、交易日覆盖和失败标的比例。
4. 检查 `warehouse.duckdb` 的 `data_versions`、`ingest_runs`、`ingest_errors`、`quality_results`，以及 `manifests/<version_id>.json`。只有 `status=published` 的版本可以用于研究。
5. 以 `data_provider=warehouse` 和该 `data_version` 提交一次研究；请求同时指定 `market_data_root`，以便定位同一个数据仓。
6. 保存研究 artifact bundle、报告和 manifest hash；以完全相同的 `data_version` 再运行一次，确认两次报告中的 `data_version` 与 `manifest_hash` 一致。

研究请求示例：

```json
{
  "research_topic": "量价因子演练",
  "data_provider": "warehouse",
  "data_version": "vYYYYMMDD_abcdefgh",
  "market_data_root": "market_data",
  "start_date": "2020-01-01",
  "end_date": "2020-12-31",
  "fallback_to_fixture": false
}
```

`warehouse` 模式不会在数据缺失时静默回退到 fixture；草稿版本、未知版本或未提供 `data_version` 的请求会被拒绝。

## 全市场基线回填

只有演练成功后才开始近 8 至 10 年全 A 股回填：

1. 为此次回填确定一个日期范围和唯一数据源快照，预先估算磁盘空间并保留至少 30% 余量。
2. 创建草稿版本，以可恢复的批次导入方式运行；保留每个失败标的和重试次数，不能以 fixture 补齐失败数据。
3. 发生中断时只恢复同一导入运行，不创建替代版本或覆盖既有 Parquet 分区。
4. 回填命令必须包含 `--require-reference-tables`，并检查失败标的比例、交易日覆盖、异常 OHLC、重复行和血缘字段。任何硬门禁失败都不得发布。
5. 发布成功后冻结该版本和 manifest；后续每日更新必须形成以该版本为父版本的增量子版本，不能修改已发布的历史版本。

## 日常更新与回滚原则

每日更新只在交易日执行，生成一个通过质量门禁的子版本。子版本的 manifest 记录 `parent_version_id` 与更新日期；读取时系统会沿父子链合并有效行情。

发现来源修订或数据错误时，不修改已发布版本。应创建新的草稿版本，重新导入、重新质检并发布；已有研究任务继续保留对旧版本的引用。回滚是切换研究任务使用的版本号，而不是删除历史数据。

## 发布验收清单

- [ ] 原始行情均为 `adjustment=none`，没有复权价格混入。
- [ ] 每行都有 `source`、`ingested_at`、`data_version`。
- [ ] `manifest_hash` 已生成，版本状态为 `published`。
- [ ] 所有硬质量门禁通过，失败标的有明确记录。
- [ ] 正式基线 manifest 的 `reference_tables_required=true`，且四类参考表的 Parquet 分区与文件哈希齐全。
- [ ] DBeaver 可查看 DuckDB 元数据，Parquet 分区和 manifest 可读。
- [ ] 固定同一 `data_version` 的两次研究复跑得到相同的 manifest hash。
- [ ] 研究报告明确披露数据版本、来源和原始不复权口径。

## 当前下一步

提供或确认一份可合法使用、可复核的两标的一年 CSV 快照后，执行上述演练并把结果写入基线验收记录。演练成功前，不启动全 A 股 8 至 10 年的正式回填。
