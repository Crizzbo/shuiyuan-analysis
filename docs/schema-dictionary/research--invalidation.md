# OBJ-029 · invalidation 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/invalidation`。
- 引用位置（Schema 指针）：`#/properties/invalidation_events/items`。
- 对象额外字段：禁止。
- 属性定义数：9（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `invalidation.id` | 失效事件标识 | string | 是 | 否 | 最短字符=1 | 当前研究中的失效事件唯一 ID；区别于计划中的 trigger.id，触发计划不会自动产生此事件。 |
| `invalidation.occurred_at` | 失效事件发生时间 | string | 是 | 否 | 格式=date-time | 触发结论失效的事件时间，不得晚于 recorded_at。 |
| `invalidation.reason` | 失效事件原因 | string | 是 | 否 | 最短字符=1 | 实际登记此次失效事件的原因，解释哪些新信息或条件改变导致原研究需要重做。不是验收结果理由。 |
| `invalidation.evidence_refs` | 证据引用 | array<string> | 是 | 否 | 项不能重复 | 支持此次实际失效事件的 evidence.id；不能直接写 trigger.id。 |
| `invalidation.earliest_step` | 最早受影响步骤 | 枚举 | 是 | 否 | 枚举=['S1', 'S2', 'S3', 'S4', 'S5', 'S6'] | 最早受影响步骤，从此步到 S6 必须全部纳入回退。 |
| `invalidation.affected_steps` | 受影响步骤列表 | array<枚举> | 是 | 否 | 至少项数=1；项不能重复 | 回退影响的全部连续后序步骤，不能只改 S2 而保留 S3—S6 有效。 |
| `invalidation.status` | 失效事件处理状态 | 枚举 | 是 | 否 | 枚举=['open', 'resolved'] | 实际失效事件的处理状态：open 尚未完成受影响步骤重研究；resolved 已按更高步骤版本完成重研究并记录解决时间。不是步骤状态，也不是 gate.result。 |
| `invalidation.baseline_versions` | 失效基线版本列表 | array<snapshot> | 是 | 否 | 至少项数=1 | 全部受影响步骤的旧版本，用于核对重新研究是否真正增版。 |
| `invalidation.resolved_at` | 失效事件解决时间 | string / null | 是 | 是 | 格式=date-time；无显式附加结构约束 | 重研究完成并解除回退的时间；open 时必须 null。 |

## 3. 关联对象

- [snapshot](research--snapshot.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>invalidation.id · 失效事件标识</summary>

Schema 指针：`#/$defs/invalidation/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>invalidation.occurred_at · 失效事件发生时间</summary>

Schema 指针：`#/$defs/invalidation/properties/occurred_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>invalidation.reason · 失效事件原因</summary>

Schema 指针：`#/$defs/invalidation/properties/reason`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>invalidation.evidence_refs · 证据引用</summary>

Schema 指针：`#/$defs/invalidation/properties/evidence_refs`。

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
<summary>invalidation.earliest_step · 最早受影响步骤</summary>

Schema 指针：`#/$defs/invalidation/properties/earliest_step`。

```json
{
  "enum": [
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6"
  ]
}
```

</details>

<details>
<summary>invalidation.affected_steps · 受影响步骤列表</summary>

Schema 指针：`#/$defs/invalidation/properties/affected_steps`。

```json
{
  "type": "array",
  "items": {
    "enum": [
      "S1",
      "S2",
      "S3",
      "S4",
      "S5",
      "S6"
    ]
  },
  "minItems": 1,
  "uniqueItems": true
}
```

</details>

<details>
<summary>invalidation.status · 失效事件处理状态</summary>

Schema 指针：`#/$defs/invalidation/properties/status`。

```json
{
  "enum": [
    "open",
    "resolved"
  ]
}
```

</details>

<details>
<summary>invalidation.baseline_versions · 失效基线版本列表</summary>

Schema 指针：`#/$defs/invalidation/properties/baseline_versions`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/snapshot"
  },
  "minItems": 1
}
```

</details>

<details>
<summary>invalidation.resolved_at · 失效事件解决时间</summary>

Schema 指针：`#/$defs/invalidation/properties/resolved_at`。

```json
{
  "anyOf": [
    {
      "type": "string",
      "format": "date-time"
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

