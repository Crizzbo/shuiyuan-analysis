# period · 财务期间

[返回统一目录](../10a-指标批输入数据字典.md)

全部字段必填；仅 1.1.0 的 source.published_at 允许 null。禁止额外字段。scale 必须大于零，由执行语义校验补充。

| 字段 | 中文名称 | 类型/引用 | 业务含义 |
| --- | --- | --- | --- |
| start | 期间起日 | string | 财务统计期间开始 |
| end | 期间止日 | string | 财务统计期间结束 |
| basis | 期间口径 | string | 季度、年度或滚动十二个月 |

## 精确结构

```json
{
  "type": "object",
  "title": "财务期间",
  "properties": {
    "start": {
      "type": "string",
      "title": "期间起日",
      "description": "财务统计期间开始",
      "format": "date"
    },
    "end": {
      "type": "string",
      "title": "期间止日",
      "description": "财务统计期间结束",
      "format": "date"
    },
    "basis": {
      "type": "string",
      "title": "期间口径",
      "description": "季度、年度或滚动十二个月",
      "enum": [
        "quarter",
        "annual",
        "ttm"
      ]
    }
  },
  "required": [
    "start",
    "end",
    "basis"
  ],
  "additionalProperties": false
}
```
