# OBJ-016 · step4_output 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step4_output`。
- 引用位置（Schema 指针）：`#/$defs/step4/properties/output/anyOf/0`；`#/$defs/step4/allOf/0/then/properties/output`。
- 对象额外字段：禁止。
- 属性定义数：12（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step4_output.valuation_method` | 估值方法 | string | 是 | 否 | 最短字符=1 | 最终采用的估值方法及业务适配，不只填 DCF 三个字。 |
| `step4_output.applicability_claim_refs` | 估值适用性判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 说明估值模型为什么适用的判断 ID。 |
| `step4_output.price_observation_ref` | 基准价格观测引用 | string | 是 | 否 | 最短字符=1 | market_price 的有效观测 ID；币种、每股口径与估值一致。 |
| `step4_output.scenarios` | 估值情景列表 | array<scenario> | 是 | 否 | 至少项数=3 | 恰好 bear/base/bull 三个情景；不等于三种任意概率预测。 |
| `step4_output.probability_basis_claim_refs` | 情景概率依据判断引用 | array<string> | 是 | 否 | 项不能重复 | 解释三情景概率赋值依据的 claim.id。程序只在使用概率时检查非空及引用有效；未验证概率校准，也未限定这些判断必须来自统计模型。 |
| `step4_output.crosscheck_calculation_refs` | 交叉核对计算引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 用于以另一口径或方法交叉核对估值的 calculation.id。程序仅要求相关计算 checked，且此列表与敏感性列表不完全相同（按列表比较）；独立性及避免通过改变顺序规避检查须人工复核。 |
| `step4_output.sensitivity_calculation_refs` | 敏感性分析计算引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 用于检验估值对关键假设变化敏感程度的 calculation.id；不是额外概率情景，也不意味着程序已执行敏感性分析。 |
| `step4_output.market_expectation_claim_refs` | 市场预期判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 当前价格隐含或市场共识预期的判断依据。 |
| `step4_output.value_bridge_claim_refs` | 价值桥接判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 企业/资产价值到股权与每股价值的桥接说明；金融股避免重复扣债。 |
| `step4_output.valuation_horizon` | 估值评估期间 | period | 是 | 否 | 引用=#/$defs/period | 估值采用的预测或价值评估期间（period），可包含未来日期；不是历史指标期间。与投资期限分开登记，当前程序未检查两种期限之间的业务一致性。 |
| `step4_output.investment_horizon` | 投资判断期间 | period | 是 | 否 | 引用=#/$defs/period | 本次投资判断对应的起止期间（period），区别于估值模型预测区间；应人工核对 research.investment_horizon_months，程序未自动换算或强制一致。 |
| `step4_output.limitations` | 估值局限 | array<string> | 是 | 否 | 至少项数=0 | S4 估值结果的适用边界、假设限制及尚未解决的问题；不是原始证据自身的缺陷列表。 |

## 3. 关联对象

- [period](research--period.md)：本表引用的公共对象定义。
- [scenario](research--scenario.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step4_output.valuation_method · 估值方法</summary>

Schema 指针：`#/$defs/step4_output/properties/valuation_method`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step4_output.applicability_claim_refs · 估值适用性判断引用</summary>

Schema 指针：`#/$defs/step4_output/properties/applicability_claim_refs`。

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
<summary>step4_output.price_observation_ref · 基准价格观测引用</summary>

Schema 指针：`#/$defs/step4_output/properties/price_observation_ref`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step4_output.scenarios · 估值情景列表</summary>

Schema 指针：`#/$defs/step4_output/properties/scenarios`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/scenario"
  },
  "minItems": 3
}
```

</details>

<details>
<summary>step4_output.probability_basis_claim_refs · 情景概率依据判断引用</summary>

Schema 指针：`#/$defs/step4_output/properties/probability_basis_claim_refs`。

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
<summary>step4_output.crosscheck_calculation_refs · 交叉核对计算引用</summary>

Schema 指针：`#/$defs/step4_output/properties/crosscheck_calculation_refs`。

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
<summary>step4_output.sensitivity_calculation_refs · 敏感性分析计算引用</summary>

Schema 指针：`#/$defs/step4_output/properties/sensitivity_calculation_refs`。

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
<summary>step4_output.market_expectation_claim_refs · 市场预期判断引用</summary>

Schema 指针：`#/$defs/step4_output/properties/market_expectation_claim_refs`。

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
<summary>step4_output.value_bridge_claim_refs · 价值桥接判断引用</summary>

Schema 指针：`#/$defs/step4_output/properties/value_bridge_claim_refs`。

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
<summary>step4_output.valuation_horizon · 估值评估期间</summary>

Schema 指针：`#/$defs/step4_output/properties/valuation_horizon`。

```json
{
  "$ref": "#/$defs/period"
}
```

</details>

<details>
<summary>step4_output.investment_horizon · 投资判断期间</summary>

Schema 指针：`#/$defs/step4_output/properties/investment_horizon`。

```json
{
  "$ref": "#/$defs/period"
}
```

</details>

<details>
<summary>step4_output.limitations · 估值局限</summary>

Schema 指针：`#/$defs/step4_output/properties/limitations`。

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

