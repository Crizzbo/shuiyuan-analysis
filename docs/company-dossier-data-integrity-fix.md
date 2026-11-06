# 公司深度档案数据真实性修复与平账治理技术设计规格书 (Company Dossier Integrity & Balance Sheet Fix Spec)

> **功能标识**：`COMPANY_DOSSIER_DATA_INTEGRITY_AND_BALANCE_SHEET_FIX_SPEC`  
> **所属业务分类**：类别 C：微观企业自由现金流与估值 / 底层数据工程层面（605 份公司深度档案假数据清退、官方三表刚性平账自检、不可变封套校验与云端真实对账）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 证据封套中枢：`financial_reporting/evidence_dossiers.py`  
> - 封套验证核心：`validate_dossier` 函数  
> - 重建调度程序：`scripts/rebuild_verified_drive_dossiers.py`  
> - 历史假数据审计底账：`data/audits/drive-deep-analysis-20261012/findings.json` 与 `audit-report.md`  
> - 替换发布清单：`reports/replacements/drive-20261012/manifest.json`  
> - 自动化测试套件：`scripts/test_evidence_dossiers.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方机构自动化投研系统早期开发中，由于未能严格践行单一事实来源（SSOT）与证据不可变链条，代码中曾存在严重的“假数据模板注入与幻觉回退”灾难。经 2026-10-12 对指定云盘目录 605 份（美股 507 份、日股 98 份）深度分析 PDF 逐份审计，发现全部命中固定营收结构、虚假净收入留存率（NRR）、伪造客户/供应商集中度比例等无来源模板事实。早期旧代码中存在五大系统性工程毒瘤：
1. **静态推算与二次缩放**：在缺乏真实财报时，按固定资产倍数与利润率虚构三表，甚至将已为百万单位的数值二次除以 $1,000,000$，将真实数字缩减百万倍；
2. **零值吞噬与或门回退**：使用 `x or default` 语法，导致标的真实的 `0`（如真实无债务、真实无库存）被当作缺失值，被迫填充为虚假正数；
3. **财报科目偷换与口径混淆**：混用净利润与每股收益（EPS）倒推错误股数，使用带息负债替代总负债破坏资产负债表平账，使用期末净资产伪装全年平均净资产虚增 ROE；
4. **未审先判与假买入线**：在证据完全缺失的情况下，自动生成通用乐观商业判断，并伪造现金流折现（DCF）买入价格线；
5. **虚假完成与假性同步**：在网络连接失败或未上传的情况下，终端盲目打印“100% 同步完成”。

本规范确立彻底清退模板虚假数据、引入证据封套 2.0.0、刚性配平自检与不可信原则的生产治理标准。

### 2. 核心用途
本功能解决全系统三大数据真实性与治理防线问题：
1. **不可信证据封套 2.0.0 (Untrusted Envelope Verification)**：在 `evidence_dossiers.py` 中建立严格的数据准入屏障，`validate_dossier` 强制从本地登记证据重新构建并逐项对比，一概不信任调用方传递的 `verified` 标志或手填数字；
2. **资产负债表刚性配平与财务口径严谨防御**：强制执行 $|Assets - (Liabilities + Equity)| \le 0.1\%$，总负债与有息负债严格物理分流，平均净资产分母缺失时严禁计算 ROE；
3. **真实性诚实披露与虚假同步物理拦截**：证据不足显式标记为 `evidence_missing` 或 `evidence_partial`，估值与买入线强制留空；对云端替换严格以实际读取的清单为准，严禁虚假声称已完成上传。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data_sources/official_filings/`：提供 SEC EDGAR 官方 10-K 与东证有価証券報告書原文 PDF/XBRL。
- `data/catalog/`：提供具备 SHA-256 哈希锁定的不可变数据目录。
- `data/audits/drive-deep-analysis-20261012/`：提供 605 份待替换问题档案的审计基准。

### 2. 后置消费 (Outputs To Downstream)
- `reports/replacements/drive-20261012/`：输出经核准的真实数据 PDF 与 JSON 事实封套。
- `reports/excel_dossiers/`：向 5-Sheet Excel 注入经配平核验的三表数据底稿。
- `financial_core/engines/business_quality_and_moat_engine.py`：消费合规的财务质量指标。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  候选证券身份清单 (不带财务与评级)   │
└──────────────────┬───────────────────┘
                   │ (提取本地不可变原文与登记观测)
                   ▼
┌──────────────────────────────────────┐
│  证据封套校验中枢 (validate_dossier) │
│  ├── SHA-256 哈希、版本、期间核验    │
│  ├── 资产负债刚性平账自检 (A = L + E)│
│  ├── 区分总负债与有息债务            │
│  └── 严格拦截或门吞噬与二次除法      │
└──────────────────┬───────────────────┘
                   │ (装配合规证据封套 2.0.0)
                   ▼
┌──────────────────────────────────────┐
│  真实性重建调度器                    │
│  (rebuild_verified_drive_dossiers)   │
│  ├── 缺失项显式标注 evidence_missing │
│  ├── 估值、评级与仓位强制留空        │
│  └── 嵌入矢量字体，渲染规范 PDF/JSON │
└──────────────────┬───────────────────┘
                   │ (落盘待发布替换清单)
                   ▼
