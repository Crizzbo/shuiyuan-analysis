# 医疗保险与管理式医疗（managed_care）买方深度投研中枢档案

版本：3.0.0；状态：adapted；生效日期：2026-11-06。
> 本文档为买方知识图谱单一事实来源 (SSOT) 行业深度研究中枢档案。用于买方研究员定性研判、机器量化引擎提取商业参数，并作为大模型买方研报生成的专业投研上下文。

---

## 一、 官方监管情报精准搜索关键字与溯源定位矩阵

本矩阵供 AI 浏览器补数抓取、数据接入解析器以及买方分析师查阅官方原始披露底稿时强制使用，确保数据来源权威且直击要害。

### 1. 美股 SEC EDGAR 官方定期财报与监管报表检索定位项
- **年度报告 Form 10-K / 季度报告 Form 10-Q 核心定位章节**：
  - `Item 1. Business - Healthcare Reform, ACA Medical Loss Ratio Mandates & CMS Rate Regulations` -> 官方监管：美国患者保护与平价医疗法案 (ACA 80%/85% 刚性最低医疗赔付率要求与保费返还 Rebate 规则)、美国医疗保险与医疗补助服务中心 (CMS) 每年公布的 Medicare Advantage 提价基准通知 (CMS Advance Notice & Final Rate Announcement)、联邦医保 RADV (Risk Adjustment Data Validation) 审计追溯追缴规则、联邦贸易委员会 (FTC) 针对三大 PBM 药房福利管理机构垂直垄断的反垄断调查；
  - `Item 7. Management's Discussion and Analysis (MD&A)` -> 重点检索子章节：`Medical Care Ratio (MCR / MLR) & Care Activity Dynamics` (全口径医疗赔付率 MCR 拆解：门诊择期手术利用率 Outpatient Procedure Utilization、高值专科药品支出侵蚀与季节性呼吸道疾病就诊波动)、`Customer / Membership Enrollments by Product Type` (商业自保 ASO 雇主客户、商业风险承保 Commercial Risk、Medicare Advantage 联邦医疗优先计划与 Medicaid 州医疗补助实际在保会员数变动)、`Optum / Evernorth Health Services Revenue & Intersegment Eliminations` (自营医疗诊所、急诊中心、PBM 药事服务分部营收、分部营业利润率及集团内部抵销后真实净贡献)、`Days in Claims Payable (DCP) & Claims Development Bridge` (未决赔款准备金周转天数 DCP 变动与前期准备金计提有利/不利开发偏差 Prior Year Reserve Development)；
  - `Item 8. Financial Statements - Note: Medical Claims Liability and Claims Development Table` -> FASB ASC 944 医疗赔偿负债底表与历年理赔三角形开发矩阵 (Claims Development Table)：已发生但未报告理赔准备金 (IBNR - Incurred But Not Reported)、各事故发生年历次重估变动差异、未决赔款准备金充分性自检；
  - `Item 8. Financial Statements - Note: Revenue Recognition - Premiums, Fees and Risk Adjustment Transfers` -> FASB ASC 606 收入拆解底表：`Premiums earned` (赚取净保费收入) vs `Products and services revenue` (PBM 药房处方药直营与诊所服务收费) vs `Risk adjustment receivables/payables` (CMS 慢性病风险因子调节资金转移款)；
  - `Item 8. Financial Statements - Note: Commitments and Contingencies / Regulatory Inquiries` -> PBM 药品回扣反垄断调查、CMS 星级评级下调诉讼与患者集体诉讼准备金。

### 2. 日股东证 EDINET / TDnet 官方披露检索项
- **日本金融厅 EDINET 有価証券報告書 (Yuho) 与东证 TDnet 決算短信**：
  - 核心标的：M3 (2413.T 医疗平台)、Medipal Holdings (7459.T 医药分销巨擘)、Alfresa Holdings (2784.T)、SUZUKEN (9987.T)；
  - 检索词：`有価証券報告書` -> `主要な経営指標等の推移 (売上収益・営業利益・医薬品等卸売売上)`, `事業の内容 (医療ポータル・治験支援・医薬品流通・調剤薬局事業)`, `薬価基準改定の影響 (薬価引き下げリスク・保険償還価格)`, `棚卸資産及び貸倒引当金 (医薬品在庫日数・医療機関向け債権)`, `セグメント情報 (医療プラットフォーム事業・エビデンスソリューション事業)`.

