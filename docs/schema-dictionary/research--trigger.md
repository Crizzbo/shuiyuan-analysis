# OBJ-013 · trigger 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/trigger`。
- 引用位置（Schema 指针）：`#/$defs/step3_output/properties/invalidation_triggers/items`；`#/$defs/step6_output/properties/triggers/items`。
- 对象额外字段：禁止。
- 属性定义数：6（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `trigger.id` | 触发条件标识 | string | 是 | 否 | 最短字符=1 | 触发条件的身份标识，供人工跟踪和后续工具识别；当前研究校验没有检查触发器列表内 ID 唯一性，编写时应避免重复。 |
| `trigger.description` | 触发条件描述 | string | 是 | 否 | 最短字符=1 | 触发器的业务含义和范围。 |
| `trigger.metric_ids` | 指标标识列表 | array<string> | 是 | 否 | 项不能重复 | 用于观察此触发条件的指标定义 ID 列表；可为空，例如非数值的治理事件。不是当前观测值，程序不会据此自动取数。 |
| `trigger.condition_description` | 触发判定条件 | string | 是 | 否 | 最短字符=1 | 可核对的触发条件文字，包括事件或指标变化及判断口径；当前不是机器可执行表达式，也不会自动判断条件是否成立。未验证行业阈值应说明其状态。 |
| `trigger.claim_refs` | 判断引用 | array<string> | 是 | 否 | 项不能重复 | 支撑该评估、事件或触发机制的 claims ID；不直接写散文替代引用。 |
| `trigger.target_steps` | 拟重新检查步骤 | array<枚举> | 是 | 否 | 至少项数=1；项不能重复 | 条件成立后拟重新检查的步骤 ID，可选 S1—S5；这是计划，不自动生成 invalidation_events。实际登记失效事件时须按最早受影响步骤覆盖至 S6。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>trigger.id · 触发条件标识</summary>

Schema 指针：`#/$defs/trigger/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>trigger.description · 触发条件描述</summary>

Schema 指针：`#/$defs/trigger/properties/description`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>trigger.metric_ids · 指标标识列表</summary>

Schema 指针：`#/$defs/trigger/properties/metric_ids`。

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
<summary>trigger.condition_description · 触发判定条件</summary>

Schema 指针：`#/$defs/trigger/properties/condition_description`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>trigger.claim_refs · 判断引用</summary>

Schema 指针：`#/$defs/trigger/properties/claim_refs`。

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
<summary>trigger.target_steps · 拟重新检查步骤</summary>

Schema 指针：`#/$defs/trigger/properties/target_steps`。

```json
{
  "type": "array",
  "items": {
    "enum": [
      "S1",
      "S2",
      "S3",
      "S4",
      "S5"
    ]
  },
  "minItems": 1,
  "uniqueItems": true
}
```

</details>

