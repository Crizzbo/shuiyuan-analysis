# Google 行情 MCP 执行规则

## 用途与边界

本来源作为优先行情快照来源，已经完成三家美股、八项字段的读写及在线计算测试。一次测试不能证明长期可用性；每次采集都检查结果和行情时点。连接依赖 agent 宿主已授权的 Google Drive 插件，不是项目内 Python 网络库，也不是 Google 官方 Sheets MCP 服务端配置。不要把 `sheetsmcp.googleapis.com` 当成本项目已安装的端点。

读取 `config/google-finance-mcp.json` 获取唯一来源配置。工具名称为当前宿主暴露的名称；其他宿主只在工具说明匹配时使用等价操作，不猜测未提供的工具。没有工具时报告 `tool_unavailable`；认证失败报告 `connection_unavailable`。不得声称插件已加载、自动修改全局 MCP 配置或索取凭据。

## 默认读取流程

批量行业验证另使用 `config/google-finance-industry-plan.json` 及标签页“行业行情验证”，范围 A1:L42；原始三只证券配置保留不覆盖。该批次额外验证 high52、low52。标准化导入、字段字典与计算连接见 `docs/market-snapshot-design.md`。

1. 发现配置中的元数据及读取工具，调用元数据检查原生表格 ID、标签页名称、网格范围和时区。测试表是项目专用表，不搜索或读取无关文件。
2. 用以下结构化参数读取当前测试范围，不传 JSON 字符串，不整表读取：

```json
{
  "spreadsheet_id": "CONFIGURE_YOUR_OWN_CLOUD_TARGET",
  "ranges": ["'金融取数测试'!A3:J8"],
  "cell_fields": "userEnteredValue,effectiveValue,formattedValue"
}
```

3. 普通公式对照 B3 应为数值 3。A6:A8 是交易所限定代码；C:J 依次为价格、币种、市值、成交量、PE、EPS、交易时间、延迟。核对公式引用与证券代码，价格应为正数，币种应为非空文本。缺失、加载中、错误值必须保留；失败字段不变成 0，也不整批宣告成功。
4. 记录本次采集 UTC 时刻、原始交易时间数值及格式、表格时区、每字段状态。`datadelay=0` 不证明行情是今天的交易，也不证明没有供应商延迟。不要凭表格时区擅自认定 `tradetime` 的交易所时区；保留原始语义并将未核对转换标为未知。周末及休市可返回最近交易日；是否过期结合交易日历、任务时点判断，不使用自然日固定阈值。
5. 保存工具原始返回（metadata、cells）和采集时刻到 `data/google-finance/raw/` 下新文件；原始字段不改写、不覆盖旧版本。清洗和单位转换另存，不把格式化字符串当数值。远程链接仅为来源身份元数据，本地研究证据路径必须指向项目内归档文件。
6. 为归档创建 `schemas/source-manifest.schema.json` 1.1.0 登记：`source_kind=secondary`、`dataset_kind=market`、`published_at=null`、`publication_precision=unknown`、`published_date=null`；`available_at` 和 `acquired_at` 使用实际观察时刻，不使用证券交易日期冒充首次可得时间。按已登记版本增加 revision，指定 supersedes_revision。执行 `python scripts/data_catalog.py register-source <项目内manifest相对路径>`，使用返回的资料版本登记研究证据。
7. 至多重试一次失败操作；仍失败则保留本地旧快照并显式标记过期/不可用。需要补数时按项目已授权策略浏览官方公开来源，不能让旧值伪装成最新值。没有调度配置时不得宣称后台自动刷新。

## 更新标的与表格

任务要求新增标的时，可在项目专用表中新增独立标签页，避免覆盖既有研究或并发 agent 的范围；先读取元数据取得真实 sheetId，再调用宿主的 batch_update_spreadsheet。使用交易所前缀，价格公式为 `=GOOGLEFINANCE($A6,"price")`，其他属性按配置替换。更新完成再读取实际 effectiveValue，不能以写入成功代替取数成功。各 agent 使用独立区域并核对自己写入的证券代码，出现覆盖冲突停止使用该批数据。

创建新的原生 Google 表格时，遵循宿主 Google Sheets 技能的创建流程（默认本地 XLSX 经 import_spreadsheet 转换）；本项目不保存用户凭据。无需为每次查询创建新文件。新增字段/市场先小样本测试，再记录覆盖范围，不能把单只证券测试推广为全市场支持。

## 数据字典

| 属性 | 中文名称 | 单位与业务含义 | 当前状态 |
|---|---|---|---|
| price | 最近报价 | 证券计价币种/股；非保证实时成交价 | 已验证 |
| currency | 计价币种 | 原始币种代码 | 已验证 |
| marketcap | 市值 | 证券计价币种；供应商快照 | 已验证 |
| volume | 当日成交量 | 原始证券数量口径；休市可能是最近交易日 | 已验证 |
| pe | 市盈率 | 倍；供应商口径，不能替代 forwardPE | 已验证 |
| eps | 每股收益 | 计价币种/股；周期及调整口径需另行核对 | 已验证 |
| tradetime | 最近交易时间 | 原始日期序列及显示值；时区转换待核对 | 已验证 |
| datadelay | 报价延迟 | 分钟；不替代交易时间检查 | 已验证 |
| priceopen/high/low/closeyest | 开盘/日高/日低/昨收 | 计价币种/股 | 官方支持，未实测 |
| change/changepct | 涨跌额/涨跌幅 | 计价币种/股及百分数；涨跌幅归一化需核对原始数值口径 | 官方支持，未实测 |
| volumeavg/shares | 平均成交量/已发行股数 | 证券数量；平均窗口未核实 | 官方支持，未实测 |
| beta/high52/low52 | Beta/52周高/52周低 | 系数及计价币种/股 | 官方支持，未实测 |

历史行情虽然可在表格显示，但供应商限制 Sheets API／Apps Script 读取，不能设计成可靠 MCP 历史行情接口。日股覆盖未验证。GOOGLEFINANCE 不提供完整三表、业务分部及行业指标；这些仍使用官方原文。不能从 PE/EPS 快照臆造财报事实。

## 来源身份与验证依据

官方字段说明的地址作为来源身份：`https://support.google.com/docs/answer/3093281?hl=zh-Hans`。本项目验证依据为 `data/google-finance/raw/20261011T094549Z.json`，并通过项目资料目录登记。该快照是工具实际返回的二级行情资料，未完成与交易所或发行人独立对账；读取成功不等于价格真实性已独立审计。
