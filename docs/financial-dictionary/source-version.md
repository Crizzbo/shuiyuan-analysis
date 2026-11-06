# 登记资料版本

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `source_id` | 资料标识 | string | 是 | 正式 sources 表标识 |
| `revision` | 资料修订号 | integer | 是 | 精确绑定原文版本 |
| `sha256` | 内容摘要 | string | 是 | 内容字节 SHA-256 |

所有字段必填；完整嵌套结构及条件约束见 `schemas/registered-financial-fact.schema.json`。
