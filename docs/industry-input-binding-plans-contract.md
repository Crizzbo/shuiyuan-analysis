# 行业驱动输入绑定方案与闭合契约技术设计规格书 (Industry Input Binding Plans Contract Spec)

> **功能标识**：`INDUSTRY_INPUT_BINDING_PLANS_CONTRACT_SPEC`  
> **所属业务分类**：类别 B：中观行业存量博弈与增量产出 / 底层数据工程层面（行业输入绑定方案、强类型闭合 Schema 契约校验、原子观测口径匹配与范围单调性锁定）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 方案配置底账：`knowledge/metrics/industry-input-binding-plans.json`  
> - 闭合契约定义：`schemas/industry-input-binding-plans.schema.json`  
> - 输入台账中枢：`financial_reporting/industry_inputs.py`  
> - 方案构建程序：`scripts/build_industry_input_binding_plans.py`  
> - 契约自动化测试套件：`scripts/test_industry_binding_plans.py`、`scripts/test_industry_driver_inputs.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在 41 个细分行业的专业胜负手指标计算中，行业指标所需的底层输入项（如医疗成本、净息差利息收入、SaaS 客户留存率）往往无法通过通用科目字典自动匹配。若采用传统模糊文本匹配或未经审核的启发式关联，极易引发严重法证灾难：一是“范围错配（Scope Mismatch）”，例如将跨国巨头的全球合并保费收入与北美单一子公司的医疗赔付成本混同计算，得出荒谬的赔付率；二是“期间倒置（Period Inversion）”，将累计 9 个月的成本与单季度的保费相除；三是“口径偷换（Definition Drift）”，将未扣除佣金的毛额替代净额。为此，系统设立了高度受控、人工法证审核的行业驱动输入绑定方案（Binding Plans），通过闭合式的 JSON Schema 契约（Draft 2020-12），刚性锁定每个行业驱动的具体公司变体、输入槽位原子映射、口径限制说明与起止会计期间。

### 2. 核心用途
本功能解决全系统三大输入绑定规范与审计问题：
1. **闭合式强约束绑定契约 (Closed Binding Schema)**：遵循 `schemas/industry-input-binding-plans.schema.json`，启用 `additionalProperties: false`，杜绝任何未经声明的冗余字段或未经验证的映射逻辑注入；
2. **多维原子观测绑定规范 (Atomic Observation Slots)**：将行业驱动所需的每一个输入槽位，映射为具备 `component`（组成项）、`kind`（数值/范围元数据/期间元数据）、`scope`（业务范围）与 `unit`（法定物理计量单位）的强类型原子绑定；
3. **同范围约束与期间单调刚性锁死 (Scope & Period Invariants)**：通过 `requires_same_scope: true` 强制分子分母属于同一合并实体，且严格核验 `period_start <= period_end`，杜绝时间与经济边界倒置。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `knowledge/metrics/industry-specifications.json`：提供 41 行业规格中的 `parent_metric_id` 与 `required_inputs_zh` 必需输入槽位定义。
- `data/catalog/`：提供不可变内容寻址的原子观测底层证据。

### 2. 后置消费 (Outputs To Downstream)
- `knowledge/metrics/industry-input-binding-plans.json`：生成经审核的统一绑定配置方案。
- `financial_reporting/industry_inputs.py`：消费绑定方案构建全系统 41 行业驱动输入总台账。
- `scripts/build_industry_driver_inputs.py`：自动化调度执行驱动总台账构建与验证。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  行业核心规格 (industry-specifications)│
└──────────────────┬───────────────────┘
                   │ (提取 123 个核心驱动的必需槽位清单)
                   ▼
┌──────────────────────────────────────┐
│  人工法证审核与绑定方案构建器        │
│  (scripts/build_industry_input_...py)│
│  ├── 审查代表标的报告口径等价性      │
│  ├── 映射 component, scope, unit     │
│  └── 声明 limitations_zh 使用限制    │
└──────────────────┬───────────────────┘
                   │ (输出方案并执行闭合 Schema 契约核验)
                   ▼
┌──────────────────────────────────────┐
│  闭合契约验证中枢 (Draft 2020-12)    │
│  ├── 验证 additionalProperties=false │
│  ├── 校验 period_start <= period_end │
│  └── 校验 parent_metric_id 唯一性    │
└──────────────────┬───────────────────┘
                   │ (落盘为不可变绑定方案配置)
                   ▼
┌──────────────────────────────────────┐
│  驱动输入台账生成器 (industry_inputs) │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

行业输入绑定方案核心实体与字段属性规范如下表：

### 1. 核心实体契约对照表
| 字段标识 | 数据类型 | 计量单位 | 约束边界 | 业务含义与说明 |
| :--- | :---: | :---: | :---: | :--- |
| `schema_version` | `str` | 常量字符串 | 固定 `"1.0.0"` | 绑定方案契约版本，仅支持生产基准 1.0.0。 |
| `parent_metric_id` | `str` | 字符串 | 规范命名 | 对应行业规格中的唯一父驱动 ID，严禁重复定义。 |
| `selected_variant_zh` | `str` | 中文字符串 | 非空描述 | 选定的具体公司、产品范围、期间与指标口径全称。 |
| `definition_reviewed` | `bool` | 布尔值 | 布尔值 | 变体业务定义是否经法证审核通过（不等于输入齐备）。|
| `requires_same_scope` | `bool` | 布尔值 | 布尔值 | 是否要求所有槽位必须使用完全一致的经济实体范围。 |
| `period_start` | `str \| null` | ISO 日期 | `YYYY-MM-DD` 或 `null` | 期间起点（期末时点观测允许为 `null`，严禁伪造）。 |
| `period_end` | `str` | ISO 日期 | `YYYY-MM-DD` | 期间终点或报告期末日期（必须 $\ge$ `period_start`）。 |
| `slots` | `Dict[str, List]`| 字典对象 | 至少包含 1 项 | 中文输入名称到绑定列表的映射，名称必须严格对齐规格。|
| `limitations_zh` | `List[str]` | 中文列表 | 至少 1 项非空描述 | 必需声明的口径局限性与使用边界，严禁空列表。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 B-1：绑定方案多层级实体拓扑图 (Plan Hierarchy Topology)
```
┌────────────────────────────────────────────────────────┐
│             【IndustryInputBindingPlans 根对象】       │
│  • schema_version: "1.0.0"                             │
│  • additionalProperties: false (闭合式契约防注入)      │
└───────────────────────────┬────────────────────────────┘
                            │ (1 对多包含 plans)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Plan 独立驱动绑定方案】                  │
