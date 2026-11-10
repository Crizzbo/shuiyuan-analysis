---
name: shuiyuan-analysis
version: 6.2.0
description: 水源分析——买方机构级股票量化投研、全市场趋势选股、九大硬核数学计算公式体系与产业链涟漪因果穿透 Agent Skill。覆盖全市场资产池（美股10,000+/日股4,400+/核心567）商业物理动力学动量逃逸模型、法务会计Beneish M-Score八维Probit防舞弊、KMV-Merton信用破产违约距离、Amihud微观流动性冲击与非线性滑点、期权偏度与异动流、宏观3状态高斯HMM、SEPA趋势模板选股、行情时效硬核验门禁、官方财报三表平账与多情景DCF估值、SOTP多业务分部损益穿透、多标的产业链上下游因果传导矩阵（DIO缓冲/转嫁权/有限责任下界）、突发事件雷达全天候守护与法定信源防伪鉴真、本地买方交易室推流交互大屏、以及 finance_tools 6 大高内聚子目录分包架构。
license: Proprietary
metadata:
  author: Shuiyuan Quant Research Architecture Team
  version: "6.2.0"
  domain: quantitative-equity-research-and-supply-chain-ripple
  triggers: 选股, 股票分析, 研报生成, 突发事件, 产业链涟漪, 产业链分析, SOTP, 业务分部拆解, 事件雷达, 行情时效, 财务估值, 趋势选股, DCF估值, 买点推演, 交易室大屏, 金融计算, 数学公式, 物理动力学, Beneish, Merton, Amihud, 期权偏度, 宏观状态机, shuiyuan-analysis
  role: buy-side-chief-quant-strategist
  scope: full-stack-equity-research-and-ripple-dynamics
---

# 水源分析 Agent Skill (v6.2.0 买方数学量化计算、物理动力学与分包架构版)

买方机构级股票量化选股、微观法证审计、SOTP 业务分部穿透、多标的产业链涟漪传导矩阵、全天候事件雷达推流大屏与 6 大业务工具子包架构。

> [!IMPORTANT]
> **程序、AI 与投研闭环三大刚性原则 (The Core Tri-Pillar Principles)**:
> 1. **程序只负责坚硬客观的数据骨架 (Objective Quantitative Skeleton)**：
>    - **官方三表刚性平账自检**：$Assets = Liabilities + Equity$ 不平账或现价/股数非法时刚性阻断，严禁输出虚假估值；
>    - **交易时段与时效硬核验门禁**：自动绑定交易所当地时区（美股 EDT/EST、A股 CST、日股 JST）并对齐交易日历，未来时间戳刚性拦截，旧日缓存自动降级为前收盘价基准；
>    - **确定性量化数学计算**：SEPA 8 大趋势硬指标、VCP 4T 波动收缩、多情景 DCF 估值矩阵、SOTP 分部损益穿透、存货周转天数 (DIO) 吸收周期与产业链涟漪因果传导矩阵；
>    - **严禁程序越界输出机械武断的定论**：废除硬编码买卖评级与固定虚假仓位，无校准概率时严格展示为“待定”。
> 2. **AI 负责赋予六维立体的思考血肉 (Multi-Dimensional Cognitive Flesh)**：
>    - 彻底破除“机械清单主义（Checklist Bureaucracy）”与“一阶线性思维”；
>    - 必须从**微观流动性反身性、跨期因果与索罗斯反身性、资金期限错配与对手盘画像、非对称凸性工程、前置证伪红线、产业链生态位共振**六大高阶认知维度开展推演；
>    - 在决策卡片底部的 `### 📝 【AI 投研日记与定性归纳】` 专区中撰写富有商业洞察的买方投研日记。
> 3. **系统闭环复盘与贝叶斯自我演进 (Retrospective Reflection & Bayesian Evolution)**：
>    - 每日对账前期预测走廊与今日真实结算，从流动性踩踏、预期差反转、对手盘被迫平仓等深层机理执行四维法证归因；
>    - 动态联合校准贝叶斯先验矩阵（更新波动率溢价、安全边际缓冲与仓位分配分布）。

---

## 一、 触发场景与意图路由矩阵 (Trigger Matrix)

当用户提出以下任一诉求时，Agent 必须主动激活本技能并路由至对应的专业处理流水线：

