# 六步分析架构与流程规则技术设计规格书 (Six-Step Research Schema & Lifecycle Specification)

> **功能标识**：`SIX_STEP_RESEARCH_SCHEMA_SPEC`  
> **所属业务分类**：类别 A/E：顶层架构与底层数据工程层面（六步因果推演、强类型门禁、三态情景 DCF 契约与回退失效传播）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 研究主契约：`schemas/research.schema.json`  
> - 校验主引擎：`scripts/validate_research.py`  
> - 自动化回归测试套件：`scripts/test_research_contract.py`  
> - 密码学事实账本：`financial_core/engines/prediction_ledger.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方机构证券研究与基本面投资决策中，传统投研过程普遍存在“因果倒置”、“前瞻性偏差”与“跳步推导”三大顽疾。常见缺陷包括：一是在未对宏观周期、行业格局（Step 1）及三表法证真实性（Step 2）充分审计前，直接预设立场给出乐观估值目标价（Step 4）；二是在使用二手数据时，混淆官方披露时点与研究截止时点，引入后验信息导致回测与实盘严重偏离；三是当底层假设发生逆转（如突发财务造假或行业监管黑天鹅）时，缺乏级联失效回退机制，导致下游决策无法自动触发熔断。本规范基于 `schemas/research.schema.json` 强类型契约，确立六步单向因果流水线、刚性门禁核验与级联失效回退机制。

### 2. 核心用途
本功能解决全系统三大研究规范与生命周期问题：
1. **六步因果单向推进流水线**：严格约束 Step 1 (周期与制度定位) ➔ Step 2 (深入基本面穿透) ➔ Step 3 (催化机制因果验证) ➔ Step 4 (多情景估值折现) ➔ Step 5 (组合风控与行动指令) ➔ Step 6 (持续跟踪与复盘上链) 的单向流转；
2. **多层级必检刚性门禁 (Mandatory Gates)**：每步必须 100% 通过预设门槛（如分类审查、三表平账、三情景单调性、概率空间归一），严禁使用“不适用”跳过整个步骤；
3. **不可篡改快照与级联失效传播 (Invalidation Cascading)**：底层证据变化自动递增版本号，并向上级联使原依赖下游快照置为 `invalidated`，阻断失效结论输出。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data/catalog/`：提供通过 SHA-256 固化的原始事实证据句柄。
- `knowledge/`：提供四维正交分类标准与 145 个标准化指标定义。
- `financial_core/api.py`：提供纯净量化引擎产出的估值模型计算结果。

### 2. 后置消费 (Outputs To Downstream)
- `reports/ai_dossiers/` 与 `reports/excel_dossiers/`：消费经门禁核验的六步研究快照装配研报。
- `data/ledger/predictions_ledger.sqlite3`：消费最终决策结论与置信度，签署不可篡改时间戳链条。
- `scripts/validate_research.py`：离线核验全盘研究 JSON 是否 100% 契约合规。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  原始财报底账与证据项 (evidences)    │
└──────────────────┬───────────────────┘
                   │ (单向时间偏序注入)
                   ▼
┌──────────────────────────────────────┐
│  六步系统性推进调度器                │
│  ├── Step 1 ➔ 门禁核验 ➔ Step 2       │
│  ├── Step 3 ➔ 门禁核验 ➔ Step 4       │
│  └── Step 5 ➔ 门禁核验 ➔ Step 6       │
└──────────────────┬───────────────────┘
                   │ (全部通过门禁)
                   ▼
┌──────────────────────────────────────┐
│  研究快照封存与不可逆存证上链        │
│  (DataStore 归档与 PredictionLedger) │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

六步研究调度与步骤流转核心参数定义如下表：

| 方法标识 | 参数名称 | 数据类型 | 计量单位 | 约束边界 | 业务释义 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `init_pipeline` | `research_id` | `str` | 字符串 | 符合正则命名 | 研究记录全局唯一标识符。 |
| `init_pipeline` | `as_of` | `str` | ISO-8601时间 | 必须包含时区 | 本次研究所依赖事实的历史截止时间点。 |
| `step_dispatch` | `step_index` | `int` | 整数 | $[1, 6]$ | 当前调度的工步序号。 |
| `step_dispatch` | `upstream_versions`| `dict` | 键值对字典 | 必须包含前序 | 本工步所依赖的所有前序工步的版本快照映射。 |
| `invalidate` | `invalidation_reason`| `str` | 中文字符串 | 非空描述 | 触发回退失效的具体业务或财务原因。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 A-1：六步单向依赖因果流水线与门禁检查拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【Step 1: 周期、制度与生命周期定位】        │
│  • 产出: 业务分部生命周期、供需/信贷/估值五维周期状态   │
│  • 刚性门禁: classification_passed, cycle_dim_verified │
└───────────────────────────┬────────────────────────────┘
                            │ (输出 Version 1.0)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Step 2: 深入基本面与法证排雷】            │
