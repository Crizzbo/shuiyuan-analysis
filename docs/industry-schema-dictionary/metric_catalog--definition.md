# definition 知识契约单表说明

契约版本：1.0.0。字段中文名称来自正式契约的 title，业务释义来自 description。

[返回统一目录](../06a-行业与指标契约数据字典.md) · [填写说明](../06-行业知识契约与软件样板.md)

所属契约：[schemas/metric-definition.schema.json](../../schemas/metric-definition.schema.json)；定义位置：`#/$defs/definition`。

## 字段表

| 定义字段标识 | 中文名称 | 类型或引用 | 必填 | 允许 null | 结构约束 | 业务含义 |
|---|---|---|---|---|---|---|
| `definition.metric_id` | 指标标识 | string | 是 | 否 | 最短字符=1 | 引用现有指标字典；细化口径不能冒充不同公司的可比观测。 |
| `definition.name_zh` | 中文名称 | string | 是 | 否 | 最短字符=1 | 知识对象或指标的中文阅读名称。 |
| `definition.definition_status` | 口径状态 | 枚举 | 是 | 否 | 枚举=['specified', 'needs_definition'] | specified 是已写明口径，needs_definition 是仍待细化；均不等于统计验证。 |
| `definition.formula` | 公式或计算方法 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 可计算时明确公式；复合指标未拆分时允许 null 并登记阻断原因。 |
| `definition.inputs` | 公式输入项列表 | array<string> | 是 | 否 | 至少项数=0 | 记录输入名称及来源方向，未来接入时还需绑定具体观测。 |
| `definition.denominator` | 分母口径 | string / null | 是 | 是 | 最短字符=1；无显式附加结构约束 | 比例类明确分母；非比例应写不适用而非随意留空。 |
| `definition.unit` | 计量单位 | string | 是 | 否 | 最短字符=1 | 必须与指标字典一致；context_defined 表示仍需选择具体单位，不能用于观测值。 |
| `definition.period_basis` | 统计期间口径 | string | 是 | 否 | 最短字符=1 | 季度、年度、TTM、单时点或 source_dependent；取值时明确对应日期。 |
| `definition.cadence` | 更新频率 | string | 是 | 否 | 最短字符=1 | 按原始资料实际发布频率取值，不表示调度已实现。 |
| `definition.applicability` | 适用条件 | string | 是 | 否 | 最短字符=1 | 方法、指标或资料可以使用的业务范围。 |
| `definition.comparability_notes` | 可比性说明 | string | 是 | 否 | 最短字符=1 | 统一合并范围、货币、复权、分母和版本等口径后方可比较。 |
| `definition.missing_data_policy` | 缺失数据策略 | 固定值 record_null_and_block_calculation | 是 | 否 | 固定=record_null_and_block_calculation | 不补零、不猜测；保留缺失原因并限制计算和结论。 |
| `definition.source_requirements` | 实际取数证据要求 | array<string> | 是 | 否 | 至少项数=1 | 需要哪些原始资料支持实际值；设计依据不能代替这些资料。 |
| `definition.source_refs` | 项目内设计依据 | array<source> | 是 | 否 | 至少项数=1 | 引用支持知识设计的文件及原文位置；不得冒充公司事实。 |
| `definition.blocking_reasons` | 口径阻断原因列表 | array<string> | 是 | 否 | 至少项数=0 | 阻止指标直接计算、跨公司比较或阈值启用的缺口。 |
| `definition.validation_status` | 口径验证状态 | 固定值 not_validated | 是 | 否 | 固定=not_validated | not_validated 为仅设计；不代表公式和金融适用性已测试。 |

## 精确结构定义

```json
{
  "type": "object",
  "properties": {
    "metric_id": {
      "type": "string",
      "minLength": 1,
      "title": "指标标识",
      "description": "引用现有指标字典；细化口径不能冒充不同公司的可比观测。"
    },
    "name_zh": {
      "type": "string",
      "minLength": 1,
      "title": "中文名称",
      "description": "知识对象或指标的中文阅读名称。"
    },
    "definition_status": {
      "enum": [
        "specified",
        "needs_definition"
      ],
      "title": "口径状态",
      "description": "specified 是已写明口径，needs_definition 是仍待细化；均不等于统计验证。"
    },
    "formula": {
      "anyOf": [
        {
          "type": "string",
          "minLength": 1
        },
        {
          "type": "null"
        }
      ],
      "title": "公式或计算方法",
      "description": "可计算时明确公式；复合指标未拆分时允许 null 并登记阻断原因。"
    },
    "inputs": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 0,
      "title": "公式输入项列表",
      "description": "记录输入名称及来源方向，未来接入时还需绑定具体观测。"
    },
    "denominator": {
      "anyOf": [
        {
          "type": "string",
          "minLength": 1
        },
        {
          "type": "null"
        }
      ],
      "title": "分母口径",
      "description": "比例类明确分母；非比例应写不适用而非随意留空。"
    },
    "unit": {
      "type": "string",
      "minLength": 1,
      "title": "计量单位",
      "description": "必须与指标字典一致；context_defined 表示仍需选择具体单位，不能用于观测值。"
    },
    "period_basis": {
      "type": "string",
      "minLength": 1,
      "title": "统计期间口径",
      "description": "季度、年度、TTM、单时点或 source_dependent；取值时明确对应日期。"
    },
    "cadence": {
      "type": "string",
      "minLength": 1,
      "title": "更新频率",
      "description": "按原始资料实际发布频率取值，不表示调度已实现。"
    },
    "applicability": {
      "type": "string",
      "minLength": 1,
      "title": "适用条件",
      "description": "方法、指标或资料可以使用的业务范围。"
    },
    "comparability_notes": {
      "type": "string",
      "minLength": 1,
      "title": "可比性说明",
      "description": "统一合并范围、货币、复权、分母和版本等口径后方可比较。"
    },
    "missing_data_policy": {
      "const": "record_null_and_block_calculation",
      "title": "缺失数据策略",
      "description": "不补零、不猜测；保留缺失原因并限制计算和结论。"
    },
    "source_requirements": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "title": "实际取数证据要求",
      "description": "需要哪些原始资料支持实际值；设计依据不能代替这些资料。"
    },
    "source_refs": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/source"
      },
      "minItems": 1,
      "title": "项目内设计依据",
      "description": "引用支持知识设计的文件及原文位置；不得冒充公司事实。"
    },
    "blocking_reasons": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 0,
      "title": "口径阻断原因列表",
      "description": "阻止指标直接计算、跨公司比较或阈值启用的缺口。"
    },
    "validation_status": {
      "const": "not_validated",
      "title": "口径验证状态",
      "description": "not_validated 为仅设计；不代表公式和金融适用性已测试。"
    }
  },
  "required": [
    "metric_id",
    "name_zh",
    "definition_status",
    "formula",
    "inputs",
    "denominator",
    "unit",
    "period_basis",
    "cadence",
    "applicability",
    "comparability_notes",
    "missing_data_policy",
    "source_requirements",
    "source_refs",
    "blocking_reasons",
    "validation_status"
  ],
  "additionalProperties": false
}
```
