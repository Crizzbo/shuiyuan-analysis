# OBJ-009 · subject 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#/$defs/subject`。
- 引用位置（Schema 指针）：`#/properties/subject`。
- 对象额外字段：禁止。
- 属性定义数：7（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `subject.company_id` | 公司标识 | string | 是 | 否 | 最短字符=1 | 公司稳定身份；不得用可变 ticker 作为唯一长期身份。 |
| `subject.security_ids` | 证券标识列表 | array<string> | 是 | 否 | 至少项数=1；项不能重复 | 证券稳定身份列表；公司可能有多种证券，必须至少一个。 |
| `subject.segments` | 业务分部列表 | array<segment> | 是 | 否 | 至少项数=1 | 业务分部清单；多业务公司分别绑定行业和商业模式。 |
| `subject.is_adr` | ADR 涉及标记 | boolean | 是 | 否 | 无显式附加结构约束 | 当前研究对象的证券范围是否涉及 ADR 的概括标记。字段位于 subject，不能表达每个 security_id 各自的 ADR 状态；多证券情形应在研究说明中解释范围。 |
| `subject.is_reit` | REIT 结构标记 | boolean | 是 | 否 | 无显式附加结构约束 | 研究主体是否按 REIT 结构研究的标记，属于主体结构信息；不代替分部行业分类，也不自动选择估值模型。 |
| `subject.classification_status` | 分类复核状态 | 枚举 | 是 | 否 | 枚举=['unreviewed', 'reviewed'] | unreviewed 尚未复核，reviewed 分类证据已复核；S1 完成必须 reviewed。 |
| `subject.unallocated_or_elimination_notes` | 未分配项目及抵销说明 | string | 是 | 否 | 最短字符=1 | 总部、内部交易抵销及未分配项目说明，避免分部重复计算。 |

## 3. 关联对象

- [segment](research--segment.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>subject.company_id · 公司标识</summary>

Schema 指针：`#/$defs/subject/properties/company_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>subject.security_ids · 证券标识列表</summary>

Schema 指针：`#/$defs/subject/properties/security_ids`。

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
<summary>subject.segments · 业务分部列表</summary>

Schema 指针：`#/$defs/subject/properties/segments`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/segment"
  },
  "minItems": 1
}
```

</details>

<details>
<summary>subject.is_adr · ADR 涉及标记</summary>

Schema 指针：`#/$defs/subject/properties/is_adr`。

```json
{
  "type": "boolean"
}
```

</details>

<details>
<summary>subject.is_reit · REIT 结构标记</summary>

Schema 指针：`#/$defs/subject/properties/is_reit`。

```json
{
  "type": "boolean"
}
```

</details>

<details>
<summary>subject.classification_status · 分类复核状态</summary>

Schema 指针：`#/$defs/subject/properties/classification_status`。

```json
{
  "enum": [
    "unreviewed",
    "reviewed"
  ]
}
```

</details>

<details>
<summary>subject.unallocated_or_elimination_notes · 未分配项目及抵销说明</summary>

Schema 指针：`#/$defs/subject/properties/unallocated_or_elimination_notes`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

