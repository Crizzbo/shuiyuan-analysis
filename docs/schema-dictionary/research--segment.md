# OBJ-008 · segment 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/segment`。
- 引用位置（Schema 指针）：`#/$defs/subject/properties/segments/items`。
- 对象额外字段：禁止。
- 属性定义数：10（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `segment.id` | 业务分部标识 | string | 是 | 否 | 最短字符=1 | 对象在所属登记表或明确作用域中的唯一 ID；不是显示名称。 |
| `segment.name` | 业务分部名称 | string | 是 | 否 | 最短字符=1 | 业务分部的显示名称；与分部稳定 ID 分开记录。 |
| `segment.industry_ids` | 行业标识列表 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 内部行业字典 ID 列表，必须为研究行业节点而非板块 ID。 |
| `segment.business_model_ids` | 商业模式标识列表 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 商业模式字典 ID 列表；可以多模式并存。 |
| `segment.classification_evidence_refs` | 分类证据引用 | array<string> | 是 | 否 | 项不能重复 | 支持分部行业与商业模式归类的证据 ID；S1 完成必须有依据。 |
| `segment.subindustry_description` | 细分业务描述 | string | 是 | 否 | 最短字符=1 | 分部业务的细分范围、地区、客户或产品口径；落实行业要求的细分。 |
| `segment.weight_basis` | 分部权重口径 | 枚举 | 是 | 否 | 枚举=['revenue', 'operating_profit', 'assets', 'unknown'] | 计算该分部占比采用的分母口径：revenue 收入、operating_profit 营业利润、assets 资产；unknown 表示口径未知。跨分部汇总前须人工核对期间、分母及抵销，程序未校验统一口径或合计为 1。 |
| `segment.weight` | 分部占比 | number / null | 是 | 是 | 最小=0；最大=1；无显式附加结构约束 | 该分部在 weight_basis 指定口径下的占比，范围 0—1；不是评分、行业概率或仓位。无法可靠确定时填 null。营业利润占比遇到负利润或超过 1 时，本版结构无法直接表达，不应强行改成合规数字。 |
| `segment.weight_period` | 分部权重对应期间 | period / null | 是 | 是 | 引用=#/$defs/period；无显式附加结构约束 | 权重对应期间；已知权重必须填 period。 |
| `segment.weight_evidence_refs` | 分部权重证据引用 | array<string> | 是 | 否 | 项不能重复 | 支持分部权重数值及分母口径的 evidence.id。可与分类证据引用同一资料，只要资料实际支持两项内容；weight 非 null 时必须有权重依据。 |

## 3. 关联对象

- [period](research--period.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>segment.id · 业务分部标识</summary>

Schema 指针：`#/$defs/segment/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>segment.name · 业务分部名称</summary>

Schema 指针：`#/$defs/segment/properties/name`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>segment.industry_ids · 行业标识列表</summary>

Schema 指针：`#/$defs/segment/properties/industry_ids`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "uniqueItems": true,
  "minItems": 1
}
```

</details>

<details>
<summary>segment.business_model_ids · 商业模式标识列表</summary>

Schema 指针：`#/$defs/segment/properties/business_model_ids`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "uniqueItems": true,
  "minItems": 1
}
```

</details>

<details>
<summary>segment.classification_evidence_refs · 分类证据引用</summary>

Schema 指针：`#/$defs/segment/properties/classification_evidence_refs`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "uniqueItems": true
}
```

</details>

<details>
<summary>segment.subindustry_description · 细分业务描述</summary>

Schema 指针：`#/$defs/segment/properties/subindustry_description`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>segment.weight_basis · 分部权重口径</summary>

Schema 指针：`#/$defs/segment/properties/weight_basis`。

```json
{
  "enum": [
    "revenue",
    "operating_profit",
    "assets",
    "unknown"
  ]
}
```

</details>

<details>
<summary>segment.weight · 分部占比</summary>

Schema 指针：`#/$defs/segment/properties/weight`。

```json
{
  "anyOf": [
    {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>segment.weight_period · 分部权重对应期间</summary>

Schema 指针：`#/$defs/segment/properties/weight_period`。

```json
{
  "anyOf": [
    {
      "$ref": "#/$defs/period"
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>segment.weight_evidence_refs · 分部权重证据引用</summary>

Schema 指针：`#/$defs/segment/properties/weight_evidence_refs`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "uniqueItems": true
}
```

</details>