| 用户核心意图 | 典型自然语言触发词 | 核心调度入口 / 工具 | 输出交付物规范 |
| :--- | :--- | :--- | :--- |
| **全市场选股与趋势扫描** | “帮我选股”、“挑几只趋势好的标的”、“扫描纳指/日经优质突破股” | `finance_tools.sepa_buy_signal_engine`<br>`scripts.run_10k_universe_pipeline` | SEPA 趋势筛选卡片、买点价格走廊、VCP 收缩形态、止损保护线 |
| **个股系统性深度投研** | “分析 NVDA / 7203 / 五粮液”、“测算某公司合理估值”、“排查财务粉饰” | `skill_gateway.default_gateway`<br>`scripts.generate_deep_dossier` | 买方深度研报档案 (Deep Dossier)、官方三表清洗、多情景 DCF 估值矩阵 |
| **多业务分部 (SOTP) 穿透** | “某公司云业务停机损失多少”、“分部拆解公司估值”、“SOTP 因果穿透” | `finance_tools.sotp_event_analyzer`<br>`scripts.run_sotp_event_penetration` | SOTP 分部加总估值表、微观物理损益穿透报告、净利冲击百分比 |
| **产业链上下游涟漪效应推演** | “台积电停电影响苹果和ASML多少”、“某代工厂断供上下游如何传导”、“产业链涟漪分析” | `financial_core.engines.supply_chain_ripple_engine`<br>`scripts.run_supply_chain_ripple_analysis` | 产业链非对称涟漪传导矩阵、DIO 吸收周期、议价转嫁冲销、各标的 $\Delta EBIT$ 测算 |
| **突发事件监控与法定鉴真** | “最近有什么重大消息”、“排查某传闻真伪”、“启动事件雷达” | `finance_tools.event_radar_collector`<br>`finance_tools.evidence_verification_pipeline` | 0-Token 事件初筛底账、AI 浏览器核验清单、SHA-256 法定鉴真防伪收据 |
| **细分行业因果与知识画像** | “分析半导体行业”、“软件行业驱动指标是什么”、“白酒行业催化与风险” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode industry` | 细分行业买方画像、驱动指标、会计关注点、敏感性因果链与对标标的 |
| **商业物理动力学与动能突破** | “测一下某股票物理动量”、“动能势能比多少”、“是否达到逃逸速度” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode physics` | 商业质量、反弹半衰期、趋势推进速度、零增长停滞底价、动能/势能比率 |
| **法务会计防舞弊 (Beneish)** | “排查某公司财务造假”、“Beneish M-Score 测算”、“排查应收账款粉饰” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode forensics` | Beneish 八维指标卡片 (DSRI/GMI/AQI/SGI等)、舞弊嫌疑红线一票否决判定 |
| **KMV 信用违约与破产预警** | “测算某公司破产违约距离”、“Merton 信用风险”、“债务暴雷排查” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode credit` | 违约距离 DD (标准差倍数)、预期违约率 EDF、破产黑天鹅前瞻告警 |
| **Amihud 流动性与冲击滑点** | “测算这只股票的买入容量”、“Amihud 滑点多少”、“排查微盘流动性陷阱” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode liquidity` | Amihud 不流动性比率、单笔建议最大容量上限、非线性动态冲击滑点惩罚 |
| **期权偏度与主力大单异动** | “看下某股票期权偏度”、“期权主力异动”、“排查隔夜暴跌对冲大单” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode options` | 25-Delta 风险反转偏度、近远月波动率比值、交易量 PCR、Gamma 做市商状态 |
| **宏观状态机与配置总预算** | “当前宏观是大牛市还是震荡”、“市场状态机识别”、“建议总仓位多少” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode regime` | 3 状态高斯 HMM 识别 (牛市/震荡/危机)、总仓位预算上限与主导策略模型 |
| **全景金融多模型融合诊断** | “全面诊断 NVDA”、“一键多模型诊断”、“全息买方评级” | `finance_tools.financial_analysis_gateway`<br>`scripts.run_financial_analysis_gateway --mode all` | 串联行业/物理/法务/信用/流动性/期权/宏观的结构化全景买方决策档案 |
| **本地买方交易室推流看板** | “打开监控大屏”、“启动交易室推流服务”、“查看拓扑大屏” | `scripts.serve_radar_dashboard`<br>`scripts.generate_radar_dashboard` | 本地轻量推流 HTTP 服务 (`http://127.0.0.1:8899`)、交互拓扑大屏 |

---

## 二、 六大核心业务子系统与量化模型架构

```mermaid
flowchart TD
    subgraph S1["【子系统 1：全市场选股与时效门禁】"]
        Universe["全市场数千家资产池 (美股10k+ / 日股4.4k+ / 核心567)"] --> FreshnessGate["行情时效与交易时钟核验 (verify_quote_freshness)"]
        FreshnessGate --> SEPA["SEPA 8 大趋势硬指标 + VCP 4T 形态筛查"]
        SEPA --> PriceCorridor["四维解耦价格走廊与止损底价"]
    end

    subgraph S2["【子系统 2：财务法证审计与多情景估值】"]
        PriceCorridor --> OfficialFilings["官方原始三表底稿 (OfficialFilingMapper)"]
        OfficialFilings --> BalanceCheck{"刚性平账自检 A=L+E"}
        BalanceCheck -- 通过 --> Forensic["法证五刀穿透 (受限现金/存货毒性DIO/应收周转)"]
        Forensic --> DCFMatrix["多阶段自由现金流折现 (悲观底价 / 中性公允 / 乐观靶心)"]
    end

    subgraph S3["【子系统 3：SOTP 分部因果与产业链涟漪推演】"]
        DCFMatrix --> SOTP["SOTP 跨业务分部因果穿透 (微观物理损益折算)"]
        SOTP --> RippleEngine["多标的产业链上下游涟漪效应引擎 (DIO吸收/议价转嫁/有限责任)"]
    end

    subgraph S4["【子系统 4：事件雷达、法定鉴真与交易室推流】"]
        NewsFeeds["全天候新闻资讯与监管通告"] --> ZeroToken["0-Token 纯本地高效初筛与分级"]
        ZeroToken --> BrowserAssistant["AI 浏览器定向核验助手 (官方公报补数清单)"]
        BrowserAssistant --> LegalVerification["SHA-256 密码学法定防伪鉴真流水线 (解除熔断)"]
        LegalVerification --> StreamServer["本地轻量推流调度服务 (GET /api/stream)"]
        StreamServer --> LiveDashboard["交易室交互拓扑大屏 (reports/event_radar_dashboard.html)"]
    end

    RippleEngine -.-> LiveDashboard
```

### 1. 全市场选股与时效门禁子系统 (Stock Selection & Freshness Gate)
- **覆盖资产池**：
  - 美股：纽交所与纳斯达克全市场 10,000+ 家上市企业 (`data/universe/sec_company_tickers.json`)；
  - 日股：东证全市场 Prime/Standard/Growth 4,400+ 家企业 (`data/universe/jpx_company_tickers.json`)；
  - 顶层核心池：Tier 0 / Tier 1 核心 567 重点标的。
