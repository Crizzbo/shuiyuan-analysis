# OBJ-024 · step3 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/step3`。
- 引用位置（Schema 指针）：`#/properties/steps/prefixItems/2`。
- 对象额外字段：禁止。
- 属性定义数：8（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `step3.id` | 固定步骤标识 | 固定值 S3 | 是 | 否 | 固定=S3 | 固定步骤 ID，与数组位置一致；不能自行改名。 |
| `step3.version` | 步骤版本 | integer | 是 | 否 | 最小=1 | 步骤版本；输入、输出、门槛或状态变更必须增版，下游不得沿用旧依赖。 |
| `step3.status` | 步骤流程状态 | 枚举 | 是 | 否 | 枚举=['pending', 'in_progress', 'completed', 'insufficient_evidence', 'needs_review', 'invalidated'] | 当前步骤的流程状态：pending、in_progress、completed、insufficient_evidence、needs_review 或 invalidated；对应输出及后序处理见说明书第 10 节。 |
| `step3.updated_at` | 步骤更新时间 | string | 是 | 否 | 格式=date-time | 步骤最后更新时间，不得晚于研究 recorded_at，入库修订不能倒退。 |
| `step3.inputs` | 步骤输入 | inputs | 是 | 否 | 引用=#/$defs/inputs | 当前步骤消费的证据、观测、判断和前序版本。 |
| `step3.gates` | 步骤验收项列表 | array<gate> | 是 | 否 | 至少项数=0 | 该步骤必须检查的门槛；已完成时名称集合必须与校验器一致。 |
| `step3.output` | 步骤专用输出 | step3_output / null | 是 | 是 | 引用=#/$defs/step3_output；无显式附加结构约束 | 对应步骤的专用输出；pending 必须 null，completed 必须完整对象。 |
| `step3.notes` | 过程备注 | array<string> | 是 | 否 | 至少项数=0 | 工作说明和未结构化的过程记录，不能用它替代必填输出或证据。 |

## 3. 关联对象

- [gate](research--gate.md)：本表引用的公共对象定义。
- [inputs](research--inputs.md)：本表引用的公共对象定义。
- [step3_output](research--step3_output.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>step3.id · 固定步骤标识</summary>

Schema 指针：`#/$defs/step3/properties/id`。

```json
{
  "const": "S3"
}
```

</details>

<details>
<summary>step3.version · 步骤版本</summary>

Schema 指针：`#/$defs/step3/properties/version`。

```json
{
  "type": "integer",
  "minimum": 1
}
```

</details>

<details>
<summary>step3.status · 步骤流程状态</summary>

Schema 指针：`#/$defs/step3/properties/status`。

```json
{
  "enum": [
    "pending",
    "in_progress",
    "completed",
    "insufficient_evidence",
    "needs_review",
    "invalidated"
  ]
}
```

</details>

<details>
<summary>step3.updated_at · 步骤更新时间</summary>

Schema 指针：`#/$defs/step3/properties/updated_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>step3.inputs · 步骤输入</summary>

Schema 指针：`#/$defs/step3/properties/inputs`。

```json
{
  "$ref": "#/$defs/inputs"
}
```

</details>

<details>
<summary>step3.gates · 步骤验收项列表</summary>

Schema 指针：`#/$defs/step3/properties/gates`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/gate"
  },
  "minItems": 0
}
```

</details>

<details>
<summary>step3.output · 步骤专用输出</summary>

Schema 指针：`#/$defs/step3/properties/output`。

```json
{
  "anyOf": [
    {
      "$ref": "#/$defs/step3_output"
    },
    {
      "type": "null"
    }
  ]
}
```

</details>

<details>
<summary>step3.notes · 过程备注</summary>

Schema 指针：`#/$defs/step3/properties/notes`。

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