### 3. 中英日三语买方核心专业词汇对照表
| 中文专业概念 | 英文机构标准术语 (US SEC / Managed Care) | 日文官方标准术语 (JPX / 厚生労働省) | 核心商业含义与关注要点 |
| :--- | :--- | :--- | :--- |
| **全口径医疗赔付率**| Medical Loss Ratio (MLR / MCR in %) | 医療費比率 (MLR・給付費比率) | 报销就医开支占保费收入比重，每上升 100 基点直接吞噬数十亿美元纯利润 |
| **每人每月保费补贴**| Per Member Per Month (PMPM Rate in USD) | 一人当たり月間保険料・給付額 (PMPM) | 衡量单个投保会员每月带来的净保费收入与发生的医疗成本，反映精算定价水准 |
| **理赔准备金周转天数**| Days in Claims Payable (DCP in Days) | 支払備金回転日数 (DCP・保険金準備金日数)| 衡量保司账面未决理赔准备金厚度，DCP 异常大幅缩水通常是人为粉饰压低当季赔付率 |
| **已发生未报案准备金**| Incurred But Not Reported (IBNR Claims) | 未報告発生損害備金 (IBNR・見積もり準備金)| 患者已在医院就诊但账单尚未递送至保司的预估负债，是管理层平滑利润的蓄水池 |
| **风险调整因子** | Risk Adjustment Factor (CMS RAF Score) | リスク調整係数 (RAFスコア・疾病重症度)| 联邦政府衡量投保老人慢性病严重程度的乘数，决定每人每月财政补贴金额高低 |
| **联邦医保星级评级**| CMS Star Ratings (Medicare Advantage) | スター評価 (メディケア品質格付け・星評価)| 满分 5 星，达到 4 星以上可享受联邦额外 5% 的巨额现金奖励返还与保费溢价 |
| **药房福利管理平台**| Pharmacy Benefit Manager (PBM Express) | 薬剤給付管理 (PBM・処方箋価格交渉) | 掌控全美处方药目录准入与药企高额折扣返利，充当药品流通环节的终极收费站 |
| **商业自保经办服务**| Administrative Services Only (ASO) | 事務代行サービス (ASO・自社年金リスク)| 雇主自担员工实际看病报销风险，保司纯粹收取固定管理费，免受赔付率波动冲击 |
| **大病前置审批许可**| Prior Authorization (Cost Control Gate) | 事前承認制度 (事前審査・高額医療抑制)| 医生开具昂贵特药或实施大型手术前必须取得保司特批，是保司卡住理赔的核心阀门 |
| **垂直医疗服务内循环**| Vertically-Integrated Care Delivery (Optum)| 垂直統合型医療サービス (自社クリニック) | 保司将理赔款直接支付给自家控股的诊所和药房，将保险低毛利洗成医疗服务高毛利 |

### 4. 权威数据提供商高频指标与宏观序列代码
- **美国医疗保险与医疗补助服务中心 (CMS) 官方精算与政策发布**：
  - `CMS Medicare Advantage Capitation Rates & Final Notice`：每年公布的下一年度 MA 联邦基准费率通知；
  - `CMS Part C and D Performance Data (Star Ratings)`：每年全美各大保司旗下各险种计划星级评定结果底账。
- **美国医院协会 (AHA) 与大型上市医院集团运营数据**：
  - `KFF Kaiser Family Foundation Medicare Advantage Tracking`：全美老年人口 MA 渗透率与拒赔率统计。
- **彭博终端 (Bloomberg Professional) 核心函数与行情字段**：
  - `HLTH <GO>`：全球健康险与医疗服务全景看板；
  - `UNH US <Equity>`, `ELV US <Equity>`, `CI US <Equity>`, `CVS US <Equity>`, `HUM US <Equity>`, `CNC US <Equity>`：全美管理式医疗旗舰代码；
  - `MEDICAL_CARE_RATIO`：全口径医疗赔付率 (MCR/MLR)；
  - `DAYS_CLAIMS_PAYABLE`：未决赔款准备金天数 (DCP)；
  - `TOTAL_ENROLLMENT_MEMBERS`：在保承保会员总数。

