# 高级分析形式与增量资产拓展架构设计文档 (Advanced Analytics & Asset Expansion)

## 1. 架构总览与设计目标

为彻底补齐系统在“微观筹码博弈数据缺失”、“估值单一静态数字缺乏敏感度全景”、“多元化持仓底层重叠风险”以及“大宗抗通胀/去美元化宏观底仓空白”的痛点，构建两大核心子系统：
1. **高级投研分析形式引擎 (`financial_reporting/advanced_analytics.py`)**：
   - 二维 DCF 参数敏感度热力图矩阵；
   - 杜邦 3 阶段与 5 阶段全景穿透拆解树与商业模式诊断；
   - 核心价值驱动因子弹性分析（龙卷风图）；
   - 筹码博弈与空头挤压（Short Squeeze）爆发力评估；
   - 催化剂与风险时序甘特调度。
2. **横向增量资产深度研究体系**：
   - **全球核心 ETF 穿透与重叠度引擎 (`financial_reporting/etf_penetration.py`)**；
   - **黄金与宏观贵金属大宗商品投研引擎 (`financial_reporting/commodity_gold_framework.py`)**。

---

## 2. 高级分析形式设计

### 2.1 二维估值参数敏感度热力矩阵 (2D DCF Sensitivity Matrix)
针对传统 DCF“只给一个数字”的虚假精确，围绕基准贴现率 \(WACC\) 与永续增长率 \(g\) 展开 \(5 \times 5\) 空间网格推演：
- **深绿区间（Deep Value，安全边际 \(\ge +40\%\)）**：极端错杀区，强力买入；
- **浅绿区间（Margin of Safety，安全边际 \(+15\% \sim +40\%\)）**：优质买点，建议 \(1/4\) 凯利布局；
- **黄色区间（Fair Center，偏离 \(-10\% \sim +15\%\)）**：公允中枢，持有观望；
- **浅红区间（Stretched，偏离 \(-25\% \sim -10\%\)）**：估值透支，分批止盈；
- **深红区间（Danger，偏离 \(< -25\%\)）**：严重泡沫，严禁下注。

### 2.2 杜邦全景分解分析 (DuPont Analysis Engine)
- **三阶段分解**：
  $$ROE = \text{销售净利率} \times \text{总资产周转率} \times \text{权益乘数}$$
- **五阶段深度分解**：
  $$ROE = \frac{\text{净利润}}{\text{税前利润 EBT}} \times \frac{\text{税前利润 EBT}}{\text{EBIT}} \times \frac{\text{EBIT}}{\text{营业收入}} \times \frac{\text{营业收入}}{\text{总资产}} \times \frac{\text{总资产}}{\text{所有者权益}}$$
- **质量评级与诊断规则**：
  - **A 级（卓越模式）**：净利率 \(\ge 25\%\) 且周转率 \(\ge 0.8\)（双轮驱动）；
  - **B 级（周转驱动）**：周转率 \(\ge 1.5\) 但净利率 \(< 5\%\)（警示运费与成本冲击）；
  - **C 级（高杠杆金融驱动）**：权益乘数 \(\ge 4.0\)（警示再融资断裂与高息挤压风险）。

### 2.3 关键价值驱动因子弹性分析（龙卷风图）
测算营业利润率（Margin）、营收规模（Revenue）、加权资本成本（WACC）、永续增长率（g）在 \(\pm 10\%\) 扰动下的公允价值摆动幅度（Swing），确定未来 12 个月最关键的“第一胜负手”。

### 2.4 筹码博弈与空头挤压（Short Squeeze）评估
结合空头流通盘占比（Short Interest % of Float）、回补天数（Days to Cover, DTC）及年化借券费率（Borrow Fee Rate），计算轧空爆发力指数（0~100 分），为高做空比率标的（如 RXRX）提供对手盘踩踏的赔率量化依据。

---

## 3. 横向增量资产模型设计

### 3.1 全球核心 ETF 穿透与重叠度模型 (`schemas/etf_dossier.schema.json`)
覆盖宽基（SPY, QQQ）、半导体（SMH）、科技（XLK）、红利防御（SCHD）与长久期美债（TLT）：
- **权重重叠度计算（Weighted Overlap）**：
  $$\text{Overlap}(A, B) = \sum_{i \in A \cap B} \min(w_{i, A}, w_{i, B})$$
- **Jaccard 标的重合度**：\(\text{Jaccard} = \frac{|A \cap B|}{|A \cup B|}\)；
- **集中度指数**：前十大集中度 CR10 与赫芬达尔指数 HHI；
- **费率复利摩擦损耗测算**：模拟 1 年 / 3 年 / 5 年在复利环境下的费率损耗。

### 3.2 黄金与宏观商品框架 (`schemas/commodity_gold.schema.json`)
- **10Y TIPS 真实利率新常态模型**：
  $$\text{Gold Fair Value} = \text{TIPS Anchor} + \text{Central Bank Structural Premium}$$
- **央行战略储备增持雷达**：追踪全球主权央行年净购金（当前超 1,000 吨/年）对金价形成的刚性安全垫；
- **上海金 (SGE) 对 COMEX 期货实物溢价**：监测亚洲实物交割需求；
- **特级金矿股 (NEM, GOLD, AEM) 营运杠杆**：
  $$\text{Operating Leverage} = \frac{\Delta \text{Cash Margin \%}}{\Delta \text{Spot Gold \%}}$$
  结合综合维持成本（AISC）测算金价上涨时金矿股自由现金流与 EPS 的乘数放大倍数。

---

## 4. 契约校验与回归测试
- `scripts/test_advanced_analytics.py`：测试杜邦、2D 敏感度、龙卷风图、空头挤压，断言全部通过；
- `scripts/test_etf_and_commodity.py`：测试 ETF 重叠度、ETF Schema 验证、黄金公允价 Schema 验证与金矿股营运杠杆，断言全部通过。
