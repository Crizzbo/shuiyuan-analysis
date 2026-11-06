# OBJ-019 · dependency 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/dependency`。
- 引用位置（Schema 指针）：`#/$defs/inputs/properties/dependencies/items`。
- 对象额外字段：禁止。
- 属性定义数：2（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `dependency.step_id` | 被依赖前序步骤标识 | 枚举 | 是 | 否 | 枚举=['S1', 'S2', 'S3', 'S4', 'S5'] | 当前步骤消费的前序步骤 ID，仅 S1—S5；必须在当前步骤之前。它标识依赖步骤，不标识触发目标。 |
| `dependency.version` | 采用的前序步骤版本 | integer | 是 | 否 | 最小=1 | 当前输入采用的前序步骤版本；有效步骤须与当前记录中对应前序 version 一致，invalidated 步骤可保留旧依赖供审计。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>dependency.step_id · 被依赖前序步骤标识</summary>

Schema 指针：`#/$defs/dependency/properties/step_id`。

```json
{
  "enum": [
    "S1",
    "S2",
    "S3",
    "S4",
    "S5"
  ]
}
```

</details>

<details>
<summary>dependency.version · 采用的前序步骤版本</summary>

Schema 指针：`#/$defs/dependency/properties/version`。

```json
{
  "type": "integer",
  "minimum": 1
}
```

</details>