- **初筛数据边界与 0-Token 纯本地物理计算铁律**：
  - 初筛仅依赖标的过去 1 年（约 200~250 交易日）的客观日 K 线价量时序 (Daily OHLCV)；
  - 纯本地执行 50/150/200 日移动均线、52 周高低点、成交量萎缩度及 VCP 波动收缩形态收敛计算；
  - **初筛阶段严格禁止调用大语言模型 (LLM)**，严禁向上下文注入全量原始财报，实现 0-Token 秒级全市场数千家上市主体初筛；
  - 仅在初筛全票通过（进入第二阶段主升浪且形态收敛就绪）后，才允许向深度分析管道准入，调用官方三表底稿、DCF 估值并撰写深度买方研报日记。
- **最新日期核心数据拉取完成度强制前置声明门禁 (`finance_tools.data_readiness_tracker`)**：
  - 每次向用户输出股票分析、选股或研报前，强制前置调用数据完备度追踪器查验本地落盘底账；
  - 强制在回复开头显式声明：当前探测到的最新基准日期（如 `2026-11-07`）、已完成拉取的标的分类清单（宏观指数与个股）及数据完备度判定。
- **SEPA 8 大趋势硬指标**：
  1. $Price > MA50 > MA150 > MA200$
  2. $MA200$ 处于上升通道至少 1 个月
  3. $Price \ge 1.25 \times 52W\_Low$
  4. $Price \ge 0.75 \times 52W\_High$（距离 52 周新高回撤不超过 25%）
  5. 波动收缩形态 (VCP 4T: 振幅逐级收敛 $20\% \to 10\% \to 5\% \to 2\%$)
- **交易时段时效硬核验门禁 (`verify_quote_freshness`)**：
  - 必须绑定交易所当地时区（美股 EDT/EST、A股 CST、日股 JST）并对齐交易日历；
  - 严格区分盘前 (Pre-Market)、盘中 (Regular)、盘后 (After-Hours) 与前收盘价基准；
  - 未来时间戳刚性拦截，旧日缓存自动降级并显式告警，严禁旧数据冒充盘中现价。

### 2. 财务法证审计与多情景 DCF 估值子系统 (Forensic Audit & Scenario DCF)
- **官方三表底稿清洗与刚性平账自检**：
  - 任何录入主管道的财报底账必须通过 $Assets = Liabilities + Equity$ 刚性平账自检；
  - 经由 `OfficialFilingMapper` 转换非标字符串，严禁未清洗字符串直传核心。
- **存货周转天数 (DIO) 与供应链上下游集中度**：
  - $DIO = \frac{\text{Average Inventory}}{\text{COGS}} \times 365$
  - 穿透上下游前五大客户与核心供应商采购/销售集中度，识别单一依赖风险。
- **长短期差异化情景 DCF 估值矩阵**：
  - 悲观防线 (Pessimistic Floor)：折现率上浮 150-200bps，永续增长率 $g$ 降至 $1.5\%$，测算清算级破产底（NCPS/NCAV）；
  - 中性公允 (Neutral Anchor)：基准 WACC 与行业公允 $g$；
  - 乐观靶心 (Optimistic Target)：反映护城河扩张与自由现金流超预期增长。

### 3. SOTP 跨业务分部微观因果损益穿透子系统 (SOTP Segment Penetration)
- **业务分部画像结构**：依据 `config/sotp_profiles.json`，将综合性巨头拆解为独立分部（如 Alphabet: Google Search, YouTube, Google Cloud, Other Bets）；
- **微观物理损益折算模型**：
  $$\Delta EBIT_{total} = \sum_{i} \left( \text{SegmentEBIT}_{i} \times \text{ImpactPct}_{i} \right)$$
  - 支持突发业务冲击（如“云数据中心断电 3 天导致服务可用性下降”、“核心晶圆厂减产 $15\%$”），精确量化至每股税后收益 (EPS) 与股权公允折现值。

### 4. 多标的产业链上下游涟漪效应传导矩阵子系统 (Supply Chain Ripple Effect)
- **全链拓扑架构**：依据 `config/supply_chain_topologies.json`（严格通过 JSONSchema 验证）：
  $$\text{上游核心设备/原材料供应商} \longrightarrow \text{核心中枢制造/代工厂} \longrightarrow \text{下游大客户/终端品牌}$$
- **存货周转天数 (DIO) 吸收周期数学模型**：
  $$\text{UncoveredDays} = \max(0.0, T_{\text{disrupt}} - DIO)$$
  $$\text{ExposureRatio} = \frac{\text{UncoveredDays}}{T_{\text{disrupt}}} \quad (\in [0.0, 1.0])$$
  - 若断供天数小于企业自身存货周转天数 ($T_{\text{disrupt}} \le DIO$)，存货完全吸收物理冲击，敞口比例为 $0.0$；
- **核心中枢标的损益与议价转嫁冲销**：
  $$\text{Shock}_{\text{hub}} = \text{BaseShock} \times \text{ExposureRatio}_{\text{hub}}$$
  $$\Delta EBIT_{\text{hub}} = \text{Shock}_{\text{hub}} \times \left(1.0 - \text{PricingPower}_{\text{hub}} \times 0.5\right)$$
- **下游大客户二级传导与衰减**：
  $$\text{EffectiveShock}_{\text{down}} = |\text{Shock}_{\text{hub}}| \times \beta_{\text{down}} \times \frac{\max(0.0, T_{\text{disrupt}} - DIO_{\text{down}})}{T_{\text{disrupt}}}$$
  $$\Delta EBIT_{\text{down}} = - \text{EffectiveShock}_{\text{down}} \times \left(1.0 - \text{PricingPower}_{\text{down}}\right)$$
- **有限责任数学边界防御**：
  - 严禁除零除负，营业利润损益严格被截断在 $[-100.0\%, +50.0\%]$ 的有限责任区间内。

