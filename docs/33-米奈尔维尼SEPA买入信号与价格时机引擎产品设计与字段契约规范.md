# 米奈尔维尼 SEPA 买入信号与价格时机引擎技术设计规格书 (SEPA Buy Signal Engine PRD)

> **功能标识**：`TACTICAL_SEPA_SIGNAL_ENGINE`  
> **所属业务分类**：类别 D：交易执行层面（买卖点量价择时与价格走廊解耦）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 核心计算引擎：`financial_core/engines/sepa_buy_signal_engine.py`  
> - 自适应参数源：`financial_core/engines/market_adaptive_params.py`  
> - 多模态呈现层：`financial_reporting/sepa_card_renderer.py`  
> - 自动化测试集：`scripts/test_sepa_buy_signal_engine.py`、`scripts/test_sepa_card_renderer.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方自上而下（Top-Down）投研流水线中，通过宏观流动性筛选与微观公司内在价值 DCF 估值锚定后，必须进入微观战术交易执行阶段。传统量化策略常将基本面估值与买卖点执行混淆，导致买入后长期承受震荡折磨或追高在流动性溢价顶峰。本功能实现马克·米奈尔维尼（Mark Minervini）SEPA（Specific Entry Point Analysis，特定入场点分析）买入信号与价格时机引擎，专注于捕捉高流动性领头羊股票在第二阶段主升浪中的低风险放量突破击球点。

### 2. 核心用途
本功能解决三大核心战术交易问题：
1. **严格的第二阶段趋势过滤**：依据 8 大客观均线与价格动量硬指标，排除处于第一阶段筑底、第三阶段高位派发及第四阶段破位衰退的标的；
2. **波动收缩形态 (VCP) 诊断**：自动识别基底内 2T~4T 的振幅递减序列与终极地量抽干状态，生成 `8W 28/2.5 4T` 标准技术足迹编码；
3. **四维价格走廊全解耦**：将枢轴买点 (Pivot)、刚性硬止损 (-7%)、建议止损 (-5%)、3R 移动保本 (+21%) 与追高超买上限 (+5%) 完全解耦，消除代码中离散散落的魔法值。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `financial_core/engines/market_quote_freshness_verifier.py`：提供经当日新鲜度与交易时段核验的标的最新股价及 50/150/200 日均线数据。
- `financial_core/engines/market_adaptive_params.py`：提供经买方自适应校准的 SEPA 动态参数对象 (`SepaAdaptiveParams`)。

### 2. 后置消费 (Outputs To Downstream)
- `financial_reporting/sepa_card_renderer.py`：消费引擎输出的强类型决策结果，渲染 A4 矢量 HTML 决策卡、Markdown 投委会备忘录及 5-Sheet Excel 工作簿。
- `financial_reporting/daily_briefing_engine.py`：将符合准入触发的优质击球卡片集成至每日美股/日股大盘研报重点标的板块。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  经新鲜度核验的市场行情与均线底账   │
└──────────────────┬───────────────────┘
                   │ (SepaInputFacts 输入契约)
                   ▼
┌──────────────────────────────────────┐
│  SEPA 买入信号与价格时机计算引擎     │
│  (SepaBuySignalEngine)               │
└──────────────────┬───────────────────┘
                   │ (SepaBuySignalResult 强类型输出)
                   ▼
┌──────────────────────────────────────┐
│  多模态呈现与决策卡片渲染中枢        │
│  ├── HTML 矢量卡片 (A4 打印优化)     │
│  ├── 投委会 Markdown 决策卡片        │
│  └── 5-Sheet Excel Sheet 1 操盘区    │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

引擎执行所依赖的全部输入参数定义如下表（对应物理类 `SepaInputFacts`）：

| 参数名称 | 字段标识 (Field Name) | 数据类型 | 计量单位 | 取值范围 | 业务含义与说明 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 证券唯一代码 | `ticker` | `str` | 无量纲 | 大写英数 | 资产池唯一标识符（如 `NVDA`, `7203`）。 |
| 最新核验现价 | `val_current_price` | `float` | 货币单位 | $\ge 0.00$ | 必须通过当日新鲜度门禁校验的真实成交价格。 |
| 50 日移动平均线 | `val_ma_50` | `float` | 货币单位 | $> 0.00$ | 衡量中期波段机构支撑力度的基准线。 |
| 150 日移动平均线 | `val_ma_150` | `float` | 货币单位 | $> 0.00$ | 衡量中长期趋势生命线的均线基准。 |
| 200 日移动平均线 | `val_ma_200` | `float` | 货币单位 | $> 0.00$ | 衡量长周期牛熊分界的均线基准。 |
| 20日前200日线 | `val_ma_200_20d_ago`| `float` | 货币单位 | $> 0.00$ | 测算长期均线向上倾斜角度的基准值。 |
| 52 周最低价 | `val_low_52w` | `float` | 货币单位 | $> 0.00$ | 衡量当前股价较底部实质脱离幅度的基准。 |
| 52 周最高价 | `val_high_52w` | `float` | 货币单位 | $> 0.00$ | 衡量当前股价距离历史高点距离的基准。 |
| 相对强度评分 | `num_rs_rank` | `float` | 百分位 | $[0.0, 100.0]$ | 标的在全市场过去 12 个月表现的相对强度分位数。 |
| 枢轴买点价格 | `val_pivot_price` | `float` | 货币单位 | $> 0.00$ | 收缩形态终点突破阻力位的高点价格。 |
| 历次回撤振幅序列 | `pct_recent_contractions`| `List[float]`| 百分比小数 | 元素 $> 0.0$ | VCP 各轮回撤振幅序列（如 `[28.0, 14.0, 6.0, 2.5]`）。 |
| 基底整理交易日 | `days_base_duration` | `int` | 日 | $\ge 1$ | 构造完整整理形态持续的交易日总数。 |
| 当日实时成交量 | `num_current_volume` | `float` | 股 / 手 | $\ge 0.0$ | 当日截至当前时点的累计成交量。 |
| 50 日均日成交量 | `num_avg_volume_50d` | `float` | 股 / 手 | $> 0.0$ | 衡量放量突破与地量萎缩的基准成交量。 |
| 终极收敛最低单日量 | `num_dryup_volume_min`| `float` | 股 / 手 | $\ge 0.0$ | 收缩期出现的最低单日成交量。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 D-1：VCP 波动收缩与放量突破量价时序结构图
```
  价格 ($)
    ▲
    │         1T (回撤 28%)
    │          ┌──┐
    │         │    │          2T (回撤 14%)
    │        │      │          ┌──┐
    │       │        │        │    │        3T (回撤 6%)
    │      │          └──┐   │      │        ┌──┐      4T (回撤 2.5%)
    ├─────┘              └──┘        └──┐   │    │      ┌──┐    放量突围
    │                                    └──┘     └──┐ │    │  ▲ [Pivot $200.00]
    │                                                 └──┘    └─┼───────►
    │                                                           │
    └───────────────────────────────────────────────────────────┴────────► 时间
  成交量
    ▲
    │   ████                                                地量抽干   放量突破
    │   ████      ██                                         (DryUp)   (> 1.5x)
    │   ████      ██          ███                               │         ████
    │   ████      ██          ███          ██                   │         ████
    │   ████      ██          ███          ██         █         ▼         ████
    └───┴─────────┴───────────┴────────────┴──────────┴─────────┴─────────┴──► 时间