### 5. 财务粉饰与暴雷排查专属防伪检索词
- `Depleting Claims Reserves (Slashing DCP Days) to Artificially Depress Current-Period MLR`（在医疗就诊实际利用率飙升时，蓄意大幅削减未决赔款准备金天数 DCP 以人为压低当期医疗赔付率、虚增净利润）；
- `Delaying Premium Rebate Accruals Under ACA 85% Minimum MLR Requirement`（在承保利润暴利且实际赔付率低于 80% 时，推迟计提依法必须返还给投保人的大额保费退款准备金）；
- `Concealing Chronic Margin Deterioration Caused by CMS Star Rating Downgrades`（在核心 Medicare 计划从 4 星跌至 3.5 星导致数亿美元政府优质奖励池泡汤后，向市场掩盖次年承保利润率的结构性崩塌）；
- `Aggressively Over-diagnosing Members to Inflate CMS Risk Adjustment Payments (Upcoding)`（通过对入保健康老年人过度增加慢性病代码以骗取联邦政府更高的每人每月财政补贴，面临司法部巨额虚假陈述法案欺诈诉讼）。

### 6. AI 浏览器自动化补数与抓取专用 Prompt / Query 模板
- **美股赔付率与准备金定向**：`site:sec.gov/ix?doc=/Archives/edgar/data/{CIK} "{TICKER}" "medical care ratio" "medical loss ratio" "days in claims payable" "Medicare Advantage"`
- **美股理赔负债与PBM定向**：`site:sec.gov/Archives/edgar/data/{CIK} "Note" "medical claims liability" "IBNR" "rebates" "Optum" "Evernorth"`
- **日股有报定向**：`site:disclosure2.edinet-fsa.go.jp "{JPX_CODE}" "有価証券報告書" "主要な経営指標" "売上高" "医薬品卸" "調剤薬局"`

---

## 二、 边界与细分体系

板块：医疗健康 (Health Care)。研究入口：医疗赔付率 (Medical Loss Ratio, MLR)、承保会员规模、每人每月保费补贴 (PMPM)、CMS 联邦星级评分与医疗服务利用率。

强制执行业务资金属性与业务架构严格细分，严禁将自负盈亏的商业承保与政府财政补贴托管混同研判：
1. **一体化垂直整合管理式医疗超级航母 (Integrated Managed Care Conglomerates: UnitedHealth Group 联合健康 - 联合健康保险 + Optum 服务闭环, The Cigna Group 康西哥 - 商业医保 + Evernorth 服务平台)**：集商业健康险、药房福利管理 (PBM)、自营连锁诊所与日间手术中心于一体，具备强大的体内资金利润循环对冲能力；
2. **专注联邦医疗优先计划的政府业务龙头 (Medicare Advantage Pure-Play: Humana 恒美, Centene 希门寿 - 专注 Medicaid 医疗补助)**：高度依赖美国联邦政府医疗保险与医疗救助中心 (CMS) 财政补贴，极易受政策星级评定与老年人就医频次波动冲击；
3. **传统商业雇主蓝十字蓝盾联盟保险旗舰 (Commercial Blue Cross Blue Shield Affiliates: Elevance Health 艾利昂斯健康 / 原 Anthem 安森)**：专注全美大中型跨国企业雇主商业健康险及自保经办服务 (ASO)，现金流极其稳健；
4. **零售药房一体化连锁承保平台 (Retail-Integrated PBM & Payers: CVS Health - Aetna 安泰保险 + Caremark PBM + 线下诊所)**：将处方药履约、健康承保与社区初级诊疗高度绑定的综合体。

---

## 三、 商业模式定位与金融机器全景

### 1. 商业模式定位与合同机制
本行业核心适用模式为：[保险承保](../../business_models/insurance_underwriting.md)。但在现代买方机构视角下，管理式医疗已彻底演进为**“法定医疗赔付率紧箍咒下，通过自营医疗服务 (Optum/Evernorth) 实现体内利润左手倒右手”**的高维商业机器。

