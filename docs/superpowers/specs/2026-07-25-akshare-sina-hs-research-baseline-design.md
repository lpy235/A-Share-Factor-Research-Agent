# AKShare 新浪沪深研究基线设计

## 目标

在当前东方财富端点不可达的网络环境中，使用 AKShare 的新浪原始不复权接口建立可暂停、可复现的沪深在市 A 股本地研究数据版本。

## 范围

数据源只包含 `stock_zh_a_daily(..., adjust="")` 能返回的沪深股票。证券清单来自 `stock_info_a_code_name()`，交易日历来自 `tool_trade_date_hist_sina()`。北京市场与已退市证券不在该入口覆盖范围内，因此版本必须记录幸存者偏差，不能标为全 A 股或正式授权基线。

## 架构

新增独立 `AkshareSinaHsRawDataSource`，不修改依赖东方财富的既有适配器。新 CLI 创建或恢复 `BackfillService` 运行，按小批次写入 Parquet；每次调用重新计算同一新浪交易日历以执行质量检查。manifest 固化 AKShare 版本、上游通道、证券范围和限制说明。

## 验证

单元测试验证代码到沪深交易所的映射、日线列规范化、`adjust=""` 与交易日历。真实运行先暂停在一个小批次，检查 Parquet、质量记录和可恢复状态，再继续完整范围。任何来源错误都会保留错误记录；不以 fixture 补数。
