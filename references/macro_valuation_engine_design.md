# 宏观联动股票估值与敏感性分析引擎设计文档 (Macro-Integrated Valuation Engine Design)

## 一、模块定位与背景

在传统自下而上的微观财务分析中，DCF（自由现金流折现）模型的无风险利率 $R_f$、加权平均资本成本（WACC）以及估值倍数往往依赖静态人工假设。这种做法割裂了宏观经济周期与企业微观基本面的联系。

本模块（`financial_reporting/macro_valuation.py`）旨在将已归档入库的宏观基准快照数据（10Y/2Y 美债收益率、期限利差、美元指数、通胀与政策基准利率）直接拉入股票估值与财务分析引擎，实现：
1. **无风险利率动态锚定**：以经过不可篡改哈希与防前视校验的 10 年期美国国债收益率作为 DCF 贴现率基础输入；
2. **多宏观情景压力测试**：在基准、降息/宽松、高通胀/紧缩三种宏观利率情景下测算公允价值与安全边际买入价；
3. **宏观传导敏感性画像**：结合 `knowledge/macro/transmission_matrix.json` 规则，对标的资产的利率久期、再融资压力、现金缓冲与汇率暴露进行自动化定性定量评估；
4. **与 `GenericFinancialMetrics` 无缝解耦与集成**：提供统一的高内聚计算类，支持批处理与审计回溯。

---

## 二、数学公式与核心算法

### 1. 资本资产定价模型 (CAPM) 与股权成本
$$r_e = R_f + \beta \times \text{ERP}$$
其中：
- $R_f$：取自宏观快照中的 `us_treasury_10y_yield`（如当前基准 $4.42\%$）；
- $\beta$：企业相对于市场的系统性风险敏感系数；
- $\text{ERP}$：股票市场风险溢价（Equity Risk Premium，基准默认 $5.0\%$）。

### 2. 加权平均资本成本 (WACC)
$$\text{WACC} = \frac{E}{V} \times r_e + \frac{D}{V} \times r_d \times (1 - T)$$
其中：
- $E$：普通股总市值（Market Cap）；
- $D$：总有息负债（Total Debt）；
- $V = E + D$：企业总资本；
- $r_d$：税前债务成本，未显式输入时以 $\max(\text{EFFR} + 150\,\text{bps}, R_f + 100\,\text{bps})$ 估算；
- $T$：有效企业所得税率（默认 $21\%$）。

### 3. 多阶段现金流折现 (Multistage DCF)
基于 `finance_tools.valuation.multistage_dcf`：
$$\text{PV} = \sum_{t=1}^{N} \frac{\text{CF}_t}{(1 + \text{WACC})^t} + \frac{\text{CF}_N \times (1 + g)}{( \text{WACC} - g ) \times (1 + \text{WACC})^N}$$
其中：
- $g$：永续增长率（Terminal Growth Rate，必须满足 $g < \text{WACC}$，通常取 $2.0\% \sim 2.5\%$）；
- 股权公允价值 $\text{Equity Value} = \text{PV} - \text{Net Debt}$；
- 每股公允价值 $\text{Fair Value per Share} = \frac{\text{Equity Value}}{\text{Shares Outstanding}}$。

### 4. 宏观三态情景压力测试 (Macro Scenario Pricing)
- **基准情景 (Base Scenario)**：$R_f = R_{f,\text{macro}}$；
- **宽松/降息情景 (Bull / Easing Scenario)**：$R_f = \max(R_{f,\text{macro}} - 75\,\text{bps}, 1.5\%)$，贴现率降低，高成长长久期资产估值弹性释放；
- **紧缩/抗通胀情景 (Bear / Tightening Scenario)**：$R_f = R_{f,\text{macro}} + 75\,\text{bps}$，贴现率上升，倍数压缩，对应极端安全边际买入测试；
- **建议买入区间 (Recommended Buy Zone)**：
  $$\text{Buy Price Range} = [\text{Bear Fair Value} \times 0.85, \; \min(\text{Bear Fair Value}, \text{Base Fair Value} \times 0.75)]$$
  确保即便宏观利率再度大幅攀升，仍具备 $\ge 15\% \sim 25\%$ 的安全垫。

---

## 三、架构与文件依赖

```
data/financial/macro-verification.json (索引)
   └── data/financial/objects/...json (宏观快照)
          │
          ▼
financial_reporting/macro_valuation.py (MacroContext & MacroValuationEngine)
   ├── 调用 finance_tools.valuation.multistage_dcf (成熟金融计算库)
   ├── 消费 knowledge/macro/transmission_matrix.json (传导规则)
   └── 赋能 financial_reporting/generic_metrics.py (综合体检扩展)
```

严格遵循：
- 仅使用项目内本地文件相对路径；
- 执行只读防前视校验；
- 纯 Python 标准库 + 已验证依赖（`finance_tools`），无外部网络请求。
