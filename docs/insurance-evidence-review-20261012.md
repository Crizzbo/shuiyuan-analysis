# 保险行业核心驱动实证核验与综合成本率设计规格书 (Insurance Driver Review & Combined Ratio Spec)

> **功能标识**：`INSURANCE_DRIVER_REVIEW_AND_COMBINED_RATIO_SPEC`  
> **所属业务分类**：类别 B：中观行业存量博弈与增量产出（财产与意外险 P&C 核心驱动因子实证、安达保险 Chubb 官方财报综合成本率 CoR 完全拆解、Regulation G 非 GAAP 核验与准备金发展对齐）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 官方摘录底账：`data/browser-search/insurance-reviewed-20261012.json`  
> - 输入台账中枢：`financial_reporting/industry_inputs.py`  
> - 专属指标核心：`financial_reporting/industry_specific.py`  
> - 行业规格底账：`knowledge/metrics/industry-specifications.json`  
> - 自动化测试套件：`scripts/test_industry_driver_inputs.py`、`scripts/test_industry_specific.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在财产与意外险（Property & Casualty, P&C）行业的基本面研究中，承保盈利能力是决定保险公司护城河深度与长期复利能力的核心胜负手。承保表现由综合成本率（Combined Ratio, CoR）唯一定义。然而，传统量化研究在接入保险公司披露时极易陷入四大口径陷阱：
1. **期间错位与口径混用**：将单季度（如 Q4 独立三月）数据与全财年（FY）累计数据混为一谈；
2. **事故年度与报告年度偷换**：混淆包含历史准备金发展（Prior Period Reserve Development）与巨灾损失（Catastrophe Losses）的报告口径，与剔除巨灾后的“当前事故年剔除巨灾”口径（Current Accident Year ex-CAT）；
3. **分部实体范围漂移**：将全球集团层面的寿险与投资业务收益混入财产意外险分部的纯承保业务；
4. **恒等式未验平账**：赔付率、保单获取成本率与行政管理费用率三项之和未进行刚性浮点对齐校验。

本规范以安达保险（Chubb Limited, NYSE: CB）2025 年第四季度官方业绩披露与 Regulation G 调整表为实证样本，确立综合成本率严格三相拆解、期间锁定与不可变证据验签标准。

### 2. 核心用途
本功能解决全系统三大保险行业驱动验证与核验问题：
1. **综合成本率三相刚性恒等式校验 (Combined Ratio Identity)**：强制执行 $CoR = \text{Loss Ratio} + \text{Policy Acquisition Cost Ratio} + \text{Administrative Expense Ratio}$，确保分项严格平账；
2. **单季度披露口径精确锚定 (Standalone Quarter Precision)**：精确标定为截至 2025-12-31 的独立三个月期间，严禁使用全财年累计值替代单季，并显式剔除寿险业务；
3. **驱动台账可计算准备度安全解锁**：推动驱动项 `insurance_driver_1` 由部分输入（`partial_inputs`）转为齐备（`input_complete`）与可计算（`calculation_ready`），同时保持全局 `research_gate = blocked` 杜绝伪造交易指令。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data_sources/official_filings/`：提供安达保险 2025 Q4 官方披露业绩摘要与 Regulation G 非 GAAP 调和表。
- `knowledge/metrics/industry-specifications.json`：提供 P&C 保险行业专属驱动的原子输入槽位契约。

### 2. 后置消费 (Outputs To Downstream)
- `data/financial/industry-driver-input-verification.json`：更新行业驱动总台账索引。
- `knowledge/metrics/driver-inputs/ind_insurance.json`：生成保险行业驱动分表。
- `financial_core/engines/business_quality_and_moat_engine.py`：消费合规的承保周期综合成本率。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  安达保险官方 2025 Q4 原表与 Reg-G   │
└──────────────────┬───────────────────┘
                   │ (AI 浏览器定向核验并摘录原表)
                   ▼
┌──────────────────────────────────────┐
│  保险专属输入校验器 (industry_inputs)│
│  ├── 独立三个月期间范围锁定          │
│  ├── 剔除寿险，锁定全球财产意外险范围│
│  ├── 三相成本率加总平账核验          │
│  └── 浮点转小数精确归一化 (54.3%->0.543)│
└──────────────────┬───────────────────┘
                   │ (更新驱动状态)
                   ▼
