# 研究与证据治理 Schema 契约体系技术设计规格书 (Research & Evidence Schema Specification)

> **文档编号**：`SY-SPEC-001`  
> **功能标识**：`CONTRACT_SCHEMA_RESEARCH_AND_MANIFEST_SUITE`  
> **所属业务分类**：类别 E：底层数据工程层面（六步研究契约、资料清单 Manifest、强类型校验门禁与时空防篡改）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 研究主契约：`schemas/research.schema.json`  
> - 资料主契约：`schemas/source-manifest.schema.json`  
> - 字段机器可读定义：`schemas/schema-field-guide.json`  
> - 自动化校验程序：`scripts/validate_research.py`  
> - 契约回归测试：`scripts/test_research_contract.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方机构研究与量化决策中，研报数据的非标化与时间错配是产生系统性风险的主要根源。传统投研文档常存在三大缺陷：一是字段命名随性、结构随意扩张，导致下游程序无法自动解析；二是事实证据与主观推断混淆，缺乏可追溯的证据哈希绑定；三是时间戳定义混乱，混淆财报所属期间（Period）、官方发布时间（Published）、公众可得时间（Available）与系统抓取时间（Acquired），引发利用后验数据测算历史的前瞻性偏差。本功能构建基于 JSON Schema Draft 2020-12 强类型契约、逐字段业务约束与单向因果时间防线的投研标准体系。

### 2. 核心用途
本功能解决三大投研数字化工程问题：
1. **强契约驱动的统一事实源 (SSOT)**：定义 `research.schema.json`（247 处业务属性）与 `source-manifest.schema.json`，禁止任何未经声明的额外属性 (`additionalProperties: false`)；
2. **微观事实到宏观判断的四层引用图谱**：建立从资料版本 (`source_id + revision`) ➔ 证据项 (`evidence.id`) ➔ 指标观测 (`observation.id`) ➔ 逻辑判断与计算 (`claim.id` / `calculation.id`) ➔ 六步决策输出的因果溯源网络；
3. **严格时间契约与历史回放门禁**：通过 ISO-8601 严格时区时间戳与精度枚举，支持历史任意截面数据的无偏回溯检验。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data_sources/` 与官方采集文件：提供未经修改的原始 PDF、XBRL、JSON 底稿。
- `schemas/source-manifest.schema.json`：约束原始资料登记凭证。

### 2. 后置消费 (Outputs To Downstream)
- `scripts/validate_research.py`：消费研究记录 JSON，执行六步跨步骤逻辑与门槛校验。
- `scripts/data_store.py` (`DataStore`)：执行只追加 (`Append-Only`) 入库封存与快照生成。
- `financial_core/`：消费经契约核验的标准财务事实驱动量化计算。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  分析师/自动流水线生成研究记录 JSON  │
└──────────────────┬───────────────────┘
                   │ (Draft 2020-12 强类型校验)
                   ▼
┌──────────────────────────────────────┐
│  Schema 契约与业务规则检验器         │
│  ├── 结构契约: research.schema.json  │
│  ├── 规则门禁: validate_research.py  │
│  └── 偏序断言: published <= available│
└──────────────────┬───────────────────┘
                   │ (契约校验 100% PASS)
                   ▼
┌──────────────────────────────────────┐
│  数据目录证据绑定与不可变快照固化    │
│  (source-map 绑定与 DataStore 归档)  │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

研究主契约顶层核心字段契约定义如下表：

