# 指标计算结果

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `metric_id` | 指标代码 | string | 是 | 计算绑定代码，不等于已完成行业全部指标 |
| `name_zh` | 指标中文名称 | string | 条件必填/可选 | 明确说明计算口径的显示名称 |
| `period` | 计算期间 | 对象引用 | 是 | 按同一报表期间执行 |
| `scope_id` | 计算范围 | string | 是 | 输入必须同范围 |
| `accounting_basis` | 计算会计准则 | string | 是 | 输入必须同准则 |
| `currency` | 输入币种 | string | 是 | 原始金额币种；比率本身无货币量纲 |
| `status` | 执行状态 | string | 是 | computed 是口径审核后计算，blocked 是缺失或无效 |
| `value` | 计算值 | number/null | 是 | 成功为有限比率；阻断为空 |
| `unit` | 结果单位 | string | 条件必填/可选 | 当前计算均为比例，百分数展示需乘 100 |
| `input_fact_refs` | 输入事实引用 | array | 条件必填/可选 | 报告内事实 ID，公式复核入口 |
| `calculation` | 公式及开源实现 | object | 条件必填/可选 | 标准金融服务返回完整调用记录；直接库调用记录 library/function/formula |
| `reason` | 阻断原因 | string | 条件必填/可选 | 无法执行时的口径或输入原因 |
| `missing_fields` | 缺少输入字段 | array | 条件必填/可选 | 无法执行时的原始字段代码 |

字段与 `schemas/financial-report.schema.json` 同源生成；对象数组的具体运行结果见 14 功能设计。