### 2. 产业链博弈位置与微观商业机器全景
```
上游企业雇主/联邦政府CMS与参保个人投保人   中游管理式医疗统筹/控费核心枢纽  下游综合医院/药品批发分销商与处方药房
┌───────────────────────────────────────┐        ┌────────────────────────────────────────┐        ┌────────────────────────────────────────┐
│ • 财富500强企业雇主与工会组织         │        │ • 全球管理式医疗与健康险超级航母       │        │ • 综合三甲医院与专科门诊手术中心       │
│ • 联邦医保局 (CMS: Medicare/Medicaid) ├───────►│   (UNH, CI, ELV, CVS, HUM, CNC)        ├───────►│ • 药房连锁 (CVS, Walgreens) 与分销商   │
│ • 商业自费投保会员与老年银发群体     │        │    (联合健康, 康西哥, 艾利昂斯健康)    │        │ • 专科医生集团与社区初级诊疗网络       │
└───────────────────────────────────────┘        └────────────────────────────────────────┘        └────────────────────────────────────────┘
```

#### (1) 联合健康 (UnitedHealth) 破解“85% 法定医疗赔付率 (ACA MLR)”的超级微观机器
- **平价医疗法案 (ACA) 的法定利润锁**：美国法律强制规定，商业医保收取的保费，至少 80%～85% 必须强制用于支付病人的看病与购药报销（即 MLR 必须 $\ge$ 85%），将传统保险承保净利率死死锁在 3%～5% 的超低天花板；
- **Optum 体内内循环解耦**：联合健康打造了庞大的 Optum 帝国（涵盖 Optum Health 旗下的 9 万名受聘专属医生网络与手术中心、OptumRx 全美第一大药事服务、Optum Insight 医疗数据算法）；
- 联合健康保险 (UnitedHealthcare) 支付给医院和药房的“医疗赔付款”，绝大部分直接流向了自家控股的 Optum 诊所和药房；
- 赔付款在集团体内转化为 Optum 高毛利的服务性营业收入，成功绕开 85% 法定限额，形成年入近 4,000 亿美元且 ROE 超 25% 的不可复制内循环印钞机。

#### (2) Medicare Advantage (MA) 政府计划的“星级奖惩与病种风险因子 (RAF)”博弈
- 联邦政府 CMS 每年根据投保老年人的慢性病严重程度评分 (Risk Adjustment Factor, RAF) 发放人头包干费；
- 获得 4 星及以上（满分 5 星）优质评级的计划，可获得联邦政府额外 5% 的巨额现金奖励返还与优质保费补贴；
- 一旦核心计划因理赔延误被 CMS 降级至 3.5 星以下，数亿美元奖励池将被瞬间剥离，导致承保利润遭遇暴击。

#### (3) 艾利昂斯健康 (Elevance Health) 的“蓝十字商业品牌与雇主 ASO 稳健年金”
- 拥有全美 14 个核心大州独家蓝十字与蓝盾 (Blue Cross Blue Shield) 牌照许可；
- 深度绑定全美数万家财富五百强企业雇主，以自保经办模式 (ASO) 为主，企业自负就医风险，保司仅收取固定的管理费，完全免受医疗赔付率波动的风险冲击。

#### (4) 康西哥 (The Cigna Group) 的“Evernorth 药房福利管理与商保协同”
- 依托 Evernorth 旗下的 Express Scripts，控制全美三分之一的处方药理赔流量；
- 在高毛利肿瘤药物、自免特药采购中向药企索取巨额返利，并通过严密的自保雇主服务实现高资本回报率运作。

---

## 四、 宏观银发医疗通胀、财政补贴政策与就医利用率动力学

引用 [共同周期框架](../../framework/cycles.md)，系统性解构全球就医就诊频率脉冲、老龄化银发就医利用率、联邦医保财政预算收缩与医疗保险估值定价。

### 1. 经典管理式医疗承保周期四步更迭
1. **老年人就医手术意愿爆发（医疗利用率激增，利润断崖）**：老年群体集中进行骨科关节置换与心血管门诊手术，行业医疗赔付率 (MLR) 从正常的 82% 意外飙升至 87%～89%，承保利润遭遇暴跌；
2. **联邦政府 CMS 下调次年医保基础补贴率（政策双杀）**：CMS 迫于财政赤字压力压低次年基准支付调价幅度，险企面临成本激增与收入受限的双重夹击，股价重挫至估值大底；
3. **险企次年激进上调保费并削减非核心附加福利**：保险公司在新的投保季全面上调保费 4%～7%、提高自付额门槛、削减额外牙科视力补贴，并收紧大病预审许可 (Prior Authorization)；
4. **医疗报销平稳与高保费收益兑现（利润暴利大年）**：手术需求脉冲式释放完毕，高保费全面到账，MLR 回落至 82% 舒适区，管理式医疗集团承保利润创历史新高。

