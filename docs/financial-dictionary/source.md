# 输入来源

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `path` | 来源路径 | string | 是 | 项目内 UTF-8 文本相对路径；不能指向项目外 |
| `sha256` | 来源内容摘要 | string | 是 | 原文件字节 SHA-256，运行时比对 |
| `locator` | 来源定位 | string | 是 | 页码、表名或行号，不仅记录文件名 |
| `excerpt` | 原文摘录 | string | 是 | 需要在本地文本中逐字找到；不自动证明数值含义 |
| `kind` | 来源类型 | string | 是 | 真实数据仅 primary，合成数据仅 synthetic |
| `published_at` | 发布时间 | string/null | 是 | 精确来源发布时间；1.1.0 未核实时填 null，不补造时刻 |
| `available_at` | 可得时间 | string | 是 | 带时区，不得晚于研究时点 |

字段与 `schemas/financial-report.schema.json` 同源生成；对象数组的具体运行结果见 14 功能设计。
