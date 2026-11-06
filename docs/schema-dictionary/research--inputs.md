# OBJ-021 · inputs 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/inputs`。
- 引用位置（Schema 指针）：`#/$defs/step1/properties/inputs`；`#/$defs/step2/properties/inputs`；`#/$defs/step3/properties/inputs`；`#/$defs/step4/properties/inputs`；`#/$defs/step5/properties/inputs`；`#/$defs/step6/properties/inputs`。
- 对象额外字段：禁止。
- 属性定义数：4（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `inputs.dependencies` | 前序版本依赖列表 | array<dependency> | 是 | 否 | 至少项数=0 | 全部前序步骤版本快照；S1 为空，Si 已开展时包含 S1 到 S(i-1)。 |
| `inputs.evidence_refs` | 证据引用 | array<string> | 是 | 否 | 项不能重复 | 引用 evidence 表中 ID；不直接填文件路径或把空数组当作已取证。 |
| `inputs.observation_refs` | 观测引用 | array<string> | 是 | 否 | 项不能重复 | 引用 observations 表中观测 ID，不能引用指标定义 ID。 |
| `inputs.claim_refs` | 判断引用 | array<string> | 是 | 否 | 项不能重复 | 支撑该评估、事件或触发机制的 claims ID；不直接写散文替代引用。 |

## 3. 关联对象

- [dependency](research--dependency.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>inputs.dependencies · 前序版本依赖列表</summary>

Schema 指针：`#/$defs/inputs/properties/dependencies`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/dependency"
  },
  "minItems": 0
}
```

</details>

<details>
<summary>inputs.evidence_refs · 证据引用</summary>

Schema 指针：`#/$defs/inputs/properties/evidence_refs`。

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
<summary>inputs.observation_refs · 观测引用</summary>

Schema 指针：`#/$defs/inputs/properties/observation_refs`。

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
<summary>inputs.claim_refs · 判断引用</summary>

Schema 指针：`#/$defs/inputs/properties/claim_refs`。

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

