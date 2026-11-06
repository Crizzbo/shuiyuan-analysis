# OBJ-030 · source_manifest 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/source-manifest.schema.json](../../schemas/source-manifest.schema.json)。
- 定义位置：`#`。
- 引用位置（Schema 指针）：根对象。
- 对象额外字段：禁止。
- 属性定义数：17（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `source_manifest.schema_version` | 契约版本 | 枚举 | 是 | 否 | 枚举=['1.0.0', '1.1.0'] | 数据契约版本，支持 1.0.0 与 1.1.0；新版保留发布日期精度，不表示步骤或软件版本。 |
| `source_manifest.source_id` | 资料系列标识 | string | 是 | 否 | 最短字符=1 | 资料系列稳定 ID，不随文件改名改变，与研究 evidence ID 不同。 |
| `source_manifest.revision` | 修订号 | integer | 是 | 否 | 最小=1 | 该研究或资料系列的修订号，从 1 连续增加；旧版不能覆盖。 |
| `source_manifest.source_path` | 资料文件路径 | string | 是 | 否 | 最短字符=1；正则限定；本地路径另做真实路径检查 | 待登记这个资料版本的本地文件路径，相对项目根目录；入库按文件字节归档及校验哈希。资料可以是新闻、行情、研究材料等，不一定是第一手原始文件。 |
| `source_manifest.source_kind` | 来源类型 | 枚举 | 是 | 否 | 枚举=['primary', 'secondary', 'project_design', 'synthetic'] | primary 原始资料、secondary 二手资料、project_design 项目设计、synthetic 合成测试。 |
| `source_manifest.dataset_kind` | 资料类别 | 枚举 | 是 | 否 | 枚举=['financial', 'market', 'industry', 'news', 'company_action', 'classification', 'research_material', 'other'] | financial 财务、market 行情、industry 行业、news 新闻、company_action 公司行动、classification 分类、research_material 研究材料或 other。 |
| `source_manifest.published_at` | 精确发布时间 | string / null | 是 | 否 | 格式=date-time | 原始资料的精确发布时间，必须带时区；1.0.0 不允许为空，1.1.0 在仅日期或未知时填 null，不得补造午夜。 |
| `source_manifest.available_at` | 信息可得时间 | string | 是 | 否 | 格式=date-time | 本次登记资料版本的可得时点，不是下载时间；历史修订应按修订版的实际可得时点登记。 |
| `source_manifest.acquired_at` | 资料获取时间 | string | 是 | 否 | 格式=date-time | 本系统实际获取本地资料的时间；可以晚于历史研究截止时间。 |
| `source_manifest.effective_period` | 资料覆盖或生效期间 | null / object | 是 | 是 | 无显式附加结构约束；不接受额外字段 | 资料对应或生效的日期区间；无法确定填 null，不用发布时间冒充。 |
| `source_manifest.effective_period.start` | 期间开始日期 | string | 是 | 否 | 格式=date | 该资料描述或生效的覆盖期间起日；不是发布时间。只有 effective_period 非 null 时此属性才必须出现；完整区间的起止顺序由资料登记检查。 |
| `source_manifest.effective_period.end` | 期间结束日期 | string | 是 | 否 | 格式=date | 该资料描述或生效的覆盖期间止日；可以不同于发布时间或获取时间，不应直接套用历史观测截止日限制。 |
| `source_manifest.license_notes` | 使用权及来源限制说明 | string | 是 | 否 | 最短字符=1 | 资料使用权及来源限制说明；填写说明不等于系统自动核实授权。 |
| `source_manifest.quality_notes` | 资料质量说明列表 | array<string> | 是 | 否 | 无显式附加结构约束 | 来源缺陷、修订、缺项或可信度限制；没有已知问题可为空数组。 |
| `source_manifest.supersedes_revision` | 被替代修订号 | integer / null | 是 | 是 | 最小=1；无显式附加结构约束 | 被本次修订替代的前版编号；首版必须 null，后续必须前版 revision。 |
| `source_manifest.published_date` | 发布日期 | string / null | 1.1.0 必须 | 否 | 格式=date | 官方资料显示的发布日期，或精确发布时间在其原时区内的日期；1.1.0 必须出现键，未知填 null。仅日期不证明该日任意时刻已经可得。 |
| `source_manifest.publication_precision` | 发布时间精度 | 枚举 | 1.1.0 必须 | 否 | 枚举=['instant', 'date', 'unknown'] | instant 有已核实的精确时刻；date 仅有日期，published_at 必须 null；unknown 两者均未知且为空。1.1.0 必填，与登记资料版本保持一致。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>source_manifest.schema_version · 契约版本</summary>

