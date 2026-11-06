# 系统工程缺口审计与质量门禁追踪设计规格书 (Engineering Gap Progress & Quality Gate Spec)

> **功能标识**：`ENGINEERING_GAP_PROGRESS_AND_AUDIT_SPEC`  
> **所属业务分类**：类别 E：底层数据工程层面（P0/P1/P2 系统工程缺口审计闭环、独立 Schema 刚性准入、强类型断言防劣变与历史技术债务清偿流水线）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 方案契约测试：`scripts/test_industry_binding_plans.py`  
> - 行情断言测试：`scripts/test_market_snapshot.py`  
> - 档案生成测试：`scripts/test_company_archive.py`  
> - 命令行入口测试：`scripts/test_cli_entrypoints.py`  
> - 代表公司测试：`scripts/test_representative_archives.py`  
> - 驱动台账测试：`scripts/test_industry_driver_inputs.py`  
> - 知识结构巡检：`scripts/validate_knowledge_structure.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方机构自动化投研系统的快速迭代中，若缺乏对历史工程缺陷与技术债务的系统性追踪机制，系统极易陷入“旧债未偿、新债累积”的恶性循环。在早期系统审计中，暴露了七项跨越数据接入、金融计算、档案生成与命令行派发的致命工程缺口（涵盖 P0 阻断级、P1 核心功能级与 P2 自动化运维级）。例如：绑定方案缺乏独立 Schema 导致非法结构注入、行情快照缺乏数值边界断言导致负价格与倒挂区间混入、公司档案生成器缺乏进程沙箱隔离导致正式生产数据被脏测试污染、CLI 缺乏参数校验导致异常静默失败等。本规范确立系统工程缺口的统一排查、法证断言、分级消减与自动化门禁拦截体系。

### 2. 核心用途
本功能解决全系统三大工程质量与防劣变治理问题：
1. **P0/P1/P2 分级技术债务闭环验收**：将全系统历史遗留缺陷严格分级归类，制定明确的单体与集成测试断言矩阵，确保每一项修复具备不可逆的代码级回归保障；
2. **进程沙箱与生产数据物理隔离**：在生成代表公司档案或运行集成测试时，强制启用 `subprocess` 临时隔离目录，严禁任何测试脚本直接修改或覆盖正式归档档案；
3. **真实性原则与未完成项诚实阻断**：严禁将“有接口定义”或“有前置依赖”误作“功能已完成”，对未完成历史统计校准或未核验长周期日线的模块，强制标记为未完成并阻断交易闸门。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `schemas/`：提供全系统强类型 JSON Schema 契约（包括 `industry-input-binding-plans.schema.json` 与 `market-snapshot.schema.json`）。
- `scripts/`：提供底层核心调度与数据构建命令行程序。

### 2. 后置消费 (Outputs To Downstream)
- `data/audits/`：输出自动化审计报告与缺口追踪快照。
- `scripts/verify_architecture_integrity.py`：作为第一道架构验收硬门禁的前置基础。
- 449 项全量回归测试套件：将审计断言转化为持久化单测用例。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  历史工程缺陷与技术债务台账          │
└──────────────────┬───────────────────┘
                   │ (按 P0/P1/P2 严重等级分发)
                   ▼
┌──────────────────────────────────────┐
│  工程质量与门禁审计器 (Audit Gate)   │
│  ├── P0: 独立 Schema 契约与行情断言  │
│  ├── P1: 沙箱隔离生成与代表公司档案  │
│  └── P2: CLI 健壮性与异常退出码核验  │
└──────────────────┬───────────────────┘
                   │ (执行自动化回归套件检验)
                   ▼
┌──────────────────────────────────────┐
│  全息回归通过 -> 锁定已修复状态      │
│  未达标项 -> 刚性阻断发布流水线      │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

工程缺口分级追踪矩阵与验收标准如下表：

### 1. 核心实体契约对照表
| 缺口级别 | 缺口标识 | 缺陷描述与治理要求 | 验证证据与断言代码 | 最终修复状态 |
| :---: | :--- | :--- | :--- | :---: |
| **P0** | `GAP_BINDING_SCHEMA` | 行业输入绑定方案缺乏独立 Schema 约束，存在非法字段与日期逆序风险。 | `test_industry_binding_plans.py` 覆盖非法结构、逆序日期与非法父驱动拦截。 | `VERIFIED_FIXED` |
| **P0** | `GAP_MARKET_ASSERT` | 行情快照缺乏正向数值边界断言，未校验 52 周极值与现价单调性。 | `test_market_snapshot.py` 覆盖 20% 跌幅、75% 区间位置、端点边界与非法区间拦截。| `VERIFIED_FIXED` |
| **P1** | `GAP_DOSSIER_ISOLATION`| 档案生成器缺乏目录隔离，测试执行可能污染正式生产档案底账。 | `test_company_archive.py` 采用 subprocess 临时沙箱目录断言生产文件零污染。 | `VERIFIED_FIXED` |
| **P1** | `GAP_REPRESENTATIVE_41`| 41 代表公司深度档案覆盖不全，部分档案缺乏底层经审计原子事实。 | `test_representative_archives.py` 检验 41 份结构档案，无事实项显式标记缺失。| `IN_PROGRESS` |
| **P1** | `GAP_DRIVER_LEDGER_87` | 123 个行业驱动中仍有 87 项处于待绑定状态，禁止以单项比例替代分子分母。| `test_industry_driver_inputs.py` 检验 123 项驱动状态，闸门刚性保持阻断。 | `IN_PROGRESS` |
| **P2** | `GAP_CLI_ROBUSTNESS` | 命令行入口缺少参数校验、未知命令容错与幂等执行断言。 | `test_cli_entrypoints.py` 覆盖 --help、必填参数、未知子命令与重复执行幂等。 | `VERIFIED_FIXED` |
| **P2** | `GAP_SCHEDULER_BACKTEST`| 缺乏自动化定时调度守护与长周期去前视历史回测数据库。 | 尚无经核验长周期日线数据库，严格禁止伪造回测胜率。 | `PLANNED` |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 E-1：工程质量防御与门禁拦截架构拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【系统工程质量与安全防御总控台】           │
│  • 架构原则: 零逆向依赖、零绝对路径、零未经校验数据   │
└───────────────────────────┬────────────────────────────┘
                            │ (分层部署工程安全网)
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 【P0 级门禁】 │    │ 【P1 级门禁】 │    │ 【P2 级门禁】 │
│ 闭合 Schema  │    │ 沙箱隔离运行 │    │ CLI 健全防御 │
│ 52周区间走廊 │    │ 事实封套平账 │    │ 幂等只追加   │
│ 零容忍非法键 │    │ 严禁模板注入 │    │ 非零异常退出 │
└──────────────┘    └──────────────┘    └──────────────┘
```