| 参数名称 | 字段标识 (Field Name) | 数据类型 | 计量单位 | 取值范围 | 业务含义与说明 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 研究记录唯一标识 | `research_id` | `str` | 字符串 | 符合正则命名 | 该份六步研究的全局唯一业务主键。 |
| 标的稳定标识 | `company_id` | `str` | 字符串 | 非空字符串 | 发行公司法律主体代码（如 `NVDA_US`）。 |
| 数据截止基准日 | `as_of_date` | `str` | ISO-8601日期 | `YYYY-MM-DD` | 本次研究依赖所有事实数据的历史截面日期。 |
| 证据引用清单 | `evidences` | `List[Object]`| 列表对象 | 长度 $\ge 1$ | 支撑本次研究全部判断的原子证据数组。 |
| 指标观测集合 | `observations` | `List[Object]`| 列表对象 | 长度 $\ge 1$ | 经标准度量的财务或经营指标实测数值集。 |
| 研判与推论集合 | `claims` | `List[Object]`| 列表对象 | 长度 $\ge 1$ | 包含事实、推断、假设与未知的显式陈述。 |
| 量化计算模型 | `calculations` | `List[Object]`| 列表对象 | 长度 $\ge 1$ | 估值模型公式、输入参数及情景结果集。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 E-1：微观证据向宏观决策四层引用拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【层级 1: 原始资料版本 (Source Manifest)】  │
│  data/catalog/objects/{hash}.blob (登记 source_id + rev)│
└───────────────────────────┬────────────────────────────┘
                            │ (由 source-map 唯一映射绑定)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【层级 2: 原子证据对象 (evidence.id)】      │
│  e_main: 标注原始文档定位页码、原文摘录与 SHA-256 摘要  │
└───────────────────────────┬────────────────────────────┘
                            │ (支撑观测与判断)
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ 【层级 3A: 指标观测对象】 │ │ 【层级 3B: 业务研判对象】 │
│ observations.id (o_fcf)   │ │ claims.id (c_assumption)  │
│ 规定指标、期间、数值与单位│ │ 声明事实/推断/假设/不适用 │
└─────────────┬─────────────┘ └───────────┬───────────────┘
              │                           │
              └─────────────┬─────────────┘
                            │ (输入量化估值计算)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【层级 4: 量化计算与六步决策输出】          │
│  calculations.id (calc_dcf) ──> Step 1~6 终审决策输出  │
└────────────────────────────────────────────────────────┘
```

#### 图 E-2：严格时间契约单向因果偏序时序图
```
  时间轴 (Time Arrow)
    │
    ├─► t_period:    [会计核算期间] ──> 业务活动实际发生的历史年度或季度区间
    │
    ├─► t_published: [官方披露时点] ──> 发行人将报表正式上传监管系统的时刻
    │
    ├─► t_available: [公众可得时点] ──> 交易所或公众终端可合法查阅该信息的时刻
    │
    ├─► t_acquired:  [系统采集时点] ──> 本地抓取程序落盘 .blob 并计算哈希的时刻
    │
    └─► t_research:  [研报签署时点] ──> 六步研究完成估值推演并锁定签名的时刻
  刚性偏序断言: t_published <= t_available <= t_acquired <= t_research
```

#### 图 E-3：字段完整性与值缺失判定决策树
```
                   ┌─────────────────────────┐
                   │    指标观测值判定流程   │
                   └────────────┬────────────┘
                                │
                 该指标在指定期间是否有披露值?
                                ├──────────────────────── 是 ──► [value = 数值实数]
                                │                                [missing_reason = null]
                                ▼ 否
                 该指标对该业务模式是否适用?
                                ├──────────────────────── 否 ──► [value = null]
                                │                                [missing_reason = "NOT_APPLICABLE"]
                                ▼ 是
                   ┌─────────────────────────┐
                   │   [value = null]        │
                   │   [missing_reason = 说明]│
                   │   (触发补数或不确定性提示)│
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **时间契约偏序拓扑排序断言**：
   $$\text{Epoch}(t_{\text{published}}) \le \text{Epoch}(t_{\text{available}}) \le \text{Epoch}(t_{\text{acquired}}) \le \text{Epoch}(t_{\text{research}})$$
   若任意相邻节点的时间差值 $\Delta t < 0$，系统判定发生时间倒流穿越，直接触发 `TimeContractViolationError` 终止流水线。
