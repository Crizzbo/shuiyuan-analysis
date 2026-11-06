# 行业核心驱动因子输入台账与槽位绑定技术设计规格书 (Industry Driver Inputs & Slot Binding Spec)

> **功能标识**：`INDUSTRY_DRIVER_INPUTS_AND_SLOT_BINDING_SPEC`  
> **所属业务分类**：类别 B：中观行业存量博弈与增量产出（41 细分行业核心胜负手驱动因子、必需输入槽位绑定、口径严格审核与研究闸门阻断机制）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 输入台账中枢：`financial_reporting/industry_inputs.py`  
> - 行业特定规格：`financial_reporting/industry_specific.py`  
> - 闭合 Schema 契约：`schemas/industry-driver-inputs.schema.json`  
> - 驱动输入台账索引：`data/financial/industry-driver-input-verification.json`  
> - 原始业务规格底账：`knowledge/metrics/industry-specifications.json`  
> - 绑定方案构建程序：`scripts/build_industry_input_binding_plans.py`  
> - 台账构建调度程序：`scripts/build_industry_driver_inputs.py`  
> - 自动化测试套件：`scripts/test_industry_driver_inputs.py`、`scripts/test_industry_specific.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方机构面向 41 个细分产业进行深度基本面建模与胜负手推演时，通用财务报表科目（如净利润、营业收入、总资产）往往无法穿透行业特异性商业本质。例如：医疗健康行业的医疗成本率（MCR）、商业银行的管理税当量净息收益率（NIM）、半导体与科技硬件的新签订单与出货量、云计算的净留存率（NDR）等，均依赖高度非标的行业驱动输入。然而，传统行业研究常面临三大系统性缺陷：一是“槽位偷换”，将不同范围（如分部与集团）、不同期间（如单季与累计）或不同口径的背景数据随意填充为核心驱动；二是“概念混淆”，将未经审核的公司特定口径直接等同于行业标准口径；三是“缺乏阻断机制”，在核心驱动输入不全或未经大样本校准时，系统私自启用经验阈值输出虚假的交易买卖点。本规范确立 41 细分行业 123 个核心驱动的严格槽位模型（Slot Model）、口径审核状态机与全流程研究阻断闸门。

### 2. 核心用途
本功能解决全系统三大行业驱动治理与输入审计问题：
1. **41 行业 123 个核心驱动槽位严格绑定 (123-Driver Slot Contracts)**：为全系统所有行业驱动定义原子输入槽位（`slots`），区分数值（`numeric`）、经济范围（`scope_metadata`）与期间元数据（`period_metadata`），缺失任意必需槽位刚性标记为缺失；
2. **口径审核与计算准备双重状态分离**：将“槽位是否采齐（`input_status`）”与“业务口径是否经法证审核（`definition_status`）”解耦，仅在两项同时核验通过时才允许 `calculation_ready = true`；
3. **行业驱动研究闸门绝对阻断 (Research Gate Blocked)**：在缺乏长期大样本历史回测统计校准前，所有驱动的 `research_gate` 一律保持 `blocked`，杜绝任何未经验证的量化阈值自动触发投资指令。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data_sources/official_filings/`：提供具备 SHA-256 哈希锁定的经审计原始年报 PDF/XBRL 底稿。
- `knowledge/metrics/industry-specifications.json`：提供 41 细分行业原始驱动业务定义与必需槽位清单。
- `data/catalog/`：提供不可变内容寻址的原子观测快照。

### 2. 后置消费 (Outputs To Downstream)
- `knowledge/metrics/driver-inputs/`：生成 41 份结构化行业分表与统一目录。
- `data/financial/industry-driver-input-verification.json`：发布输入台账最新索引。
- `financial_core/engines/business_quality_and_moat_engine.py`：消费合规驱动输入驱动行业护城河评分。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  经审计的官方披露原件与不可变观测    │
└──────────────────┬───────────────────┘
                   │ (提取原子观测与页码定位)
                   ▼
┌──────────────────────────────────────┐
│  行业输入绑定方案中枢 (binding_plans)│
│  ├── 映射必需槽位 (slots)            │
│  ├── 区分数值与范围/期间元数据       │
│  └── 校验口径等价性与费用覆盖        │
└──────────────────┬───────────────────┘
                   │ (执行台账构建与验证)
                   ▼
┌──────────────────────────────────────┐
│  行业驱动输入台账生成器 (driver_inputs)│
│  ├── 验证 41 行业 123 驱动完整性     │
│  ├── 闭合 Schema 契约校验            │
│  └── 锁定 research_gate = blocked    │
└──────────────────┬───────────────────┘
                   │ (落盘不可变底账)
                   ▼
┌──────────────────────────────────────┐
│  生成 41 行业分表与全局台账索引      │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

行业驱动台账核心字段字典与槽位配置规范如下表：

