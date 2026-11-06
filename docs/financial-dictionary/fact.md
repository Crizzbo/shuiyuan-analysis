# 标准财务事实

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `id` | 事实标识 | string | 是 | 由报告、字段、期间、范围和原文定位生成的 SHA-256 |
| `field` | 字段代码 | string | 是 | 经审核的报表科目映射，未映射科目不以相似名称替代 |
| `name_zh` | 中文名称 | string | 是 | 科目业务中文名称 |
| `value` | 基础货币金额 | string | 是 | 十进制字符串，保留精度和正负号；不是展示用百万金额 |
| `period` | 财务期间 | 对象引用 | 是 | 原报表期间，流量与存量分开 |
| `scope_id` | 报表范围 | string | 是 | consolidated 合并总额；consolidated_continuing 合并持续经营；不可混算 |
| `accounting_basis` | 会计准则 | string | 是 | 明确保留准则，不把 IFRS 与 GAAP 等同 |
| `currency` | 币种 | string | 是 | ISO 三字母币种，不自动换汇 |
| `unit` | 量纲 | string | 是 | 本阶段仅金额 |
| `scale` | 金额尺度 | integer | 是 | 已转换为基础货币单位，因此恒为 1；原尺度见原文 |
| `concept` | 原始科目 | string | 是 | XBRL 展开 QName 或已核对的 PDF 精确行名 |
| `source` | 原文证据 | 对象引用 | 是 | 项目内原文、哈希、定位和实际可得时点 |
| `rounding_tolerance` | 金额舍入容差 | string/null | 是 | 基础货币单位；四舍五入取半个最小展示单位，截断取一个单位；未知为空并阻断勾稽 |
| `status` | 事实质量状态 | string | 是 | extracted 表示完成提取，仍待研究审核；冲突和勾稽失败禁止计算 |
| `duplicate_refs` | 同值重复原文引用 | array | 是 | 仅同字段、期间、范围、准则、币种且同金额时归并；保留所有证据 |

字段与 `schemas/financial-report.schema.json` 同源生成；对象数组的具体运行结果见 14 功能设计。
