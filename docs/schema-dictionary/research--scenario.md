# OBJ-015 · scenario 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/scenario`。
- 引用位置（Schema 指针）：`#/$defs/step4_output/properties/scenarios/items`。
- 对象额外字段：禁止。
- 属性定义数：5（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `scenario.name` | 估值情景名称 | 枚举 | 是 | 否 | 枚举=['bear', 'base', 'bull'] | 估值情景名称，固定为 bear、base 或 bull；同一步骤必须包含三个不同情景。 |
| `scenario.assumption_refs` | 假设引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 引用 claims 中 kind=assumption 的对象；不允许循环或引用 fact 充当假设。 |
| `scenario.intrinsic_value_per_share` | 情景每股内在价值 | quantity | 是 | 否 | 引用=#/$defs/quantity | 情景每股价值数量对象，币种与基准价一致且与计算结果对应。 |
| `scenario.calculation_refs` | 计算引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 引用 calculations 表的 ID，不填方法名或代码路径。 |
| `scenario.probability` | 情景概率 | number / null | 是 | 是 | 最小=0；最大=1；无显式附加结构约束 | 对该估值情景的权重判断，范围 0—1；不是收益率或置信区间。没有依据时应显式填 null，Schema 不提供默认值；S4 完成时三个概率须全部 null，或全部有值、合计为 1 且有依据引用。 |

## 3. 关联对象

- [quantity](research--quantity.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>scenario.name · 估值情景名称</summary>

Schema 指针：`#/$defs/scenario/properties/name`。

```json
{
  "enum": [
    "bear",
    "base",
    "bull"
  ]
}
```

</details>

<details>
<summary>scenario.assumption_refs · 假设引用</summary>

Schema 指针：`#/$defs/scenario/properties/assumption_refs`。

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
<summary>scenario.intrinsic_value_per_share · 情景每股内在价值</summary>

Schema 指针：`#/$defs/scenario/properties/intrinsic_value_per_share`。

```json
{
  "$ref": "#/$defs/quantity"
}
```

</details>

<details>
<summary>scenario.calculation_refs · 计算引用</summary>

Schema 指针：`#/$defs/scenario/properties/calculation_refs`。

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
<summary>scenario.probability · 情景概率</summary>

Schema 指针：`#/$defs/scenario/properties/probability`。

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