### 5. 突发事件雷达全天候守护与法定信源防伪鉴真子系统 (Event Radar & Legal Verification)
- **0-Token 纯本地高效初筛**：
  - 基于高优先级正则词库对海量盘前/盘中资讯进行本地极速初筛与关键词去噪；
  - 仅对匹配到实体与关键业务分类的高价值资讯调用大模型结构化提取，节省 $95\%+$ Token 消耗；
- **AI 浏览器定向核验助手 (`BrowserVerificationAssistant`)**：
  - 自动为待核验重大传闻生成官方监管（SEC/JPX/EDGAR）、行业协会、公司官网的定向核验补数清单；
- **法定信源 SHA-256 防伪鉴真流水线 (`EvidenceVerificationPipeline`)**：
  - 官方公报原文下载落盘后，通过密码学哈希签名生成防伪鉴真收据（Verification Receipt）；
  - 验签属实后，自动将事件状态从 `Unverified_Rumor` 跃迁为 `Confirmed_Fact`，解除传闻熔断限制。

### 6. 本地买方交易室推流服务与拓扑交互大屏 (Trading Room Live Stream Dashboard)
- **纯标准库轻量推流调度器**：`scripts/serve_radar_dashboard.py` 基于 `http.server`，零物理第三方重量级网络库依赖；
- **交易室动态推流 API 清单**：
  - `GET /api/stream` 或 `/api/live`: 提供探活心跳、未核实传闻熔断计数与增量推流；
  - `GET /api/events`: 导出全量事件雷达底账与分级状态；
  - `GET /api/receipts`: 导出官方公报 SHA-256 防伪鉴真收据清单；
  - `GET /api/supply-chain/topologies`: 导出可用产业链拓扑架构清单；
  - `GET /api/supply-chain/ripple`: 实时计算并推流特定事件的全产业链穿透推演报告；
  - `POST /api/verify`: 接收官方证据文件路径，现场执行验签并解除熔断；
- **交互拓扑大屏**：`reports/event_radar_dashboard.html` 原生支持产业链涟漪效应控制台，动态调整断供天数与冲击强度，即时渲染上下游损益矩阵。

### 7. 金融工具中继层 6 大高内聚子目录分包架构 (`finance_tools/`)
为了解决工具层单目录扁平膨胀、查找费劲的问题，`finance_tools/` 全面解耦重构为 6 大专业业务领域子包，并建立 100% 向下兼容门面：
1. **`finance_tools.screening`**：全市场选股与价格时机引擎（SEPA 8 大趋势硬指标、VCP 4T 波动收缩、万家资产池构建与候选优选排序）；
2. **`finance_tools.forensics_and_valuation`**：财务法证审计与多情景估值模型（法证手术刀排查受限现金/存货DIO/应收周转、三表平账、DCF估值、单位经济学与护城河）；
3. **`finance_tools.risk_and_derivatives`**：风险管理与衍生品定价引擎（美式期权二叉树、期权因果分析、投资组合风险预算、信用违约与极端黑天鹅压力测试）；
4. **`finance_tools.macro_and_ripple`**：宏观冲击与产业链涟漪分析器（宏观传导、SOTP 跨业务分部因果穿透、多标的供应链上下游涟漪效应矩阵与制度风险评级）；
5. **`finance_tools.events_and_verification`**：突发事件雷达与鉴真监控流水线（0-Token 极速初筛、SHA-256 密码学法定信源防伪鉴真、AI 浏览器定向核验助手与告警调度器）；
6. **`finance_tools.governance_and_pipeline`**：数据底账、时效门禁与基础设施管道（数据完备度追踪、行情交易时钟时效门禁、指标管道与不可篡改预测账本）。
- **100% 向下兼容门面保证**：根目录下 42 个历史模块保留完整兼容门面（Facade/Relay），既有脚本与测试用例 `from finance_tools.xxx import yyy` 零破坏直接可用。

---

## 三、 核心数学模型与金融计算公式全集 (Mathematical Formulation & Quant Engines)

本技能的全部投研判断、买卖时机与风控边界均建立在纯本地硬核数学推导之上，**严禁大模型主观臆造数字**。Agent 在生成研报、推演买点与撰写买方投研日记时，必须严格引用并遵循以下数学模型：

### 1. 通用商业物理动力学方程 (Universal Physical Dynamics)
将企业在商业世界中的竞争与股价运行抽象为牛顿物理学运动体系：
- **商业质量 (Business Mass)**：
  $$m = \ln(1 + \text{TotalAssets}) \times (1 + \text{MoatScore})$$
  其中 $\text{MoatScore} \in [0.0, 1.0]$ 为企业护城河评分（品牌、转换成本、网络效应、规模优势）。
- **趋势推进速度与加速度 (Velocity & Acceleration)**：
  $$v_t = \frac{P_t - P_{t-k}}{k}, \quad a_t = \frac{v_t - v_{t-k}}{k} \quad (k \text{ 通常取 20 交易日})$$
- **商业动量定理 (Momentum)**：
  $$p = m \cdot v_t$$
- **动能与势能比率 (Kinetic-to-Potential Energy Ratio & Escape Velocity)**：
  $$E_k = \frac{1}{2} m v_t^2, \quad E_p = m \cdot g_{\text{market}} \cdot \max(0, P_{\text{resistance}} - P_t)$$
  $$\text{Ratio}_{E} = \frac{E_k}{E_p + \epsilon}$$
  - **火箭逃逸速度判定准则**：若 $\text{Ratio}_E \ge 1.0$，判定动能足以克服上方套牢盘引力势能，达成**逃逸速度 (Escape Velocity)**，确认为高胜率主升浪突破；若 $\text{Ratio}_E < 1.0$，判定为虚假诱多冲高回落。
