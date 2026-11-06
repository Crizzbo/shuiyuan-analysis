# snapshot：行情采集批次

| 字段 | 中文名称 | 类型 | 业务含义 |
|---|---|---|---|
| schema_version | 契约版本 | string | 固定1.0.0 |
| source_kind | 来源性质 | string | secondary，二级行情 |
| source_id | 数据来源标识 | string | google_finance_sheets |
| source_path | 原始资料路径 | string | 项目内原始工具返回，不是远程链接 |
| source_sha256 | 原始资料摘要 | string | 原始文件字节 SHA-256，用于绑定证据版本 |
| acquired_at | 实际采集时刻 | datetime | 含时区；首次观察约束，非证券交易时刻 |
| spreadsheet_id | 表格标识 | string | Google 原生表格身份 |
| sheet_name | 标签页名称 | string | 本批次有限范围所属页 |
| spreadsheet_timezone | 表格配置时区 | string | 元数据返回；不等于已核实交易所时区 |
| quotes | 证券行情集合 | array | 不重复证券列表；详见quote表 |