│  • parent_metric_id: "pct_healthcare_mcr"              │
│  • definition_reviewed: true | requires_same_scope: true│
│  • period_start: "2023-01-01" | period_end: "2023-12-31"│
└───────────────────────────┬────────────────────────────┘
                            │ (按中文槽位名分解 slots)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Slot 槽位绑定项 (Binding)】              │
│  • component: "medical_costs" (原子组成项标识)         │
│  • kind: "numeric" | "scope_metadata" | "period_meta" │
│  • scope: "unitedhealth_group_consolidated"            │
│  • unit: "USD" (法定计量单位)                          │
└────────────────────────────────────────────────────────┘
```

#### 图 B-2：绑定方案加载、结构校验与同范围对齐时序图
```
  调度器 / 台账构建器
    │
    ├─► [读取 JSON 方案] ──> 加载 knowledge/metrics/industry-input-binding-plans.json
    │
    ├─► [Schema 契约拦截] ──> Draft202012Validator 严格校验 additionalProperties
    │
    ├─► [期间单调性校验] ──> 断言 period_start <= period_end
    │
    ├─► [槽位完整性核验] ──> 遍历 slots 检查是否包含规格声明的全部 required_inputs_zh
    │
    ├─► [同范围匹配核查] ──> 若 requires_same_scope=true，断言所有 numeric 槽位 scope 严格相等
    │
    └─► [放行交付] ──> 注入 financial_reporting.industry_inputs.build_ledger
```

#### 图 B-3：绑定方案准入与口径合法性判定决策树
```
                   ┌─────────────────────────┐
                   │    绑定方案核验输入     │
                   └────────────┬────────────┘
                                │
                 是否通过 Draft 2020-12 闭合 Schema 校验?
                                ├──────────────────────── 否 ──► 【SCHEMA_VALIDATION_FAILURE】(阻断：报文非法)
                                ▼ 是
                 period_start 是否存在且大于 period_end?
                                ├──────────────────────── 是 ──► 【CHRONOLOGY_INVERSION_ERROR】(阻断：时间倒置)
                                ▼ 否
                 requires_same_scope 是否满足同范围一致性?
                                ├──────────────────────── 否 ──► 【SCOPE_COLLISION_ERROR】(阻断：范围不匹配)
                                ▼ 是
                   ┌─────────────────────────┐
                   │  【PLAN_VALIDATED: OK】 │
                   │  方案合法，允许装配台账 │
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **期间单调性因果守恒方程**：
   $$\Delta t = \text{Date}(\text{period\_end}) - \text{Date}(\text{period\_start}) \ge 0$$
   当 `period_start` 不为 `null` 时，$\Delta t$ 必须非负；严禁出现负向时长或未来穿越。