### 2. 就医频次激增与赔付率击穿负反馈动力学
```
老年病患门诊择期手术爆发 ──► 医疗赔付率 (MLR) 飙升突破 87.5% ──► 传统承保营业利润暴跌 50%+
     ▲                                                                                │
     │                                                                                ▼
保司全面上调次年保费、收紧大病审批 ◄── 削减未决赔款准备金天数 (DCP) 掩盖失血 ◄── 触发联邦医保降星惩罚与审计罚款
```

---

## 五、 买方穿透式财报排雷四道防线与核心量化指标矩阵

共享候选指标：`roe`, `medical_loss_ratio`。定义见 [指标字典](../../metrics/catalog.json)。

### 1. 买方机构四道防线审查清单
1. **第一道防线：穿透全口径医疗赔付率 (MLR / MCR) 的纯正度** -> 审查 MCR 变动中门诊手术和专科药费的真实占比，警惕通过压低未决赔款准备金 (DCP) 蓄意粉饰当季赔付率的造假行为；
2. **第二道防线：穿透未决赔款准备金周转天数 (Days in Claims Payable, DCP)** -> 审查 DCP 是否连续两个季度出现 3 天以上的大幅下挫，断言管理层是否存在推迟计提准备金以美化利润的嫌疑；
3. **第三道防线：穿透 CMS 联邦医保质量星级评定 (Star Ratings) 变动** -> 核查旗下获得 4 星以上优质评价的会员人数占比是否维持在 70% 以上，严防因降级至 3.5 星而丧失数亿美元现金奖励池；
4. **第四道防线：穿透非承保医疗健康服务 (Optum/Evernorth) 利润独立性** -> 剥离集团内部结算交易，审查自营诊所与药房服务面向第三方客户的真实内生净利润增速是否坚挺在 12% 以上。

### 2. 行业专属量化监控指标矩阵
| 监控维度 | 指标名称与代码 | 正常健康区间 | 警示与危险红线 | 领先意义与因果传导 |
|---|---|---|---|---|
| **承保生死** | `managed_care_driver_1`：全口径医疗赔付率 (Medical Loss Ratio, MLR)| 81.5% ～ 84.0% 最佳区间| > 87.5% 严重赔付失血 | 管理式医疗最核心的第一生死指标，MLR 每上升 100 基点直接吞噬数十亿营业利润 |
| **会员底盘** | `managed_care_driver_2`：核心承保有效会员总数及险种结构拆解| 会员总数 YoY +3%～+6%| 核心商业/MA会员持续负流失| 衡量全险种市场份额扩张与黏性的关键基石，会员流失预示规模经济壁垒松动 |
| **提价转嫁** | `managed_care_driver_3`：同险种每人每月可比保费调整 (PMPM Rate Revision)| 调整幅度跑赢医疗通胀 1～2%| 提价幅度落后通胀成本| 检验险企能否顺利将院端医疗成本上涨转嫁给雇主与投保人的终极提价标尺 |
| **体内造血** | Optum / Evernorth 等非承保医疗服务营业利润占比 | 占比 > 45.0% 且稳步提升 | < 20.0% 纯依赖传统承保 | 衡量企业是否具备抗 MLR 周期波动的安全气囊，服务占比越高估值越抗跌 |
| **理赔储备** | 未决赔款准备金周转天数 (Days in Claims Payable, DCP) | 48 天 ～ 54 天 稳健平稳 | < 42 天 准备金严重少计 | 检验财报利润成色是否存在美化嫌疑的试金石，DCP 异常骤降预示未来大额补提 |
| **星级红利** | 联邦医保 4 星及以上优质评级会员覆盖占比 (Star Rating %)| 覆盖率 > 75.0% | 覆盖率跌破 50.0% 爆雷 | 决定保司能否拿到联邦政府额外 5% 巨额现金奖励的关键命门，星级跳水利润必崩 |

---

## 六、 估值锚点、深跌安全边际与买点/卖点触发事件体系

