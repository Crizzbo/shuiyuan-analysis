# OBJ-010 · assessment 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/assessment`。
- 引用位置（Schema 指针）：`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/lifecycle`；`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/supply_demand`；`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/earnings`；`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/credit`；`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/sentiment`；`#/$defs/step1_output/properties/segment_positions/items/properties/positions/properties/pricing`；`#/$defs/step2_output/properties/checks/properties/business_model`；`#/$defs/step2_output/properties/checks/properties/demand_growth`；`#/$defs/step2_output/properties/checks/properties/competition`；`#/$defs/step2_output/properties/checks/properties/financial_quality`；`#/$defs/step2_output/properties/checks/properties/cash_flow`；`#/$defs/step2_output/properties/checks/properties/debt_liquidity`；`#/$defs/step2_output/properties/checks/properties/governance`；`#/$defs/step2_output/properties/checks/properties/capital_allocation`；`#/$defs/step5_output/properties/company_quality`；`#/$defs/step5_output/properties/price_attractiveness`；`#/$defs/step5_output/properties/action_suitability`；`#/$defs/step5_output/properties/permanent_loss_risks/items`。
- 对象额外字段：禁止。
- 属性定义数：3（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `assessment.verdict` | 评估结论 | string | 是 | 否 | 最短字符=1 | 该评估对象的文字结论；含义取决于它所在的周期维度、基础检查或风险评估位置。当前无统一评分或状态枚举，不能把文字自动当作交易指令。 |
| `assessment.claim_refs` | 判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 支持本项评估结论的 claim.id 列表，至少一项；可引用事实、推断、假设、未知或不适用判断，具体适用性须复核。不是直接引用证据 ID。 |
| `assessment.limitations` | 本项评估局限 | array<string> | 是 | 否 | 至少项数=0 | 这项评估本身的局限、证据缺口或适用边界；无已知事项可填空数组。不会自动改变步骤状态。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>assessment.verdict · 评估结论</summary>

Schema 指针：`#/$defs/assessment/properties/verdict`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>assessment.claim_refs · 判断引用</summary>

Schema 指针：`#/$defs/assessment/properties/claim_refs`。

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
<summary>assessment.limitations · 本项评估局限</summary>

Schema 指针：`#/$defs/assessment/properties/limitations`。

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

