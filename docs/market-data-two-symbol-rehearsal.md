# 两标的一年本地数据演练验收记录

## 范围

本记录对应 2020 年 `000001.SZ` 与 `600000.SH` 的本地、不可再分发演练快照。它验证数据仓、版本绑定和研究复跑流程，不构成全 A 股正式历史基线，也不支持因子批准或交易决策。

## 数据快照

- 数据版本：`v20201231_fb995fa6`
- manifest hash：`beb54b87336dc167cf7dd51c3f284a875156f98b48b5b69f9f6cf24f181b3475`
- 数据来源：`akshare_sina_public_local_rehearsal`
- 上游：AKShare `stock_zh_a_daily` 经新浪财经公开历史 A 股接口，`adjust=""`；交易日历来自 `tool_trade_date_hist_sina`。
- 本地来源元数据：`market_data/source_snapshots/akshare_sina_2020_two_symbol_rehearsal/source_metadata.json`，其 SHA-256 已写入 manifest 的 `snapshot_ref`。
- 原始行情 CSV SHA-256：`966f2d85479cb4377538eea27da1294b4642d1d3242dd32dd43ee88a63767501`
- 交易日历 CSV SHA-256：`d41c46e7989979f43059e668dae5dec177124836186831b8a7976e8fd88dbb7c`
- 行情行数：486；交易日：243；每只标的：243。

## 质量结果

以下硬门禁均以 `affected_count=0` 通过：血缘字段、`symbol + trade_date` 唯一性、OHLC 合理性、`adjustment=none`、交易日覆盖、失败标的比例。

证券主表、证券状态和公司行为文件没有随本次公开演练快照提供，因此相关契约仅保留为 warning 级质量记录。全市场正式基线必须补齐这些参考表并重新验收。

## 固定版本复跑

两次运行使用完全相同的 `warehouse` 配置，均设置 `fallback_to_fixture=false`：

| 运行 ID | 结果 |
| --- | --- |
| `run_b9223a05da71` | 完成 |
| `run_5f5ce9804224` | 完成 |

两次运行的 `data_version`、manifest hash、DSL 公式、IS/OOS 指标和 `selected_factors` 均完全一致。两标的横截面不足以通过当前准入门禁，`selected_factors` 为空；因此没有登记因子候选，也没有生成 PM 建议或人工因子库决策。这是样本规模限制，不是数据版本复现失败。

## 结论与后续

任务 8 的本地两标的一年演练已完成。任务 9 仍需明确许可、覆盖全 A 股且包含证券主表、停复牌、ST、退市和公司行为的正式离线快照；不得将本次公开演练版本扩展为生产历史库。
