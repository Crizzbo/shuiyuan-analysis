# 水源智能量化投研系统 (Shuiyuan Quant Research & Intelligence System)

> **版本**：`v6.4.0`  
> **定位**：买方机构级全市场量化趋势选股、商业物理动力学动量逃逸、法务会计与信用风控、SOTP分部与多标的产业链因果穿透、小资金非对称高爆发倒金字塔加仓、全天候交易室推流大屏与 AI Agent Skill 一体化投研系统。  
> **核心原则**：程序负责坚硬客观的数据骨架（0-Token 本地数学计算、时效硬核验门禁、三表刚性平账），AI 负责赋予六维立体的买方认知血肉（反身性、对手盘、因果穿透、非对称凸性）。

---

## 目录 (Table of Contents)
- [一、 系统核心工程哲学与分层架构](#一-系统核心工程哲学与分层架构)
- [二、 十大硬核数学计算模型与金融物理动力学公式全集](#二-十大硬核数学计算模型与金融物理动力学公式全集)
- [三、 【核心专章】AI 使用与 Skills 技能调用指南 (AI Agent & Skill Invocation Guide)](#三-核心专章ai-使用与-skills-技能调用指南-ai-agent--skill-invocation-guide)
  - [0. AI 防呆心智模型与刚性防走弯路决策树 (Anti-Detour Protocol)](#0-ai-防呆心智模型与刚性防走弯路决策树-anti-detour-protocol)
  - [1. 技能定位与工程位置](#1-技能定位与工程位置)
  - [2. AI 意图识别与场景触发路由矩阵](#2-ai-意图识别与场景触发路由矩阵)
  - [3. 调用方式一：Claude Code / AI Agent Slash Command (`/shuiyuan-analysis`)](#3-调用方式一claude-code--ai-agent-slash-command-shuiyuan-analysis)
  - [4. 调用方式二：Python API 级统一网关调用 (`FinancialAnalysisGateway`)](#4-调用方式二python-api-级统一网关调用-financialanalysisgateway)
  - [5. 调用方式三：终端 CLI 统一调度入口 (`run_financial_analysis_gateway.py`)](#5-调用方式三终端-cli-统一调度入口-run_financial_analysis_gatewaypy)
  - [6. 资金画像模式切换：机构稳健 vs 小资金高爆发](#6-资金画像模式切换机构稳健-vs-小资金高爆发)
  - [7. AI 规范 Prompt 与结构化交付物模板](#7-ai-规范-prompt-与结构化交付物模板)
- [四、 本地买方交易室推流服务与交互拓扑大屏](#四-本地买方交易室推流服务与交互拓扑大屏)
- [五、 全盘万家资产池与流式批处理调度体系](#五-全盘万家资产池与流式批处理调度体系)
- [六、 四道架构防劣变验收硬门禁 (Non-Regression Gates)](#六-四道架构防劣变验收硬门禁-non-regression-gates)
- [七、 附录：12 本专责核心设计典籍 SSOT 地图](#七-附录12-本专责核心设计典籍-ssot-地图)
- [八、 工程全量依赖规范与环境配置指引 (System Dependencies & Environment Guide)](#八-工程全量依赖规范与环境配置指引-system-dependencies--environment-guide)
- [九、 冷热数据分层生命周期与云端防泄露架构 (Hot/Warm/Cold Data Lifecycle)](#九-冷热数据分层生命周期与云端防泄露架构-hotwarmcold-data-lifecycle)

---

## 一、 系统核心工程哲学与分层架构

系统严格遵循买方机构高标准研发规范，彻底破除“保守打补丁、层层套 fallback、死代码硬编码绝对路径、无校准虚假数字”的工程弊端：

```
┌────────────────────────────────────────────────────────────────────────┐
│ [应用与调度层] scripts/                                                  │
│   ├── run_financial_analysis_gateway.py (统一多模式金融网关 CLI)          │
│   ├── run_10k_universe_pipeline.py (全市场万家资产池批处理调度流水线)    │
│   ├── serve_radar_dashboard.py (交易室轻量推流 HTTP 调度服务)            │
│   └── verify_architecture_integrity.py (架构防劣变全息巡检)             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼ 依赖
┌────────────────────────────────────────────────────────────────────────┐
│ [报告呈现与时效门禁层] financial_reporting/                             │
│   ├── quote_freshness_gateway.py (行情时钟与交易时效硬核验门禁)         │
│   ├── briefing_pdf_renderer.py / deep_pdf_renderer.py (矢量报告渲染器)   │
│   └── reports/event_radar_dashboard.html (交易室交互拓扑大屏)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼ 依赖
┌────────────────────────────────────────────────────────────────────────┐
│ [中继与专业工具分包层] finance_tools/ (6 大高内聚子目录 + 兼容 Facade)  │
│   ├── screening/ (全市场选股、SEPA 8 大指标、VCP 4T 收缩)                │
│   ├── forensics_and_valuation/ (法务 Beneish、三表平账、DCF 估值)        │
│   ├── risk_and_derivatives/ (期权偏度、KMV-Merton 信用违约、VaR 预算)    │
│   ├── macro_and_ripple/ (宏观 HMM、SOTP 分部穿透、多标的产业链涟漪)      │
│   ├── events_and_verification/ (0-Token 初筛、SHA-256 密码学法定鉴真)    │
│   └── governance_and_pipeline/ (数据完备度追踪、统一金融网关、账本管理)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼ 依赖
┌────────────────────────────────────────────────────────────────────────┐
│ [底层纯净金融核心引擎层] financial_core/ (零外层依赖、纯相对导入)         │
│   ├── engines/universal_physical_dynamics_engine.py (商业物理动力学)    │
│   ├── engines/sepa_buy_signal_engine.py (SEPA 买点与倒金字塔加仓)        │
│   ├── engines/supply_chain_ripple_engine.py (产业链涟漪因果传导)        │
│   ├── engines/prediction_ledger.py (SHA-256 密码学时间链条账本)         │
│   └── engines/credit_risk_engine.py (KMV-Merton 结构化违约距离)          │
└────────────────────────────────────────────────────────────────────────┘
```

### 三大刚性工程铁律：
1. **0-Token 纯本地物理计算铁律**：初筛仅依赖标的过去 1 年客观日 K 线价量时序 (OHLCV)，由 `sepa_buy_signal_engine` 执行 50/150/200 日移动均线、52 周高低点及 VCP 波动收缩计算。初筛阶段严禁向大语言模型注入全量原始数据，实现 0-Token 秒级万家标的扫描。
2. **行情时效与交易时钟核验硬门禁 (`verify_quote_freshness`)**：在输出任何分析、估值或期权定价前，强制对齐交易所时区（美股 EDT/EST、日股 JST），区分盘前 (Pre-Market)、盘中 (Regular)、盘后 (After-Hours) 与前收盘价，未来时间戳硬性拦截，旧日缓存自动降级并显式告警。
3. **官方三表刚性平账自检**：录入主管道的财报底账必须经由 `OfficialFilingMapper` 转换非标字符串，并通过 $Assets = Liabilities + Equity$ 刚性平账自检，不平账严禁直传估值模型。

---

## 二、 十大硬核数学计算模型与金融物理动力学公式全集

系统全部投研判断、买卖时机与风控边界均建立在纯本地硬核数学推导之上，**严禁大模型主观臆造数字**：

### 1. 通用商业物理动力学方程 (Universal Physical Dynamics)
- **商业质量 (Business Mass)**：
  $$m = \ln(1 + \text{TotalAssets}) \times (1 + \text{MoatScore}), \quad \text{MoatScore} \in [0.0, 1.0]$$
- **趋势速度与加速度**：$v_t = \frac{P_t - P_{t-k}}{k}, \quad a_t = \frac{v_t - v_{t-k}}{k}$
- **动量与动能**：$p = m \cdot v_t, \quad E_k = \frac{1}{2} m v_t^2$
- **重力势能与动能势能比 (火箭逃逸速度准则)**：
  $$E_p = m \cdot g_{\text{market}} \cdot \max(0, P_{\text{resistance}} - P_t), \quad \text{Ratio}_E = \frac{E_k}{E_p + \epsilon}$$
  - $\text{Ratio}_E \ge 1.0 \implies$ 达成逃逸速度，突破有效；$\text{Ratio}_E < 1.0 \implies$ 假突破冲高回落。
- **阻尼振荡半衰期 (恐慌平复周期)**：$t_{1/2} = \frac{\ln 2}{\gamma}, \quad \gamma = \frac{\beta_{\text{down}} \cdot \sigma_{\text{daily}}}{\text{CashBufferRatio}}$
- **零增长停滞底价 (绝对铁底)**：$P_{\text{floor}} = \frac{\text{Normalized Owner Earnings}}{WACC}$

### 2. 法务会计 Beneish M-Score 八维 Probit 概率模型
$$M = -4.84 + 0.920 \cdot DSRI + 0.528 \cdot GMI + 0.404 \cdot AQI + 0.892 \cdot SGI + 0.115 \cdot DEPI - 0.172 \cdot SGAI + 4.037 \cdot TATA + 0.0327 \cdot LVGI$$
- **防舞弊门禁**：$M > -1.78$ 判定存在财务操纵粉饰嫌疑，**一票否决淘汰出选股池**；$M \le -2.22$ 为健康报表。

### 3. KMV-Merton 结构化信用违约与破产风险模型
股权作为以资产为标的的欧式看涨期权（Merton 1974）：
$$E = V_A \mathcal{N}(d_1) - D e^{-r T} \mathcal{N}(d_2), \quad \sigma_E E = \mathcal{N}(d_1) \sigma_A V_A$$
- **违约触发点**：$D = \text{ShortTermDebt} + 0.5 \times \text{LongTermDebtNoncurrent}$
- **违约距离与预期违约率**：$DD = \frac{\ln(V_A / D) + (\mu_A - 0.5 \sigma_A^2)T}{\sigma_A \sqrt{T}}, \quad EDF = \mathcal{N}(-DD)$
- **风控阈值**：$DD > 3.0$ 安全；$DD < 2.0$ 或 $EDF > 5.0\%$ 触发破产黑天鹅告警，禁止持仓。

### 4. Amihud 微观流动性冲击与动态非线性滑点模型
$$\text{ILLIQ} = \frac{1}{N} \sum_{t=1}^N \frac{|R_t|}{\text{Volume}_t \times P_t}$$
$$\text{Slippage}(bps) = \text{BaseSpread} + \lambda \times \left( \frac{\text{OrderValue}}{\text{ADV}_{20}} \right)^{0.6} \times \sigma_{\text{daily}} \times 10000$$
- **建议单笔最大容量上限**：$\text{Capacity}_{\max} = \text{ADV}_{20} \times \left( \frac{\text{MaxAllowableSlippage} - \text{BaseSpread}}{\lambda \cdot \sigma_{\text{daily}} \times 10000} \right)^{1 / 0.6}$
- **流动性陷阱门禁**：$\text{ADV}_{20} < \$5\text{M}$ 或计算滑点 $> 50\text{ bps}$ 强制打上 `ILLIQUID_TRAP` 标签。

### 5. 期权波动率偏度与主力大单异动模型
- **25-Delta 风险反转偏度**：$Skew_{25D} = IV_{25D, \text{put}} - IV_{25D, \text{call}}$（$>0.08$ 预警机构隔夜跳水对冲大单）；
- **期限结构倒挂比**：$TS = \frac{IV_{\text{front}, ATM}}{IV_{\text{back}, ATM}}$（$>1.15$ 预警近期财报或监管黑天鹅）；
- **做市商 Gamma 状态**：$S > \text{GammaFlip} \implies$ Long Gamma（震荡抑制）；$S < \text{GammaFlip} \implies$ Short Gamma（加速踩踏）。

### 6. 宏观 3-状态高斯隐马尔可夫模型 (Gaussian HMM)
$$S_t \in \{1: \text{BULL\_MOMENTUM (牛市)}, 2: \text{RANGE\_BOUND\_VALUE (震荡)}, 3: \text{CRISIS\_DEFENSE (危机)}\}$$
- **总仓位自适应预算**：$\text{GrossExposure} = \sum_{k=1}^3 P(S_t = k \mid \mathcal{F}_t) \times \text{ExposureCap}_k$
  - $\text{ExposureCap} = \{ \text{BULL}: 100\%, \text{RANGE}: 60\%, \text{CRISIS}: 0\%\sim 20\% \}$

### 7. SEPA 趋势模板八大数学不等式与 Minervini VCP 收缩方程
1. $P_t > MA50_t > MA150_t > MA200_t$
2. $MA200_t > MA200_{t-20}$（200日均线斜率维持正值至少 1 个月）
3. $P_t \ge 1.25 \times \min(P_{52W})$
4. $P_t \ge 0.75 \times \max(P_{52W})$
5. 相对强弱 $RS_{\text{score}} \ge 80$
- **VCP 4T 收缩序列方程**：$\Delta \text{Range}_1 \approx 20\% \to \Delta \text{Range}_2 \approx 10\% \to \Delta \text{Range}_3 \approx 5\% \to \Delta \text{Range}_4 \le 2.5\%$
- **成交量枯竭判定**：$\text{Volume}_{\text{pivot}} \le 0.50 \times \overline{\text{Volume}}_{50}$

### 8. 多阶段情景 DCF 估值矩阵与 WACC 资本成本方程
$$PV = \sum_{t=1}^{N_1} \frac{\text{FCFF}_t}{(1+WACC)^t} + \sum_{j=N_1+1}^{N_2} \frac{\text{FCFF}_j}{(1+WACC)^j} + \frac{\text{FCFF}_{N_2} (1+g)}{(WACC - g)(1+WACC)^{N_2}}$$
- 悲观底价（$WACC+200\text{bps}, g=1.5\%$）、中性公允（基准参数）、乐观靶心（护城河扩张）。

### 9. 41 大细分行业因果敏感性弹性系数模型
$$\frac{\Delta \text{EBIT}_i}{\text{EBIT}_i} = \sum_{k=1}^m \epsilon_{i, k} \cdot \frac{\Delta X_k}{X_k}$$
（覆盖半导体、软件、工业机械、汽车、能源、银行等 41 个行业专属边际弹性系数）。

### 10. 小资金非对称高爆发倒金字塔加仓与极速保本模型 (Small-Cap Asymmetric Execution)
针对非机构小资金定制的爆发型量化数学体系：
- **极限硬止损方程**：$\text{StopLossPrice} = \text{PivotPrice} \times (1.0 - 0.035)$（单笔试错成本硬锁在 $-3.5\%$，定义单股风险 $R = 0.035 \times \text{PivotPrice}$）；
- **6:1 跃升盈亏比目标**：$\text{TargetProfitPrice} = \text{PivotPrice} + 6.0 \times R = \text{PivotPrice} \times (1.0 + 0.21)$（目标 $+21.0\% \sim +30.0\%$ 爆发靶心）；
- **1.5R 极速零风险保本机制 (Free-Roll Breakeven Valve)**：当浮盈达到 $1.5R$（约 $+5.0\%$）时，强制将止损线上移至买入成本价，达成**绝对零风险（Free-Roll）**；
- **倒金字塔顺势加仓梯队**：首次突破试探建仓 $50\%$ ➔ 浮盈 $+5\%$ 顺势加仓 $30\%$ ➔ 浮盈 $+10\%$ 主升浪锁仓 $20\%$；
- **物理逃逸动能真伪核验门禁**：$R_E = \frac{E_k}{E_p + \epsilon} \times (\text{Vol}/\overline{\text{Vol}}_{50})^{0.5} \ge 1.0$，过滤冲高回落诱多假突破。

---

## 三、 【核心专章】AI 使用与 Skills 技能调用指南 (AI Agent & Skill Invocation Guide)

本章节为大语言模型（Claude、ChatGPT、本地开源模型等）以及各种自主 Agent 体系（Claude Code、AutoGPT、LangChain、CrewAI、AutoGen）提供标准化的技能识别、调用契约与输出规范。

### 0. AI 防呆心智模型与刚性防走弯路决策树 (Anti-Detour Protocol)

> **核心戒律：程序负责坚硬客观的数据骨架，AI 负责六维立体的认知血肉。严禁直觉先行、严禁无据荐股。**

#### 决策树分流状态机 (Deterministic Cognitive State Machine)
```
                    [用户输入意图判定]
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
  【意图 A: 选股 / 推荐股票】             【意图 B: 指定标的诊断】
  ("买哪个" / "选股" / "找标的")          ("分析NVDA" / "AAPL买点")
        │                                       │
        ▼                                       ▼
[步骤 1: 物理全盘初筛准入池获取]        [步骤 1: 行情时效硬门禁核查]
python scripts/run_financial_analysis_gateway.py  verify_quote_freshness
  --mode screening --top 10                       ↓ 显式声明时间戳与盘段
        │                               [步骤 2: 财报三表平衡自检]
        ▼                               Assets == Liabilities + Equity
[步骤 2: 纯客观候选池排名锁定]                  ↓ 严禁未平账脏数据入模
严格锁定 Stage_2_Pivot_Ready 标的       [步骤 3: SEPA 趋势模板客观计算]
严禁从自身记忆中随机挑选热门大票!               ↓ 50/150/200日均线与RS评分
        │                                       ├─ Out_Of_Trend? ──► [一票硬否决 终止]
        ▼                                       └─ Stage_2_Uptrend ──► 准入
[步骤 3: 标的法务会计与破产排查]                        │
Beneish M-Score & KMV 违约距离                  ▼
        │                               [步骤 4: 六大模型与物理动量全息推演]
        ▼                               逃逸动能比 RE、期权偏度、Amihud滑点
[步骤 4: 小资金/机构操盘要素锁定]                       │
开仓枢轴 + 紧止损 + 6:1盈亏比 + 周期                    ▼
        │                               [步骤 5: 结构化买方研报日记交付]
        └───────────────────────┬───────────────┘
                                ▼
                    【规范化买方决策输出】
```

#### 四大绝对禁令 (Four Non-Negotiable Prohibitions)
1. **禁令一：严禁不调网关、凭直觉脑补推荐热门股票**
   - 凡遇到用户询问“买哪个”、“推荐股票”、“今天买什么”等选股请求，**严禁**直接从模型记忆中挑选熟知的大票（如毫无理由直接推 NVDA、AAPL、TSLA）；
   - **必须物理执行** `FinancialAnalysisGateway.get_top_screening_candidates()` 或 CLI `--mode screening`，从美日 14,892 家全盘资产池初筛准入的客观名单中输出。
2. **禁令二：严禁推翻量化引擎的“一票否决权”**
   - 若 SEPA 引擎判定股票处于 Stage 4（阴跌期）或 Stage 1（筑底震荡期），或趋势判定为 `Out_Of_Trend`，AI **严禁**为了讨好用户或主观找理由将其包装为“具备投资价值”；
   - 必须坚决执行 `HARD_REJECT_DISQUALIFIED` 否决评级并给出警示。
3. **禁令三：严格区分“全盘初筛 (Inward)”与“个股体检 (Outward)”认知路径**
   - 寻找标的走 **全盘初筛路径**：全盘底账 $\to$ 突破就绪标的 $\to$ 行业与法务过滤 $\to$ 输出执行计划；
   - 诊断指定股票走 **深度体检路径**：时效门禁 $\to$ 三表平账 $\to$ 趋势准入 $\to$ 物理逃逸 $\to$ 估值与加仓。
4. **禁令四：小资金操盘五要素硬锁定 (Five-Element Small-Cap Lock)**
   - 凡涉及小资金高爆发方案，必须在报告首段显式锁死：① 开仓突破枢轴价 ($P_{pivot}$)、② -3.5% 刚性硬止损价 ($P_{stop}$)、③ 1.5R (+5.0%) 零风险平保触发价 ($P_{breakeven}$)、④ 6:1 目标盈利靶心 ($P_{target}$)、⑤ 预期持有兑现时间周期 (2~8 周)。缺失任何一要素均属严重违规。

---

### 1. 技能定位与工程位置
本工程已将完整的量化投研体系原生打包为 Agent Skill：
- **项目专属技能路径**：`.claude/skills/shuiyuan-analysis/SKILL.md`（Git 版本受控）
- **根目录技能路径**：`SKILL.md`
- **技能名称**：`shuiyuan-analysis` (v6.4.0)
- **技能角色**：买方首席量化策略师 (Buy-Side Chief Quant Strategist)

### 2. AI 意图识别与场景触发路由矩阵
当用户在对话中表达以下意图或关键词时，AI Agent 必须主动识别并路由调用本技能：

| 用户自然语言意图 | 典型关键词 / 触发句 | 对应执行模式 | 核心调用底层模块 |
| :--- | :--- | :--- | :--- |
| **全市场选股与买点初筛** | “今天买哪个股票”、“帮我选股”、“全盘筛选突破标的”、“有什么值得买” | `screening` | `finance_tools.screening.screening_candidate_ranker`<br>`FinancialAnalysisGateway.get_top_screening_candidates` |
| **小资金高爆发加仓** | “小资金怎么做”、“高爆发策略”、“翻倍加仓计划”、“非对称买点”、“极紧止损” | `timing` (`--small-cap`) | `financial_core.engines.sepa_buy_signal_engine`<br>`FinancialAnalysisGateway.analyze_timing_and_execution` |
| **机构稳健选股与时机** | “测一下某股票买点走廊”、“第二阶段主升浪判断”、“VCP 收敛度” | `timing` | `financial_core.engines.sepa_buy_signal_engine` |
| **商业物理动力学分析** | “测一下某股票物理动量”、“动能势能比多少”、“是否达到逃逸速度” | `physics` | `financial_core.engines.universal_physical_dynamics_engine` |
| **法务会计防舞弊核查** | “排查某公司财务造假”、“算一下 Beneish M-Score”、“排查应收账款粉饰” | `forensics` | `finance_tools.forensics_and_valuation.forensics_and_valuation` |
| **破产违约距离测算** | “排查某公司债务违约风险”、“KMV-Merton 信用测算”、“暴雷排查” | `credit` | `financial_core.engines.credit_risk_engine` |
| **流动性冲击与滑点** | “测算这只股票的买入容量”、“Amihud 滑点多少”、“排查微盘流动性陷阱” | `liquidity` | `finance_tools.risk_and_derivatives.risk_and_derivatives` |
| **期权偏度与异动流** | “看下某股票期权偏度”、“期权主力异动”、“排查隔夜暴跌对冲大单” | `options` | `finance_tools.risk_and_derivatives.risk_and_derivatives` |
| **宏观状态机与仓位预算**| “当前宏观是大牛市还是震荡”、“市场状态机识别”、“建议总仓位多少” | `regime` | `financial_core.engines.market_regime_switching_engine` |
| **细分行业因果画像** | “分析半导体行业”、“软件行业驱动指标是什么”、“白酒行业催化与风险” | `industry` | `finance_tools.governance_and_pipeline.financial_analysis_gateway` |
| **全景多模型综合诊断** | “全面诊断 NVDA”、“一键多模型诊断”、“全息买方评级” | `all` | `FinancialAnalysisGateway.analyze_comprehensive` |
| **产业链涟漪传导推演** | “台积电停电影响苹果和ASML多少”、“代工厂断供上下游如何传导” | `ripple` | `scripts/run_supply_chain_ripple_analysis.py` |
| **多业务分部 (SOTP) 穿透**| “某公司云业务停机损失多少”、“SOTP 因果穿透” | `sotp` | `scripts/run_sotp_event_penetration.py` |

---

### 3. 调用方式一：Claude Code / AI Agent Slash Command (`/shuiyuan-analysis`)
在支持 Claude Code 或 Agent SDK 的终端中，AI 或用户可以直接输入斜杠命令调用：
```bash
/shuiyuan-analysis
```
或带参数传递具体诉求：
```bash
/shuiyuan-analysis 帮我用小资金高爆发模式分析 NVDA 的当前买点与倒金字塔加仓计划
```

---

### 4. 调用方式二：Python API 级统一网关调用 (`FinancialAnalysisGateway`)
在 Python 脚本或 Agent 代码内部，直接通过单一事实来源网关执行 0-Token 纯本地计算：

```python
from finance_tools.governance_and_pipeline.financial_analysis_gateway import (
    FinancialAnalysisGateway,
)

gateway = FinancialAnalysisGateway.get_instance()

# 示例 0: 全盘初筛准入优质候选池聚合与排序 (选股唯一事实来源，严禁主观凭空推荐!)
screening_result = gateway.get_top_screening_candidates(top_n=10, market="ALL")  # 支持 ALL / US / JP
print("全盘初筛准入标的总数:", screening_result["total_qualified_count"])
print("核心旗舰买点池 (Pivot Ready):", len(screening_result["top_pivot_ready_candidates"]))
for cand in screening_result["top_pivot_ready_candidates"]:
    print(f"[{cand['market']}] {cand['ticker']} ({cand['company_name']}) | 现价: {cand['latest_price']} | 突破枢轴: {cand['pivot_price']}")

# 示例 1: 小资金非对称高爆发加仓计划与时机分析
timing_result = gateway.analyze_timing_and_execution(
    symbol="NVDA",
    raw_bars=daily_bars_list,  # 包含 date, open, high, low, close, volume, turnover 的字典列表
    profile="Aggressive_Small_Cap",  # 关键：指定小资金画像
)
print("小资金硬止损线:", timing_result["small_cap_plan"]["hard_stop_loss_price"])
print("1.5R 零风险平保触发价:", timing_result["small_cap_plan"]["breakeven_trigger_price"])
print("6:1 目标盈利靶心:", timing_result["small_cap_plan"]["target_profit_price"])
print("倒金字塔第一加仓位:", timing_result["small_cap_plan"]["first_pyramid_price"])

# 示例 2: 细分行业因果敏感性查询
industry_report = gateway.analyze_industry("NVDA")  # 自动映射至 semiconductors
print("行业核心驱动因子:", industry_report.key_drivers)
print("会计关注点:", industry_report.accounting_focus)
print("因果敏感性矩阵:", industry_report.causal_sensitivities)

# 示例 3: 一键全景买方金融与行业融合诊断 (全模型联动)
comp_report = gateway.analyze_comprehensive(
    symbol="NVDA",
    raw_bars=daily_bars_list,
    market="US",
    profile="Aggressive_Small_Cap",
)
print("终局行动裁决:", comp_report.actionable_verdict)
print("结构化中文买方日记:", comp_report.executive_summary_zh)
```

---

### 5. 调用方式三：终端 CLI 统一调度入口 (`run_financial_analysis_gateway.py`)
AI 可以在系统后台或由用户通过 Bash/PowerShell 直接运行 CLI：

```bash
# 0. 全盘初筛准入池优选排序 (选股第一步：获取 Stage_2_Pivot_Ready 突破就绪榜单)
python scripts/run_financial_analysis_gateway.py --mode screening --top 10 --market US
python scripts/run_financial_analysis_gateway.py --mode screening --top 10 --market JP

# 1. 小资金高爆发加仓与逃逸动能分析 (最常用)
python scripts/run_financial_analysis_gateway.py --mode timing --target NVDA --small-cap

# 2. 机构标准稳健选股与时机分析
python scripts/run_financial_analysis_gateway.py --mode timing --target NVDA

# 3. 细分行业知识与因果敏感性分析 (支持股票代码或行业名称)
python scripts/run_financial_analysis_gateway.py --mode industry --target semiconductors
python scripts/run_financial_analysis_gateway.py --mode industry --target 软件

# 4. 商业物理动力学分析 (质量/动量/动能势能比/逃逸速度)
python scripts/run_financial_analysis_gateway.py --mode physics --target NVDA

# 5. 法务会计 Beneish M-Score 防舞弊核算
python scripts/run_financial_analysis_gateway.py --mode forensics --target NVDA

# 6. KMV-Merton 结构化信用违约与破产风险
python scripts/run_financial_analysis_gateway.py --mode credit --target NVDA

# 7. Amihud 微观流动性冲击与非线性动态滑点
python scripts/run_financial_analysis_gateway.py --mode liquidity --target NVDA --order-value 100000

# 8. 期权偏度与异动流
python scripts/run_financial_analysis_gateway.py --mode options --target NVDA

# 9. 宏观 3-状态高斯 HMM 识别
python scripts/run_financial_analysis_gateway.py --mode regime --target SPY

# 10. 全景买方融合综合诊断 (输出格式可选 text 或 json)
python scripts/run_financial_analysis_gateway.py --mode all --target NVDA --small-cap --format text
```

---

### 6. 资金画像模式切换：机构稳健 vs 小资金高爆发
系统提供两种截然不同风险收益特征的执行画像，AI Agent 必须根据用户资金属性自适应切换：

| 对比维度 | 机构稳健画像 (`Standard_Institutional`) | 小资金高爆发画像 (`Aggressive_Small_Cap`) |
| :--- | :--- | :--- |
| **设计核心目标** | 规避大幅回撤、兼顾容量、平滑净值曲线 | **极限非对称盈亏比、以窄止损博爆发翻倍** |
| **硬止损阈值** | $-7.0\% \sim -8.0\%$ 宽止损缓冲 | **$-3.5\%$ 极限压紧硬止损**（严禁深套） |
| **目标盈亏比 (R:R)** | $2.5:1 \sim 3.0:1$ 稳健获利目标 | **$6.0:1$ 非对称暴利靶心** ($+21.0\% \sim +30.0\%$) |
| **保本平保机制** | 浮盈 $+10\%$ 或 $2.0R$ 触发平保 | **浮盈达到 $1.5R$ ($+5.0\%$) 立即无风险保本 (Free-Roll)** |
| **加仓策略** | 单笔全额建仓或均分仓位 | **倒金字塔顺势加仓：50% ➔ +30% ➔ +20%** |
| **物理逃逸门禁** | 仅作为参考动量指标 | **硬门禁：$R_E = E_k / E_p \ge 1.0$，拦截冲高回落** |
| **适用人群** | 养老金、险资、大体量专户 | **小资金成长账户、追求高资本周转率与爆发力账户** |

---

### 7. AI 规范 Prompt 与结构化交付物模板

#### A. AI Agent 必须遵守的 Prompt 约束规范：
1. **前置行情时效与数据完备度声明**：每次回复开头，强制声明数据基准时间戳、交易时钟状态（盘前/盘中/盘后/前收盘），严禁模糊引用。
2. **拒绝大表刷屏**：必须以清晰的“独立卡片”呈现买点走廊、阻力位、支撑位与执行价格。
3. **严禁臆造数字**：所有财务指标、止损位、目标位必须由底层网关计算产出。
4. **强制买方日记**：在输出末尾必须包含 `### 📝 【AI 投研日记与定性归纳】`，从微观流动性反身性、跨期因果、对手盘画像、非对称凸性四个维度进行深度思辨。

#### B. 标准富文本交付卡片模板：
```markdown
### 🛡️ 【行情时效与数据完备度前置声明】
- **基准时间戳**：2026-11-10 16:00:00 EDT (美股盘后结算价基准)
- **数据新鲜度状态**：已完成官方历史日 K 线落盘核验，非未来虚假数据。

---

### 🎯 【标的买方量化诊断卡片：NVDA (英伟达)】
- **资金画像模式**：【小资金高爆发非对称画像 (Aggressive_Small_Cap)】
- **趋势形态判定**：SEPA 第二阶段主升浪已确立 | VCP 波动收缩 3T 收敛就绪
- **物理逃逸动能比率 ($R_E$)**：`1.38` (达成火箭逃逸速度，突破有效，非冲高假突破)

#### 🚀 【小资金非对称倒金字塔执行计划】
| 阶梯阶段 | 触发条件 | 执行价格 | 仓位调度 | 风控与止损约束 |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: 突破首建仓** | 突破 Pivot 枢轴点 | **$135.00** | **50%** 底仓 | **硬止损 $130.28 (-3.5%)**，风险敞口 $R = $4.72 |
| **Stage 2: 顺势初加仓** | 突破次级平台 (+5.0%) | **$142.08** | **+30%** | **触发 1.5R 极速平保，止损线上移至成本价 $135.00 (Free-Roll 零风险)** |
| **Stage 3: 主升浪锁仓** | 加速脱离成本 (+10.0%) | **$148.50** | **+20%** | **锁死全额仓位，追踪止盈** |
| **Target: 终极爆发靶心**| 达成 6:1 盈亏比目标 | **$163.35** | **锁定利润** | **全仓实现 +21.00% 暴利靶心** |

---

### 📝 【AI 投研日记与定性归纳】
1. **微观流动性与反身性**：NVDA 在 $135 枢轴点处换手率骤降至历史 50 日均量的 42%，筹码呈现高纯度锁定。买方大单在盘口不留痕迹，空头无法通过砸盘触发被动止损盘。
2. **对手盘画像**：上方套牢盘在经历 3 次 VCP 收缩清洗后已彻底出清，当前主要对手盘为场外等待回调上车的踏空资金，一旦突破 $135 将引发空头挤压 (Gamma Squeeze)。
3. **非对称凸性工程**：小资金绝不参与震荡磨损。以 -3.5% 的极窄试错成本去博取 6:1 的爆发空间，并在 +5% 处利用 1.5R 机制将下行风险彻底清零，实现纯白嫖式利润奔跑。
```

---

## 四、 本地买方交易室推流服务与交互拓扑大屏

系统内置纯标准库实现的轻量交易室推流服务 (`scripts/serve_radar_dashboard.py`)，零外部网络框架依赖：

### 启动推流服务：
```bash
python scripts/serve_radar_dashboard.py --port 8899 --open-browser
```
服务将在本地 `http://127.0.0.1:8899` 启动并自动在浏览器中唤起大屏。

### 交易室推流 REST API：
- `GET /api/stream`: 提供心跳检测与增量未核实传闻事件流；
- `GET /api/events`: 导出全量事件雷达底账与分级状态；
- `GET /api/receipts`: 导出官方公报 SHA-256 密码学防伪鉴真收据；
- `GET /api/supply-chain/topologies`: 获取当前注册的产业链拓扑架构；
- `GET /api/supply-chain/ripple`: 动态执行断供冲击天数推演，推流上下游损益矩阵；
- `POST /api/verify`: 接收官方下载文件路径，现场验签并解除传闻熔断限制。

---

## 五、 全盘万家资产池与流式批处理调度体系

针对美股全市场（10,000+ 家）与东证全市场（4,400+ 家）共计全量数千家上市主体，系统采用分级资产池架构与流式调度管道：
- **Tier 0 (P0)**：核心旗舰蓝筹（三表全息底稿、多情景 DCF、库存周转 DIO）；
- **Tier 1 (P1)**：主线成长股（定期情景更新与买点跟踪）；
- **Tier 2 / Tier 3 (P2/P3)**：全市场数千家上市公司的全息索引与 0-Token 极速初筛。
- **流式分批管道 (Chunk-and-Stream)**：以 50~150 家企业为批次切片，边计算边落盘边推流，支持意外中断断点续传。

---

## 六、 四道架构防劣变验收硬门禁 (Non-Regression Gates)

任何代码与文档变更，必须依次通过四道硬门禁方可交付：

1. **架构完整性全息巡检**：
   ```bash
   python scripts/verify_architecture_integrity.py
   ```
   - 验证底层纯净金融核心零污染、全量模块导入零环路、门面与底账就绪。
2. **全量单元测试与便携 CI 零失败**：
   ```bash
   python scripts/run_ci.py
   python -m unittest discover -s scripts -p "test_*.py"
   ```
   - 保证测试数量只增不减，100% PASS。
3. **四大治理回归全绿**：
   ```bash
   python scripts/test_data_store.py
   python scripts/validate_knowledge_structure.py
   python scripts/test_research_contract.py
   python scripts/test_industry_mapping.py
   ```
4. **不可篡改密码学账本验签**：
   ```bash
   python -c "from financial_core.engines.prediction_ledger import PredictionLedger; assert PredictionLedger().verify_integrity()['tampered'] == False"
   ```

---

## 七、 附录：12 本专责核心设计典籍 SSOT 地图

系统深层规范收敛为 12 本专责设计典籍，确立排他的单一事实来源：

| 典籍编号 | 典籍代号与文件路径 | 核心业务专责 (Responsibility Scope) | 权威单一事实来源 (SSOT) |
| :--- | :--- | :--- | :--- |
| **SPEC-01** | [`SPEC_01_系统总体架构与分层工程总纲.md`](docs/SPEC_01_系统总体架构与分层工程总纲.md) | 系统愿景、六大功能域全景、四层单向依赖与命名规范 | **系统顶层工程架构与分层铁律 SSOT** |
| **SPEC-02** | [`SPEC_02_多模态视觉呈现与研报Token设计规范.md`](docs/SPEC_02_多模态视觉呈现与研报Token设计规范.md) | 买方研报排版、设计令牌、自然中文语义与无截断打印 | **研报排版、Token 与视觉契约 SSOT** |
| **SPEC-03** | [`SPEC_03_行业知识中枢与微观商业机器解构规格书.md`](docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md) | 11 大板块 41 个行业知识中枢、所有者收益与动态护城河 | **行业知识、商业模式与护城河解构 SSOT** |
| **SPEC-04** | [`SPEC_04_六步研究法与官方财报三表契约规范.md`](docs/SPEC_04_六步研究法与官方财报三表契约规范.md) | 六步研究法、官方三表强勾稽、营运资本循环 (DIO/DSO) | **六步研究法与官方三表动态勾稽 SSOT** |
| **SPEC-05** | [`SPEC_05_数据采集AI浏览器补数与证据治理规范.md`](docs/SPEC_05_数据采集AI浏览器补数与证据治理规范.md) | 数据采集中枢、AI 浏览器补数 SOP、三表平账自检门禁 | **数据治理、AI 补数与平账证据链 SSOT** |
| **SPEC-06** | [`SPEC_06_核心金融计算与多情景DCF估值引擎设计书.md`](docs/SPEC_06_核心金融计算与多情景DCF估值引擎设计书.md) | 纯净金融核心计算、三态情景 DCF、KMV-Merton 破产模型 | **金融数学公式、DCF 走廊与信用风险 SSOT** |
| **SPEC-07** | [`SPEC_07_买方时机决策与技术足迹分析引擎设计书.md`](docs/SPEC_07_买方时机决策与技术足迹分析引擎设计书.md) | SEPA 买入信号引擎、8 大趋势硬指标、VCP 递归收敛 | **技术足迹分析与 SEPA 买入时机 SSOT** |
| **SPEC-08** | [`SPEC_08_期权全周期因果分析与仓位风控引擎设计书.md`](docs/SPEC_08_期权全周期因果分析与仓位风控引擎设计书.md) | 期权因果推导、波动率曲面、无套利边界与 1/4 凯利仓位 | **期权定价因果链与仓位风控 SSOT** |
| **SPEC-09** | [`SPEC_09_全球宏观流动性与跨资产配置体系设计书.md`](docs/SPEC_09_全球宏观流动性与跨资产配置体系设计书.md) | 宏观流动性雷达、美联储资产负债表、跨资产迁徙路径 | **宏观流动性传导与黑天鹅风控 SSOT** |
| **SPEC-10** | [`SPEC_10_千家资产池流式建档与公司深度档案生成流水线.md`](docs/SPEC_10_千家资产池流式建档与公司深度档案生成流水线.md) | 万家企业资产池、流式分批建档流水线、5-Sheet Excel | **全盘资产池管理与流式建档流水线 SSOT** |
| **SPEC-11** | [`SPEC_11_云端无头每日行情与研报自动化调度流水线.md`](docs/SPEC_11_云端无头每日行情与研报自动化调度流水线.md) | 美股/日股每日定时无头调度、行情时效核验门禁 | **云端无头自动化与定时调度流水线 SSOT** |
| **SPEC-12** | [`SPEC_12_系统质量工程密码学账本与全息测试验收标准.md`](docs/SPEC_12_系统质量工程密码学账本与全息测试验收标准.md) | SHA-256 密码学不可篡改预测账本、四道架构验收硬门禁 | **质量工程、密码学验签与验收门禁 SSOT** |

---

## 八、 工程全量依赖规范与环境配置指引 (System Dependencies & Environment Guide)

系统遵循《CLAUDE.md》与《AGENTS.md》之“**单一事实来源 (SSOT) 与极致做减法**”原则，全量生产与投研开发依赖统一收敛于项目根目录的 [`requirements.txt`](requirements.txt)。

### 1. 运行环境基准 (Python Runtime Baseline)
- **推荐版本**：`Python 3.10.x` 或 `Python 3.11.x`（生产稳定版）；
- **兼容范围**：`Python 3.10 ~ 3.13`（全量代码严格通过语法树解析与类型断言）；
- **运行哲学**：**0-Token 纯本地物理计算**。所有量化计算、均线、期权二叉树、情景 DCF 估值与财报平账检验 100% 在本地执行，绝不向大模型盲目注入无用长文本，无外部付费 API 密钥依赖。

### 2. 五大功能域依赖矩阵 (Dependency Matrix)

| 功能分类 (Domain) | 核心依赖包 (Packages) | 版本约束 (Constraint) | 核心业务专责与应用场景 (Business Purpose) |
| :--- | :--- | :--- | :--- |
| **一、 核心科学计算与数值基石** | `numpy`<br>`scipy`<br>`pandas`<br>`scikit-learn` | `>=1.26.0,<2.3.0`<br>`>=1.12.0,<1.15.0`<br>`>=2.1.0,<2.4.0`<br>`>=1.3.0,<1.6.0` | 标的 250 日 OHLCV 向量化计算、SEPA 50/150/200 日移动均线、卡尔曼滤波、极值分布拟合、HMM 隐马尔可夫大盘牛熊总阀门识别。 |
| **二、 金融量化、估值与组合回测** | `numpy-financial`<br>`pyxirr`<br>`quantstats`<br>`financetoolkit` | `>=1.0.0,<=1.1.0`<br>`>=0.10.0,<=0.10.8`<br>`>=0.0.60,<=0.0.86`<br>`>=2.1.0,<=2.2.1` | 不规则现金流高精度 XIRR 贴现（DCF 估值矩阵与所有者收益）、买方夏普比率/最大回撤/尾部风险归因、官方财报杜邦分析。 |
| **三、 官方数据采集与时钟门禁** | `requests`<br>`urllib3`<br>`aiohttp`<br>`yfinance`<br>`python-dateutil`<br>`pytz` | `>=2.31.0,<=2.34.2`<br>`>=2.0.0,<3.0.0`<br>`>=3.9.0,<3.12.0`<br>`>=0.2.35,<=1.7.0`<br>`>=2.8.2,<=3.0.0`<br>`>=2024.1,<=2026.6` | 官方监管页面数据提取、行情时效新鲜度门禁（`verify_quote_freshness`）时钟核对、交易日历计算与日期降序时序索引。 |
| **四、 财报法证与研报多模态呈现** | `arelle-release`<br>`lxml`<br>`openpyxl`<br>`pymupdf`<br>`pypdf`<br>`reportlab` | `>=2.45.0,<=2.46.1`<br>`>=5.1.0,<=6.1.3`<br>`>=3.1.2,<=3.1.5`<br>`>=1.24.0,<=1.28.2`<br>`>=4.0.0,<=6.10.2`<br>`>=4.1.0,<=4.4.0` | SEC EDGAR 官方原始 10-K/10-Q XBRL 格式底稿解析、买方 5-Sheet Excel 动态公式建造、A4 矢量 PDF 研报双语无截断排版。 |
| **五、 架构治理、Schema与质量工程** | `jsonschema`<br>`PyYAML`<br>`typing_extensions` | `>=4.20.0,<=4.25.1`<br>`>=6.0.1,<=6.0.3`<br>`>=4.10.0,<=4.16.0` | 深度档案与每日研报 JSON Schema 刚性契约核验、系统全局配置字典解析、SHA-256 不可篡改时间账本验签。 |

### 3. 环境初始化与一键安装指引 (Quick Installation)

#### 模式 A：本机标准环境安装 (推荐)
```bash
# 1. 升级 pip 安装器至最新
python -m pip install --upgrade pip

# 2. 一键安装全盘依赖 (单一事实来源)
pip install -r requirements.txt
```

#### 模式 B：项目内置隔离环境自动化初始化
工程内置自动引导脚本，可一键在项目目录内建立干净隔离的 `.venv-ci` 环境并完成依赖闭环验证：
```bash
# 自动建立隔离环境并安装锁定依赖 (仅限 Python 3.10)
python scripts/bootstrap_ci.py
```

### 4. 依赖合规与全息测试验收门禁 (Verification Gates)
依赖安装或升级完成后，必须执行以下命令确保全盘架构与单元测试 100% PASS：

```bash
# 1. 架构完整性全息巡检 (零逆向依赖、纯相对导入核验)
python scripts/verify_architecture_integrity.py

# 2. 全量单元测试套件回归 (包含流水线看板引擎测试)
python -m unittest discover -s scripts -p "test_*.py"

# 3. 四大治理回归全绿断言
python scripts/test_data_store.py
python scripts/validate_knowledge_structure.py
python scripts/test_research_contract.py
python scripts/test_industry_mapping.py
```

---

## 九、 冷热数据分层生命周期与云端防泄露架构 (Hot/Warm/Cold Data Lifecycle)

系统严格贯彻**“GitHub 云端只放冷热加工工具与方法，本地工作站物理隔离留存数据本体”**的架构边界。详细设计请查阅专著文档：[冷热数据分层生命周期与云端防泄露架构说明书](docs/HOT_WARM_COLD_DATA_ARCHITECTURE.md)。

### 1. 三层本地数据定位
- **🔥 热数据 (`data/hot/`)**：近 30 天行情与近 1~2 年高频财报快照，零压缩毫秒直读，直通盘前 3 分钟决策与看板大屏；
- **🌤️ 温数据 (`data/warm/`)**：30 天 ~ 3 年标准 K 线与近 3 年（12 季度）财报切片，附带轻量索引清单，服务形态收敛与 DCF 估值；
- **❄️ 冷数据 (`data/cold/`)**：3 年以上历史全周期底稿通过 Gzip 高倍压缩下沉（节省 **85% ~ 93%** 空间），并携带 SHA-256 指纹清单支持秒级无损唤醒还原。

### 2. 常用冷热加工与防泄露门禁指令
```bash
# 查看本地冷/温/热数据磁盘空间分布
python scripts/compact_cold_data.py --status

# 对单只标的执行无损冷热分层打样 (默认保留原文件)
python scripts/compact_cold_data.py --sample-ticker NVDA

# 验证冷数据压缩包秒级唤醒与 SHA-256 完整性校验
python scripts/compact_cold_data.py --restore-check NVDA

# 执行云端 GitHub 防数据泄露物理检查（并可选挂载 git pre-commit 钩子）
python scripts/verify_no_data_leak_guard.py
```