┌──────────────────────────────────────┐
│  生成 manifest.json 并执行实测对账   │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

证据封套 2.0.0 核心实体字段字典与约束规范如下表：

### 1. 核心实体契约对照表
| 字段标识 | 数据类型 | 计量单位 | 约束边界 | 业务含义与说明 |
| :--- | :---: | :---: | :---: | :--- |
| `schema_version` | `str` | 常量字符串 | 固定 `"2.0.0"` | 证据封套版本，启用生产级真实性校验。 |
| `ticker` | `str` | 交易代码 | 规范代码 | 标的官方交易代码（如 `AAPL`, `STX`）。 |
| `market` | `str` | 市场代码 | `"US"` 或 `"JP"`| 交易所属国家/地区市场。 |
| `total_assets` | `float` | 货币实数 | 有限正数 | 官方资产负债表列报的资产总计。 |
| `total_liabilities`| `float` | 货币实数 | 有限正数 | 官方资产负债表列报的负债总计（严禁使用带息负债替代）。|
| `total_equity` | `float` | 货币实数 | 有限实数 | 官方资产负债表列报的股东权益合计。 |
| `total_debt` | `float` | 货币实数 | $\ge 0.0$ | 有息长短期借款与租赁负债合计（独立于总负债）。 |
| `cfo` | `float` | 货币实数 | 有限实数 | 经营活动产生的现金流量净额。 |
| `capex` | `float` | 货币实数 | $\ge 0.0$ | 物业、厂房及设备资本支出。 |
| `sbc` | `float` | 货币实数 | $\ge 0.0$ | 股份支付薪酬费用（真实所有者 FCF 必扣减项）。 |
| `average_equity` | `float \| null`| 货币实数 | 严格平均值 | 期初期末平均净资产；缺失时置 `null` 且阻断 ROE。|
| `evidence_status`| `str` | 枚举字符串 | 3 态枚举 | 真实证据完备度（`evidence_missing` 等）。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 C-1：证据封套 2.0.0 防御与校验拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【未受信输入对象 (Raw Caller Payload)】    │
│  • 严禁盲信: verified=true 标志或调用方手填数字        │
│  • 严禁使用: x or default 吞噬真实零值                 │
└───────────────────────────┬────────────────────────────┘
                            │ (强制从物理证据库重建并比对)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【证据封套核验中枢 (validate_dossier)】    │
│  • 门禁 1: 物理文件 SHA-256 哈希与不可变清单一致性     │
│  • 门禁 2: 资产负债平账自检 |A - (L + E)| <= 0.1%     │
│  • 门禁 3: 负债科目解耦: total_liabilities != total_debt│
│  • 门禁 4: 期间分母严谨性: 禁止以期末值冒充平均值      │
└───────────────────────────┬────────────────────────────┘
                            │ (通过自检放行装配)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【证据封套 2.0.0 (Evidence Dossier)】      │
│  • 真实核验项: 写入官方事实并附带原文页码              │
│  • 未披露项: 显式标注 evidence_missing，买入线留空     │
└────────────────────────────────────────────────────────┘
```

#### 图 C-2：假数据清退、封套构建与云盘真实替换时序图
```
  调度器 (rebuild_verified_drive_dossiers)
    │
    ├─► [扫描 605 份历史档案] ──> 比对 findings.json 确认全部假数据文件
    │
    ├─► [读取本地不可变财报] ──> 获取通过平账自检的真实三表底稿
    │
    ├─► [执行 validate_dossier] ──> 逐项核验货币、单位、期间与勾稽关系
    │     │
    │     ├── 发现缺失项 ──► 标记 evidence_missing，估值留空
    │     └── 发现平账破损 ──► 抛出 BalanceSheetMismatch 阻断
    │
    ├─► [渲染合规纯净 PDF/JSON] ──> 嵌入项目内字体，生成替换实体
    │
    └─► [云盘真实对账替换] ──> 逐文件执行上传并读取云盘目录确认，不打虚假100%