2. **同范围实体同构方程**：
   $$\forall i, j \in \text{Slots}_{\text{numeric}}, \quad \text{Scope}(s_i) \equiv \text{Scope}(s_j) \quad (\text{if } \text{requires\_same\_scope} = \text{true})$$
   当开启强同范围约束时，所有数值型输入槽位的经济主体范围必须全等，严禁分部与合并报表口径混合运算。
3. **槽位映射完全覆盖度方程**：
   $$\text{Coverage} = \frac{|\text{Slots}_{\text{plan}} \cap \text{Inputs}_{\text{spec}}|}{|\text{Inputs}_{\text{spec}}|} \equiv 1.0$$
   绑定方案中提供的槽位键名集合必须与行业规格中定义的必需输入集合严格对齐。

---

## 五、 状态机与生命周期 (Plan Lifecycle)

### 1. 绑定方案审核与就绪状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `PLN_01` | `DRAFT_PENDING` | 草稿待审态 | 方案初稿已建立，但 `definition_reviewed = false`。 | 允许预览，严禁驱动生产计算。 |
| `PLN_02` | `REVIEWED_VALID`| 审核通过态 | 方案经法证审核，且闭合 Schema 校验与同范围检验全通过。| 允许装配行业驱动台账。 |
| `PLN_03` | `SCOPE_MISMATCH`| 范围冲突拦截态| 声明了 `requires_same_scope` 但各槽位使用了不同分部范围。 | 阻断台账构建并报错。 |
| `PLN_04` | `TIME_INVERTED` | 时间倒置拦截态| `period_start` 晚于 `period_end`。 | 抛出不可变时间异常。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

行业输入绑定方案标准化持久化记录结构体：

```json
{
  "schema_version": "1.0.0",
  "plans": [
    {
      "parent_metric_id": "pct_healthcare_mcr",
      "selected_variant_zh": "UnitedHealth Group 报告医疗成本率 (MCR)",
      "definition_reviewed": true,
      "requires_same_scope": true,
      "period_start": "2023-01-01",
      "period_end": "2023-12-31",
      "slots": {
        "医疗成本": [
          {
            "component": "medical_costs",
            "kind": "numeric",
            "scope": "unitedhealth_group_consolidated",
            "unit": "USD"
          }
        ],
        "保费收入": [
          {
            "component": "premiums",
            "kind": "numeric",
            "scope": "unitedhealth_group_consolidated",
            "unit": "USD"
          }
        ]
      },
      "limitations_zh": [
        "仅适用于 UnitedHealth Group 合并口径下的商业健康险与医疗服务",
        "保费收入未扣除向外部承保机构分保支出的毛额口径需在附注中复核"
      ]
    }
  ]
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 契约版本 | `schema_version` | `str` | 常量 | 方案遵循的 Schema 契约版本（固定 `"1.0.0"`）。 |
| 绑定方案列表 | `plans` | `List[Plan]` | 列表 | 经人工审核的具体公司口径选用方案集合。 |
| 父驱动代号 | `parent_metric_id` | `str` | 字符串 | 行业规格中定义的行业胜负手驱动唯一标识。 |
| 口径审核标识 | `definition_reviewed`| `bool` | 布尔值 | 该变体的会计与商业口径是否已通过审核。 |
| 同范围要求 | `requires_same_scope`| `bool` | 布尔值 | 指示分子分母是否必须属于完全相同的合并范围。 |
| 槽位映射映射 | `slots` | `dict` | 字典 | 中文输入名称到原子观测项的映射明细。 |
| 使用局限说明 | `limitations_zh` | `List[str]` | 列表 | 人工法证审核确认的口径适用边界与缺陷披露。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁包含任何未声明扩展字段**：输入方案文件必须严格通过 `schemas/industry-input-binding-plans.schema.json` 校验，开启 `additionalProperties: false` 拦截。
- [ ] **同范围约束刚性对齐**：当 `requires_same_scope` 为 `true` 时，相关数值型槽位的 `scope` 必须字面量完全相同，严禁使用前缀或模糊匹配。
- [ ] **时间起止绝对单调性**：`period_start` 存在时必须小于等于 `period_end`，严禁出现逆序时间戳。
- [ ] **局限性说明严禁为空**：每个绑定方案必须显式提供至少 1 条针对该口径缺陷或局限性的具体中文说明（`limitations_zh`），严禁空列表。
- [ ] **离线纯净运行无外部依赖**：方案校验器与台账生成程序必须使用本地标准库与本地项目内依赖，严禁进行任何远程网络解析或联网抓取。