#### 图 E-2：工程缺口自动化审计与回归流水线时序图
```
  自动化持续交付流水线
    │
    ├─► [阶段 1: P0 级断言] ──> 运行 test_industry_binding_plans 与 test_market_snapshot
    │     └── 出现任何 Schema 违规或价格越界 ──► 立即退出中断
    │
    ├─► [阶段 2: P1 级沙箱] ──> 在独立 TempDir 中运行档案生成器，校验产物与正式库隔离
    │
    ├─► [阶段 3: P2 级命令行] ──> 遍历全量 CLI 入口，断言异常退出码非零与重复执行幂等
    │
    └─► [发布门禁验收通过] ──> 生成缺口审计台账，更新系统状态空间
```

#### 图 E-3：技术债务清偿与质量验收判定决策树
```
                   ┌─────────────────────────┐
                   │    工程缺陷修复验收     │
                   └────────────┬────────────┘
                                │
                 是否通过闭合 Schema 与物理边界断言 (P0)?
                                ├──────────────────────── 否 ──► 【REJECT: P0_VIOLATION】(阻断：安全隐患)
                                ▼ 是
                 是否在独立沙箱执行且生产正式文件零污染 (P1)?
                                ├──────────────────────── 否 ──► 【REJECT: P1_POLLUTION】(阻断：环境污染)
                                ▼ 是
                 CLI 参数错误或未知子命令是否均抛出非零退出码 (P2)?
                                ├──────────────────────── 否 ──► 【REJECT: P2_SILENT_FAILURE】(阻断：静默失败)
                                ▼ 是
                   ┌─────────────────────────┐
                   │  【AUDIT_GATE: PASSED】 │
                   │  缺陷消减闭环，允许交付 │
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **工程缺陷消除率 (Defect Remediation Rate, DRR)**：
   $$DRR = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{Gap}_i.\text{status} == \text{"VERIFIED\_FIXED"})}{N_{\text{total\_gaps}}} \times 100\%$$
   P0 级缺陷必须满足 $DRR_{\text{P0}} \equiv 100\%$ 方可解锁生产构建。
2. **行情区间位置归一化防御方程**：
   $$\text{Pos} = \frac{P - \text{Low}_{52w}}{\text{High}_{52w} - \text{Low}_{52w}}$$
   边界断言：当 $P \equiv \text{High}_{52w}$ 时 $\text{Pos} = 1.0$；当 $P \equiv \text{Low}_{52w}$ 时 $\text{Pos} = 0.0$；若 $P < \text{Low}_{52w}$ 或 $P > \text{High}_{52w}$，断言引擎必须直接抛出 `InconsistentRangeError`。

---

## 五、 状态机与生命周期 (Gap Lifecycle)

### 1. 技术债务生命周期状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `GAP_01` | `IDENTIFIED` | 缺口已确认 | 审计发现缺陷，已建立问题说明与复现测试。 | 挂入 P0/P1/P2 积压队列。 |
| `GAP_02` | `IN_PROGRESS` | 修复推进中 | 核心逻辑已重写，部分单元测试已通过。 | 阻断关联业务模块发布。 |
| `GAP_03` | `VERIFIED_FIXED`| 验证已修复 | 修复代码已合入，回归套件全绿且无劣变。 | 标记已修复，放行门禁。 |
| `GAP_04` | `PLANNED` | 规划延期态 | 依赖外部长周期基础设施（如日线数据库）。| 保持显式缺失，阻断交易。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

工程缺口审计报告（`engineering-audit-report.json`）标准化契约：

```json
{
  "schema_version": "1.0.0",
  "audit_timestamp": "2026-10-12T18:00:00Z",
  "summary": {
    "total_gaps": 7,
    "verified_fixed": 4,
    "in_progress": 2,
    "planned": 1,
    "p0_blockers_remaining": 0
  },
  "audit_details": [
    {
      "gap_id": "GAP_BINDING_SCHEMA",
      "severity": "P0",
      "component": "schemas/industry-input-binding-plans.schema.json",
      "test_suite": "scripts/test_industry_binding_plans.py",
      "status": "VERIFIED_FIXED",
      "assertions_passed": [
        "reject_missing_required_fields",
        "reject_inverted_chronology",
        "reject_undeclared_additional_properties"
      ]
    },
    {
      "gap_id": "GAP_MARKET_ASSERT",
      "severity": "P0",
      "component": "financial_reporting/market_snapshot.py",
      "test_suite": "scripts/test_market_snapshot.py",
      "status": "VERIFIED_FIXED",
      "assertions_passed": [
        "assert_20_percent_drawdown",
        "assert_75_percent_relative_position",
        "assert_boundary_endpoints_and_inconsistent_range"
      ]
    }
  ]
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 审计时间戳 | `audit_timestamp` | `str` | ISO-8601 | 包含时区的物理审计完成时间。 |
| 缺口总数 | `total_gaps` | `int` | 整数 | 纳入全系统质量追踪的工程缺陷总项数。 |
| 已验证修复数 | `verified_fixed` | `int` | 整数 | 具备完备自动化回归测试并通过验收的缺口数。|
| 剩余 P0 阻断数 | `p0_blockers_remaining`| `int` | 整数 | 尚未修复的 P0 级严重隐患数（必须清零）。|
| 审计明细清单 | `audit_details` | `List[Object]`| 列表 | 逐项缺陷的测试套件与断言通过记录。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **P0 级缺陷零容忍**：任何包含未解决 P0 缺陷的版本绝对禁止标记为生产可用，必须阻断流水线。
- [ ] **沙箱隔离执行严禁污染正式库**：执行集成测试与档案构建测试时，必须使用临时目录或 mock，严禁破坏 `data/` 下已有正式档案。
- [ ] **CLI 异常退出码严格非零**：所有命令行脚本在遇到非法入参、缺少必填项或内部报错时，必须抛出非零退出码（如 `sys.exit(1)`），严禁静默吞噬异常。
- [ ] **重复执行强幂等性**：对同一来源或快照重复执行数据处理程序，必须保证产物哈希一致，严禁因多次执行生成重复脏数据。
- [ ] **缺口披露必须诚实客观**：未完成的历史数据校验或回测数据库必须诚实标记为未完成，严禁在文档中虚假宣称已全盘达成。
