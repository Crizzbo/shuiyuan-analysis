# 全球核心指数 ETF 与黄金大宗商品研究体系技术设计规格书 (Multi-Asset ETF & Gold Commodity Specification)

> **功能标识**：`MULTI_ASSET_ETF_GOLD_COMMODITY_SUITE`  
> **所属业务分类**：类别 B：中观行业与多资产大类（ETF 成分穿透重叠度、大宗商品宏观脱钩定价与金矿营运杠杆）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - ETF 穿透引擎：`financial_core/engines/cross_asset_engine.py` (`ETFPenetrationEngine`)  
> - 黄金宏观定价：`financial_core/engines/cross_asset_engine.py` (`GoldCommodityEngine`)  
> - 数据契约规范：`schemas/etf_dossier.schema.json`、`schemas/commodity_gold.schema.json`  
> - 批处理流水线：`scripts/run_multi_asset_research_pipeline.py`  
> - 自动化测试集：`scripts/test_cross_asset_engine.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在跨资产大类资产配置中，买方机构面临两大核心痛点：一是多 ETF 组合配置中普遍存在“表象分散、底层集中”的伪分散陷阱（例如同时配置 SPY 与 QQQ 时，前五大巨头成分权重重合度逼近 50%），在科技股流动性收紧时承受非预期共振回撤；二是传统以实际利率（10Y TIPS）为单因子的黄金定价模型在新常态下出现结构性脱钩，无法解释逆全球化背景下主权央行加速购金对金价的常态化溢价。本功能构建跨资产大类穿透分析与大宗商品重定价体系。

### 2. 核心用途
本功能解决三大跨资产大类投研问题：
1. **ETF 前十大成分股权重重合度穿透**：测算任意 ETF 对之间的最小权重重叠率、赫芬达尔指数 (HHI) 及六维风格因子暴露；
2. **复利费率损耗仿真**：量化主题型高费率 ETF 对比低费率宽基在 1 年、3 年、5 年复利下的隐性资本摩擦金额；
3. **黄金去美元化宏观重定价与金矿营运杠杆**：构建由 10Y TIPS 真实利率锚、主权央行超额购金溢价与上海金 (SGE) 现货溢价构成的定价方程，并测算特级金矿股基于维持成本 (AISC) 的自由现金流放大杠杆。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data/universe/etf_holdings_cache.json`：提供标的 ETF 官方最新公布的全部成分股及权重底账。
- `data/macro/market_rates_snapshot.json`：提供 10Y TIPS 收益率、央行年度净购金吨数及 SGE 溢价数据。

### 2. 后置消费 (Outputs To Downstream)
- `financial_reporting/excel_dossier_builder.py`：消费 ETF 重叠度与金矿营运杠杆，渲染 5-Sheet Excel Sheet 5 多资产对冲模块。
- `reports/ai_dossiers/`：落盘符合 `schemas/etf_dossier.schema.json` 的 JSON 深度档案。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  ETF 官方全量成分持仓与宏观利率底稿  │
└──────────────────┬───────────────────┘
                   │ (强类型输入契约)
                   ▼
┌──────────────────────────────────────┐
│  多资产跨类别量化分析中枢            │
│  ├── ETF 成分权重重叠度与 HHI 集中度  │
│  ├── 六维风格因子暴露 (Growth/Value) │
│  ├── 黄金主权去美元化溢价解耦模型    │
│  └── 金矿 AISC 边际毛利扩张杠杆测算  │
└──────────────────┬───────────────────┘
                   │ (多资产分析契约与评级)
                   ▼
┌──────────────────────────────────────┐
│  4-Sheet 多资产联动工作簿与矢量档案  │
│  (Multi-Asset Workbook / PDF / JSON) │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

ETF 穿透与黄金定价方法核心参数契约定义如下表：