Schema 指针：`#/properties/schema_version`。

```json
{
  "enum": [
    "1.0.0",
    "1.1.0"
  ]
}
```

</details>

<details>
<summary>source_manifest.source_id · 资料系列标识</summary>

Schema 指针：`#/properties/source_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>source_manifest.revision · 修订号</summary>

Schema 指针：`#/properties/revision`。

```json
{
  "type": "integer",
  "minimum": 1
}
```

</details>

<details>
<summary>source_manifest.source_path · 资料文件路径</summary>

Schema 指针：`#/properties/source_path`。

```json
{
  "type": "string",
  "minLength": 1,
  "pattern": "^(?![A-Za-z][A-Za-z0-9+.-]*:)(?![/\\\\]).+"
}
```

</details>

<details>
<summary>source_manifest.source_kind · 来源类型</summary>

Schema 指针：`#/properties/source_kind`。

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
<summary>source_manifest.dataset_kind · 资料类别</summary>

Schema 指针：`#/properties/dataset_kind`。

```json
{
  "enum": [
    "financial",
    "market",
    "industry",
    "news",
    "company_action",
    "classification",
    "research_material",
    "other"
  ]
}
```

</details>

<details>
<summary>source_manifest.published_at · 精确发布时间</summary>

Schema 指针：`#/properties/published_at`。

```json
{
  "type": [
    "string",
    "null"
  ],
  "format": "date-time",
  "title": "精确发布时间",
  "description": "未知时为空，禁止从日期补造午夜时间"
}
```

</details>

<details>
<summary>source_manifest.available_at · 信息可得时间</summary>

Schema 指针：`#/properties/available_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>source_manifest.acquired_at · 资料获取时间</summary>

Schema 指针：`#/properties/acquired_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>source_manifest.effective_period · 资料覆盖或生效期间</summary>

Schema 指针：`#/properties/effective_period`。

```json
{
  "anyOf": [
    {
      "type": "null"
    },
    {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "start",
        "end"
      ],
      "properties": {
        "start": {
          "type": "string",
          "format": "date"
        },
        "end": {
          "type": "string",
          "format": "date"
        }
      }
    }
  ]
}
```

</details>

<details>
<summary>source_manifest.effective_period.start · 期间开始日期</summary>

Schema 指针：`#/properties/effective_period/anyOf/1/properties/start`。

```json
{
  "type": "string",
  "format": "date"
}
```

</details>

<details>
<summary>source_manifest.effective_period.end · 期间结束日期</summary>

Schema 指针：`#/properties/effective_period/anyOf/1/properties/end`。

```json
{
  "type": "string",
  "format": "date"
}
```

</details>

<details>
<summary>source_manifest.license_notes · 使用权及来源限制说明</summary>

Schema 指针：`#/properties/license_notes`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>source_manifest.quality_notes · 资料质量说明列表</summary>

Schema 指针：`#/properties/quality_notes`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  }
}
```

</details>

<details>
<summary>source_manifest.supersedes_revision · 被替代修订号</summary>

Schema 指针：`#/properties/supersedes_revision`。

```json
{
  "anyOf": [
    {
      "type": "integer",
      "minimum": 1
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>source_manifest.published_date · 发布日期</summary>

Schema 指针：`#/properties/published_date`。

```json
{
  "type": [
    "string",
    "null"
  ],
  "format": "date",
  "title": "发布日期",
  "description": "仅来自官方页面的日期证据；不替代首次观察时刻"
}
```

</details>

<details>
<summary>source_manifest.publication_precision · 发布时间精度</summary>

Schema 指针：`#/properties/publication_precision`。

```json
{
  "enum": [
    "instant",
    "date",
    "unknown"
  ],
  "title": "发布时间精度",
  "description": "明确区分精确时刻、日期和未知"
}
```

</details>

