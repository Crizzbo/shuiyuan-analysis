# source · 输入来源

[返回统一目录](../10a-指标批输入数据字典.md)

全部字段必填；仅 1.1.0 的 source.published_at 允许 null。禁止额外字段。scale 必须大于零，由执行语义校验补充。

| 字段 | 中文名称 | 类型/引用 | 业务含义 |
| --- | --- | --- | --- |
| path | 来源路径 | string | 项目内 UTF-8 文本相对路径；不能指向项目外 |
| sha256 | 来源内容摘要 | string | 原文件字节 SHA-256，运行时比对 |
| locator | 来源定位 | string | 页码、表名或行号，不仅记录文件名 |
| excerpt | 原文摘录 | string | 需要在本地文本中逐字找到；不自动证明数值含义 |
| kind | 来源类型 | string | 真实数据仅 primary，合成数据仅 synthetic |
| published_at | 发布时间 | ['string', 'null'] | 精确来源发布时间；1.1.0 未核实时填 null，不补造时刻 |
| available_at | 可得时间 | string | 带时区，不得晚于研究时点 |

## 精确结构

```json
{
  "type": "object",
  "title": "输入来源",
  "properties": {
    "path": {
      "type": "string",
      "title": "来源路径",
      "description": "项目内 UTF-8 文本相对路径；不能指向项目外"
    },
    "sha256": {
      "type": "string",
      "title": "来源内容摘要",
      "description": "原文件字节 SHA-256，运行时比对",
      "pattern": "^[a-f0-9]{64}$"
    },
    "locator": {
      "type": "string",
      "title": "来源定位",
      "description": "页码、表名或行号，不仅记录文件名",
      "minLength": 1
    },
    "excerpt": {
      "type": "string",
      "title": "原文摘录",
      "description": "需要在本地文本中逐字找到；不自动证明数值含义",
      "minLength": 1
    },
    "kind": {
      "type": "string",
      "title": "来源类型",
      "description": "真实数据仅 primary，合成数据仅 synthetic",
      "enum": [
        "primary",
        "secondary",
        "synthetic"
      ]
    },
    "published_at": {
      "type": [
        "string",
        "null"
      ],
      "title": "发布时间",
      "description": "精确来源发布时间；1.1.0 未核实时填 null，不补造时刻",
      "format": "date-time"
    },
    "available_at": {
      "type": "string",
      "title": "可得时间",
      "description": "带时区，不得晚于研究时点",
      "format": "date-time"
    }
  },
  "required": [
    "path",
    "sha256",
    "locator",
    "excerpt",
    "kind",
    "published_at",
    "available_at"
  ],
  "additionalProperties": false
}
```