┌──────────────────────────────────────┐
│  推动 insurance_driver_1 达标可计算  │
│  └── 保持 research_gate = blocked    │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

安达保险 Q4 核心实测事实与转换契约对照如下表：

### 1. 核心实体契约对照表
| 字段标识 | 官方报告原值 | 标准化规范值 | 计量单位 | 约束边界 | 业务含义与说明 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `loss_ratio` | `54.3%` | `0.543` | 小数比率 | $[0.0, 1.0]$ | 赔付及理赔费用率（Net Losses and LAE Ratio）。 |
| `acquisition_ratio`| `18.9%` | `0.189` | 小数比率 | $[0.0, 1.0]$ | 保单获取成本率（Policy Acquisition Cost Ratio）。 |
| `expense_ratio` | `8.0%` | `0.080` | 小数比率 | $[0.0, 1.0]$ | 行政与管理费用率（Administrative Expense Ratio）。|
| `combined_ratio` | `81.2%` | `0.812` | 小数比率 | $[0.0, 1.0]$ | 综合成本率（Combined Ratio，作为恒等式检验项）。 |
| `period_type` | `"3 Months"` | `"quarterly"` | 枚举字符串 | 独立单季 | 统计窗口严格为截至 2025-12-31 的独立三个月。 |
| `scope_segment` | `"P&C"` | `"property_casualty"`| 实体代号 | 分部范围 | 剔除人寿保险，包含巨灾与往期准备金发展的净口径。|

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 B-1：安达保险综合成本率三相拆解拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【综合成本率 (Combined Ratio, CoR)】       │
│  • 标准化规范值: 0.812 (81.2%)                         │
│  • 适用范围: Global P&C Consolidated (剔除寿险)        │
└───────────────────────────┬────────────────────────────┘
                            │ (三项加总刚性恒等式)
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 赔付理赔费用率 │    │ 保单获取成本率 │    │ 运营管理费用率 │
│  (Loss Ratio)│    │ (Acquisition)│    │(Administrative)
│ 0.543 (54.3%)│    │ 0.189 (18.9%)│    │ 0.080 (8.0%) │
└──────────────┘    └──────────────┘    └──────────────┘
```

#### 图 B-2：保险驱动核验、口径审核与台账就绪时序图
```
  官方 2025 Q4 业绩原表
    │
    ├─► [提取 Q4 独立三月披露数值] ──> 锁定 2025-10-01 至 2025-12-31
    │
    ├─► [分部范围审查] ──> 确认纯财产意外险分部，排除寿险
    │
    ├─► [执行恒等式平账检验] ──> 断言 |(0.543 + 0.189 + 0.080) - 0.812| <= 1e-4
    │
    ├─► [装配不可变快照] ──> 写入 data/browser-search/insurance-reviewed-20261012.json
    │
    └─► [更新驱动总台账] ──> insurance_driver_1 状态迁移至 calculation_ready
```

#### 图 B-3：综合成本率准入与口径合法性判定决策树
```
                   ┌─────────────────────────┐
                   │    保险专属驱动输入     │
                   └────────────┬────────────┘
                                │
                 是否混淆了全财年累计值 (85.7%) 与单季度值 (81.2%)?
                                ├──────────────────────── 是 ──► 【PERIOD_MISMATCH_ERROR】(阻断：期间错位)
                                ▼ 否
                 是否混用了剔除巨灾事故年口径 (80.4%) 与报告口径?
                                ├──────────────────────── 是 ──► 【DEFINITION_DRIFT_ERROR】(阻断：口径不一致)
                                ▼ 否
                 分项之和是否严格等于综合成本率 (|Sum - CoR| <= 1e-4)?
                                ├──────────────────────── 否 ──► 【IDENTITY_UNRECONCILED】(阻断：平账失败)
                                ▼ 是
                   ┌─────────────────────────┐
                   │ 【DRIVER_INPUT: READY】 │
                   │  槽位齐备且口径审核通过 │
                   │  research_gate = blocked│
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **综合成本率三相完全恒等式**：
   $$CoR = R_{\text{loss}} + R_{\text{acq}} + R_{\text{admin}}$$
   安达保险 2025 Q4 实测代入：
   $$CoR = 54.3\% + 18.9\% + 8.0\% = 81.2\% \quad (\text{绝对平账误差 } 0.0\%)$$
