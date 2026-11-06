# Schema 数据字典统一目录

| 文档属性 | 值 |
|---|---|
| 文档编号 | SY-DD-001 |
| 文档版本 | 1.5.0 |
| 契约版本 | 1.1.0，兼容 1.0.0 |
| 状态 | 项目内部规范；不代表外部标准认证 |
| 生成方式 | 从两份正式 Schema 提取结构；业务释义按完整字段标识由 schema-field-meanings.json 独立维护 |
| 覆盖口径 | 属性定义计数；条件分支中的重复声明不重复计数 |

操作说明见 [Schema 配套说明书](05-Schema配套说明书.md)，跨字段约束见 [规则索引](05b-Schema规则索引.md)。机器可读说明见 [字段指南](../schemas/schema-field-guide.json)，业务释义维护源见 [逐字段释义](../schemas/schema-field-meanings.json)，本次修正依据见 [业务释义核对记录](05c-数据字典业务释义核对记录.md)。

## 阅读约定

各字段的中文名称由 [中文名称维护源](../schemas/schema-field-names.json)按完整字段标识独立维护，机器可读字典使用 `name_zh` 属性。中文名称是阅读标签，JSON 实例仍使用原有英文属性键；同名英文属性在不同业务对象中可有不同中文名称。

本文件仅维护统一目录及阅读约定。每个对象表在 `schema-dictionary/` 中独立成文，包含对象定义、字段表、关联对象和精确结构定义。下面的对象名均可点击进入单表说明；每个单表都有返回目录的入口。这里的“表”指 Schema 对象字段表，不意味着新增数据库物理表。

“定义字段标识”是对象定义名加属性名，**不是可以直接复制使用的实例 JSON 路径**。例如 `observation.value` 对应实例 `$.observations[0].value`，`step2_output.checks` 对应 `$.steps[1].output.checks`。精确 Schema 指针定位规范定义，不定位实例数据或原文证据。

JSON 类型保留 string、integer、number、boolean、object、array、null；枚举与固定值的实际类型由精确结构定义中的值确定。引用对象名表示必须展开相应定义，不是新增 JSON 类型。

必填、可空、空数组是三个独立维度。本字典不推断默认值，也不要求所有复用对象同时实例化。业务说明中的示例、建议和项目默认范围不是新增结构约束。

“必须出现”按所属对象解释，不表示该对象在任何状态都要实例化。允许 null 的必填字段也必须写出键；例如 pending 步骤 output=null。数组允许空与 null 是不同含义。所有当前定义对象禁止额外字段。

表中约束是结构约束；证据引用、未来信息、单位、状态、概率、来源绑定和历史版本等跨字段规则另由校验器检查。相同对象通过 $ref 复用时参考其独立表。定义对象不另复制到 research 顶层。

内联对象的字段用点号/[] 表示数据路径；schema_pointer 为精确 Schema 位置，不是原文证据 locator。

## 对象索引

| 对象编号 | 定义名 | 契约文件 | 定义指针 | 属性数 |
|---|---|---|---|---|
| OBJ-001 | [research](schema-dictionary/research--research.md) | `schemas/research.schema.json` | `#` | 15 |
| OBJ-002 | [quantity](schema-dictionary/research--quantity.md) | `schemas/research.schema.json` | `#/$defs/quantity` | 3 |
| OBJ-003 | [period](schema-dictionary/research--period.md) | `schemas/research.schema.json` | `#/$defs/period` | 3 |
| OBJ-004 | [evidence](schema-dictionary/research--evidence.md) | `schemas/research.schema.json` | `#/$defs/evidence` | 11 |
| OBJ-005 | [observation](schema-dictionary/research--observation.md) | `schemas/research.schema.json` | `#/$defs/observation` | 10 |
| OBJ-006 | [claim](schema-dictionary/research--claim.md) | `schemas/research.schema.json` | `#/$defs/claim` | 8 |
| OBJ-007 | [calculation](schema-dictionary/research--calculation.md) | `schemas/research.schema.json` | `#/$defs/calculation` | 9 |
| OBJ-008 | [segment](schema-dictionary/research--segment.md) | `schemas/research.schema.json` | `#/$defs/segment` | 10 |
| OBJ-009 | [subject](schema-dictionary/research--subject.md) | `schemas/research.schema.json` | `#/$defs/subject` | 7 |
| OBJ-010 | [assessment](schema-dictionary/research--assessment.md) | `schemas/research.schema.json` | `#/$defs/assessment` | 3 |
| OBJ-011 | [step1_output](schema-dictionary/research--step1_output.md) | `schemas/research.schema.json` | `#/$defs/step1_output` | 12 |
| OBJ-012 | [step2_output](schema-dictionary/research--step2_output.md) | `schemas/research.schema.json` | `#/$defs/step2_output` | 11 |
| OBJ-013 | [trigger](schema-dictionary/research--trigger.md) | `schemas/research.schema.json` | `#/$defs/trigger` | 6 |
| OBJ-014 | [step3_output](schema-dictionary/research--step3_output.md) | `schemas/research.schema.json` | `#/$defs/step3_output` | 14 |
| OBJ-015 | [scenario](schema-dictionary/research--scenario.md) | `schemas/research.schema.json` | `#/$defs/scenario` | 5 |
| OBJ-016 | [step4_output](schema-dictionary/research--step4_output.md) | `schemas/research.schema.json` | `#/$defs/step4_output` | 12 |
| OBJ-017 | [step5_output](schema-dictionary/research--step5_output.md) | `schemas/research.schema.json` | `#/$defs/step5_output` | 13 |
| OBJ-018 | [step6_output](schema-dictionary/research--step6_output.md) | `schemas/research.schema.json` | `#/$defs/step6_output` | 13 |
| OBJ-019 | [dependency](schema-dictionary/research--dependency.md) | `schemas/research.schema.json` | `#/$defs/dependency` | 2 |
| OBJ-020 | [gate](schema-dictionary/research--gate.md) | `schemas/research.schema.json` | `#/$defs/gate` | 4 |
| OBJ-021 | [inputs](schema-dictionary/research--inputs.md) | `schemas/research.schema.json` | `#/$defs/inputs` | 4 |
| OBJ-022 | [step1](schema-dictionary/research--step1.md) | `schemas/research.schema.json` | `#/$defs/step1` | 8 |
| OBJ-023 | [step2](schema-dictionary/research--step2.md) | `schemas/research.schema.json` | `#/$defs/step2` | 8 |
| OBJ-024 | [step3](schema-dictionary/research--step3.md) | `schemas/research.schema.json` | `#/$defs/step3` | 8 |
| OBJ-025 | [step4](schema-dictionary/research--step4.md) | `schemas/research.schema.json` | `#/$defs/step4` | 8 |
| OBJ-026 | [step5](schema-dictionary/research--step5.md) | `schemas/research.schema.json` | `#/$defs/step5` | 8 |
| OBJ-027 | [step6](schema-dictionary/research--step6.md) | `schemas/research.schema.json` | `#/$defs/step6` | 8 |
| OBJ-028 | [snapshot](schema-dictionary/research--snapshot.md) | `schemas/research.schema.json` | `#/$defs/snapshot` | 2 |
| OBJ-029 | [invalidation](schema-dictionary/research--invalidation.md) | `schemas/research.schema.json` | `#/$defs/invalidation` | 9 |
| OBJ-030 | [source_manifest](schema-dictionary/source_manifest--source_manifest.md) | `schemas/source-manifest.schema.json` | `#` | 17 |

