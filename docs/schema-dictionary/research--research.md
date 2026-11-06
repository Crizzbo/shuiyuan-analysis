# OBJ-001 · research 单表说明

文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。

[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)

## 1. 对象定义

- 所属契约：[schemas/research.schema.json](../../schemas/research.schema.json)。
- 定义位置：`#`。
- 引用位置（Schema 指针）：根对象。
- 对象额外字段：禁止。
- 属性定义数：15（含当前表所属内联对象属性，不含引用对象的展开属性）。

字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。

## 2. 字段表

| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |
|---|---|---|---|---|---|---|
| `research.schema_version` | 契约版本 | 枚举 | 是 | 否 | 枚举=['1.0.0', '1.1.0'] | 数据契约版本，支持 1.0.0 与 1.1.0；新版保留发布日期精度，不表示步骤或软件版本。 |
| `research.research_id` | 研究标识 | string | 是 | 否 | 最短字符=1 | 研究记录的稳定身份，同一研究各修订保持不变。 |
| `research.revision` | 修订号 | integer | 是 | 否 | 最小=1 | 该研究或资料系列的修订号，从 1 连续增加；旧版不能覆盖。 |
| `research.is_fictional` | 合成研究标记 | boolean | 是 | 否 | 无显式附加结构约束 | 标记整份研究是否为合成演示。true 不等于所有测试，false 不等于资料已核实；真实研究不得包含 synthetic 证据，且入库时须绑定已登记来源。 |
| `research.as_of` | 信息截止时间 | string | 是 | 否 | 格式=date-time | 本次研究使用信息的截止时点，含时区；不能引用此时尚不可得的信息。 |
| `research.recorded_at` | 记录形成时间 | string | 是 | 否 | 格式=date-time | 本次研究记录形成时间；不得早于 as_of。 |
| `research.market_session_date` | 市场交易日期 | string | 是 | 否 | 格式=date | 本次研究选用的美股交易日期，不是报告生成地的自然日期。应按实际交易日选择；当前校验仅检查日期格式及不晚于 as_of 的日期部分，未接入交易日历。 |
| `research.investment_horizon_months` | 投资判断期限（月） | integer | 是 | 否 | 最小=1 | 投资判断期限（月）；项目默认 6—24，其他期限应在说明中解释。 |
| `research.subject` | 研究对象 | subject | 是 | 否 | 引用=#/$defs/subject | 研究对象，公司、证券与业务分部身份分开。 |
| `research.evidence` | 证据登记表 | array<evidence> | 是 | 否 | 至少项数=0 | 本次研究的证据登记表，其他对象通过 evidence_refs 引用。 |
| `research.observations` | 指标观测登记表 | array<observation> | 是 | 否 | 至少项数=0 | 指标观测登记表，保留时点、单位、口径与缺失原因。 |
| `research.claims` | 判断登记表 | array<claim> | 是 | 否 | 至少项数=0 | 事实、推断、假设、未知或不适用的判断登记表。 |
| `research.calculations` | 计算登记表 | array<calculation> | 是 | 否 | 至少项数=0 | 计算登记表，保留实现文件、输入、假设、结果及校验记录。 |
| `research.steps` | 六步研究记录 | array<step1, step2, step3, step4, step5, step6> | 是 | 否 | 至少项数=6；最多项数=6 | 六步记录，严格 S1 到 S6，各步骤仍须独立通过验收。 |
| `research.invalidation_events` | 失效事件列表 | array<invalidation> | 是 | 否 | 至少项数=0 | 新证据导致结论失效与重新研究的事件；空数组表示无事件。 |

## 3. 关联对象

- [calculation](research--calculation.md)：本表引用的公共对象定义。
- [claim](research--claim.md)：本表引用的公共对象定义。
- [evidence](research--evidence.md)：本表引用的公共对象定义。
- [invalidation](research--invalidation.md)：本表引用的公共对象定义。
- [observation](research--observation.md)：本表引用的公共对象定义。
- [step1](research--step1.md)：本表引用的公共对象定义。
- [step2](research--step2.md)：本表引用的公共对象定义。
- [step3](research--step3.md)：本表引用的公共对象定义。
- [step4](research--step4.md)：本表引用的公共对象定义。
- [step5](research--step5.md)：本表引用的公共对象定义。
- [step6](research--step6.md)：本表引用的公共对象定义。
- [subject](research--subject.md)：本表引用的公共对象定义。

## 4. 精确结构定义

以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。

<details>
<summary>research.schema_version · 契约版本</summary>

Schema 指针：`#/properties/schema_version`。

```json
{
  "enum": [
    "1.0.0",
    "1.1.0"
  ]
}
```

</details>

<details>
<summary>research.research_id · 研究标识</summary>

Schema 指针：`#/properties/research_id`。

```json
{
  "type": "string",
  "minLength": 1
}
```

</details>

<details>
<summary>research.revision · 修订号</summary>

Schema 指针：`#/properties/revision`。

```json
{
  "type": "integer",
  "minimum": 1
}
```

</details>

<details>
<summary>research.is_fictional · 合成研究标记</summary>

Schema 指针：`#/properties/is_fictional`。

```json
{
  "type": "boolean"
}
```

</details>

<details>
<summary>research.as_of · 信息截止时间</summary>

Schema 指针：`#/properties/as_of`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>research.recorded_at · 记录形成时间</summary>

Schema 指针：`#/properties/recorded_at`。

```json
{
  "type": "string",
  "format": "date-time"
}
```

</details>

<details>
<summary>research.market_session_date · 市场交易日期</summary>

Schema 指针：`#/properties/market_session_date`。

```json
{
  "type": "string",
  "format": "date"
}
```

</details>

<details>
<summary>research.investment_horizon_months · 投资判断期限（月）</summary>

Schema 指针：`#/properties/investment_horizon_months`。

```json
{
  "type": "integer",
  "minimum": 1
}
```

</details>

<details>
<summary>research.subject · 研究对象</summary>

Schema 指针：`#/properties/subject`。

```json
{
  "$ref": "#/$defs/subject"
}
```

</details>

<details>
<summary>research.evidence · 证据登记表</summary>

Schema 指针：`#/properties/evidence`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/evidence"
  },
  "minItems": 0
}
```

</details>

<details>
<summary>research.observations · 指标观测登记表</summary>

Schema 指针：`#/properties/observations`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/observation"
  },
  "minItems": 0
}
```

</details>

<details>
<summary>research.claims · 判断登记表</summary>

Schema 指针：`#/properties/claims`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/claim"
  },
  "minItems": 0
}
```

</details>

<details>
<summary>research.calculations · 计算登记表</summary>

Schema 指针：`#/properties/calculations`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/calculation"
  },
  "minItems": 0
}
```

</details>

<details>
<summary>research.steps · 六步研究记录</summary>

Schema 指针：`#/properties/steps`。

```json
{
  "type": "array",
  "prefixItems": [
    {
      "$ref": "#/$defs/step1"
    },
    {
      "$ref": "#/$defs/step2"
    },
    {
      "$ref": "#/$defs/step3"
    },
    {
      "$ref": "#/$defs/step4"
    },
    {
      "$ref": "#/$defs/step5"
    },
    {
      "$ref": "#/$defs/step6"
    }
  ],
  "items": false,
  "minItems": 6,
  "maxItems": 6
}
```

</details>

<details>
<summary>research.invalidation_events · 失效事件列表</summary>

Schema 指针：`#/properties/invalidation_events`。

```json
{
  "type": "array",
  "items": {
    "$ref": "#/$defs/invalidation"
  },
  "minItems": 0
}
```

</details>

