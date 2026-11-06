# dimension 知识契约单表说明

契约版本：1.0.0。字段中文名称来自正式契约的 title，业务释义来自 description。

[返回统一目录](../06a-行业与指标契约数据字典.md) · [填写说明](../06-行业知识契约与软件样板.md)

所属契约：[schemas/industry-knowledge.schema.json](../../schemas/industry-knowledge.schema.json)；定义位置：`#/$defs/dimension`。

## 字段表

| 定义字段标识 | 中文名称 | 类型或引用 | 必填 | 允许 null | 结构约束 | 业务含义 |
|---|---|---|---|---|---|---|
| `dimension.dimension_id` | 研究维度标识 | 枚举 | 是 | 否 | 枚举=['lifecycle', 'supply_demand', 'earnings', 'credit', 'sentiment', 'pricing'] | 长期生命周期与供需、盈利、融资、情绪、定价分别登记。 |
| `dimension.name_zh` | 中文名称 | string | 是 | 否 | 最短字符=1 | 知识对象或指标的中文阅读名称。 |
| `dimension.question` | 研究问题 | string | 是 | 否 | 最短字符=1 | 本维度需要回答的问题，而非预设结论。 |
| `dimension.required_metric_ids` | 必查指标列表 | array<string> | 是 | 否 | 项不能重复 | 须检查适用性和可得性的指标；允许说明不适用，但不能跳过整个维度。 |
| `dimension.evidence_requirements` | 证据要求列表 | array<string> | 是 | 否 | 至少项数=1 | 拟取证的内容、口径及时间要求，不表示已有该证据。 |
| `dimension.judgment_criteria` | 判断准则 | criteria | 是 | 否 | 引用=#/$defs/criteria | 定性判断条件，不构成统计验证后的数值阈值。 |
| `dimension.counterevidence` | 反证方向列表 | array<string> | 是 | 否 | 至少项数=1 | 应主动查找的相反证据；不是已登记的实际反证。 |

## 精确结构定义

```json
{
  "type": "object",
  "properties": {
    "dimension_id": {
      "enum": [
        "lifecycle",
        "supply_demand",
        "earnings",
        "credit",
        "sentiment",
        "pricing"
      ],
      "title": "研究维度标识",
      "description": "长期生命周期与供需、盈利、融资、情绪、定价分别登记。"
    },
    "name_zh": {
      "type": "string",
      "minLength": 1,
      "title": "中文名称",
      "description": "知识对象或指标的中文阅读名称。"
    },
    "question": {
      "type": "string",
      "minLength": 1,
      "title": "研究问题",
      "description": "本维度需要回答的问题，而非预设结论。"
    },
    "required_metric_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true,
      "title": "必查指标列表",
      "description": "须检查适用性和可得性的指标；允许说明不适用，但不能跳过整个维度。"
    },
    "evidence_requirements": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "title": "证据要求列表",
      "description": "拟取证的内容、口径及时间要求，不表示已有该证据。"
    },
    "judgment_criteria": {
      "$ref": "#/$defs/criteria",
      "title": "判断准则",
      "description": "定性判断条件，不构成统计验证后的数值阈值。"
    },
    "counterevidence": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "title": "反证方向列表",
      "description": "应主动查找的相反证据；不是已登记的实际反证。"
    }
  },
  "required": [
    "dimension_id",
    "name_zh",
    "question",
    "required_metric_ids",
    "evidence_requirements",
    "judgment_criteria",
    "counterevidence"
  ],
  "additionalProperties": false
}
```