- **阻尼振荡半衰期 (Damped Harmonic Oscillation Half-Life，恐慌平复周期)**：
  $$t_{1/2} = \frac{\ln 2}{\gamma}, \quad \text{其中阻尼系数 } \gamma = \frac{\beta_{\text{down}} \cdot \sigma_{\text{daily}}}{\text{CashBufferRatio}}$$
  度量黑天鹅冲击后，市场恐慌振幅衰减至一半所需的交易日天数。
- **稳态公允价值与零增长停滞底价 (Zero-Growth Stagnation Floor)**：
  $$P_{\text{floor}} = \frac{\text{Normalized Owner Earnings}}{WACC}$$
  作为极端悲观情景下的绝对估值铁底。

### 2. 法务会计 Beneish M-Score 八维 Probit 概率模型
用于在财报出具后或季报分析中，以统计概率严密识别财务粉饰与舞弊造假：
- **八维财务异动指数**：
  1. 应收账款指数：$DSRI = \frac{\text{AR}_t / \text{Sales}_t}{\text{AR}_{t-1} / \text{Sales}_{t-1}}$
  2. 毛利率恶化指数：$GMI = \frac{(\text{Sales}_{t-1} - \text{COGS}_{t-1})/\text{Sales}_{t-1}}{(\text{Sales}_t - \text{COGS}_t)/\text{Sales}_t}$
  3. 资产质量指数：$AQI = \frac{1 - (\text{CA}_t + \text{PPE}_t + \text{Sec}_t)/\text{TA}_t}{1 - (\text{CA}_{t-1} + \text{PPE}_{t-1} + \text{Sec}_{t-1})/\text{TA}_{t-1}}$
  4. 营业收入增长指数：$SGI = \frac{\text{Sales}_t}{\text{Sales}_{t-1}}$
  5. 折旧率变动指数：$DEPI = \frac{\text{Depr}_{t-1} / (\text{PPE}_{t-1} + \text{Depr}_{t-1})}{\text{Depr}_t / (\text{PPE}_t + \text{Depr}_t)}$
  6. 销售与管理费用指数：$SGAI = \frac{\text{SGA}_t / \text{Sales}_t}{\text{SGA}_{t-1} / \text{Sales}_{t-1}}$
  7. 财务杠杆异动指数：$LVGI = \frac{(\text{LTD}_t + \text{CL}_t)/\text{TA}_t}{(\text{LTD}_{t-1} + \text{CL}_{t-1})/\text{TA}_{t-1}}$
  8. 总应计利润与总资产比率：$TATA = \frac{\text{NetIncome}_t - \text{OperatingCashFlow}_t}{\text{TA}_t}$
- **M-Score 综合 Probit 方程**：
  $$M = -4.84 + 0.920 \cdot DSRI + 0.528 \cdot GMI + 0.404 \cdot AQI + 0.892 \cdot SGI + 0.115 \cdot DEPI - 0.172 \cdot SGAI + 4.037 \cdot TATA + 0.0327 \cdot LVGI$$
- **硬核防舞弊门禁**：
  - 若 $M > -1.78$，判定标的存在严重操纵利润嫌疑，**一票否决淘汰出选股池**；
  - 若 $M \le -2.22$，判定为健康高质财务报表。

### 3. KMV-Merton 结构化信用违约与破产风险模型
将公司股权视为以公司底层资产价值为标的的欧式看涨期权（Merton 1974），计算违约距离与黑天鹅破产概率：
- **股权期权定价联立方程**：
  $$E = V_A \mathcal{N}(d_1) - D e^{-r T} \mathcal{N}(d_2)$$
  $$\sigma_E E = \frac{\partial E}{\partial V_A} \sigma_A V_A = \mathcal{N}(d_1) \sigma_A V_A$$
  $$d_1 = \frac{\ln(V_A / D) + (r + 0.5 \sigma_A^2)T}{\sigma_A \sqrt{T}}, \quad d_2 = d_1 - \sigma_A \sqrt{T}$$
  其中 $E$ 为股权总市值，$\sigma_E$ 为股权年化波动率，$V_A$ 为底层资产价值，$\sigma_A$ 为资产波动率。
- **违约触发点 (Default Point, DP)**：
  $$D = \text{ShortTermDebt} + 0.5 \times \text{LongTermDebtNoncurrent}$$
- **违约距离 (Distance-to-Default, DD) 与预期违约率 (Expected Default Frequency, EDF)**：
  $$DD = \frac{\ln(V_A / D) + (\mu_A - 0.5 \sigma_A^2)T}{\sigma_A \sqrt{T}}, \quad EDF = \mathcal{N}(-DD)$$
- **买方风控阈值**：$DD > 3.0$ 为安全稳健标的；$DD < 2.0$ 或 $EDF > 5.0\%$ 强制触发破产黑天鹅告警，禁止持仓。

### 4. Amihud 微观流动性冲击与动态非线性滑点模型
防范微盘股与流动性幻觉（Paper Profit Trap），计算实战交易摩擦：
- **Amihud 非流动性指标 (ILLIQ)**：
  $$\text{ILLIQ} = \frac{1}{N} \sum_{t=1}^N \frac{|R_t|}{\text{Volume}_t \times P_t}$$
- **动态非线性滑点冲击方程 (Square-Root / 0.6 幂律冲击)**：
  $$\text{Slippage}(bps) = \text{BaseSpread} + \lambda \times \left( \frac{\text{OrderValue}}{\text{ADV}_{20}} \right)^{0.6} \times \sigma_{\text{daily}} \times 10000$$
  其中 $\text{BaseSpread}$ 为基础买卖价差（如大盘美股取 2 bps，日股取 5 bps），$\lambda$ 为市场冲击系数，$\text{ADV}_{20}$ 为20日日均成交额。