```

#### 图 D-2：四维解耦价格走廊与风控空间比例图
```
  价格 ($)
    ▲
    │                                ┌── 目标靶心 / 3R 移动保本点 ($242.00) [+21%]
    │                                │
    │         ┌── 追高上限 ($210.00) [+5%] ─── 严禁追高拦截线
    │         │
    ├─────────┴── 枢轴买点 ($200.00) ─── 放量击球基准点 (Pivot)
    │         │
    │         ├── 建议止损线 ($190.00) [-5%]
    │         │
    │         └── 刚性硬止损 ($186.00) [-7%] ─── 纪律平仓线
    └───────────────────────────────────────────────────────► 时间
```

#### 图 D-3：买入信号有限状态机 (FSM) 跃迁图
```
                    ┌─────────────────────────┐
                    │      全量标的池输入     │
                    └────────────┬────────────┘
                                 │
                  8 大趋势指标通过? (Stage 2)
                                 ├──────────────────────── 否 ──► 【OUT_OF_TREND】
                                 │                                  (趋势一票否决)
                                 ▼ 是
                    ┌─────────────────────────┐
                    │  第二阶段主升浪准入池   │
                    └────────────┬────────────┘
                                 │
                 突破脱离买点 > +5%?
                                 ├──────────────────────── 是 ──► 【EXTENDED_OVERBOUGHT】
                                 │                                  (超买追高拦截)
                                 ▼ 否
                 现价跌入买点下方但守住止损
                 且成交量萎缩 (Squat)?
                                 ├──────────────────────── 是 ──► 【SQUAT_REVERSAL_WATCH】
                                 │                                  (深蹲洗盘观察)
                                 ▼ 否
                 P >= Pivot 且放量突破
                 且 VCP 紧密收敛就绪?
                                 ├──────────────────────── 是 ──► 【PIVOT_TRIGGERED】
                                 │                                  (买点触发准入)
                                 ▼ 否
                                 └─────────────────────────────► 【WATCHLIST_FORMING】
                                                                    (重点自选跟踪)