│  • 产出: 真实所有者收益、受限资金剔除、八大排雷检查项   │
│  • 刚性门禁: mandatory_checks_pass, balance_sheet_even │
└───────────────────────────┬────────────────────────────┘
                            │ (输出 Version 1.0)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Step 3: 催化机制与预期差因果验证】        │
│  • 产出: 未来 12-24M 催化清单、传导时间窗口、失效触发器│
│  • 刚性门禁: transmission_causal, monitoring_baseline  │
└───────────────────────────┬────────────────────────────┘
                            │ (输出 Version 1.0)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Step 4: 多情景估值与弹性安全边际】        │
│  • 产出: 悲观底/中性公允/乐观靶心三情景每股价值折现    │
│  • 刚性门禁: 3_scenarios_strictly_monotonic, sum_p=1.0 │
└───────────────────────────┬────────────────────────────┘
                            │ (输出 Version 1.0)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Step 5: 组合风控与投资行动指令】          │
│  • 产出: 综合买方评级、击球区底线 (Strike)、仓位在险界限│
│  • 刚性门禁: permanent_loss_assessed, action_verdict   │
└───────────────────────────┬────────────────────────────┘
                            │ (输出 Version 1.0)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Step 6: 持续跟踪、归因与复盘上链】        │
│  • 产出: 监控日程表、重分析触发器清单、密码学上链凭证  │
│  • 刚性门禁: ledger_integrity_pass, review_plan_sealed │
└────────────────────────────────────────────────────────┘
```

#### 图 A-2：级联失效回退 (Invalidation Cascading) 状态迁移时序图
```
  正常工序: S1 (v1) ──> S2 (v1) ──> S3 (v1) ──> S4 (v1) ──> S5 (v1) ──> S6 (v1)
                            │
                            ▼ (突发财报重述或财务造假红牌)
  触发事件: [InvalidationEvent: S2 发现存货严重虚增]
                            │
                            ├─► S2 状态变为: INVALIDATED (准备重新核算 v2)
                            ├─► S3 级联失效: INVALIDATED
                            ├─► S4 级联失效: INVALIDATED (原估值作废)
                            ├─► S5 级联失效: INVALIDATED (行动指令熔断)
                            └─► S6 级联失效: INVALIDATED
                            │
                            ▼ (重新完成 S2 审计并递增版本)
  恢复重建: S1 (v1) ──> S2 (v2) ──> S3 (v2) ──> S4 (v2) ──> S5 (v2) ──> S6 (v2)
```

#### 图 A-3：Step 4 三情景估值单调走廊与概率空间决策树
```
                   ┌─────────────────────────┐
                   │    三情景 DCF 测算结果   │
                   └────────────┬────────────┘
                                │
                 P_pessimistic < P_neutral < P_optimistic?
                                ├──────────────────────── 否 ──► 【SCENARIOS_NON_MONOTONIC】
                                │                                  (单调性冲突，立即报错阻断)
                                ▼ 是
                 是否赋予了情景概率权重?
                                ├──────────────────────── 是 ──► \sum p_i \equiv 1.00?
                                │                                ├── 否 ──► 【PROBABILITY_NOT_SUM_ONE】
                                │                                └── 是 ──► [公允期望值 = \sum p_i * P_i]
                                ▼ 否
                   ┌─────────────────────────┐
                   │  概率默认全部置为 null  │
                   │  以中性锚点为基准决策   │
                   │  (STATUS: GATE_PASS)    │
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **三情景单调性刚性不等式断言**：
   $$P_{\text{pessimistic}} < P_{\text{neutral}} < P_{\text{optimistic}}$$
   若出现反向倒挂或点位重合，系统判定估值模型失效并拒绝通过 `model_applicability` 门禁。
2. **情景概率空间归一化约束**：
   $$\sum_{s \in \{\text{pessimistic, neutral, optimistic}\}} p_s = 1.00 \quad (\text{当 } p_s \neq \text{null})$$
3. **加权期望公允价值与安全边际买入触发**：
   $$\mathbb{E}[P] = p_{\text{pess}} P_{\text{pess}} + p_{\text{neut}} P_{\text{neut}} + p_{\text{opt}} P_{\text{opt}}$$
   $$\text{StrikePrice} = \mathbb{E}[P] \times (1.0 - \text{MOS}_{\text{elastic}})$$

---

## 五、 状态机与生命周期 (State Registry)

