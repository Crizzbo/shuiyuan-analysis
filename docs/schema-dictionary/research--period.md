# OBJ-003 · period 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/period`。
- 引用位置（Schema 指针）：`#/$defs/observation/properties/period`；`#/$defs/segment/properties/weight_period/anyOf/0`；`#/$defs/step3_output/properties/catalysts/items/properties/expected_window`；`#/$defs/step4_output/properties/valuation_horizon`；`#/$defs/step4_output/properties/investment_horizon`。
- 对象额外字段：禁止。
- 属性定义数：3（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `period.start` | 期间开始日期 | string | 是 | 否 | 格式=date | 该期间的开始日期。含义随引用位置变化：观测为历史覆盖开始，权重为占比口径期间开始，催化和估值可为未来窗口开始。历史观测校验 start ≤ end；其他窗口的业务顺序须人工核对。 |
| `period.end` | 期间结束日期 | string | 是 | 否 | 格式=date | 该期间的结束日期。仅历史 observation.period 强制不晚于 as_of 日期；不能把这个要求套到催化、估值或投资窗口。其他期间并未统一执行起止顺序检查。 |
| `period.basis` | 期间口径 | 枚举 | 是 | 否 | 枚举=['quarter', 'year', 'ttm', 'point_in_time', 'custom'] | 期间口径：quarter 单季，year 年度，ttm 滚动十二个月，point_in_time 单时点，custom 自定义区间。程序不根据标签推算日期长度，日期与口径的一致性须复核。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>period.start · 期间开始日期</summary>

Schema 指针：`#/$defs/period/properties/start`。

```json
{
  "type": "string",
  "format": "date"
}
```

</details>

<details>
<summary>period.end · 期间结束日期</summary>

Schema 指针：`#/$defs/period/properties/end`。

```json
{
  "type": "string",
  "format": "date"
}
```

</details>

<details>
<summary>period.basis · 期间口径</summary>

Schema 指针：`#/$defs/period/properties/basis`。

```json
{
  "enum": [
    "quarter",
    "year",
    "ttm",
    "point_in_time",
    "custom"
  ]
}
```

</details>

