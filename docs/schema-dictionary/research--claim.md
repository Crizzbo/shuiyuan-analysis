# OBJ-006 · claim 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/claim`。
- 引用位置（Schema 指针）：`#/properties/claims/items`。
- 对象额外字段：禁止。
- 属性定义数：8（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `claim.id` | 判断标识 | string | 是 | 否 | 最短字符=1 | 对象在所属登记表或明确作用域中的唯一 ID；不是显示名称。 |
| `claim.kind` | 判断类型 | 枚举 | 是 | 否 | 枚举=['fact', 'inference', 'assumption', 'unknown', 'not_applicable'] | 本条判断的认识类型：fact 为有证据支持的事实陈述，inference 为据资料推导的结论，assumption 为计算或推断采用的前提，unknown 为尚无法确认的问题，not_applicable 为说明不适用的事项。不是评分或交易状态。 |
| `claim.statement` | 判断内容 | string | 是 | 否 | 最短字符=1 | 本条判断实际主张的内容。unknown 应说明未知事项，not_applicable 应说明不适用范围和理由；这是填写要求，当前程序只检查非空，不能验证文字解释是否充分。 |
| `claim.evidence_refs` | 证据引用 | array<string> | 是 | 否 | 项不能重复 | 引用 evidence 表中 ID；不直接填文件路径或把空数组当作已取证。 |
| `claim.observation_refs` | 观测引用 | array<string> | 是 | 否 | 项不能重复 | 引用 observations 表中观测 ID，不能引用指标定义 ID。 |
| `claim.counterevidence_refs` | 反证引用 | array<string> | 是 | 否 | 项不能重复 | 引用可能削弱或否定本条判断的 evidence.id。可以与其他判断的支持证据重叠；是否构成有效反证需人工核验，当前程序只检查引用并在 S2 完成时检查存在反证引用。 |
| `claim.assumption_refs` | 假设引用 | array<string> | 是 | 否 | 项不能重复 | 引用 claims 中 kind=assumption 的对象；不允许循环或引用 fact 充当假设。 |
| `claim.uncertainty` | 不确定性说明 | string | 是 | 否 | 最短字符=1 | 说明本条判断不确定的来源、边界及可能改变结论的条件。它是文字说明，不是概率字段；当前没有置信度数值或自动概率校准。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>claim.id · 判断标识</summary>

Schema 指针：`#/$defs/claim/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>claim.kind · 判断类型</summary>

Schema 指针：`#/$defs/claim/properties/kind`。

```json
{
  "enum": [
    "fact",
    "inference",
    "assumption",
    "unknown",
    "not_applicable"
  ]
}
```

</details>

<details>
<summary>claim.statement · 判断内容</summary>

Schema 指针：`#/$defs/claim/properties/statement`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>claim.evidence_refs · 证据引用</summary>

Schema 指针：`#/$defs/claim/properties/evidence_refs`。

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
<summary>claim.observation_refs · 观测引用</summary>

Schema 指针：`#/$defs/claim/properties/observation_refs`。

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
<summary>claim.counterevidence_refs · 反证引用</summary>

Schema 指针：`#/$defs/claim/properties/counterevidence_refs`。

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
<summary>claim.assumption_refs · 假设引用</summary>

Schema 指针：`#/$defs/claim/properties/assumption_refs`。

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
<summary>claim.uncertainty · 不确定性说明</summary>

Schema 指针：`#/$defs/claim/properties/uncertainty`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

