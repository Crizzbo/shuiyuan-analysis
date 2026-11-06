# 正式财务事实登记

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `schema_version` | 契约版本 | string | 是 | 正式登记封套版本 |
| `registration_id` | 登记标识 | string | 是 | 除自身之外登记封套 canonical JSON 的 SHA-256 |
| `entity_id` | 公司标识 | string | 是 | 与原文浏览器登记和财报一致 |
| `report_id` | 报告版本标识 | string | 是 | 重述以新报告标识追加，比较列不自动归入历史发布 |
| `fact` | 标准财务事实 | 对象引用 | 是 | 原始报表科目，金额十进制字符串，保留范围及期间 |
| `quality_status` | 核验状态 | string | 是 | 原文及解析核验通过；不代表审计意见、行业判断或六步完成 |
| `report_ref` | 财报快照引用 | object | 是 | 财报快照引用；结构见契约 |
| `plan_ref` | 解析配置引用 | object | 是 | 解析配置引用；结构见契约 |
| `implementation_ref` | 解析实现引用 | object | 是 | 解析实现引用；结构见契约 |
| `original_source` | 原始 ZIP/PDF 登记版本 | object | 是 | 原始 ZIP/PDF 登记版本；结构见契约 |
| `evidence_source` | 派生证据登记版本 | object | 是 | 派生证据登记版本；结构见契约 |
| `taxonomy_validation` | 分类标准校验 | object | 是 | Inline XBRL 必须 passed；PDF 为 not_applicable |

所有字段必填；完整嵌套结构及条件约束见 `schemas/registered-financial-fact.schema.json`。