2. **观测事实加权置信度方程**：
   $$Score_{\text{observation}} = \mathbb{I}(\text{is\_verified}) \times \left(1.0 - 0.20 \times \mathbb{I}(\text{is\_restated})\right) \times \frac{1}{1 + \lambda \times \Delta t_{\text{lag}}}$$
   其中：$\Delta t_{\text{lag}}$ 为从可得时间到采集时间的滞后天数。
3. **证据覆盖率与完整度自检方程**：
   $$\text{EvidenceCoverageRate} = \frac{\sum_{c \in \text{Claims}} \mathbb{I}(|\text{c.evidence\_ids}| \ge 1)}{|\text{Claims}|} \equiv 1.00$$
   断言要求：全量推论与判断的证据支持率必须严格等于 $100\%$。

---

## 五、 状态机与研究生命周期 (State Registry)

### 1. 业务对象状态与质量分类空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定条件 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `STAT_01` | `FACT_ESTABLISHED`| 客观事实确立 | 经官方财报原件核验且可精准定位。 | 允许作为估值底层依据。 |
| `STAT_02` | `INFERENCE_BOUND` | 逻辑推论闭环 | 基于明确事实与前置步骤推导得出。 | 记录传导路径与敏感度。 |
| `STAT_03` | `EXPLICIT_ASSUME` | 显式假设限定 | 包含明确的边界与外部失效触发条件。| 关联黑天鹅敏感度测试。 |
| `STAT_04` | `NOT_APPLICABLE`  | 明确不适用标 | 商业模式不具备该特征（如重资产指标）。| 显式置空并记录不适用说明。|

---

## 六、 返回值与输出数据结构 (Output Contracts)

研究契约经校验器通过后，产出标准校验与入库凭证：

```json
{
  "research_id": "RES_NVDA_20261103_001",
  "contract_version": "1.1.0",
  "validation_passed": true,
  "violations_count": 0,
  "time_contract_status": "MONOTONIC_VALID",
  "evidence_integrity": {
    "total_evidences": 12,
    "total_claims": 28,
    "unsupported_claims": 0,
    "coverage_rate_pct": 100.0
  },
  "as_of_timestamp": "2026-11-03T15:00:00Z",
  "archived_blob_path": "data/catalog/research/RES_NVDA_20261103_001/rev_1.json"
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 契约版本号 | `contract_version` | `str` | 语义化版本 | 本次研究所遵循的 Schema 版本（如 `1.1.0`）。 |
| 校验通过标识 | `validation_passed` | `bool` | 布尔值 | 指示是否 100% 通过结构与业务跨字段门禁。 |
| 时间契约状态 | `time_contract_status`| `str` | 枚举字符串 | 时间单调递增验证结果，合规为 `MONOTONIC_VALID`。|
| 证据覆盖率 | `coverage_rate_pct` | `float` | 百分比 | 获得底层证据支持的判断占总判断的比例（刚性 100%）。|
| 归档快照路径 | `archived_blob_path` | `str` | 相对文件路径 | 经哈希锁定的不可变研究快照在数据目录中的物理存储位置。|

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁额外属性扩展**：所有 JSON Schema 根节点与嵌套对象必须显式配置 `"additionalProperties": false`，严禁写入未在字典中声明的任意字段。
- [ ] **证据覆盖率刚性 100%**：任何 `claim` 必须至少关联一个合法的 `evidence.id`，严禁存在孤立无证据支持的主观判断。
- [ ] **时间偏序单调递增断言**：必须满足 $t_{\text{published}} \le t_{\text{available}} \le t_{\text{acquired}} \le t_{\text{research}}$，发生时间倒流直接抛错阻断。
- [ ] **严禁字符串 "null" 代替 JSON null**：缺失值或未知项必须使用标准 JSON `null` 并在 `missing_reason` 中说明原因，禁止写入字符串 `"null"` 或 `"None"`。
- [ ] **只追加不可变底账维护**：更新已有研究必须递增 `revision` 并生成新快照，严禁对已登记的历史版本执行覆盖或物理删除。