- **建议最大单笔订单容量上限 (Order Capacity Ceiling)**：
  $$\text{Capacity}_{\max} = \text{ADV}_{20} \times \left( \frac{\text{MaxAllowableSlippage} - \text{BaseSpread}}{\lambda \cdot \sigma_{\text{daily}} \times 10000} \right)^{1 / 0.6}$$
- **流动性陷阱硬门禁**：若 $\text{ADV}_{20} < \$5\text{M}$ 或计算滑点 $> 50\text{ bps}$，标的打上 `ILLIQUID_TRAP`，严禁重仓。

### 5. 期权波动率偏度与异动流模型 (Option Volatility Skew & Order Flow)
利用衍生品聪明资金前瞻性识别正股暴跌或挤压风险：
- **25-Delta 风险反转偏度 (Risk Reversal Skew)**：
  $$Skew_{25D} = IV_{25D, \text{put}} - IV_{25D, \text{call}}$$
  度量下行看跌期权相对于上行看涨期权的溢价程度。$Skew_{25D} > 0.08$ 预警机构资金正在重金采购隔夜跳水对冲。
- **期限结构倒挂比 (Term Structure Ratio)**：
  $$TS = \frac{IV_{\text{front}, ATM}}{IV_{\text{back}, ATM}}$$
  $TS > 1.15$ 预警近期存在极高确定性财报暴雷或监管突发调查。
- **认沽/认购成交量与持仓量比率 (Put-Call Ratio, PCR)**：
  $$PCR_{\text{vol}} = \frac{\text{Volume}_{\text{put}}}{\text{Volume}_{\text{call}}}, \quad PCR_{\text{oi}} = \frac{\text{OpenInterest}_{\text{put}}}{\text{OpenInterest}_{\text{call}}}$$
- **做市商 Gamma 状态判定 (Dealer Gamma Exposure)**：
  $$S > \text{GammaFlip} \implies \text{Long Gamma} \quad (\text{市场波动受做市商反向对冲抑制，处于高胜率震荡区间})$$
  $$S < \text{GammaFlip} \implies \text{Short Gamma} \quad (\text{做市商追涨杀跌，破位时将引发非线性加速踩踏})$$

### 6. 宏观 3-状态高斯隐马尔可夫模型 (Gaussian HMM Regime Switching)
动态识别大盘宏观所处的物理运行阶段并分配总风险预算：
- **状态空间**：
  $$S_t \in \{1: \text{BULL\_MOMENTUM (牛市主升)}, 2: \text{RANGE\_BOUND\_VALUE (震荡低吸)}, 3: \text{CRISIS\_DEFENSE (危机避险)}\}$$
- **状态转移概率矩阵**：
  $$A_{ij} = P(S_t = j \mid S_{t-1} = i), \quad \sum_{j=1}^3 A_{ij} = 1$$
- **观测收益率条件正态发射概率**：
  $$P(R_t \mid S_t = k) = \frac{1}{\sqrt{2\pi \sigma_k^2}} \exp\left( - \frac{(R_t - \mu_k)^2}{2\sigma_k^2} \right)$$
- **自适应仓位预算分配方程**：
  $$\text{GrossExposure} = \sum_{k=1}^3 P(S_t = k \mid \mathcal{F}_t) \times \text{ExposureCap}_k$$
  $$\text{其中 } \text{ExposureCap} = \{ \text{BULL}: 100\%, \text{RANGE}: 60\%, \text{CRISIS}: 0\%\sim 20\% \}$$

### 7. SEPA 趋势模板八大数学不等式与 Minervini VCP 收缩方程
严格执行 0-Token 纯本地筛选的 8 大客观数学硬条件：
- **趋势模板八大数学不等式**：
  1. $P_t > MA50_t > MA150_t > MA200_t$
  2. $MA200_t > MA200_{t-20}$（200日均线斜率维持正值至少 1 个月）
  3. $P_t \ge 1.25 \times \min_{\tau \in [t-250, t]} (P_\tau)$（股价高于52周最低价至少25%）
  4. $P_t \ge 0.75 \times \max_{\tau \in [t-250, t]} (P_\tau)$（距离52周最高价回撤不超过25%）
  5. 相对强弱排名指标：$RS_{\text{score}} \ge 80$（处于全市场前20%强势龙头股序列）
- **Minervini VCP 4T 波动收缩率收敛序列方程**：
  $$\Delta \text{Range}_k = \frac{\text{High}_k - \text{Low}_k}{\text{Pivot}_k}$$
  收敛判别条件：$\Delta \text{Range}_1 \approx 20\% \to \Delta \text{Range}_2 \approx 10\% \to \Delta \text{Range}_3 \approx 5\% \to \Delta \text{Range}_4 \le 2.5\%$
  成交量枯竭判定：$\text{Volume}_{\text{pivot}} \le 0.50 \times \overline{\text{Volume}}_{50}$（浮筹彻底清洗完毕）。

### 8. 多阶段情景 DCF 估值矩阵与 WACC 资本成本方程
- **加权平均资本成本 (WACC)**：
  $$WACC = \frac{E}{V} K_e + \frac{D}{V} K_d (1 - t_c)$$
  $$K_e = R_f + \beta (R_m - R_f) + \text{SizePremium}$$
- **多阶段自由现金流折现方程**：
  $$PV = \sum_{t=1}^{N_1} \frac{\text{FCFF}_t}{(1+WACC)^t} + \sum_{j=N_1+1}^{N_2} \frac{\text{FCFF}_j}{(1+WACC)^j} + \frac{\text{FCFF}_{N_2} (1+g)}{(WACC - g)(1+WACC)^{N_2}}$$