```

#### 图 C-3：财报科目合法性与平账判定决策树
```
                   ┌─────────────────────────┐
                   │    财报科目输入核验     │
                   └────────────┬────────────┘
                                │
                 |Total Assets - (Liabilities + Equity)| <= 0.1%?
                                ├──────────────────────── 否 ──► 【BALANCE_SHEET_DISCREPANCY】(阻断：报表不平)
                                ▼ 是
                 是否试图将期末净资产当作全年平均净资产计算 ROE?
                                ├──────────────────────── 是 ──► 【INVALID_AVERAGE_DENOMINATOR】(阻断：虚假ROE)
                                ▼ 否
                 真实所有者现金流计算是否已扣除 SBC?
                                ├──────────────────────── 否 ──► 【FALSE_FCF_EXCLUSION】(阻断：美化现金流)
                                ▼ 是
                   ┌─────────────────────────┐
                   │  【ENVELOPE_VERIFIED】  │
                   │  证据真实无伪造，放行   │
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **资产负债表刚性配平绝对容差方程**：
   $$\Delta_{\text{balance}} = |\text{Total Assets} - (\text{Total Liabilities} + \text{Total Stockholders' Equity})|$$
   刚性准入条件：
   $$\frac{\Delta_{\text{balance}}}{\text{Total Assets}} \le 0.1\% \quad (\text{误差严禁超过千分之一})$$
2. **净资产收益率 (ROE) 严谨平均分母方程**：
   $$ROE = \frac{\text{Net Income}}{\text{Average Stockholders' Equity}} = \frac{\text{Net Income}}{\frac{\text{Equity}_{t-1} + \text{Equity}_t}{2}}$$
   当且仅当同时具备期初与期末权益且期间跨度为完整 12 个月时允许计算；缺失期初时，`ROE` 必须输出为 `null`，严禁直接使用期末净资产 $\text{Equity}_t$ 充当分母。
3. **真实所有者自由现金流方程**：
   $$FCF_{\text{owner}} = CFO - \text{CapEx} - SBC$$
   严禁将股份支付薪酬作为非现金调节项加回而不作扣减。

---

## 五、 状态机与生命周期 (Dossier Lifecycle)

### 1. 证据封套与档案构建状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `DOS_01` | `evidence_missing` | 证据完全缺失 | 标的尚未在本地登记任何经审计的官方事实。 | 报告生成缺口页，估值留空。 |
| `DOS_02` | `evidence_partial` | 证据部分采齐 | 基础三表已录入，但关键行业胜负手驱动缺失。| 呈现已知财务，阻断买入线。 |
| `DOS_03` | `evidence_complete`| 证据完全齐备 | 官方三表平账且行业 123 驱动槽位全核验通过。| 解锁多情景估值与护城河推演。|
| `DOS_04` | `RECONCILE_FAILED` | 平账校验失败 | 资产负债不平衡度超过千分之一。 | 触发红牌警报，打回补数队列。 |
| `DOS_05` | `SYNC_UNCONFIRMED` | 云盘未确认态 | 本地已生成，但尚未读取云盘清单确认覆盖。 | 严禁声称 100% 同步完成。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

公司深度档案封套 2.0.0 标准化 JSON 结构体：

```json
{
  "schema_version": "2.0.0",
  "ticker": "AAPL",
  "market": "US",
  "fiscal_year": 2024,
  "accounting_standard": "US-GAAP",
  "balance_sheet_reconciled": true,
  "balance_discrepancy_ratio": 0.00001,
  "financial_facts": {
    "total_assets": 364980.0,
    "total_liabilities": 308030.0,
    "total_equity": 56950.0,
    "total_debt": 106629.0,
    "cfo": 118264.0,
    "capex": 9451.0,
    "sbc": 11651.0,
    "owner_fcf": 97162.0
  },
  "metrics": {
    "debt_to_equity_ratio": 1.872,
    "roe": null,
    "roe_block_reason": "average_equity_missing_requires_previous_year"
  },
  "evidence_status": "evidence_partial",
  "valuation_summary": {
    "target_buy_price": null,
    "fair_value": null,
    "status": "valuation_blocked_pending_calibrated_drivers"
  }
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 封套版本 | `schema_version` | `str` | 常量 | 固定 `"2.0.0"`，生产级纯净事实封套。 |
| 平账核验通过 | `balance_sheet_reconciled`| `bool` | 布尔值 | 资产负债表是否满足 $A = L + E$ 刚性自检。|
| 资产不平衡比率 | `balance_discrepancy_ratio`| `float` | 小数 | 不平衡差额占总资产的比率（要求 $\le 0.001$）。|
| 真实所有者现金流 | `owner_fcf` | `float` | 百万美元 | $CFO - CapEx - SBC$ 计算的真实现金流。 |
| ROE 计算状态 | `roe` | `float \| null`| 小数 | 仅在具备平均净资产时计算，否则强制置空。 |
| 目标买入价格 | `target_buy_price` | `float \| null`| 货币/股 | 未经大样本校准前强制留空，严禁伪造。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁或门语法吞噬有效零值**：提取数据必须使用 `if val is not None`，严禁使用 `val or default` 将合法 `0` 错误替换为默认正值。
- [ ] **严禁对百万单位重复除以百万**：必须校验数据源量纲，已换算为百万（$M$）的科目严禁二次除以 $1,000,000$ 造成数值湮灭。
- [ ] **资产负债表平账千分之一刚性红线**：$|A - (L + E)| / A$ 必须 $\le 0.1\%$，任何平账失败的财报一律阻断进入后续估值。
- [ ] **负债科目严禁概念偷换**：总负债必须使用 `total_liabilities`，有息负债必须使用 `total_debt`，严禁跨概念粗暴替代。
- [ ] **严禁虚假声称云盘同步完成**：云端替换操作必须逐文件核验上传返回值并读取远端目录清单，严禁在未确认的情况下打印虚假 100% 成功。
