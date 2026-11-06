# field：供应商行情字段

| 字段 | 中文名称 | 类型 | 业务含义 |
|---|---|---|---|
| attribute | 属性标识 | enum | 对应GOOGLEFINANCE英文参数 |
| value | 标准有效值 | number/string/null | 从effectiveValue读取；未知及错误为空 |
| unit | 单位 | string | 明确计价单位；金额币种由currency字段提供 |
| status | 字段状态 | enum | ok、missing、formula_mismatch、provider_error、invalid_value |
| formula | 原始公式 | string/null | 必须引用当前行及正确属性；不是计算结果 |
| display_value | 原始显示值 | string/null | 仅供人核对，不解析成金额或日期 |
| provider_error | 供应商错误对象 | object/null | 原样保留类型及消息，不转成正常值 |

| 属性 | 中文名称 | 单位 | 口径说明 |
|---|---|---|---|
| price | 最近报价 | currency_per_share | 非保证实时成交价 |
| currency | 计价币种 | currency_code | 三位大写代码 |
| marketcap | 市值 | currency | 供应商快照，不推断稀释股数 |
| volume | 成交量 | shares | 原始证券数量口径；可能为最近交易日 |
| pe | 市盈率 | multiple | 供应商口径；不是forwardPE |
| eps | 每股收益 | currency_per_share | 财报周期及调整口径未知，不当作官方财务事实 |
| tradetime | 最近交易时间 | provider_date_serial | Google日期序列，时区未核实；同时保留显示值 |
| datadelay | 报价延迟 | minutes | 0不代表今天有交易 |
| high52 | 52周最高价 | currency_per_share | 供应商窗口；复权方式未知 |
| low52 | 52周最低价 | currency_per_share | 供应商窗口；复权方式未知 |