### 1. 法定估值路线与资本约束下股权收益模型
严格基于**资本约束下股权自由现金流折现 (FCFE) 结合不同业务分部市盈率 (P/E)**：
- **一体化超级航母估值锚点**：依托 Optum 医疗服务的高成长与高 ROIC，享有较高的稳健市盈率倍数 (P/E, 17x～22x)；
- **纯政府险 (Medicare/Medicaid) 承保商估值锚点**：受政策调控与赔付率波动剧烈压制，采用折价市盈率倍数 (P/E, 11x～15x)；
- **坚决避免赔付率峰值悲观割肉**：在全行业就医利用率暴增导致季度 MLR 突破 88% 的至暗时刻，市场往往线性外推其将永久亏损，此时逆向审视险企下年度保费重置提价空间，往往具备极佳的周期安全边际。

### 2. 三态情景因果卡片与触发事件
| 情景维度 | 估值锚点与区间 | 核心触发事件 (Trigger Events) | 买方决策与仓位纪律 |
|---|---|---|---|
| **悲观安全底线** | **11x～14x P/E (对应医疗就诊率失控与降星削补贴政策双杀)** | 1. 老年银发门诊手术井喷，全口径医疗赔付率 MCR 飙升突破 89%，承保业务发生严重亏损<br>2. 核心大州 Medicare Advantage 计划遭遇 CMS 降级至 3.5 星，丧失数亿美元现金奖励返还<br>3. 联邦政府宣布对 PBM 处方药返利启动全面反垄断起诉，强制要求剥离一体化医生诊所网络 | **逆向底仓买点**：仅限手握庞大 Optum 医疗服务造血闭环、净资产收益率 ROE 超 20% 的超级航母，左侧重仓定投 |
| **中性公允中枢** | **18x～22x P/E (对应 8%～11% 复合净利润增长与 MLR 82% 舒适区)** | 1. 医疗赔付率平稳运行在 82.0%～83.5% 舒适区间，保费提价顺利消化医疗通胀与就医利用率<br>2. Optum/Evernorth 等高毛利医疗服务业务保持 13%～16% 稳健复合扩张，利润占比超过 50%<br>3. 保持将充沛自由现金流用于持续提高现金股息与注销式股票回购，增厚每股收益 | **基准持有与动态再平衡**：享有抗宏观经济衰退的极佳防守性与类消费品般极高现金确定性 |
| **乐观进攻靶心** | **26x～30x P/E (价值医疗绝对垄断溢价与逆周期抱团狂热)** | 1. 全球宏观衰退引发市场对确定性高现金流行业无脑抱团，推动管理式医疗估值倍数创历史峰值<br>2. 价值医疗 (Value-Based Care) 控费神话彻底兑现，医疗赔付率降至 80.5% 历史极端低位<br>3. 市场陷入对“大型险企已成为国家医疗唯一垄断总管、享有无限提价权”的非理性狂欢，估值倍数严重透支 | **获利了结与减仓兑现**：全市场预期极度打满，随之而来的平价医疗法案超额利润强制退款 (Rebate) 与政策砍价必将引发膝跳式暴跌 |

---

## 七、 催化剂与动态跟踪链条

围绕**赔付率 (MLR)、会员变动、保费费率调整、CMS 政策公告与准备金天数**建立动态跟踪链条：
1. **高频跟踪**：美国门诊手术与住院就医频次高频追踪调研、联邦公报 CMS 最终费率通知 (Final Rate Notice) 公布；
2. **中频跟踪**：季度财报综合医疗赔付率指标 (`managed_care_driver_1`)、有效会员总数增速 (`managed_care_driver_2`)、同险种可比保费费率调价到位率 (`managed_care_driver_3`)、DCP 准备金天数；
3. **失效条件**：若美国联邦立法通过“全民单一支付人制度 (Single-Payer Healthcare / Medicare for All)”彻底废除商业健康险，原有商业管理式医疗体系估值必须坚决彻底毁灭性清零。

---

## 八、 核心代表性上市企业对标矩阵