### 1. 步骤执行生命周期状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `ST_01` | `PENDING` | 待启动态 | 前序步骤已完成，本步骤尚未开始。 | `output` 置空，等待调度。 |
| `ST_02` | `IN_PROGRESS` | 进行中态 | 正在提取证据与运行模型。 | 允许保留中间运算笔记。 |
| `ST_03` | `COMPLETED` | 成功完成态 | 步骤输出完整，本步所有门禁 100% 通过。 | 生成版本快照，解锁下一步。 |
| `ST_04` | `INSUFFICIENT_EVD`| 证据不足态 | 底层三表或关键事实缺失。 | 阻断推进，触发补数任务。 |
| `ST_05` | `NEEDS_REVIEW` | 待复核态 | 存在逻辑冲突或计算未核对。 | 冻结流水线，转入人工介入。 |
| `ST_06` | `INVALIDATED` | 级联失效态 | 上游版本发生变更或被回退事件废弃。 | 标记历史失效，拒绝对外输出。 |

### 2. 终审决策评级状态空间 (Step 5 Verdict)

| 状态代号 | 英文枚举标识 | 中文评级名称 | 判定条件 | 买方应对策略 |
| :--- | :--- | :--- | :--- | :--- |
| `VD_01` | `ACTION_MET` | 满足行动条件 | 现价低于黄金买点且法证零红旗。 | 允许建仓，遵循金字塔买入法。 |
| `VD_02` | `WATCH` | 维持观察跟踪 | 估值公允，等待催化兑现或价格回调。 | 严禁盲目追高，定期跟踪财报。 |
| `VD_03` | `NOT_MET` | 条件不符回避 | 现金流脆弱或估值处于泡沫高位。 | 坚决不买，已持有者止损/减仓。 |
| `VD_04` | `UNABLE_JUDGE`| 无法达成判断 | 存在不可消除的重大商业模式未知项。 | 放弃研究，不参与该标的交易。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

单标的六步研究完成时，产出完整结构体契约：

```json
{
  "schema_version": "1.0.0",
  "research_id": "RES_NVDA_20261103_001",
  "revision": 1,
  "is_fictional": false,
  "as_of": "2026-11-03T16:00:00Z",
  "subject": {
    "company_id": "NVDA_US",
    "ticker": "NVDA",
    "primary_industry_id": "ind_semiconductors"
  },
  "steps": {
    "s1_positioning": { "status": "COMPLETED", "version": "1.0", "gates_passed": true },
    "s2_deep_dive": { "status": "COMPLETED", "version": "1.0", "gates_passed": true },
    "s3_catalysts": { "status": "COMPLETED", "version": "1.0", "gates_passed": true },
    "s4_valuation": {
      "status": "COMPLETED",
      "version": "1.0",
      "gates_passed": true,
      "output": {
        "scenarios": {
          "pessimistic": 105.00,
          "neutral": 155.00,
          "optimistic": 210.00
        },
        "strike_price": 125.64
      }
    },
    "s5_decision": {
      "status": "COMPLETED",
      "version": "1.0",
      "verdict": "WATCH",
      "action_summary": "现价高于击球底线，维持观察。"
    },
    "s6_tracking": { "status": "COMPLETED", "version": "1.0", "ledger_sealed": true }
  }
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 研究流水号 | `research_id` | `str` | 字符串 | 单次研究全局唯一业务键。 |
| 截止时点 | `as_of` | `str` | ISO-8601 | 数据截止基准时间戳。 |
| 步骤状态 | `status` | `str` | 枚举字符串 | 对应步骤的当前执行生命周期状态。 |
| 击球买入底线 | `strike_price` | `float` | 货币单位/股 | 考虑弹性安全边际后的最高允许买入挂单价。|
| 终审决策评级 | `verdict` | `str` | 枚举字符串 | 买方最终投资行动结论（WATCH / ACTION_MET 等）。|

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁跳步与逆序推进**：步骤推进必须严格按 S1 ➔ S6 单向推进，上游步骤未达 `COMPLETED` 状态严禁调度下游。
- [ ] **门禁全数通过硬断言**：所有核心门禁（如 `mandatory_checks`、`balance_sheet_even`）必须通过，严禁填入 `not_applicable` 绕过检查。
- [ ] **三情景严格单调递增**：必须满足 $P_{\text{pessimistic}} < P_{\text{neutral}} < P_{\text{optimistic}}$，出现反向或点位重合立即抛错阻断。
- [ ] **合成数据与生产隔离**：合成测试用例必须显式标记 `is_fictional: true`，且决策状态严禁标记为 `ACTION_MET`。
- [ ] **失效级联全面回退**：任意步骤触发 `invalidation_event` 时，必须将其自身及所有下游步骤重置为 `INVALIDATED`，严禁残存孤立有效输出。
