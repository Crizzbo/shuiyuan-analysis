# OBJ-014 · step3_output 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step3_output`。
- 引用位置（Schema 指针）：`#/$defs/step3/properties/output/anyOf/0`；`#/$defs/step3/allOf/0/then/properties/output`。
- 对象额外字段：禁止。
- 属性定义数：14（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step3_output.catalysts` | 催化事件列表 | array<object> | 是 | 否 | 至少项数=0 | 具体催化事件清单；没有可靠事件时用空数组并填原因。 |
| `step3_output.catalysts[].id` | 催化事件标识 | string | 是 | 否 | 最短字符=1 | S3 某项催化事件的身份标识，区别于 evidence.id 和 claim.id；当前程序未检查催化事件列表内该 ID 的唯一性。 |
| `step3_output.catalysts[].event` | 催化事件内容 | string | 是 | 否 | 最短字符=1 | 可识别的事件，不用笼统利好代替。 |
| `step3_output.catalysts[].transmission` | 事件传导机制 | string | 是 | 否 | 最短字符=1 | 该催化事件影响经营、现金流或市场预期的传导机制文字；不是已实现收益或数值计算结果。 |
| `step3_output.catalysts[].expected_window` | 事件预期窗口 | period | 是 | 否 | 引用=#/$defs/period | 催化剂预期发生或验证窗口，允许未来时间。 |
| `step3_output.catalysts[].claim_refs` | 判断引用 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 支持该催化事件及其传导机制的 claim.id 列表；不是事件原文文件路径。 |
| `step3_output.no_catalyst_reason` | 无催化事件原因 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 没有具体催化剂的原因；存在催化剂时必须 null。 |
| `step3_output.monitoring_indicators` | 跟踪指标列表 | array<object> | 是 | 否 | 至少项数=1 | 需要持续验证的指标、更新频率及基线。 |
| `step3_output.monitoring_indicators[].metric_id` | 指标标识 | string | 是 | 否 | 最短字符=1 | 项目指标字典中已登记的指标 ID；不能填中文指标名或临时自造 ID。 |
| `step3_output.monitoring_indicators[].rationale` | 指标选择理由 | string | 是 | 否 | 最短字符=1 | 选取该指标的因果理由，解释其对应假设。 |
| `step3_output.monitoring_indicators[].cadence` | 计划更新频率 | string | 是 | 否 | 最短字符=1 | 计划更新频率，按资料实际发布规律填写，不承诺尚未实现的自动任务。 |
| `step3_output.monitoring_indicators[].baseline_observation_refs` | 基线观测引用 | array<string> | 是 | 否 | 项不能重复 | 作为该跟踪指标比较基线的 observation.id，可有多条以表达历史区间；不等于一个默认阈值。无基线时填空数组并解释 missing_baseline_reason。 |
| `step3_output.monitoring_indicators[].missing_baseline_reason` | 基线缺失原因 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 基线缺失原因；有基线时必须 null。 |
| `step3_output.invalidation_triggers` | 论点失效触发条件列表 | array<trigger> | 是 | 否 | 至少项数=1 | 原论点失效或需要重研究的条件。 |

## 3. 关联对象

- [period](research--period.md)：本表引用的公共对象定义。
- [trigger](research--trigger.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step3_output.catalysts · 催化事件列表</summary>

Schema 指针：`#/$defs/step3_output/properties/catalysts`。

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "id": {
        "type": "string",
        "minLength": 1
      },
      "event": {
        "type": "string",
        "minLength": 1
      },
      "transmission": {
        "type": "string",
        "minLength": 1
      },
      "expected_window": {
        "$ref": "#/$defs/period"
      },
      "claim_refs": {
        "type": "array",
        "items": {
          "type": "string",
          "minLength": 1
        },
        "uniqueItems": true,
        "minItems": 1
      }
    },
    "required": [
      "id",
      "event",
      "transmission",
      "expected_window",
      "claim_refs"
    ],
    "additionalProperties": false
  },
  "minItems": 0
}
```

</details>

<details>
<summary>step3_output.catalysts[].id · 催化事件标识</summary>

Schema 指针：`#/$defs/step3_output/properties/catalysts/items/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step3_output.catalysts[].event · 催化事件内容</summary>

Schema 指针：`#/$defs/step3_output/properties/catalysts/items/properties/event`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step3_output.catalysts[].transmission · 事件传导机制</summary>

Schema 指针：`#/$defs/step3_output/properties/catalysts/items/properties/transmission`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step3_output.catalysts[].expected_window · 事件预期窗口</summary>

Schema 指针：`#/$defs/step3_output/properties/catalysts/items/properties/expected_window`。

```json
{
  "$ref": "#/$defs/period"
}
```

</details>

<details>
<summary>step3_output.catalysts[].claim_refs · 判断引用</summary>

Schema 指针：`#/$defs/step3_output/properties/catalysts/items/properties/claim_refs`。

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
<summary>step3_output.no_catalyst_reason · 无催化事件原因</summary>

Schema 指针：`#/$defs/step3_output/properties/no_catalyst_reason`。

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
<summary>step3_output.monitoring_indicators · 跟踪指标列表</summary>

Schema 指针：`#/$defs/step3_output/properties/monitoring_indicators`。

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "metric_id": {
        "type": "string",
        "minLength": 1
      },
      "rationale": {
        "type": "string",
        "minLength": 1
      },
      "cadence": {
        "type": "string",
        "minLength": 1
      },
      "baseline_observation_refs": {
        "type": "array",
        "items": {
          "type": "string",
          "minLength": 1
        },
        "uniqueItems": true
      },
      "missing_baseline_reason": {
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
    },
    "required": [
      "metric_id",
      "rationale",
      "cadence",
      "baseline_observation_refs",
      "missing_baseline_reason"
    ],
    "additionalProperties": false
  },
  "minItems": 1
}
```

</details>

<details>
<summary>step3_output.monitoring_indicators[].metric_id · 指标标识</summary>

Schema 指针：`#/$defs/step3_output/properties/monitoring_indicators/items/properties/metric_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step3_output.monitoring_indicators[].rationale · 指标选择理由</summary>

Schema 指针：`#/$defs/step3_output/properties/monitoring_indicators/items/properties/rationale`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step3_output.monitoring_indicators[].cadence · 计划更新频率</summary>

Schema 指针：`#/$defs/step3_output/properties/monitoring_indicators/items/properties/cadence`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step3_output.monitoring_indicators[].baseline_observation_refs · 基线观测引用</summary>

Schema 指针：`#/$defs/step3_output/properties/monitoring_indicators/items/properties/baseline_observation_refs`。

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
<summary>step3_output.monitoring_indicators[].missing_baseline_reason · 基线缺失原因</summary>

Schema 指针：`#/$defs/step3_output/properties/monitoring_indicators/items/properties/missing_baseline_reason`。

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
<summary>step3_output.invalidation_triggers · 论点失效触发条件列表</summary>

Schema 指针：`#/$defs/step3_output/properties/invalidation_triggers`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/trigger"
  },
  "minItems": 1
}
```

</details>

