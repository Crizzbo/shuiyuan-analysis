# criteria 知识契约单表说明

契约版本：1.0.0。字段中文名称来自正式契约的 title，业务释义来自 description。

[返回统一目录](../06a-行业与指标契约数据字典.md) · [填写说明](../06-行业知识契约与软件样板.md)

所属契约：[schemas/industry-knowledge.schema.json](../../schemas/industry-knowledge.schema.json)；定义位置：`#/$defs/criteria`。

## 字段表

| 定义字段标识 | 中文名称 | 类型或引用 | 必填 | 允许 null | 结构约束 | 业务含义 |
|---|---|---|---|---|---|---|
| `criteria.improving` | 改善判断条件 | string | 是 | 否 | 最短字符=1 | 哪些证据组合支持改善，并须检查相反解释。 |
| `criteria.deteriorating` | 恶化判断条件 | string | 是 | 否 | 最短字符=1 | 哪些证据组合支持恶化，区分周期与结构因素。 |
| `criteria.unknown` | 无法判断条件 | string | 是 | 否 | 最短字符=1 | 缺失、冲突、不可比或边界未定义时应返回 unknown。 |

## 精确结构定义

```json
{
  "type": "object",
  "properties": {
    "improving": {
      "type": "string",
      "minLength": 1,
      "title": "改善判断条件",
      "description": "哪些证据组合支持改善，并须检查相反解释。"
    },
    "deteriorating": {
      "type": "string",
      "minLength": 1,
      "title": "恶化判断条件",
      "description": "哪些证据组合支持恶化，区分周期与结构因素。"
    },
    "unknown": {
      "type": "string",
      "minLength": 1,
      "title": "无法判断条件",
      "description": "缺失、冲突、不可比或边界未定义时应返回 unknown。"
    }
  },
  "required": [
    "improving",
    "deteriorating",
    "unknown"
  ],
  "additionalProperties": false
}
```