2. **承保利润率 (Underwriting Margin) 互补方程**：
   $$\text{Margin}_{\text{underwriting}} = 1.0 - CoR = 1.0 - 0.812 = 0.188 \quad (18.8\%)$$
   指示标的每收取 1 美元净自留保费，获得 18.8 美分的纯承保承保利润（不含浮存金投资收益）。

---

## 五、 状态机与生命周期 (Verification Lifecycle)

### 1. 保险驱动输入状态迁移空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `INS_01` | `partial_inputs` | 槽位部分缺失 | 仅收集到 CoR 总值，缺少三相分项拆解。 | 保持不可计算状态。 |
| `INS_02` | `input_complete` | 槽位采齐通过 | 赔付、获取、管理及综合成本率全部到位且平账。| 允许推进定义审核。 |
| `INS_03` | `calculation_ready`| 计算准备就绪 | 经法证核验证实为独立 Q4 且剔除寿险。 | 解锁专属指标引擎运算。 |
| `INS_04` | `GATE_BLOCKED` | 研究闸门阻断 | 未完成大规模行业样本统计校准。 | 严禁输出买卖行动阈值。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

保险专属驱动实测核验结果（`insurance-reviewed-20261012.json`）标准化契约：

```json
{
  "schema_version": "1.0.0",
  "ticker": "CB",
  "company_name": "Chubb Limited",
  "period": {
    "fiscal_year": 2025,
    "quarter": "Q4",
    "period_start": "2025-10-01",
    "period_end": "2025-12-31",
    "duration_months": 3
  },
  "segment": "Property & Casualty Consolidated",
  "ratios": {
    "loss_and_lae_ratio": 0.543,
    "policy_acquisition_ratio": 0.189,
    "administrative_expense_ratio": 0.080,
    "combined_ratio": 0.812
  },
  "reconciliation": {
    "sum_of_components": 0.812,
    "discrepancy": 0.0,
    "identity_verified": true
  },
  "status": "calculation_ready",
  "research_gate": "blocked"
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 标的代码 | `ticker` | `str` | 字符串 | 安达保险官方证券代码（`CB`）。 |
| 报告期间 | `period` | `object` | 对象 | 严格限定为独立单季度的三个月时间窗口。 |
| 承保业务分部 | `segment` | `str` | 字符串 | 标明为财产意外险合并口径（严格剔除寿险）。 |
| 综合成本率 | `combined_ratio` | `float` | 小数 | 核心胜负手指标（`0.812` 表示 $81.2\%$）。 |
| 平账校验通过 | `identity_verified`| `bool` | 布尔值 | 分项加总是否严格满足承保恒等式。 |
| 研究闸门状态 | `research_gate` | `str` | 常量枚举 | 固定保持 `blocked`，杜绝伪造交易指令。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁混淆单季度与全财年口径**：安达保险 Q4 综合成本率 $81.2\%$ 严禁替换为全财年累计值 $85.7\%$。
- [ ] **严禁混用报告事故年与剔除巨灾口径**：必须严格区分包含实际准备金调整的报告口径，严禁与当前事故年剔除巨灾的 $80.4\%$ 混淆。
- [ ] **分部范围必须明确剔除人寿保险**：P&C 综合成本率只反映财产险承保效益，严禁将寿险或投资收益混入分母保费。
- [ ] **三相分项加总必须刚性平账**：赔付费用率、保单获取成本率、行政管理费用率之和必须与披露的 CoR 绝对一致，误差 $\le 10^{-4}$。
- [ ] **严禁依据单一样本启用量化买卖阈值**：单个公司的历史报告仅作为口径校正样本，研究闸门必须保持 `blocked`，严禁触发自动化仓位。
