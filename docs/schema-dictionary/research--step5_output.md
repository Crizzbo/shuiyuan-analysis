# OBJ-017 · step5_output 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step5_output`。
- 引用位置（Schema 指针）：`#/$defs/step5/properties/output/anyOf/0`；`#/$defs/step5/allOf/0/then/properties/output`。
- 对象额外字段：禁止。
- 属性定义数：13（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step5_output.decision` | 研究决策结论 | 枚举 | 是 | 否 | 枚举=['watch', 'action_conditions_met', 'conditions_not_met', 'unable_to_judge'] | watch 观察；action_conditions_met 满足条件；conditions_not_met 不满足；unable_to_judge 暂无法判断。 |
| `step5_output.company_quality` | 公司质量评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 独立评估公司质量，不与便宜程度混为一个总分。 |
| `step5_output.price_attractiveness` | 价格吸引力评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 当前价格相对价值与情景风险的吸引力。 |
| `step5_output.action_suitability` | 行动适宜性评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 指定期限与风险约束下的行动适宜性，缺组合信息需限制结论。 |
| `step5_output.permanent_loss_risks` | 永久资本损失风险评估列表 | array<assessment> | 是 | 否 | 至少项数=1 | 可能造成永久资本损失的风险评估列表，每项是 assessment 对象（结论、判断引用及局限），至少一项；不能直接填风险字符串数组。 |
| `step5_output.entry_conditions` | 进入或加仓条件列表 | array<string> | 是 | 否 | 至少项数=1 | 进入或加仓前拟要求满足的条件文字列表。当前不含条件状态或表达式字段，程序不会自动核验条件或下单。 |
| `step5_output.exit_conditions` | 退出或减仓条件列表 | array<string> | 是 | 否 | 至少项数=1 | 拟退出或减仓的条件文字列表，包括论点失效、风险约束或价值变化；不等同于自动止损委托。 |
| `step5_output.portfolio_assessment` | 组合评估范围状态 | 枚举 | 是 | 否 | 枚举=['not_assessed', 'assessed'] | 组合层评估范围：not_assessed 表示未完成，position_fraction 必须 null 且组合计算引用为空；assessed 表示声明已评估并必须提供组合证据及计算。程序不验证全部组合风险维度已覆盖。 |
| `step5_output.portfolio_evidence_refs` | 组合评估证据引用 | array<string> | 是 | 否 | 项不能重复 | 组合资金、持仓、限制等证据；需要使用项目内资料。 |
| `step5_output.portfolio_calculation_refs` | 组合评估计算引用 | array<string> | 是 | 否 | 项不能重复 | 集中度、相关性、压力等组合计算引用。 |
| `step5_output.position_fraction` | 建议仓位占比 | number / null | 是 | 是 | 最小=0；最大=1；无显式附加结构约束 | 研究记录提出的目标证券仓位占比（0—1），不是分部权重或已成交持仓。未评估组合必须 null；已评估也允许 null。当前未定义组合资产分母及现金、杠杆口径，给出数值时须在研究说明中交代。 |
| `step5_output.validated_rule_refs` | 已验证行业规则引用 | array<string> | 是 | 否 | 项不能重复 | 支持行动条件判断的已验证行业规则键；现实现使用 statistical_validation_status=validated 的 industry_id。仅在 decision=action_conditions_met 时强制检查非空及已验证状态；不代表代码自动完成统计验证。 |
| `step5_output.decision_claim_refs` | 决策依据判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 最终结果与条件的判断依据。 |

## 3. 关联对象

- [assessment](research--assessment.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step5_output.decision · 研究决策结论</summary>

Schema 指针：`#/$defs/step5_output/properties/decision`。

```json
{
  "enum": [
    "watch",
    "action_conditions_met",
    "conditions_not_met",
    "unable_to_judge"
  ]
}
```

</details>

<details>
<summary>step5_output.company_quality · 公司质量评估</summary>

Schema 指针：`#/$defs/step5_output/properties/company_quality`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step5_output.price_attractiveness · 价格吸引力评估</summary>

Schema 指针：`#/$defs/step5_output/properties/price_attractiveness`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step5_output.action_suitability · 行动适宜性评估</summary>

Schema 指针：`#/$defs/step5_output/properties/action_suitability`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step5_output.permanent_loss_risks · 永久资本损失风险评估列表</summary>

Schema 指针：`#/$defs/step5_output/properties/permanent_loss_risks`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/assessment"
  },
  "minItems": 1
}
```

</details>

<details>
<summary>step5_output.entry_conditions · 进入或加仓条件列表</summary>

Schema 指针：`#/$defs/step5_output/properties/entry_conditions`。

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
<summary>step5_output.exit_conditions · 退出或减仓条件列表</summary>

Schema 指针：`#/$defs/step5_output/properties/exit_conditions`。

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
<summary>step5_output.portfolio_assessment · 组合评估范围状态</summary>

Schema 指针：`#/$defs/step5_output/properties/portfolio_assessment`。

```json
{
  "enum": [
    "not_assessed",
    "assessed"
  ]
}
```

</details>

<details>
<summary>step5_output.portfolio_evidence_refs · 组合评估证据引用</summary>

Schema 指针：`#/$defs/step5_output/properties/portfolio_evidence_refs`。

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
<summary>step5_output.portfolio_calculation_refs · 组合评估计算引用</summary>

Schema 指针：`#/$defs/step5_output/properties/portfolio_calculation_refs`。

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
<summary>step5_output.position_fraction · 建议仓位占比</summary>

Schema 指针：`#/$defs/step5_output/properties/position_fraction`。

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
<summary>step5_output.validated_rule_refs · 已验证行业规则引用</summary>

Schema 指针：`#/$defs/step5_output/properties/validated_rule_refs`。

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
<summary>step5_output.decision_claim_refs · 决策依据判断引用</summary>

Schema 指针：`#/$defs/step5_output/properties/decision_claim_refs`。

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

