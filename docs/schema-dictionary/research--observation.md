# OBJ-005 · observation 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/observation`。
- 引用位置（Schema 指针）：`#/properties/observations/items`。
- 对象额外字段：禁止。
- 属性定义数：10（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `observation.id` | 观测标识 | string | 是 | 否 | 最短字符=1 | 对象在所属登记表或明确作用域中的唯一 ID；不是显示名称。 |
| `observation.metric_id` | 指标标识 | string | 是 | 否 | 最短字符=1 | 项目指标字典中已登记的指标 ID；不能填中文指标名或临时自造 ID。 |
| `observation.segment_id` | 业务分部标识 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 当前 subject.segments 中的分部 ID；观测为公司合并层时允许 null。 |
| `observation.period` | 观测期间 | period | 是 | 否 | 引用=#/$defs/period | 这条历史观测覆盖的期间或时点，引用 period 对象；当前校验要求 start ≤ end ≤ as_of 的日期部分。未来预测窗口不应写成历史观测。 |
| `observation.available_at` | 信息可得时间 | string | 是 | 否 | 格式=date-time | 这条观测及其当前口径的可得时点，不是经营期间末日；有值时不得早于其支持证据的可得时点，也不得晚于研究截止时点。 |
| `observation.value` | 观测数量对象 | quantity / null | 是 | 是 | 引用=#/$defs/quantity；无显式附加结构约束 | 观测结果：有值时填 quantity 对象，包含 value、unit、currency；缺失时填 JSON null，并在 missing_reason 说明原因。这里不能直接填裸数字。 |
| `observation.missing_reason` | 数值缺失原因 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 缺失数值的原因；value 非 null 时这里必须 null。 |
| `observation.accounting_basis` | 会计及统计口径 | string | 是 | 否 | 最短字符=1 | 观测的会计及统计口径，如 GAAP／调整后、合并／分部、单季／TTM。非财务观测应说明相应采样或价格口径；没有会计口径时说明不适用，而非假定全部口径不适用。 |
| `observation.comparability_notes` | 可比性说明 | string | 是 | 否 | 最短字符=1 | 说明该观测与历史、同业或其他口径比较时的限制及调整，例如并购范围、汇率、复权、客户定义变化；字符串必填，无已知问题应明确说明。 |
| `observation.evidence_refs` | 证据引用 | array<string> | 是 | 否 | 项不能重复 | 引用 evidence 表中 ID；不直接填文件路径或把空数组当作已取证。 |

## 3. 关联对象

- [period](research--period.md)：本表引用的公共对象定义。
- [quantity](research--quantity.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>observation.id · 观测标识</summary>

Schema 指针：`#/$defs/observation/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>observation.metric_id · 指标标识</summary>

Schema 指针：`#/$defs/observation/properties/metric_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>observation.segment_id · 业务分部标识</summary>

Schema 指针：`#/$defs/observation/properties/segment_id`。

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

<details>
<summary>observation.period · 观测期间</summary>

Schema 指针：`#/$defs/observation/properties/period`。

```json
{
  "$ref": "#/$defs/period"
}
```

</details>

<details>
<summary>observation.available_at · 信息可得时间</summary>

Schema 指针：`#/$defs/observation/properties/available_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>observation.value · 观测数量对象</summary>

Schema 指针：`#/$defs/observation/properties/value`。

```json
{
  "anyOf": [
    {
      "$ref": "#/$defs/quantity"
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>observation.missing_reason · 数值缺失原因</summary>

Schema 指针：`#/$defs/observation/properties/missing_reason`。

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

<details>
<summary>observation.accounting_basis · 会计及统计口径</summary>

Schema 指针：`#/$defs/observation/properties/accounting_basis`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>observation.comparability_notes · 可比性说明</summary>

Schema 指针：`#/$defs/observation/properties/comparability_notes`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>observation.evidence_refs · 证据引用</summary>

Schema 指针：`#/$defs/observation/properties/evidence_refs`。

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