### 1. 核心实体契约对照表
| 字段标识 | 数据类型 | 计量单位 | 约束边界 | 业务含义与说明 |
| :--- | :---: | :---: | :---: | :--- |
| `parent_metric_id` | `str` | 字符串 | 规范命名 | 沿用项目原有驱动标识，保持全局唯一业务键。 |
| `industry_id` | `str` | 字符串 | 41行业代码 | 所属 41 内部研究行业分类代码（如 `ind_healthcare`）。 |
| `selected_variant_zh`| `str` | 中文字符串 | 非空描述 | 本次选用的公司、产品、业务范围和计量基础。 |
| `slots` | `List[Object]` | 列表 | 与原始规格对齐 | 该驱动必须满足的原子输入槽位集合。 |
| `missing_slot_ids` | `List[str]` | 列表 | 缺失ID列表 | 必需输入中当前没有绑定有效证据的槽位清单。 |
| `input_status` | `str` | 枚举字符串 | 3 态枚举 | 输入槽位齐备状态（`input_complete` 等）。 |
| `definition_status` | `str` | 枚举字符串 | 2 态枚举 | 业务口径审核状态（`company_variant_reviewed` 等）。|
| `calculation_ready` | `bool` | 布尔值 | 布尔值 | 指示该驱动是否达到可计算门槛（严禁伪造）。 |
| `research_gate` | `str` | 常量枚举 | 固定 `blocked` | 研究闸门状态，本版本刚性阻断。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 B-1：41 行业 123 驱动槽位与证据绑定架构拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【41 行业驱动输入总台账 (Drivers Ledger)】  │
│  • 覆盖: 41 个细分产业、123 个核心胜负手驱动           │
│  • 架构: schemas/industry-driver-inputs.schema.json    │
└───────────────────────────┬────────────────────────────┘
                            │ (包含 123 个驱动项)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Driver 驱动对象 (如医疗成本率 MCR)】     │
│  • parent_metric_id: "pct_healthcare_mcr"              │
│  • selected_variant_zh: "UnitedHealth 报告医疗成本率"  │
└───────────────────────────┬────────────────────────────┘
                            │ (分解为必需输入槽位 slots)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Slot 原子输入槽位集合】                  │
│  • slot_1 (numeric): 医疗成本金额 ($M)                │
│  • slot_2 (numeric): 保险保费收入 ($M)                │
│  • slot_3 (scope_metadata): 经济合并范围声明           │
│  • slot_4 (period_metadata): 统计起止期间声明          │
└───────────────────────────┬────────────────────────────┘
                            │ (N 对 1 绑定底层证据)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【不可变原子观测与原文摘录 (Observations)】│
│  • observation_id: 64位内容哈希指纹                    │
│  • source_ref: 官方年报 PDF 字节摘要与页码定位         │
└────────────────────────────────────────────────────────┘
```

#### 图 B-2：驱动槽位清洗、单位归一化与口径审核时序图
```
  原始年报披露
    │
    ├─► [提取披露原值与单位] ──> 例如: 24,500 百万美元, 括号负数
    │
    ├─► [数值尺度归一化] ──> 标准化为基本货币单位 (USD) 或股数
    │
    ├─► [绑定 Slot 槽位] ──> 关联对应 slot_id，确认经济范围与期间
    │
    ├─► [执行口径审核 (Definition Review)]
    │     ├── 检查费用覆盖与会计口径一致性
    │     ├── 检查是否为同名偷换 (如加权股数 vs 发行股数)
    │     └── 审核通过 ──► 标记 definition_status = company_variant_reviewed
    │
    └─► [判定计算准备状态]
          └── 若 input_complete AND company_variant_reviewed ──► calculation_ready = true
```

#### 图 B-3：行业驱动计算准备度与闸门阻断判定决策树
```
                   ┌─────────────────────────┐
                   │    行业驱动输入核验     │
                   └────────────┬────────────┘
                                │
                 该驱动全部必需槽位是否已成功绑定有效证据?
                                ├──────────────────────── 否 ──► 【INPUT_STATUS: PARTIAL / PENDING】
                                │                                  (输入不齐，禁止进入计算准备)
                                ▼ 是
                 所绑定的公司特定口径是否经过法证核验与定义审核?
                                ├──────────────────────── 否 ──► 【DEFINITION_STATUS: REVIEW_PENDING】
                                │                                  (口径待审，calculation_ready=false)
                                ▼ 是
                   ┌─────────────────────────┐
                   │ 【CALCULATION_READY: TRUE】│
                   │  输入齐备且口径审核通过 │
                   │  research_gate = blocked│
                   │  (待大样本校准后方可放行)│
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **医疗成本率 (Medical Cost Ratio, MCR) 标准测算方程**：
   $$MCR = \frac{\text{Medical Costs Incurred}}{\text{Premium Revenue}} \times 100\%$$
   刚性约束：分子与分母必须来自同一报告范围（如纯商业健康险分部），严禁将投资收益或服务佣金混入分母保费收入。
