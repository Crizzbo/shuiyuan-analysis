# OBJ-020 · gate 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/gate`。
- 引用位置（Schema 指针）：`#/$defs/step1/properties/gates/items`；`#/$defs/step2/properties/gates/items`；`#/$defs/step3/properties/gates/items`；`#/$defs/step4/properties/gates/items`；`#/$defs/step5/properties/gates/items`；`#/$defs/step6/properties/gates/items`。
- 对象额外字段：禁止。
- 属性定义数：4（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `gate.id` | 验收项名称 | string | 是 | 否 | 最短字符=1 | 当前步骤的验收项名称；completed 时必须与该步骤的强制验收项集合完全一致。不是整个项目中的全局唯一对象 ID。 |
| `gate.result` | 验收结果 | 枚举 | 是 | 否 | 枚举=['pass', 'fail', 'not_applicable'] | 该验收项的评审结果：pass 通过、fail 未通过、not_applicable 不适用；强制验收项必须 pass 才能完成步骤。它不叫 status，也不是步骤流程状态。 |
| `gate.reason` | 验收依据说明 | string | 是 | 否 | 最短字符=1 | 本项验收结果的具体理由和依据。当前程序只检查字符串非空，不能证明解释充分或验收结论真实。 |
| `gate.evidence_refs` | 证据引用 | array<string> | 是 | 否 | 项不能重复 | 支持该验收结果的 evidence.id 列表；结构允许空数组。completed 步骤必须有 inputs.evidence_refs，但程序未要求每个 gate 的证据列表都非空。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>gate.id · 验收项名称</summary>

Schema 指针：`#/$defs/gate/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>gate.result · 验收结果</summary>

Schema 指针：`#/$defs/gate/properties/result`。

```json
{
  "enum": [
    "pass",
    "fail",
    "not_applicable"
  ]
}
```

</details>

<details>
<summary>gate.reason · 验收依据说明</summary>

Schema 指针：`#/$defs/gate/properties/reason`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>gate.evidence_refs · 证据引用</summary>

Schema 指针：`#/$defs/gate/properties/evidence_refs`。

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