- **三情景差异化估值走廊**：
  - **悲观底价 (Pessimistic Floor)**：$WACC + 200\text{bps}, g = 1.5\%$，叠加净流动资产破产清算折让 (NCAV)；
  - **中性公允 (Neutral Anchor)**：行业基准 WACC 与公允永续增长率 $g$；
  - **乐观靶心 (Optimistic Target)**：护城河扩张溢价与资本回报提升。

### 9. 41 大细分行业因果敏感性弹性系数模型
细分行业营业利润与核心驱动因子的因果传导数学方程：
$$\frac{\Delta \text{EBIT}_i}{\text{EBIT}_i} = \sum_{k=1}^m \epsilon_{i, k} \cdot \frac{\Delta X_k}{X_k}$$
其中 $\epsilon_{i, k}$ 为行业 $i$ 对因子 $k$ 的边际敏感性弹性系数。例如：
- 半导体行业：$\epsilon_{\text{CapEx}} = +1.35, \epsilon_{\text{WaferPrice}} = +0.85$；
- 航空与海运航运：$\epsilon_{\text{BrentCrude}} = -1.20, \epsilon_{\text{Tariff}} = -0.90$；
- 银行与商业金融：$\epsilon_{\text{NIM}} = +2.10, \epsilon_{\text{NonPerformingLoan}} = -1.80$。

---

## 四、 标准操作流程 (SOP 五步闭环)

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as 买方投研员 / Agent
    participant Gateway as Skill 适配网关 / CLI
    participant Core as 金融分析与推演核心
    participant DB as SQLite 账本 / JSON 底账
    participant Screen as 交易室大屏推流服务

    Analyst->>Gateway: 输入标的 (如 NVDA) 或突发事件
    Gateway->>Core: 校验交易时段与行情时效 (verify_quote_freshness)
    Core->>Core: 官方三表平账 (A=L+E) + DCF多情景复算
    alt 涉及突发事件或供应链断供
        Gateway->>Core: 触发 SOTP 分部穿透或产业链涟漪传导
        Core->>Core: 计算 DIO 吸收周期、转嫁冲销与上下游 ΔEBIT
    end
    Core->>DB: 写入预测底账并生成 SHA-256 时间链条
    DB->>Screen: 触发推流更新 (GET /api/stream)
    Screen-->>Analyst: 输出富文本卡片 + 交易室大屏实时推流展示
```

### 步骤一：标的意图解析与行情新鲜度门禁
在调用任何计算前，必须先通过 `MarketQuoteVerifier` 核验数据时间戳：
```python
from financial_reporting.quote_freshness_gateway import verify_quote_freshness

quote_snapshot = verify_quote_freshness(ticker="NVDA", raw_quote_dict=quote_data)
# 强制断言数据处于合法交易时钟区间内，拒绝未来时间戳
```

### 步骤二：选股与买点走廊测算
```python
from finance_tools.sepa_buy_signal_engine import SEPABuySignalEngine

engine = SEPABuySignalEngine()
signal_result = engine.evaluate_ticker("NVDA", daily_bars_df)
# 输出: trend_template_pass (bool), vcp_stage, base_pivot, stop_loss_price
```

### 步骤三：SOTP 与产业链涟漪效应因果穿透
```python
from finance_tools.supply_chain_ripple_analyzer import SupplyChainRippleAnalyzer

analyzer = SupplyChainRippleAnalyzer()
report = analyzer.analyze_event_ripple(
    event_id="EVT_20261016_TSMC_FAB18_DISRUPTION",
    disruption_days=45.0
)
print(f"核心中枢影响: {report.core_hub_impact.ebit_impact_pct:.2f}%")
for down in report.downstream_impacts:
    print(f"下游客户 {down.entity_name}: 损益 {down.ebit_impact_pct:.2f}% (DIO缓冲: {down.dio_days}天)")
```

### 步骤四：突发事件雷达鉴真与防伪收据
```python
from finance_tools.evidence_verification_pipeline import EvidenceVerificationPipeline