2. **净息收益率 (Net Interest Margin, NIM) 管理税当量方程**：
   $$NIM_{\text{FTE}} = \frac{\text{Net Interest Income (Fully Tax-Equivalent)}}{\text{Average Interest-Earning Assets}} \times 100\%$$
   必须显式区分法定 GAAP 报表列报净息差与管理层税当量口径，严禁跨口径混用。
3. **驱动输入完备度指数 (Driver Completeness Index, DCI)**：
   $$DCI = \frac{\sum_{i=1}^{N_{\text{slots}}} \mathbb{I}(\text{slot}_i.\text{status} == \text{"bound"})}{N_{\text{slots}}} \times 100\%$$
   当且仅当 $DCI \equiv 100\%$ 时，`input_status` 方可判定为 `input_complete`。

---

## 五、 状态机与生命周期 (Driver State Registry)

### 1. 行业驱动输入与口径状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `DRV_01` | `input_complete` | 槽位输入齐备 | 驱动所声明的全部必需输入槽位均已绑定有效证据。 | 允许推进口径审核。 |
| `DRV_02` | `partial_inputs` | 槽位部分绑定 | 至少 1 项槽位已绑定，但仍存在缺失槽位。 | 列入补数清单，阻断计算。 |
| `DRV_03` | `pending_input_binding`| 槽位完全未绑 | 尚无任何必需输入槽位绑定有效证据。 | 保持初始状态，记录缺口。 |
| `DEF_01` | `company_variant_reviewed`| 公司口径已审 | 所选标的的产品范围、会计期间与费用覆盖已核验。| 结合输入齐备解锁可计算。 |
| `DEF_02` | `definition_review_pending`| 定义审核待决 | 等价性未完全证明或口径差异未完全切除。 | 保持不可计算状态。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

行业驱动台账构建完成后，产出全局校验索引结构体：

```json
{
  "schema_version": "1.0.0",
  "observation_snapshot_path": "data/catalog/objects/a1b2c3...blob",
  "observation_snapshot_sha256": "a1b2c3d4...64位十六进制",
  "binding_plan_path": "data/catalog/objects/e5f6a7...blob",
  "binding_plan_sha256": "e5f6a7b8...64位十六进制",
  "summary": {
    "total_industries": 41,
    "total_drivers": 123,
    "input_complete_count": 9,
    "calculation_ready_count": 7,
    "research_gate_blocked_count": 123
  },
  "drivers": [
    {
      "parent_metric_id": "pct_healthcare_mcr",
      "industry_id": "ind_healthcare_services",
      "name_zh": "医疗成本率",
      "selected_variant_zh": "UnitedHealth 报告医疗成本率",
      "input_status": "input_complete",
      "definition_status": "company_variant_reviewed",
      "calculation_ready": true,
      "research_gate": "blocked",
      "slots": [
        {
          "slot_id": "pct_healthcare_mcr_slot_1",
          "name_zh": "医疗成本",
          "status": "bound",
          "unit": "USD",
          "component": "medical_costs_amount"
        }
      ]
    }
  ]
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 总覆盖行业数 | `total_industries` | `int` | 整数 | 纳入台账管理的内部细分行业总数（41 个）。 |
| 核心胜负手总数 | `total_drivers` | `int` | 整数 | 全系统定义的行业胜负手驱动总数（123 个）。|
| 输入齐备数 | `input_complete_count` | `int` | 整数 | 全部必需槽位均已绑定有效证据的驱动总数。 |
| 计算就绪数 | `calculation_ready_count`| `int` | 整数 | 槽位齐备且口径审核双重通过的驱动总数。 |
| 闸门阻断数 | `research_gate_blocked_count`| `int` | 整数 | 处于阻断状态的研究闸门总数（刚性 123）。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁槽位偷换与粗暴替代**：加权稀释股数严禁替代期初期末实际发行普通股数，资本开支总额严禁替代网络维持与扩张拆分。
- [ ] **严禁将未审核口径自动泛化**：单一样本公司选用的特定产品或地区口径，严禁代码自动泛化至同行业其他公司。
- [ ] **未经验证前研究闸门刚性阻断**：所有 123 项行业驱动的 `research_gate` 必须保持为 `blocked`，严禁在缺乏历史样本统计校准前启用数值阈值。
- [ ] **会计括号负号必须物理保留**：在提取现金流量表项目或减项指标时，原始披露中的括号必须严格转换为负浮点数，严禁丢失负号。
- [ ] **只读本地文件与无网络断言**：台账构建程序仅允许只读访问项目内本地证据文件，严禁包含任何在线网络爬虫或外部 API 探测逻辑。
