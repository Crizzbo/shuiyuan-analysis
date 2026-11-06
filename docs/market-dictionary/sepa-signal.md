# sepa_signal：米奈尔维尼 SEPA 买方时机与风控边界数据字典

> **版本**：1.1.0 (敏捷工程 Living Architecture 物理对齐版)  
> **更新日期**：2026-11-03  
> **物理代码契约**：`financial_core/engines/sepa_buy_signal_engine.py`  
> **Schema 契约**：`schemas/deep_dossier.schema.json`（属性 `sepa_result`）、`schemas/daily_briefing.schema.json`（属性 `sepa_signal`）  
> **业务粒度**：单只上市标的（美股/日股）的特定买入点分析、VCP 形态收缩足迹与价格风控边界。

---

## 1. 核心状态与技术足迹字段 (`SepaBuySignalResult`)

物理数据结构映射：`financial_core.engines.sepa_buy_signal_engine.SepaBuySignalResult`

| 物理字段名 | 中文语义名称 | 数据类型 | 约束条件 / 物理枚举值 | 业务含义与买方操盘动作 |
| :--- | :--- | :--- | :--- | :--- |
| `ticker` | 证券代码 | `string` | 纯大写英数 | 资产池唯一股票代码（如 `NVDA`, `AAPL`, `7203`） |
| `val_current_price` | 最新核验现价 | `float` | $\ge 0.00$ | 经时效门禁核验的当前交易价格（美分/日元级） |
| `status_trend_stage` | 生命周期阶段 | `enum` | 4 态枚举：<br>• `Stage_1_Consolidation`<br>• `Stage_2_Markup`<br>• `Stage_3_Distribution`<br>• `Stage_4_Capitulation` | 标的生命周期状态：<br>• `Stage_1_Consolidation`（第一阶段筑底横盘，观望）<br>• `Stage_2_Markup`（第二阶段主升突围，唯一准入做多）<br>• `Stage_3_Distribution`（第三阶段高位派发，分批止盈）<br>• `Stage_4_Capitulation`（第四阶段衰退投降，绝对禁买） |
| `status_vcp_contraction`| VCP收缩评级 | `enum` | 4 态枚举：<br>• `No_Contraction`<br>• `Loose_Shaping`<br>• `Contracting`<br>• `Tight_Pivot_Ready` | 波动收缩状态：<br>• `No_Contraction`（未形成收缩，宽幅发散）<br>• `Loose_Shaping`（初步收敛中，回撤偏大）<br>• `Contracting`（标准收敛推进中，振幅递减）<br>• `Tight_Pivot_Ready`（极度紧密收敛，地量抽干准备突破） |
| `status_buy_signal` | 买入信号判定层级 | `enum` | 5 态枚举：<br>• `Out_Of_Trend`<br>• `Watchlist_Forming`<br>• `Pivot_Triggered`<br>• `Extended_Overbought`<br>• `Squat_Reversal_Watch` | 综合买方时机决断：<br>• `Out_Of_Trend`（趋势否决：严禁买入）<br>• `Watchlist_Forming`（重点自选：耐心等待收敛）<br>• `Pivot_Triggered`（放量突破：果断击球开火）<br>• `Extended_Overbought`（超买脱轨：脱离买点超 5%，严禁追高）<br>• `Squat_Reversal_Watch`（深蹲洗盘：守住底线坚决不割肉） |
| `is_trend_template_passed` | 趋势模板全票通过 | `boolean`| `True` / `False` | 8 大趋势模板硬指标是否全部通过（必须全为 True 才进入第二阶段主升浪） |
| `technical_footprint_code`| 经典技术足迹代码 | `string` | 米奈尔维尼标准格式 | 格式如 `8W 28/2.5 4T`（8周基底，最大回撤28%，最终紧密收缩2.5%，经历4次收缩） |
| `cnt_contractions` | 波动收缩总次数 | `integer`| $\ge 0$ | 基底整理期间的波段收缩次数（典型超级大牛股经历 2~4 次收缩） |
| `is_volume_dryup_confirmed` | 地量抽干确认标志 | `boolean`| `True` / `False` | 收敛期间最低单日成交量是否降至 50 日均量的 50% 以下（确认浮动筹码彻底抽干） |
| `is_breakout_volume_confirmed` | 突破放量确认标志 | `boolean`| `True` / `False` | 突破枢轴买点时成交量是否达到 50 日均量的 1.5 倍以上（主力买盘进场） |
| `is_squat_holding` | 深蹲震仓保护状态 | `boolean`| `True` / `False` | 突破后若遇扰动缩量回踩买点下方，但在止损线和均线上方，置位保护防割肉 |
| `directive_action_zh` | 买方操盘行动指令 | `string` | 纯自然中文 | 机构级明确操盘动作（如“果断开火”、“严禁追高”、“给予1~2天观察期”） |

---

## 2. 价格防线走廊字段 (`SepaPriceBoundaries`)

物理数据结构映射：`financial_core.engines.sepa_buy_signal_engine.SepaPriceBoundaries`

| 物理字段名 | 中文语义名称 | 数据类型 | 精度/格式 | 核心计算公式与风控底线 |
| :--- | :--- | :--- | :---: | :--- |
| `val_pivot_price` | 枢轴买点价格基准 | `float` | 0.01 | 紧密收敛形态最高阻力线，放量突破开火基准价 |
| `val_stop_loss_price` | 刚性硬止损价 | `float` | 0.01 | $P_{\text{pivot}} \times (1 - \text{pct\_hard\_stop})$，盘中跌破无条件砍仓，不可逾越的绝对红线 |
| `val_recommended_stop_price` | 建议精准止损价 | `float` | 0.01 | $P_{\text{pivot}} \times (1 - \text{pct\_rec\_stop})$，常态波段精准止损线（默认 -5.0%） |
| `val_risk_unit_usd` | 单股初始风险敞口 $1R$ | `float` | 0.01 | $P_{\text{pivot}} - P_{\text{stop}}$，衡量后续盈利倍数的单位基准 |
| `val_breakeven_trigger_price` | 移动保本触发价 | `float` | 0.01 | $P_{\text{pivot}} + 3.0 \times R$，浮盈达 3R 时止损无条件提至买入成本价保本 |
| `val_extended_limit_price` | 追高超买脱轨上限 | `float` | 0.01 | $P_{\text{pivot}} \times 1.05$，突破买点上方 +5.0% 极限价，超过此价严禁追高 |
| `val_target_profit_price` | 目标止盈靶心 | `float` | 0.01 | $P_{\text{pivot}} + 3.0 \times R$，基准 3:1 盈亏比兑现位 |
| `pct_hard_stop_loss` | 刚性硬止损百分比 | `float` | 0.01% | 默认 7.00% |
| `pct_recommended_stop_loss` | 推荐止损百分比 | `float` | 0.01% | 默认 5.00% |
| `pct_current_to_pivot` | 现价较买点溢价率 | `float` | 0.01% | $(P_{\text{current}} - P_{\text{pivot}}) / \max(0.01, P_{\text{pivot}}) \times 100\%$ |
| `is_within_buy_range` | 是否处于黄金击球区 | `boolean`| `True` / `False` | 现价是否严格处于 $[P_{\text{pivot}}, P_{\text{extended\_limit}}]$ 闭区间内 |