pipeline = EvidenceVerificationPipeline(auto_refresh_reports=True)
receipt = pipeline.verify_single_event(
    event_id="EVT_20261016_TSMC_FAB18_DISRUPTION",
    evidence_file="data/evidence/regulatory_filing.pdf",
    note="官方公报确认"
)
```

### 步骤五：启动交易室推流服务与大屏展示
```bash
# 启动本地推流服务 (默认端口 8899)
python scripts/serve_radar_dashboard.py --port 8899 --open-browser
```

---

## 五、 核心工具脚本与命令行调度清单 (CLI Registry)

| 脚本路径 | 业务核心功能 | 常用命令示例 |
| :--- | :--- | :--- |
| `scripts/run_screening_universe_batch.py` | 万家企业初筛批处理与流式调度管道 (断点续传/150分块) | `python scripts/run_screening_universe_batch.py --market ALL` |
| `scripts/export_qualified_screening_candidates.py` | 初筛准入候选池优选排序与导出 CLI (抽干比/收敛度) | `python scripts/export_qualified_screening_candidates.py --top 20` |
| `scripts/collect_screening_universe_data.py` | 全盘万家初筛资产池数据契约与分块索引构建 | `python scripts/collect_screening_universe_data.py --status` |
| `scripts/check_data_readiness.py` | 最新日期核心数据拉取完成度与时效底账巡检 | `python scripts/check_data_readiness.py` |
| `scripts/run_supply_chain_ripple_analysis.py` | 产业链上下游涟漪传导推演 CLI | `python scripts/run_supply_chain_ripple_analysis.py --event EVT_001 --days 45` |
| `scripts/run_sotp_event_penetration.py` | 跨业务分部 (SOTP) 因果穿透 CLI | `python scripts/run_sotp_event_penetration.py --ticker GOOGL --segment cloud --loss 10` |
| `scripts/serve_radar_dashboard.py` | 交易室轻量推流调度与 API 服务 | `python scripts/serve_radar_dashboard.py --port 8899` |
| `scripts/generate_radar_dashboard.py` | 静态交互拓扑大屏生成器 | `python scripts/generate_radar_dashboard.py` |
| `scripts/run_event_radar_daemon.py` | 事件雷达常驻守护监控服务 | `python scripts/run_event_radar_daemon.py --interval 60` |
| `scripts/generate_deep_dossier.py` | 公司深度投研档案自动化生成 | `python scripts/generate_deep_dossier.py --ticker NVDA` |
| `scripts/generate_daily_briefing.py` | 美股/日股大盘每日研报生成 | `python scripts/generate_daily_briefing.py --market US` |
| `scripts/run_10k_universe_pipeline.py` | 全盘资产池批处理调度流水线 | `python scripts/run_10k_universe_pipeline.py --chunk-size 50` |
| `scripts/run_financial_analysis_gateway.py` | 金融计算与细分行业分析统一调度入口 (行业/物理/法务/信用/流动性/期权/宏观/全景) | `python scripts/run_financial_analysis_gateway.py --mode all --ticker NVDA`<br>`python scripts/run_financial_analysis_gateway.py --mode industry --target semiconductors`<br>`python scripts/run_financial_analysis_gateway.py --mode physics --ticker NVDA`<br>`python scripts/run_financial_analysis_gateway.py --mode forensics --ticker NVDA`<br>`python scripts/run_financial_analysis_gateway.py --mode credit --ticker NVDA`<br>`python scripts/run_financial_analysis_gateway.py --mode liquidity --ticker NVDA`<br>`python scripts/run_financial_analysis_gateway.py --mode options --ticker NVDA`<br>`python scripts/run_financial_analysis_gateway.py --mode regime --ticker SPY` |

---

## 六、 四道架构防劣变验收硬门禁 (Non-Regression Gates)

任何代码与文档改修完成后，必须按顺序执行并通过以下四道硬门禁方可交付：

1. **架构完整性全息巡检**：
   ```bash
   python scripts/verify_architecture_integrity.py
   ```
   - 断言底层纯净金融核心零污染、全量模块导入零环路、门面与底账就绪。
2. **便携 CI 套件与全量单测零失败**：
   ```bash
   python scripts/run_ci.py
   python -m unittest discover -s scripts -p "test_*.py"
   ```
   - 所有测试用例 100% PASS，测试数量只增不减。
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

## 七、 版本演进记录 (CHANGELOG)

- **v6.2.0 (2026-11-10)**: **核心数学计算模型与金融物理公式库全面入典**。
  - 将通用商业物理动力学（质量/动量/动能势能比/逃逸速度/阻尼振荡半衰期）、法务会计 Beneish M-Score 八维 Probit 概率方程、KMV-Merton 结构化信用违约方程、Amihud 微观流动性冲击与动态非线性滑点模型、期权偏度与异动流、宏观 3-状态高斯 HMM、SEPA 8 大硬指标、多情景 DCF 及 41 大细分行业因果弹性模型完整植入 Skill 规范。
- **v6.1.0 (2026-11-08)**: **实测风控评估报告归档、失效场景防御体系设计与 finance_tools 6 大高内聚子目录分包重构**。
  - **实测风控报告正式归档**：将 10 年 826 标的跨周期对撞回测评估与五大模型实测报告归档入典 (`docs/36-量化交易系统全息评估与风控架构实测报告.md`)；
  - **失效场景防御与增量中枢设计**：落地 Amihud 流动性门禁、Merton 信用破产距离、Beneish M-Score 法证及央行流动性脉冲等系统化防御体系技术设计 (`docs/37-实测失效场景系统化防御体系与增量信息中枢架构设计文档.md`)；
  - **金融工具模块分包重组**：将 `finance_tools/` 扁平膨胀的 42 个模块彻底按业务职能解耦为 `screening/`、`forensics_and_valuation/`、`risk_and_derivatives/`、`macro_and_ripple/`、`events_and_verification/`、`governance_and_pipeline/` 六大高内聚子包，并在根目录提供 100% 向下兼容门面，既有导入零破坏直接复用。
- **v6.0.0 (2026-11-08)**: **全市场选股、SOTP 因果穿透、多标的产业链涟漪矩阵与交易室推流大屏全面封装合流**。
  - **SEPA 趋势选股与时效门禁合流**：整合全市场资产池（美股10k+/日股4.4k+/核心567）扫描、SEPA 8 大硬指标、VCP 4T 收缩、价格走廊与 `verify_quote_freshness` 硬核门禁；
  - **SOTP 多业务分部因果穿透**：上线综合巨头跨业务分部微观物理损益折算模型，告别单一标签粗糙估值；
  - **多标的产业链上下游涟漪效应传导矩阵**：建立存货周转天数 (DIO) 吸收周期、议价转嫁冲销、下游大客户二级传导与有限责任区间数学边界防御机制；
  - **突发事件雷达与法定防伪鉴真**：上线 0-Token 本地初筛、AI 浏览器定向核验助手、SHA-256 密码学公报防伪鉴真流水线与传闻熔断解除机制；
  - **本地买方交易室推流服务**：基于 Python 标准库构建轻量 HTTP推流服务 (`serve_radar_dashboard.py`)，提供 `/api/stream`、`/api/events`、`/api/supply-chain/ripple` 等 REST 接口与交互拓扑大屏。
- **v5.0.0 (2026-10-15)**: 买方高阶投研认知模型与投研闭环复盘反思体系全面上线。
- **v4.1.0 (2026-10-15)**: 官方三表刚性平账自检与交易时钟区间核验上线。
- **v4.0.0 (2026-10-14)**: 金融分析核心与 Skill 网关彻底物理解耦。
