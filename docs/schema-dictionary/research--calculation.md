# OBJ-007 · calculation 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/calculation`。
- 引用位置（Schema 指针）：`#/properties/calculations/items`。
- 对象额外字段：禁止。
- 属性定义数：9（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `calculation.id` | 计算标识 | string | 是 | 否 | 最短字符=1 | 对象在所属登记表或明确作用域中的唯一 ID；不是显示名称。 |
| `calculation.method` | 计算方法 | string | 是 | 否 | 最短字符=1 | 本次计算所采用的方法及口径名称，用于说明结果如何产生；不是行业分类，也不等于程序已执行该计算。 |
| `calculation.method_version` | 计算方法版本 | string | 是 | 否 | 最短字符=1 | 计算方法或实现采用的版本标识。与 implementation_path 共同记录实现来源；当前校验不比对代码内版本，也不自动验证版本真实性。 |
| `calculation.implementation_path` | 计算实现文件路径 | local_path | 是 | 否 | 引用=#/$defs/local_path | 项目内计算实现文件；记录存在不代表已执行或公式正确。 |
| `calculation.input_observation_refs` | 输入观测引用 | array<string> | 是 | 否 | 项不能重复 | 计算输入观测 ID；缺失值不可参与已登记计算。 |
| `calculation.assumption_refs` | 假设引用 | array<string> | 是 | 否 | 项不能重复 | 引用 claims 中 kind=assumption 的对象；不允许循环或引用 fact 充当假设。 |
| `calculation.outputs` | 计算输出列表 | array<quantity> | 是 | 否 | 至少项数=1 | 本次计算输出的 quantity 对象列表，至少一项。当前结构没有输出名称字段，S4 通过数量对象的数值、单位和币种匹配情景结果；不能填写指标 ID 或纯数值列表。 |
| `calculation.verification_status` | 计算核对状态 | 枚举 | 是 | 否 | 枚举=['unchecked', 'checked'] | 计算核对记录状态：unchecked 表示未声明完成核对，checked 表示声明已核对且必须引用核对证据。程序不执行公式，也不能据此证明计算正确。 |
| `calculation.verification_evidence_refs` | 计算核对证据引用 | array<string> | 是 | 否 | 项不能重复 | 计算核对记录的证据 ID；checked 时必须非空。 |

## 3. 关联对象

- [quantity](research--quantity.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>calculation.id · 计算标识</summary>

Schema 指针：`#/$defs/calculation/properties/id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>calculation.method · 计算方法</summary>

Schema 指针：`#/$defs/calculation/properties/method`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>calculation.method_version · 计算方法版本</summary>

Schema 指针：`#/$defs/calculation/properties/method_version`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>calculation.implementation_path · 计算实现文件路径</summary>

Schema 指针：`#/$defs/calculation/properties/implementation_path`。

```json
{
  "$ref": "#/$defs/local_path"
}
```

</details>

<details>
<summary>calculation.input_observation_refs · 输入观测引用</summary>

Schema 指针：`#/$defs/calculation/properties/input_observation_refs`。

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
<summary>calculation.assumption_refs · 假设引用</summary>

Schema 指针：`#/$defs/calculation/properties/assumption_refs`。

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
<summary>calculation.outputs · 计算输出列表</summary>

Schema 指针：`#/$defs/calculation/properties/outputs`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/quantity"
  },
  "minItems": 1
}
```

</details>

<details>
<summary>calculation.verification_status · 计算核对状态</summary>

Schema 指针：`#/$defs/calculation/properties/verification_status`。

```json
{
  "enum": [
    "unchecked",
    "checked"
  ]
}
```

</details>

<details>
<summary>calculation.verification_evidence_refs · 计算核对证据引用</summary>

Schema 指针：`#/$defs/calculation/properties/verification_evidence_refs`。

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

