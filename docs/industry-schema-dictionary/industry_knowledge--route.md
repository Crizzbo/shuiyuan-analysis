# route 知识契约单表说明

契约版本：1.0.0。字段中文名称来自正式契约的 title，业务释义来自 description。

[返回统一目录](../06a-行业与指标契约数据字典.md) · [填写说明](../06-行业知识契约与软件样板.md)

所属契约：[schemas/industry-knowledge.schema.json](../../schemas/industry-knowledge.schema.json)；定义位置：`#/$defs/route`。

## 字段表

| 定义字段标识 | 中文名称 | 类型或引用 | 必填 | 允许 null | 结构约束 | 业务含义 |
|---|---|---|---|---|---|---|
| `route.business_model_ids` | 商业模式标识列表 | array<string> | 是 | 否 | 项不能重复 | 候选模式，实际公司分部归类需另有证据。 |
| `route.method` | 方法说明 | string | 是 | 否 | 最短字符=1 | 估值路线或指标计算的具体文字口径。 |
| `route.applicability` | 适用条件 | string | 是 | 否 | 最短字符=1 | 方法、指标或资料可以使用的业务范围。 |
| `route.limitations` | 局限说明列表 | array<string> | 是 | 否 | 至少项数=1 | 缺口、失效条件和不可自动检查的事项。 |

## 精确结构定义

```json
{
  "type": "object",
  "properties": {
    "business_model_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true,
      "title": "商业模式标识列表",
      "description": "候选模式，实际公司分部归类需另有证据。"
    },
    "method": {
      "type": "string",
      "minLength": 1,
      "title": "方法说明",
      "description": "估值路线或指标计算的具体文字口径。"
    },
    "applicability": {
      "type": "string",
      "minLength": 1,
      "title": "适用条件",
      "description": "方法、指标或资料可以使用的业务范围。"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "title": "局限说明列表",
      "description": "缺口、失效条件和不可自动检查的事项。"
    }
  },
  "required": [
    "business_model_ids",
    "method",
    "applicability",
    "limitations"
  ],
  "additionalProperties": false
}
```