```

#### 图 D-4：深蹲假摔防割肉保护决策树
```
           【突破后股价跌破买点 (P < Pivot)】
                          │
             当前现价是否高于刚性硬止损线?
             (P >= Pivot * (1 - 7%))
                          ├───────────────── 否 ──► 执行纪律平仓 (触发止损)
                          ▼ 是
             当前成交量是否低于 50 日均量?
             (Volume < AvgVolume50d)
                          ├───────────────── 否 ──► 警惕异常放量出逃 (提前收缩止损)
                          ▼ 是
             锁定进入【深蹲洗盘观察状态 (SQUAT_REVERSAL_WATCH)】
             - 保持既有底仓不进行割肉操作；
             - 观察 1~2 个交易日等待缩量企稳；
             - 若后续放量重新收复 Pivot 买点，维持主升浪判定。
```

---

### 2. 数学公式定义与推导

1. **趋势模板 8 大硬指标全票通过逻辑**：
   - 现价站上长期线：$P > MA_{150}$ 且 $P > MA_{200}$
   - 均线多头排列：$MA_{150} > MA_{200}$
   - 200 日线上升斜率：$MA_{200} > MA_{200, 20d\_ago}$
   - 50 日线上穿中长期线：$MA_{50} > MA_{150}$ 且 $MA_{50} > MA_{200}$
   - 现价处于波段主升：$P > MA_{50}$
   - 较底部脱离充分度：$(P - Low_{52w}) / Low_{52w} \ge 30.0\%$
   - 距离高点回撤幅度：$(High_{52w} - P) / High_{52w} \le 25.0\%$
   - 相对强度分位数：$RS\_Rank \ge 70.0$
2. **四维解耦价格走廊边界公式**：
   - 刚性硬止损价：$P_{stop} = P_{pivot} \times (1 - \text{pct\_hard\_stop})$
   - 建议止损价：$P_{rec\_stop} = P_{pivot} \times (1 - \text{pct\_rec\_stop})$
   - 单股风险单位 ($1R$)：$R = P_{pivot} - P_{stop}$
   - 追高上限拦截价：$P_{ext} = P_{pivot} \times (1 + 0.05)$
   - 3R 目标止盈与移动保本价：$P_{target} = P_{pivot} + 3.0 \times R$
   - 现价溢价率：$\Delta P\% = \frac{P - P_{pivot}}{P_{pivot}} \times 100\%$

---

## 五、 状态机与生命周期流转 (State Machine)

### 1. 离散状态空间枚举对照表

| 状态标识 | 英文枚举标识 (`BuySignalTier`) | 中文状态名称 | 触发条件说明 | 机构操盘指令含义 |
| :--- | :--- | :--- | :--- | :--- |
| `TIER_01` | `OUT_OF_TREND` | 趋势一票否决 | 未满足第二阶段 8 大硬指标中的任意一项。 | 移出交易计划列表，禁止买入。 |
| `TIER_02` | `WATCHLIST_FORMING` | 重点自选跟踪 | 满足第二阶段，但形态收敛或放量未完成。 | 纳入每日观察池，等待形态成熟。 |
| `TIER_03` | `PIVOT_TRIGGERED` | 放量突破买点触发 | 放量突破买点且处于黄金击球区间内。 | 建立试探性底仓，挂好止损单。 |
| `TIER_04` | `EXTENDED_OVERBOUGHT` | 追高超买脱轨拦截 | 突破后脱离买点幅度超过 5.0%。 | 严禁追高开仓，等待回踩或新基底。 |
| `TIER_05` | `SQUAT_REVERSAL_WATCH` | 突破深蹲洗盘观察 | 价格轻微回踩跌破买点但守住止损且缩量。 | 保持底仓不割肉，观察 1~2 天逆转。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

引擎执行完毕后，统一返回确定性的强类型数据对象 (`SepaBuySignalResult`)：

```json
{
  "ticker": "NVDA",
  "val_current_price": 204.64,
  "status_trend_stage": "Stage_2_Markup",
  "status_vcp_contraction": "Tight_Pivot_Ready",
  "status_buy_signal": "Pivot_Triggered",
  "is_trend_template_passed": true,
  "trend_criteria_checks": {
    "1": true, "2": true, "3": true, "4": true,
    "5": true, "6": true, "7": true, "8": true
  },
  "technical_footprint_code": "8W 28/2.5 4T",
  "cnt_contractions": 4,
  "is_volume_dryup_confirmed": true,
  "is_breakout_volume_confirmed": true,
  "is_squat_holding": false,
  "price_boundaries": {
    "val_pivot_price": 200.00,
    "val_stop_loss_price": 186.00,
    "val_recommended_stop_price": 190.00,
    "val_risk_unit_usd": 14.00,
    "val_breakeven_trigger_price": 242.00,
    "val_extended_limit_price": 210.00,
    "val_target_profit_price": 242.00,
    "pct_hard_stop_loss": 7.00,
    "pct_recommended_stop_loss": 5.00,
    "pct_current_to_pivot": 2.32,
    "is_within_buy_range": true
  },
  "directive_action_zh": "【买入触发】放量突破枢轴买点，建立第一笔试探底仓",
  "meta_trend_stage": { "state_name": "第二阶段主升浪" },
  "meta_vcp_status": { "state_name": "紧密收敛准备突破" },
  "meta_buy_signal": { "state_name": "放量突破买点触发" }
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 技术足迹编码 | `technical_footprint_code` | `str` | 紧凑编码 | 表达整理周数、最大与最小振幅及收缩轮次的标准足迹。 |
| 趋势阶段状态 | `status_trend_stage` | `str` | 枚举代号 | 当前股票所处的生命周期阶段。 |
| VCP收敛状态 | `status_vcp_contraction` | `str` | 枚举代号 | 当前整理基底的形态收缩成熟度。 |
| 买入信号决断 | `status_buy_signal` | `str` | 枚举代号 | 终极战术决策分类（准入/超买/深蹲/观察/否决）。 |
| 黄金击球区间 | `is_within_buy_range` | `bool` | 布尔值 | 指示现价是否处于 `[Pivot, Pivot * 1.05]` 击球带内。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **价格与股数非负下界**：输入现价、均线与买点必须大于 0.00，禁止传入负数价格或零价格；若出现非正价格，引擎必须抛出 `ValueError`。
- [ ] **除零安全截断**：计算现价溢价率与回撤幅度时，分母项 `val_pivot_price` 必须经过 `max(0.01, P)` 保护，严禁除以零引发未捕获崩溃。
- [ ] **强类型与字典双模兼容**：卡片渲染器 `SepaCardRenderer` 必须同时支持解析 `SepaBuySignalResult` 强类型对象与经过 JSON 序列化的原生嵌套字典。
- [ ] **时效性与交易时段校验**：引擎入参必须由上游传递经新鲜度核验的时间戳与交易状态，盘前与盘后数据必须显式标注基准时点。
- [ ] **无损数据传递**：四维价格走廊输出字段必须全部以浮点数传递至报告层，禁止因截断舍入导致止损与盈亏比失真。
