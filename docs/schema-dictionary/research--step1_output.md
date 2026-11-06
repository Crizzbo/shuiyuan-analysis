# OBJ-011 · step1_output 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step1_output`。
- 引用位置（Schema 指针）：`#/$defs/step1/properties/output/anyOf/0`；`#/$defs/step1/allOf/0/then/properties/output`。
- 对象额外字段：禁止。
- 属性定义数：12（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step1_output.segment_positions` | 分部周期定位列表 | array<object> | 是 | 否 | 至少项数=1 | 所有分部的周期定位，每个登记分部必须且仅有一项。 |
| `step1_output.segment_positions[].segment_id` | 业务分部标识 | string | 是 | 否 | 最短字符=1 | 引用当前研究 subject.segments 中的分部 ID；可空性以本字段结构定义为准。 |
| `step1_output.segment_positions[].industry_rule_id` | 行业规则标识 | string | 是 | 否 | 最短字符=1 | 该分部周期定位采用的行业规则键；现实现以 industry_id 作为规则键，必须属于该分部 industry_ids。不是独立规则修订号，也不表示规则已统计验证。 |
| `step1_output.segment_positions[].positions` | 周期维度评估 | object | 是 | 否 | 不接受额外字段 | 六个独立状态，不要求同步；每个状态用 assessment 表示。 |
| `step1_output.segment_positions[].positions.lifecycle` | 长期生命周期评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 该分部产品或行业的长期发展阶段评估（assessment），应说明市场范围、渗透率口径及阶段依据；与供需、盈利等周期分别记录，不能全部归为同一周期标签。 |
| `step1_output.segment_positions[].positions.supply_demand` | 供需与资本周期评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 供需与产能/库存周期状态，区别于长期生命周期。 |
| `step1_output.segment_positions[].positions.earnings` | 盈利周期评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 盈利周期与正常化利润状态，不能只看当前 PE。 |
| `step1_output.segment_positions[].positions.credit` | 信贷与融资评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 融资供给、条件、再融资及公司偿债环境。 |
| `step1_output.segment_positions[].positions.sentiment` | 情绪与风险偏好评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 市场情绪与风险偏好，恐惧本身不是买入依据。 |
| `step1_output.segment_positions[].positions.pricing` | 定价与预期评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 价格已反映的市场预期与定价状态。 |
| `step1_output.research_priorities` | 研究重点列表 | array<string> | 是 | 否 | 至少项数=1 | 下一步重点研究问题，至少一项，不取消其他基础检查。 |
| `step1_output.conclusion_claim_refs` | 定位结论判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 支撑 S1 整体定位结论的 claim.id，区别于每个周期维度 assessment.claim_refs。 |

## 3. 关联对象

- [assessment](research--assessment.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step1_output.segment_positions · 分部周期定位列表</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions`。

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "segment_id": {
        "type": "string",
        "minLength": 1
      },
      "industry_rule_id": {
        "type": "string",
        "minLength": 1
      },
      "positions": {
        "type": "object",
        "properties": {
          "lifecycle": {
            "$ref": "#/$defs/assessment"
          },
          "supply_demand": {
            "$ref": "#/$defs/assessment"
          },
          "earnings": {
            "$ref": "#/$defs/assessment"
          },
          "credit": {
            "$ref": "#/$defs/assessment"
          },
          "sentiment": {
            "$ref": "#/$defs/assessment"
          },
          "pricing": {
            "$ref": "#/$defs/assessment"
          }
        },
        "required": [
          "lifecycle",
          "supply_demand",
          "earnings",
          "credit",
          "sentiment",
          "pricing"
        ],
        "additionalProperties": false
      }
    },
    "required": [
      "segment_id",
      "industry_rule_id",
      "positions"
    ],
    "additionalProperties": false
  },
  "minItems": 1
}
```

</details>

<details>
<summary>step1_output.segment_positions[].segment_id · 业务分部标识</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/segment_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step1_output.segment_positions[].industry_rule_id · 行业规则标识</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/industry_rule_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions · 周期维度评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions`。

```json
{
  "type": "object",
  "properties": {
    "lifecycle": {
      "$ref": "#/$defs/assessment"
    },
    "supply_demand": {
      "$ref": "#/$defs/assessment"
    },
    "earnings": {
      "$ref": "#/$defs/assessment"
    },
    "credit": {
      "$ref": "#/$defs/assessment"
    },
    "sentiment": {
      "$ref": "#/$defs/assessment"
    },
    "pricing": {
      "$ref": "#/$defs/assessment"
    }
  },
  "required": [
    "lifecycle",
    "supply_demand",
    "earnings",
    "credit",
    "sentiment",
    "pricing"
  ],
  "additionalProperties": false
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions.lifecycle · 长期生命周期评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/lifecycle`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions.supply_demand · 供需与资本周期评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/supply_demand`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions.earnings · 盈利周期评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/earnings`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions.credit · 信贷与融资评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/credit`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions.sentiment · 情绪与风险偏好评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/sentiment`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step1_output.segment_positions[].positions.pricing · 定价与预期评估</summary>

Schema 指针：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/pricing`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step1_output.research_priorities · 研究重点列表</summary>

Schema 指针：`#/$defs/step1_output/properties/research_priorities`。

```json
{
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "minItems": 1
}
```

</details>

<details>
<summary>step1_output.conclusion_claim_refs · 定位结论判断引用</summary>

Schema 指针：`#/$defs/step1_output/properties/conclusion_claim_refs`。

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

