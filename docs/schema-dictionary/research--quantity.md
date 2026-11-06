# OBJ-002 · quantity 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/quantity`。
- 引用位置（Schema 指针）：`#/$defs/observation/properties/value/anyOf/0`；`#/$defs/calculation/properties/outputs/items`；`#/$defs/scenario/properties/intrinsic_value_per_share`。
- 对象额外字段：禁止。
- 属性定义数：3（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `quantity.value` | 数量数值 | number | 是 | 否 | 无显式附加结构约束 | 数量对象中的数值，必须有限；不能是字符串、布尔值、NaN 或 Infinity。 |
| `quantity.unit` | 计量单位 | string | 是 | 否 | 最短字符=1 | 明确实际单位，比例 ratio 用 0.2 表示 20%；价格用 currency_per_share。 |
| `quantity.currency` | 币种 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 金额币种，如 USD；非金额一般 null，金额和每股价格不可省略币种。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>quantity.value · 数量数值</summary>

Schema 指针：`#/$defs/quantity/properties/value`。

```json
{
  "type": "number"
}
```

</details>

<details>
<summary>quantity.unit · 计量单位</summary>

Schema 指针：`#/$defs/quantity/properties/unit`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>quantity.currency · 币种</summary>

Schema 指针：`#/$defs/quantity/properties/currency`。

```json
{
  "anyOf": [
    {
      "type": "string",
      "minLength": 1
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

