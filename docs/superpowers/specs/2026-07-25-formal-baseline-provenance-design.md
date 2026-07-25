# 正式基线来源元数据设计

## 目标

让正式全 A 股数据基线的来源、使用依据、覆盖范围、原始不复权声明和人工复核信息随数据版本不可变地保存，而不是仅依赖运行手册。

## 方案

`import-csv --formal-baseline --provenance-json <file>` 进入正式模式。模式自动启用四类参考表门禁，并读取本地 JSON。JSON 必须包含 `schema_version`、`source_name`、`snapshot_ref`、`source_location`、`authorization_basis`、`license_or_terms`、`coverage_start`、`coverage_end`、`universe_description`、`field_definition_ref`、`price_adjustment`、`reviewed_by`、`reviewed_at`。

导入器验证来源和快照标识与 CLI 参数一致，覆盖日期包含请求区间，价格口径为 `none`，复核日期可解析。通过后把 JSON 内容及 SHA-256 写入 manifest。该校验只证明操作者提供了结构化证据，不能验证第三方许可证或授权材料的真实性。

## 兼容性与测试

未启用 `--formal-baseline` 的现有演练行为不变。正式模式缺少 JSON、字段缺失、参数不一致、日期不足或非不复权声明都应在写入前失败；完整元数据与四张参考表可正常发布。