| 方法标识 | 参数名称 | 数据类型 | 计量单位 | 约束边界 | 业务释义 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `calc_overlap` | `dict_holdings_a` | `Dict[str, float]`| 权重小数 | 和为 $1.0$ | ETF A 的成分股票代码与对应资产配置权重字典。 |
| `calc_overlap` | `dict_holdings_b` | `Dict[str, float]`| 权重小数 | 和为 $1.0$ | ETF B 的成分股票代码与对应资产配置权重字典。 |
| `simulate_fee` | `val_principal` | `float` | 货币单位 | $> 0.0$ | 组合初始投资本金规模（默认 100,000 美元）。 |
| `simulate_fee` | `pct_expense_ratio`| `float` | 比率小数 | $[0.0001, 0.03]$ | ETF 基金管理费率与托管综合费率。 |
| `gold_pricing` | `pct_tips_real_yield`| `float` | 比率小数 | 实数 | 美国 10 年期通胀保值国债 (TIPS) 即期收益率。 |
| `gold_pricing` | `val_cb_tonnes` | `float` | 吨 / 年 | $\ge 0.0$ | 全球主权央行过去 12 个月累计净购金总量。 |
| `gold_miner` | `val_spot_gold_price`| `float` | 美元 / 盎司 | $> 0.0$ | 国际现货黄金即期结算价格。 |
| `gold_miner` | `val_aisc_cost` | `float` | 美元 / 盎司 | $> 0.0$ | 金矿企业综合维持采矿成本 (AISC)。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 B-1：ETF 成分持仓穿透与资产配置重叠矩阵图
```
┌────────────────────────────────────────────────────────┐
│                   【标的 ETF 成分权重穿透】            │
│  ETF A: SPY (标普 500) ──> MSFT(7.1%), AAPL(6.8%), NVDA(6.2%)...│
│  ETF B: QQQ (纳斯达克 100) ──> MSFT(8.8%), AAPL(7.9%), NVDA(7.5%)...│
└───────────────────────────┬────────────────────────────┘
                            │ (成分集合交集与极小值求和)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【前十大重合持仓交集与配置冗余】           │
│  • 权重重合度 Overlap = min(w_A, w_B) 之和 = 46.8%     │
│  • Jaccard 相似度 = 交集数量 / 并集数量 = 16.5%         │
│  • 赫芬达尔集中度 HHI_A = 125 (适度分散), HHI_B = 412 (中度集中)│
└────────────────────────────────────────────────────────┘
```

#### 图 B-2：黄金新常态重定价与主权去美元化脱钩模型图
```
  黄金公允价值 ($/oz)
    ▲
    │                                ┌── 新常态金价中枢 ($2,650)
    │                                │   [基础利率锚 + 结构性去美元化常态溢价]
    │                 ┌──────────────┴── 主权央行超额购金溢价 (+15%~30%)
    │  历史纯利率锚 ──┼── 传统 10Y TIPS 负相关定价区间 ($1,950)
    │  (传统负相关)   │
    │                 ▼
    ├─────────────────────────────────────────────────► 实际利率 TIPS (%)
   -1.0%             0.0%             1.0%            2.0%
```

#### 图 B-3：特级金矿股 AISC 营运杠杆与现金流放大阶梯图
```
  单位毛利与现金流 ($/oz)
    ▲
    │                                     ┌── 现货金价暴涨至 $2,600 (涨幅 +30%)
    │                                     │   单位自由现金毛利 = $1,200 (暴涨 +100%)
    │                                     │   【营运杠杆放大乘数: 3.33 倍】
    │                 ┌── 现货金价基准 $2,000
    │                 │   单位现金毛利 = $600
    │  刚性开采成本 ──┼── 综合维持成本 (AISC) 恒定线: $1,400/oz
    │  (AISC 刚性)    │   [采矿、选矿、开支固定]
    ├─────────────────┴───────────────────────────────────► 金价周期阶段
```

---

### 2. 核心数学模型推导

1. **ETF 成分权重重合度模型**：
   $$\text{Overlap}(A, B) = \sum_{i \in \text{Holdings}_A \cap \text{Holdings}_B} \min\left(w_{i, A}, \; w_{i, B}\right)$$
   赫芬达尔-赫希曼集中度指数 (HHI)：
   $$HHI = \sum_{i=1}^{N} (100 \times w_i)^2$$
2. **复利费率损耗绝对值方程**：
   $$\Delta \text{Wealth}(T) = C_0 \left[(1 + r)^T - (1 + r - e)^T\right]$$
   其中 $C_0$ 为初始资金，$r$ 为基准毛年化回报率，$e$ 为 ETF 年度综合费率。
