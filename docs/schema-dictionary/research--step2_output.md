# OBJ-012 · step2_output 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step2_output`。
- 引用位置（Schema 指针）：`#/$defs/step2/properties/output/anyOf/0`；`#/$defs/step2/allOf/0/then/properties/output`。
- 对象额外字段：禁止。
- 属性定义数：11（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step2_output.checks` | 基础研究检查项 | object | 是 | 否 | 不接受额外字段 | S2 必须填写的八项基础检查。 |
| `step2_output.checks.business_model` | 商业模式评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 收入、现金流、单位经济和资本需求的研究结论。 |
| `step2_output.checks.demand_growth` | 需求与增长评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 需求真实性、增长来源与可持续性。 |
| `step2_output.checks.competition` | 竞争格局评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 竞争格局、议价权、进入壁垒和护城河。 |
| `step2_output.checks.financial_quality` | 财务质量评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 会计质量、一次性项目、财务口径与报表风险。 |
| `step2_output.checks.cash_flow` | 现金流评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 经营现金转化、资本支出和现金流可持续性。 |
| `step2_output.checks.debt_liquidity` | 债务与流动性评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 债务结构、现金、到期、契约和流动性风险。 |
| `step2_output.checks.governance` | 公司治理评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 治理、关联交易、股权结构和管理层激励。 |
| `step2_output.checks.capital_allocation` | 资本配置评估 | assessment | 是 | 否 | 引用=#/$defs/assessment | 资本开支、并购、分红、回购及股权稀释的配置效果。 |
| `step2_output.thesis_claim_refs` | 投资论点判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 核心投资论点的判断 ID。 |
| `step2_output.critical_unknown_claim_refs` | 关键未知事项判断引用 | array<string> | 是 | 否 | 项不能重复 | S2 识别的、足以影响研究或决策的关键未知事项所对应的 claim.id。业务上应引用 unknown 判断；当前程序只核对 ID 存在，并在 S5 行动条件满足时要求该列表为空，未强制检查 kind。 |

## 3. 关联对象

- [assessment](research--assessment.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step2_output.checks · 基础研究检查项</summary>

Schema 指针：`#/$defs/step2_output/properties/checks`。

```json
{
  "type": "object",
  "properties": {
    "business_model": {
      "$ref": "#/$defs/assessment"
    },
    "demand_growth": {
      "$ref": "#/$defs/assessment"
    },
    "competition": {
      "$ref": "#/$defs/assessment"
    },
    "financial_quality": {
      "$ref": "#/$defs/assessment"
    },
    "cash_flow": {
      "$ref": "#/$defs/assessment"
    },
    "debt_liquidity": {
      "$ref": "#/$defs/assessment"
    },
    "governance": {
      "$ref": "#/$defs/assessment"
    },
    "capital_allocation": {
      "$ref": "#/$defs/assessment"
    }
  },
  "required": [
    "business_model",
    "demand_growth",
    "competition",
    "financial_quality",
    "cash_flow",
    "debt_liquidity",
    "governance",
    "capital_allocation"
  ],
  "additionalProperties": false
}
```

</details>

<details>
<summary>step2_output.checks.business_model · 商业模式评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/business_model`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.demand_growth · 需求与增长评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/demand_growth`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.competition · 竞争格局评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/competition`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.financial_quality · 财务质量评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/financial_quality`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.cash_flow · 现金流评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/cash_flow`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.debt_liquidity · 债务与流动性评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/debt_liquidity`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.governance · 公司治理评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/governance`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.checks.capital_allocation · 资本配置评估</summary>

Schema 指针：`#/$defs/step2_output/properties/checks/properties/capital_allocation`。

```json
{
  "$ref": "#/$defs/assessment"
}
```

</details>

<details>
<summary>step2_output.thesis_claim_refs · 投资论点判断引用</summary>

Schema 指针：`#/$defs/step2_output/properties/thesis_claim_refs`。

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
<summary>step2_output.critical_unknown_claim_refs · 关键未知事项判断引用</summary>

Schema 指针：`#/$defs/step2_output/properties/critical_unknown_claim_refs`。

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

