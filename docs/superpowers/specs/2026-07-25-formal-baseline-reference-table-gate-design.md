# 正式基线参考表门禁设计

## 目标

防止缺少证券主表、交易日历、证券状态或公司行为的日线快照被误发布为正式全 A 股研究基线，同时保留小样本本地演练入口。

## 设计

`QualityGateService` 接受 `required_reference_tables` 布尔策略。策略关闭时，缺失参考表产生 warning；策略开启时，每张缺失表产生 `<table>_required` 硬失败，因而版本不能从 draft 发布。已提供表继续使用既有契约校验，证券状态还需与证券主表一致。

`BackfillService` 只负责保存并透传该策略。`import-csv` 通过显式 `--require-reference-tables` 选择正式基线路径，并将选择记录在发布 manifest 的 `reference_tables_required`。交易日历 CSV 本来就是 CLI 必填项，但质量服务仍对四类表完整建模，供非 CLI 调用复用。

## 边界与验证

该开关不授权任何数据源，也不把公开 AKShare/Sina 演练数据转为生产基线。测试覆盖：缺表时质量结果为硬失败且草稿保留；四表齐全且开关开启时仍可发布；默认 bars-only 演练兼容行为不变。