3. **黄金新常态重定价显式脱钩方程**：
   $$P_{\text{gold}} = P_0 \times \exp\Big( -\lambda (y_{\text{tips}} - y_0) \Big) \times \left(1 + \text{Premium}_{\text{cb}}\right) + \text{Basis}_{\text{SGE}}$$
   $$\text{Premium}_{\text{cb}} = \min\left(0.30, \; \max\left(0, \frac{\text{Tonnes} - 500}{100}\right) \times 0.15\right)$$
4. **特级金矿龙头营运杠杆放大乘数**：
   $$\text{Operating Leverage Multiplier} = \frac{\Delta P_{\text{gold}}}{P_{\text{gold}, 0} - AISC}$$

---

## 五、 状态机与配置预警生命周期 (State Registry)

### 1. ETF 配置重合与集中度预警状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定条件 | 投研配置建议 |
| :--- | :--- | :--- | :--- | :--- |
| `ETF_01` | `LOW_OVERLAP_DIVERSE`| 优质低重叠分散 | 权重重合度 $< 25\%$ 且 $HHI < 200$。 | 理想分散配置标的，维持组合。 |
| `ETF_02` | `MODERATE_OVERLAP` | 中度适度重叠 | 权重重合度处于 $[25\%, 50\%)$ 之间。 | 正常行业交叉，监控风格漂移。 |
| `ETF_03` | `HIGH_REDUNDANCY` | 高度冗余伪分散 | 权重重合度 $\ge 50\%$。 | 存在持仓重复，建议剔除冗余。 |
| `ETF_04` | `SINGLE_STOCK_DOM` | 单一巨头过度集中 | 单一成分股权重 $> 20\%$。 | 丧失组合意义，按个股风险穿透。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

跨资产大类分析执行完毕后，统一输出强类型契约字典：

```json
{
  "etf_overlap_analysis": {
    "pair": "SPY_vs_QQQ",
    "pct_weighted_overlap": 0.468,
    "pct_jaccard_similarity": 0.165,
    "status_redundancy": "Moderate_Overlap",
    "top_shared_holdings": [
      {"ticker": "MSFT", "weight_a": 0.071, "weight_b": 0.088, "min_overlap": 0.071},
      {"ticker": "AAPL", "weight_a": 0.068, "weight_b": 0.079, "min_overlap": 0.068},
      {"ticker": "NVDA", "weight_a": 0.062, "weight_b": 0.075, "min_overlap": 0.062}
    ]
  },
  "gold_macro_pricing": {
    "val_fair_value_gold_usd": 2650.0,
    "val_spot_market_price_usd": 2680.0,
    "pct_tips_discount": -0.042,
    "pct_cb_structural_premium": 0.185,
    "val_sge_physical_basis": 28.50,
    "gold_miner_leverage": {
      "ticker": "NEM",
      "val_aisc_usd_oz": 1420.0,
      "num_fcf_leverage_multiplier": 3.12
    }
  }
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 权重重合度 | `pct_weighted_overlap` | `float` | 比率小数 | 组合间共同重叠持仓的加权相似度比率。 |
| 黄金公允定价 | `val_fair_value_gold_usd` | `float` | 美元 / 盎司 | 融合实际利率锚与央行购金溢价的黄金理论价值。 |
| 央行购金常态溢价 | `pct_cb_structural_premium`| `float` | 比率小数 | 主权去美元化储备多元化给金价带来的结构性加价率。|
| 金矿现金流营运杠杆 | `num_fcf_leverage_multiplier`| `float` | 杠杆倍数 | 现货金价每上涨 1% 所带动的企业单位现金毛利增幅。|

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **ETF 权重归一化校验**：任意输入的 ETF 持仓字典权重求和必须满足 $|\sum w_i - 1.0| \le 0.01$，若权重和严重失真必须拒绝计算。
- [ ] **金矿 AISC 刚性成本断言**：金矿企业综合维持成本 AISC 必须严格大于零；若金价跌破 AISC，营运杠杆截断保护，禁止输出除以负毛利的荒谬杠杆倍数。
- [ ] **央行购金溢价封顶上限**：央行溢价模型设定硬上限 $\text{Premium}_{\text{cb}} \le 30\%$，杜绝无边界外推导致黄金估值无限暴涨。
- [ ] **Schema 强校验通过**：产出的全部 JSON 结果文件必须通过 `schemas/etf_dossier.schema.json` 与 `schemas/commodity_gold.schema.json` 结构验证。
