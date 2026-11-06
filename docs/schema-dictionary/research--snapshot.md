# OBJ-028 · snapshot 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/snapshot`。
- 引用位置（Schema 指针）：`#/$defs/invalidation/properties/baseline_versions/items`。
- 对象额外字段：禁止。
- 属性定义数：2（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `snapshot.step_id` | 基线受影响步骤标识 | 枚举 | 是 | 否 | 枚举=['S1', 'S2', 'S3', 'S4', 'S5', 'S6'] | 失效事件基线中受影响步骤的 ID，可包含 S1—S6；与依赖对象只允许前序的含义不同。 |
| `snapshot.version` | 失效前步骤基线版本 | integer | 是 | 否 | 最小=1 | 该失效事件登记的受影响步骤旧版本；用于检查重新研究的版本是否增加，不应改成当前新版本。 |

## 3. 关联对象

本表未引用其他公共对象。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>snapshot.step_id · 基线受影响步骤标识</summary>

Schema 指针：`#/$defs/snapshot/properties/step_id`。

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
<summary>snapshot.version · 失效前步骤基线版本</summary>

Schema 指针：`#/$defs/snapshot/properties/version`。

```json
{
  "type": "integer",
  "minimum": 1
}
```

</details>

