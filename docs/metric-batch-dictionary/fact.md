# fact · 原始输入事实

[返回统一目录](../10a-指标批输入数据字典.md)

全部字段必填；仅 1.1.0 的 source.published_at 允许 null。禁止额外字段。scale 必须大于零，由执行语义校验补充。

| 字段 | 中文名称 | 类型/引用 | 业务含义 |
| --- | --- | --- | --- |
| id | 原始事实标识 | string | 批内原始事实 ID，不是正式研究 observation ID |
| field | 原始字段代码 | string | 执行绑定规定的输入字段 |
| entity_id | 公司标识 | string | 必须与请求公司一致 |
| scope_id | 业务范围标识 | string | 合并或指定分部，禁止混用 |
| period | 财务期间 | #/$defs/period | 分子分母需完全匹配 |
| accounting_basis | 会计口径 | string | 本批仅支持 GAAP |
| value | 金额数值 | number | 有限实际数值，不自动填零 |
| unit | 量纲 | string | 本批分子分母均为金额 |
| currency | 币种 | string | 三位大写 ASCII 代码 |
| scale | 金额尺度乘数 | number | 如百万美元填 1000000；统一为基础货币单位后计算 |
| source | 来源与时点 | #/$defs/source | 定位、内容及可得时间 |

## 精确结构

```json
{
  "type": "object",
  "title": "原始输入事实",
  "properties": {
    "id": {
      "type": "string",
      "title": "原始事实标识",
      "description": "批内原始事实 ID，不是正式研究 observation ID",
      "minLength": 1
    },
    "field": {
      "type": "string",
      "title": "原始字段代码",
      "description": "执行绑定规定的输入字段",
      "minLength": 1
    },
    "entity_id": {
      "type": "string",
      "title": "公司标识",
      "description": "必须与请求公司一致",
      "minLength": 1
    },
    "scope_id": {
      "type": "string",
      "title": "业务范围标识",
      "description": "合并或指定分部，禁止混用",
      "minLength": 1
    },
    "period": {
      "$ref": "#/$defs/period",
      "title": "财务期间",
      "description": "分子分母需完全匹配"
    },
    "accounting_basis": {
      "type": "string",
      "title": "会计口径",
      "description": "本批仅支持 GAAP",
      "enum": [
        "GAAP"
      ]
    },
    "value": {
      "type": "number",
      "title": "金额数值",
      "description": "有限实际数值，不自动填零"
    },
    "unit": {
      "type": "string",
      "title": "量纲",
      "description": "本批分子分母均为金额",
      "enum": [
        "currency"
      ]
    },
    "currency": {
      "type": "string",
      "title": "币种",
      "description": "三位大写 ASCII 代码",
      "pattern": "^[A-Z]{3}$"
    },
    "scale": {
      "type": "number",
      "title": "金额尺度乘数",
      "description": "如百万美元填 1000000；统一为基础货币单位后计算",
      "minimum": 0
    },
    "source": {
      "$ref": "#/$defs/source",
      "title": "来源与时点",
      "description": "定位、内容及可得时间"
    }
  },
  "required": [
    "id",
    "field",
    "entity_id",
    "scope_id",
    "period",
    "accounting_basis",
    "value",
    "unit",
    "currency",
    "scale",
    "source"
  ],
  "additionalProperties": false
}
```
