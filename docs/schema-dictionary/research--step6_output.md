# OBJ-018 · step6_output 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step6_output`。
- 引用位置（Schema 指针）：`#/$defs/step6/properties/output/anyOf/0`；`#/$defs/step6/allOf/0/then/properties/output`。
- 对象额外字段：禁止。
- 属性定义数：13（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step6_output.monitoring_plan` | 监测计划列表 | array<object> | 是 | 否 | 至少项数=1 | 指标更新计划；记录负责人和时间，不代表已有调度服务。 |
| `step6_output.monitoring_plan[].metric_id` | 指标标识 | string | 是 | 否 | 最短字符=1 | 项目指标字典中已登记的指标 ID；不能填中文指标名或临时自造 ID。 |
| `step6_output.monitoring_plan[].cadence` | 计划更新频率 | string | 是 | 否 | 最短字符=1 | 计划更新频率，按资料实际发布规律填写，不承诺尚未实现的自动任务。 |
| `step6_output.monitoring_plan[].owner` | 监测负责人 | string | 是 | 否 | 最短字符=1 | 负责检查与更新该指标的人或角色。 |
| `step6_output.monitoring_plan[].last_observation_ref` | 最近采用观测引用 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 这条监测计划最近采用的 observation.id，无引用时填 null；当前只检查 ID 存在，不检查它是否为该 metric_id 最新观测或是否有有效数值。填写时应自行核对。 |
| `step6_output.monitoring_plan[].next_due_at` | 下次指标检查时间 | string | 是 | 否 | 格式=date-time | 下次指标检查时间，须晚于 as_of。 |
| `step6_output.triggers` | 重研究触发条件列表 | array<trigger> | 是 | 否 | 至少项数=1 | 持续跟踪中重新执行前序步骤的条件。 |
| `step6_output.review_records` | 复盘记录列表 | array<object> | 是 | 否 | 至少项数=0 | 复盘记录；初次建立跟踪计划时可为空。 |
| `step6_output.review_records[].reviewed_at` | 复盘时间 | string | 是 | 否 | 格式=date-time | 本次复盘时间，不得晚于 recorded_at。 |
| `step6_output.review_records[].new_evidence_refs` | 本次新纳入证据引用 | array<string> | 是 | 否 | 项不能重复 | 本次复盘新纳入考虑的 evidence.id，可以是此前已经发布或登记的资料；不要求资料是刚刚发布的。当前没有自动比对上一修订以判定是否真正新增。 |
| `step6_output.review_records[].changed_claim_refs` | 本次改变判断引用 | array<string> | 是 | 否 | 项不能重复 | 本次复盘认为需要更新或已改变的 claim.id，引用当前研究登记表；字段没有旧判断内容或逐项差异，历史变化须结合研究修订查询，程序不自动生成差异。 |
| `step6_output.review_records[].conclusion` | 复盘结论 | string | 是 | 否 | 最短字符=1 | 复盘结果和处理说明，保留失败与反证。 |
| `step6_output.next_review_at` | 下次总体复盘时间 | string | 是 | 否 | 格式=date-time | 下次总体复盘时间，须晚于 as_of。 |

## 3. 关联对象

- [trigger](research--trigger.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step6_output.monitoring_plan · 监测计划列表</summary>

Schema 指针：`#/$defs/step6_output/properties/monitoring_plan`。

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
      "cadence": {
        "type": "string",
        "minLength": 1
      },
      "owner": {
        "type": "string",
        "minLength": 1
      },
      "last_observation_ref": {
        "anyOf": [
          {
            "type": "string",
            "minLength": 1
          },
          {
            "type": "null"
          }
        ]
      },
      "next_due_at": {
        "type": "string",
        "format": "date-time"
      }
    },
    "required": [
      "metric_id",
      "cadence",
      "owner",
      "last_observation_ref",
      "next_due_at"
    ],
    "additionalProperties": false
  },
  "minItems": 1
}
```

</details>

<details>
<summary>step6_output.monitoring_plan[].metric_id · 指标标识</summary>

Schema 指针：`#/$defs/step6_output/properties/monitoring_plan/items/properties/metric_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step6_output.monitoring_plan[].cadence · 计划更新频率</summary>

Schema 指针：`#/$defs/step6_output/properties/monitoring_plan/items/properties/cadence`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step6_output.monitoring_plan[].owner · 监测负责人</summary>

Schema 指针：`#/$defs/step6_output/properties/monitoring_plan/items/properties/owner`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step6_output.monitoring_plan[].last_observation_ref · 最近采用观测引用</summary>

Schema 指针：`#/$defs/step6_output/properties/monitoring_plan/items/properties/last_observation_ref`。

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
<summary>step6_output.monitoring_plan[].next_due_at · 下次指标检查时间</summary>

Schema 指针：`#/$defs/step6_output/properties/monitoring_plan/items/properties/next_due_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>step6_output.triggers · 重研究触发条件列表</summary>

Schema 指针：`#/$defs/step6_output/properties/triggers`。

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

<details>
<summary>step6_output.review_records · 复盘记录列表</summary>

Schema 指针：`#/$defs/step6_output/properties/review_records`。

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "reviewed_at": {
        "type": "string",
        "format": "date-time"
      },
      "new_evidence_refs": {
        "type": "array",
        "items": {
          "type": "string",
          "minLength": 1
        },
        "uniqueItems": true
      },
      "changed_claim_refs": {
        "type": "array",
        "items": {
          "type": "string",
          "minLength": 1
        },
        "uniqueItems": true
      },
      "conclusion": {
        "type": "string",
        "minLength": 1
      }
    },
    "required": [
      "reviewed_at",
      "new_evidence_refs",
      "changed_claim_refs",
      "conclusion"
    ],
    "additionalProperties": false
  },
  "minItems": 0
}
```

</details>

<details>
<summary>step6_output.review_records[].reviewed_at · 复盘时间</summary>

Schema 指针：`#/$defs/step6_output/properties/review_records/items/properties/reviewed_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>step6_output.review_records[].new_evidence_refs · 本次新纳入证据引用</summary>

Schema 指针：`#/$defs/step6_output/properties/review_records/items/properties/new_evidence_refs`。

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
<summary>step6_output.review_records[].changed_claim_refs · 本次改变判断引用</summary>

Schema 指针：`#/$defs/step6_output/properties/review_records/items/properties/changed_claim_refs`。

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
<summary>step6_output.review_records[].conclusion · 复盘结论</summary>

Schema 指针：`#/$defs/step6_output/properties/review_records/items/properties/conclusion`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>step6_output.next_review_at · 下次总体复盘时间</summary>

Schema 指针：`#/$defs/step6_output/properties/next_review_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