| 标的代码 | 证券简称 | 细分赛道与核心定位 | 核心网络 / 业务载体 | 真实造血画像 (FCF / ROE) | 买方研判与关键监测点 |
|---|---|---|---|---|---|
| **UNH** | 联合健康 (UnitedHealth)| 全球管理式医疗与健康服务绝对航母| UnitedHealthcare 商业承保, Optum 医疗服务/PBM | ROE 长期保持在 25% 以上；年化经营现金流近 300 亿美元 | Optum 营业利润增长韧性、Medicare Advantage 医疗赔付率 (MLR) |
| **ELV** | 艾利昂斯健康 (Elevance)| 商业雇主与蓝十字蓝盾旗舰平台 | 14州独占蓝十字蓝盾牌照, Carelon 综合医疗服务 | 股息与回购极为充沛；自由现金流抗周期性极强 | 商业雇主会员续约率、Medicaid 资格重新审核对会员基数的影响 |
| **CI** | 康西哥 (The Cigna Group)| 跨国商业医保与 Evernorth 服务航母| Cigna Healthcare, Evernorth (含 Express Scripts PBM) | 资本配置极其积极；激进开展数百亿美元股票回购 | Evernorth 专科特药分成增长、企业端健康福利渗透率与并购 |
| **CVS** | CVS Health | 零售连锁药房与垂直承保综合航母 | 9000+线下 CVS 药房, Aetna 保险, Caremark PBM | 经营现金流强劲；高股息派发 | Aetna 联邦医疗星级降级后的利润修复、零售门店关店降本进度 |
| **HUM** | 恒美 (Humana) | Medicare Advantage 老年政府医保先锋| 专注全美退休老年人群 Medicare Advantage 计划 | 强周期弹性；赔付率飙升时利润遭遇剧烈挤压 | CMS 最终费率通知、老年病患门诊手术就医利用率与提价 |
| **CNC** | 希门寿 (Centene) | 全美最大低收入 Medicaid 医疗救助龙头| Medicaid 政府救助管理式医疗, 医保交换市场 | 规模效应显著；专注于财政补助低收入人群 | 各州 Medicaid 合同重新招标结果、红线资格审核后留存情况 |

---

## 九、 行业适配规则（本地契约与法定买方核心反证逻辑）

适配日期：2026-11-06。定性行业适配完成，历史统计验证未完成；本节覆盖上方通用种子的估值候选。

### 1. 必须先细分
一体化航母/政府医保龙头/雇主商业蓝盾/零售PBM承保；保险承保与医疗实体服务必须严格分部独立。同一行业内不同业务必须分别取证，严禁混用分母、利润口径和估值模型。

### 2. 特有指标
- `managed_care_driver_1`：全口径医疗赔付率：实际已发生医疗支出 / 净赚保费收入 (MLR/MCR)；
- `managed_care_driver_2`：核心承保有效会员数：按商业雇主、Medicare Advantage 与 Medicaid 分类统计；
- `managed_care_driver_3`：同险种可比保费费率调整幅度：剔除病种结构变化后的净费率年化变动。

完整定义见 [指标字典](../../metrics/catalog.json)，单位与数据来源未确定时不可计算。

### 3. 判断与反证
行业改善需同时检查驱动、现金流和资本风险；不能把收入增长或价格上涨直接当成投资结论。
**法定买方核心反证逻辑**：**“单季度保费规模与总营收高增不等于管理式医疗企业具备稳固护城河；若保费增长完全被老年人就医手术利用率失控爆发所反噬、导致全口径医疗赔付率突破 88% 恶性亏损红线，且核心 Medicare 计划遭遇 CMS 降星惩罚与审计追溯扣款，微薄的承保利润将被彻底击穿倒贴，引发净利润断崖暴跌并导致市场对其精算定价能力产生根本性动摇。”**

### 4. 估值适配
资本金约束下 FCFE 与分部 SOTP 估值；未决赔款准备金缺口与长效商誉专项调整。使用前明确财务口径、数据前提、期限与价值桥接；未验证的倍数不能成为行动阈值。

### 5. 深跌适配
比较自身与同子行业历史回撤分位及波动，结合盈利修正、债务与结构性损害。回撤仅是研究入口，具体数值阈值未启用。无有效历史数据时返回证据不足。

### 6. 验证与本地依据
机器配置见 [行业规则](../../taxonomy/industry_rules.json)。依据项目内 [投资原则](../../01-philosophy.md)、[行业研究素材](../../02-industry-framework.md)、[情绪素材](../../03-market-psychology.md)。本节是设计推导，不是原文逐条证实或统计结论。
