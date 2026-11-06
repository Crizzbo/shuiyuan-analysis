# source 知识契约单表说明

契约版本：1.0.0。字段中文名称来自正式契约的 title，业务释义来自 description。

[返回统一目录](../06a-行业与指标契约数据字典.md) · [填写说明](../06-行业知识契约与软件样板.md)

所属契约：[schemas/metric-definition.schema.json](../../schemas/metric-definition.schema.json)；定义位置：`#/$defs/source`。

## 字段表

| 定义字段标识 | 中文名称 | 类型或引用 | 必填 | 允许 null | 结构约束 | 业务含义 |
|---|---|---|---|---|---|---|
| `source.source_path` | 依据文件路径 | string | 是 | 否 | 最短字符=1 | 相对项目根目录的已存在文件，真实路径不得越界。 |
| `source.locator` | 依据定位信息 | string | 是 | 否 | 最短字符=1 | 章节、条目或 JSON 对象标识；由人工核实内容相关性。 |
| `source.source_kind` | 依据类型 | 枚举 | 是 | 否 | 枚举=['project_design', 'primary', 'secondary', 'synthetic'] | project_design 为项目知识设计，primary/secondary 为实际资料，synthetic 为模拟。 |

## 精确结构定义

```json
{
  "type": "object",
  "properties": {
    "source_path": {
      "type": "string",
      "minLength": 1,
      "title": "依据文件路径",
      "description": "相对项目根目录的已存在文件，真实路径不得越界。"
    },
    "locator": {
      "type": "string",
      "minLength": 1,
      "title": "依据定位信息",
      "description": "章节、条目或 JSON 对象标识；由人工核实内容相关性。"
    },
    "source_kind": {
      "enum": [
        "project_design",
        "primary",
        "secondary",
        "synthetic"
      ],
      "title": "依据类型",
      "description": "project_design 为项目知识设计，primary/secondary 为实际资料，synthetic 为模拟。"
    }
  },
  "required": [
    "source_path",
    "locator",
    "source_kind"
  ],
  "additionalProperties": false
}
```
