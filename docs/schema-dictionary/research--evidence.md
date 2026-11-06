# OBJ-004 · evidence 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/evidence`。
- 引用位置（Schema 指针）：`#/properties/evidence/items`。
- 对象额外字段：禁止。
- 属性定义数：11（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `evidence.id` | 证据标识 | string | 是 | 否 | 最短字符=1 | 对象在所属登记表或明确作用域中的唯一 ID；不是显示名称。 |
| `evidence.source_path` | 资料文件路径 | local_path | 是 | 否 | 引用=#/$defs/local_path | 本证据所依据的本地资料文件路径，相对项目根目录；可以来自 primary 或 secondary 等资料。归档快照可能改写为项目内内容对象路径，不保证始终保留原始文件名。 |
| `evidence.locator` | 原文定位信息 | string | 是 | 否 | 最短字符=1 | 原文位置，如章节、页码、行号或 JSON 字段；不能只写文件名。 |
| `evidence.source_kind` | 来源类型 | 枚举 | 是 | 否 | 枚举=['primary', 'secondary', 'project_design', 'synthetic'] | primary 原始资料、secondary 二手资料、project_design 项目设计、synthetic 合成测试。 |
| `evidence.published_at` | 精确发布时间 | string / null | 是 | 是 | 格式=date-time；无显式附加结构约束 | 原始资料的精确发布时间，必须带时区；1.0.0 不允许为空，1.1.0 在仅日期或未知时填 null，不得补造午夜。 |
| `evidence.available_at` | 信息可得时间 | string | 是 | 否 | 格式=date-time | 所引用资料这个版本的可得时点，用于判断研究截止时是否能够获得。与发布时间和系统获取时间分开；后来的更正版本不能沿用旧版可得时间。 |
| `evidence.acquired_at` | 资料获取时间 | string | 是 | 否 | 格式=date-time | 本系统实际获取本地资料的时间；可以晚于历史研究截止时间。 |
| `evidence.excerpt_or_summary` | 原文摘录或摘要 | string | 是 | 否 | 最短字符=1 | 与当前判断相关的原文摘录或忠实概括，需配合 locator 人工核验。 |
| `evidence.limitations` | 证据局限 | array<string> | 是 | 否 | 至少项数=0 | 证据、评估或模型的局限与未解决事项；无已知事项时可为空数组。 |
| `evidence.published_date` | 发布日期 | string / null | 1.1.0 必须 | 是 | 格式=date；无显式附加结构约束 | 官方资料显示的发布日期，或精确发布时间在其原时区内的日期；1.1.0 必须出现键，未知填 null。仅日期不证明该日任意时刻已经可得。 |
| `evidence.publication_precision` | 发布时间精度 | 枚举 | 1.1.0 必须 | 否 | 枚举=['instant', 'date', 'unknown'] | instant 有已核实的精确时刻；date 仅有日期，published_at 必须 null；unknown 两者均未知且为空。1.1.0 必填，与登记资料版本保持一致。 |

## 3. 关联对象


## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>evidence.id · 证据标识</summary>

Schema 指针：`#/$defs/evidence/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>evidence.source_path · 资料文件路径</summary>

Schema 指针：`#/$defs/evidence/properties/source_path`。

```json
{
  "$ref": "#/$defs/local_path"
}
```

</details>

<details>
<summary>evidence.locator · 原文定位信息</summary>

Schema 指针：`#/$defs/evidence/properties/locator`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>evidence.source_kind · 来源类型</summary>

Schema 指针：`#/$defs/evidence/properties/source_kind`。

```json
{
  "enum": [
    "primary",
    "secondary",
    "project_design",
    "synthetic"
  ]
}
```

</details>

<details>
<summary>evidence.published_at · 精确发布时间</summary>

Schema 指针：`#/$defs/evidence/properties/published_at`。

```json
{
  "anyOf": [
    {
      "type": "string",
      "format": "date-time"
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>evidence.available_at · 信息可得时间</summary>

Schema 指针：`#/$defs/evidence/properties/available_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>evidence.acquired_at · 资料获取时间</summary>

Schema 指针：`#/$defs/evidence/properties/acquired_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>evidence.excerpt_or_summary · 原文摘录或摘要</summary>

Schema 指针：`#/$defs/evidence/properties/excerpt_or_summary`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>evidence.limitations · 证据局限</summary>

Schema 指针：`#/$defs/evidence/properties/limitations`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "minItems": 0
}
```

</details>

<details>
<summary>evidence.published_date · 发布日期</summary>

Schema 指针：`#/$defs/evidence/properties/published_date`。

```json
{
  "anyOf": [
    {
      "type": "string",
      "format": "date"
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>evidence.publication_precision · 发布时间精度</summary>

Schema 指针：`#/$defs/evidence/properties/publication_precision`。

```json
{
  "enum": [
    "instant",
    "date",
    "unknown"
  ]
}
```

</details>

