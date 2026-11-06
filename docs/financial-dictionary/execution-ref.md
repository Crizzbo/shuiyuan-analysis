# 执行材料引用

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `path` | 项目内路径 | string | 是 | 不可变执行材料副本；拒绝越界 |
| `sha256` | 内容摘要 | string | 是 | 内容字节 SHA-256 |

所有字段必填；完整嵌套结构及条件约束见 `schemas/registered-financial-fact.schema.json`。
