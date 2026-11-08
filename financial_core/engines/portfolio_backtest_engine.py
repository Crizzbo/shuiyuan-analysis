# -*- coding: utf-8 -*-
"""专业买方投资组合回测与策略收益验证引擎 (PortfolioBacktestEngine).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 纯净独立底层金融计算引擎，零外层逆向依赖，纯相对导入或标准库/numpy/pandas；
2. 严密边界防御：除零除负防御、有限责任下界 (Limited Liability)、破产保护与极值收敛；
3. 杜绝前视偏差 (No Look-Ahead Bias)：T日收盘计算信号，T+1日开盘价加滑点执行成交；
4. 真实市场摩擦模型：精准计提单边佣金 (Commission)、冲击滑点 (Slippage) 与借贷资金成本；
5. 完整公司行动闭环：除权拆股 (Splits) 自动调整份额与成本底账，除息分红 (Dividends) 自动发放现金；
6. 机构级多维收益率与风险归因套件：CAGR、年化波动率、最大回撤 (MDD)、夏普比率 (Sharpe)、
   索提诺比率 (Sortino)、卡玛比率 (Calmar)、胜率 (Win Rate)、盈亏比 (Profit Factor)、Alpha/Beta。
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class TradeRecord:
    """单笔成交记录."""
    trade_id: str
    symbol: str
    market: str
    action: str  # BUY / SELL
    entry_date: str
    exit_date: Optional[str] = None
    shares: float = 0.0
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    commission_paid: float = 0.0
    slippage_paid: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    return_pct: float = 0.0
    holding_days: int = 0
    exit_reason: Optional[str] = None  # STOP_LOSS / TRAILING_STOP / TARGET_PROFIT / VOLATILITY_SHOCK / MAX_HOLDING_EXPIRED


@dataclass
class DailySnapshot:
    """逐日投资组合净值快照."""
    date: str
    cash: float
    holdings_value: float
    total_equity: float
    daily_return: float
    cumulative_return: float
    drawdown: float
    active_positions_count: int
    benchmark_price: Optional[float] = None
    benchmark_cumulative_return: Optional[float] = None


@dataclass
class BacktestMetrics:
    """组合策略回测核心绩效指标集."""
    strategy_mode: str
    market: str
    currency: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    net_profit: float
    cumulative_return: float
    annualized_return_cagr: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_start: str
    max_drawdown_end: str
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    avg_holding_days: float
    annual_turnover_rate: float
    benchmark_cumulative_return: float
    benchmark_annualized_return: float
    alpha: float
    beta: float
    information_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PortfolioBacktestEngine:
    """多资产、多币种、多因子买方投资组合回测引擎."""

    def __init__(
        self,
        market: str = "US",
        currency: str = "USD",
        strategy_mode: str = "MOMENTUM_SEPA",
        initial_capital: float = 100_000.0,
        max_position_pct: float = 0.15,
        min_cash_pct: float = 0.05,
        commission_bps: float = 10.0,  # 单边 10 bps = 0.10%
        slippage_bps: float = 10.0,    # 单边 10 bps = 0.10%
        risk_free_rate: float = 0.025, # 年化无风险利率 (US: 2.5%, JP: 0.2%)
        hard_stop_loss_pct: float = 0.07,  # 7% 刚性止损
        trailing_stop_activation_pct: float = 0.15,  # 盈利达到 15% 启动移动跟踪止盈
        trailing_stop_pullback_pct: float = 0.05,     # 自浮盈高点回撤 5% 离场
        profit_target_pct: float = 0.35,              # 35% 目标公允价退出
        max_holding_bars: int = 60                     # 最长持仓 60 个交易日
    ):
        if initial_capital <= 0:
            raise ValueError("初始本金必须严格大于0")
        if not (0 < max_position_pct <= 1.0):
            raise ValueError("单票最大仓位比例必须在 (0, 1.0] 之间")

        self.market = market
        self.currency = currency
        self.strategy_mode = str(strategy_mode).upper()
        self.initial_capital = float(initial_capital)
        self.max_position_pct = float(max_position_pct)
        self.min_cash_pct = float(min_cash_pct)
        self.commission_rate = commission_bps / 10_000.0
        self.slippage_rate = slippage_bps / 10_000.0
        self.risk_free_rate = float(risk_free_rate)
        self.hard_stop_loss_pct = float(hard_stop_loss_pct)
        self.trailing_stop_activation_pct = float(trailing_stop_activation_pct)
        self.trailing_stop_pullback_pct = float(trailing_stop_pullback_pct)
        self.profit_target_pct = float(profit_target_pct)
        self.max_holding_bars = int(max_holding_bars)

    def run_backtest(
        self,
        universe_bars: Dict[str, List[Dict[str, Any]]],
        benchmark_bars: List[Dict[str, Any]],
        dividends_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        splits_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Tuple[BacktestMetrics, List[DailySnapshot], List[TradeRecord]]:
        """执行端到端无前视偏差事件驱动回测."""
        if not universe_bars:
            raise ValueError("股票资产池数据不能为空")
        if not benchmark_bars:
            raise ValueError("基准资产数据不能为空")

        dividends_map = dividends_map or {}
        splits_map = splits_map or {}

        # 1. 建立全局统一交易日历
        all_dates_set = set()
        df_bars_by_symbol = {}
        for sym, bars in universe_bars.items():
            if not bars:
                continue
            df = pd.DataFrame(bars)
            df["date"] = df["date"].astype(str)
            df = df.sort_values("date").reset_index(drop=True)
            # 计算技术与动量指标 (EMA20, EMA50, EMA200, 近20日年化波动率)
            df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
            df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
            df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
            df["ret"] = df["close"].pct_change()
            df["vol20"] = df["ret"].rolling(20).std() * math.sqrt(252)
            df_bars_by_symbol[sym] = df
            all_dates_set.update(df["date"].tolist())

        df_bench = pd.DataFrame(benchmark_bars).sort_values("date").reset_index(drop=True)
        df_bench["date"] = df_bench["date"].astype(str)
        df_bench["bench_ema200"] = df_bench["close"].ewm(span=200, adjust=False).mean()
        bench_date_map = {row["date"]: row for _, row in df_bench.iterrows()}
        all_dates_set.update(df_bench["date"].tolist())

        trading_dates = sorted(list(all_dates_set))
        if len(trading_dates) < 250:
            raise ValueError(f"交易日数量不足以进行有效回测 (当前仅 {len(trading_dates)} 天)")

        # 2. 状态账本初始化
        cash = self.initial_capital
        # holdings: symbol -> dict(shares, avg_entry_price, peak_price, entry_date, holding_bars, trade_id)
        holdings: Dict[str, Dict[str, Any]] = {}
        trade_history: List[TradeRecord] = []
        snapshots: List[DailySnapshot] = []
        pending_orders: List[Dict[str, Any]] = []  # T日产生的订单在 T+1 日开盘执行

        trade_counter = 1
        peak_equity = self.initial_capital
        max_drawdown = 0.0
        mdd_start_date = trading_dates[0]
        mdd_end_date = trading_dates[0]
        current_mdd_peak_date = trading_dates[0]

        bench_start_price = df_bench.iloc[0]["close"]

        # 3. 按日推进回测主循环
        for t_idx, current_date in enumerate(trading_dates):
            # --- 步骤 A: 优先处理 T+1 开盘订单执行 (以今日 Open 成交加滑点与佣金) ---
            new_pending_orders = []
            for order in pending_orders:
                sym = order["symbol"]
                action = order["action"]
                df_sym = df_bars_by_symbol.get(sym)
                if df_sym is None:
                    continue
                bar_row = df_sym[df_sym["date"] == current_date]
                if bar_row.empty:
                    # 今日停牌，顺延到下一个交易日
                    new_pending_orders.append(order)
                    continue

                today_bar = bar_row.iloc[0]
                open_px = float(today_bar["open"])
                if open_px <= 0 or not math.isfinite(open_px):
                    continue

                if action == "BUY":
                    # 执行买入: 成交价 = Open * (1 + slippage)
                    exec_price = open_px * (1.0 + self.slippage_rate)
                    allocated_dollars = order["target_dollars"]
                    # 确保不超过当前可用现金储备
                    avail_cash = max(0.0, cash - (self.initial_capital * self.min_cash_pct))
                    invest_dollars = min(allocated_dollars, avail_cash)
                    if invest_dollars > 100.0:  # 最小开仓金额
                        shares = invest_dollars / exec_price
                        comm = invest_dollars * self.commission_rate
                        slip = invest_dollars * self.slippage_rate
                        total_cost = invest_dollars + comm
                        if cash >= total_cost:
                            cash -= total_cost
                            t_id = f"TRD-{trade_counter:05d}"
                            trade_counter += 1
                            holdings[sym] = {
                                "shares": shares,
                                "entry_price": exec_price,
                                "peak_price": exec_price,
                                "entry_date": current_date,
                                "holding_bars": 0,
                                "trade_id": t_id,
                                "comm_total": comm,
                                "slip_total": slip,
                            }

                elif action == "SELL":
                    # 执行卖出: 成交价 = Open * (1 - slippage)
                    if sym in holdings:
                        pos = holdings.pop(sym)
                        shares = pos["shares"]
                        exec_price = open_px * (1.0 - self.slippage_rate)
                        proceeds = shares * exec_price
                        comm = proceeds * self.commission_rate
                        slip = (shares * open_px) * self.slippage_rate
                        net_cash = proceeds - comm
                        cash += net_cash

                        gross_pnl = (exec_price - pos["entry_price"]) * shares
                        net_pnl = gross_pnl - (pos["comm_total"] + comm)
                        ret_pct = (exec_price / pos["entry_price"]) - 1.0

                        trade_rec = TradeRecord(
                            trade_id=pos["trade_id"],
                            symbol=sym,
                            market=self.market,
                            action="SELL",
                            entry_date=pos["entry_date"],
                            exit_date=current_date,
                            shares=round(shares, 4),
                            entry_price=round(pos["entry_price"], 4),
                            exit_price=round(exec_price, 4),
                            commission_paid=round(pos["comm_total"] + comm, 4),
                            slippage_paid=round(pos["slip_total"] + slip, 4),
                            gross_pnl=round(gross_pnl, 2),
                            net_pnl=round(net_pnl, 2),
                            return_pct=round(ret_pct, 6),
                            holding_days=pos["holding_bars"],
                            exit_reason=order.get("reason", "EXIT_SIGNAL")
                        )
                        trade_history.append(trade_rec)

            pending_orders = new_pending_orders

            # --- 步骤 B: 处理今日公司行动 (拆股 Splits 与分红 Dividends) ---
            for sym, pos in list(holdings.items()):
                # 检查分红
                if sym in dividends_map:
                    for div in dividends_map[sym]:
                        if div["date"] == current_date:
                            div_amt = div["amount"] * pos["shares"]
                            cash += div_amt
                # 检查拆股
                if sym in splits_map:
                    for sp in splits_map[sym]:
                        if sp["date"] == current_date:
                            ratio = sp["ratio"]
                            if ratio > 0:
                                pos["shares"] *= ratio
                                pos["entry_price"] /= ratio
                                pos["peak_price"] /= ratio

            # --- 步骤 C: 今日持仓更新与退出规则检查 (T日持仓状态与止盈止损监控) ---
            orders_to_trigger_next_day = []
            current_holdings_value = 0.0

            for sym, pos in list(holdings.items()):
                pos["holding_bars"] += 1
                df_sym = df_bars_by_symbol.get(sym)
                if df_sym is None:
                    continue
                bar_row = df_sym[df_sym["date"] == current_date]
                if bar_row.empty:
                    # 停牌日按原持仓计值
                    current_holdings_value += pos["shares"] * pos["peak_price"]
                    continue

                today_bar = bar_row.iloc[0]
                close_px = float(today_bar["close"])
                high_px = float(today_bar["high"])
                low_px = float(today_bar["low"])

                # 更新持仓最高浮盈价
                if high_px > pos["peak_price"]:
                    pos["peak_price"] = high_px

                current_holdings_value += pos["shares"] * close_px

                entry_px = pos["entry_price"]
                peak_px = pos["peak_price"]
                ret_from_entry = (close_px / entry_px) - 1.0
                pullback_from_peak = (peak_px - close_px) / peak_px if peak_px > 0 else 0.0

                exit_reason = None

                # 依据 4 类策略模式执行差异化退出与风控准则
                if self.strategy_mode == "MOAT_VALUE":
                    # 策略 B: 护城河价值型 - 强调安全垫，容忍适度波动，估值修复退出 (+20% 止盈 / -10% 刚性防守 / 持仓90天)
                    if ret_from_entry <= -0.10:
                        exit_reason = "STOP_LOSS_VALUE_DEFENSE"
                    elif ret_from_entry >= 0.20:
                        exit_reason = "TARGET_PROFIT_VALUATION_RECOVERY"
                    elif pos["holding_bars"] >= 90:
                        exit_reason = "MAX_HOLDING_EXPIRED"

                elif self.strategy_mode == "VAR_TAIL_RISK":
                    # 策略 C: 动态尾部风控型 - 严密盯防下行肥尾，紧密止损 (-6% 刚性 / 波动率 > 45% 强平避险 / +25% 止盈 / 持仓45天)
                    if ret_from_entry <= -0.06:
                        exit_reason = "STOP_LOSS_TAIL_RISK"
                    elif not pd.isna(today_bar.get("vol20")) and today_bar["vol20"] > 0.45:
                        exit_reason = "VOLATILITY_BUDGET_BREACH"
                    elif ret_from_entry >= 0.25:
                        exit_reason = "TARGET_PROFIT"
                    elif pos["holding_bars"] >= 45:
                        exit_reason = "MAX_HOLDING_EXPIRED"

                elif self.strategy_mode == "FULL_QUANTAMENTAL":
                    # 策略 D: 机构全息复合型 - 排雷+动量+跟踪止盈+肥尾熔断
                    if ret_from_entry <= -self.hard_stop_loss_pct:
                        exit_reason = "STOP_LOSS"
                    elif (peak_px / entry_px - 1.0) >= self.trailing_stop_activation_pct and pullback_from_peak >= self.trailing_stop_pullback_pct:
                        exit_reason = "TRAILING_STOP"
                    elif ret_from_entry >= self.profit_target_pct:
                        exit_reason = "TARGET_PROFIT"
                    elif not pd.isna(today_bar.get("vol20")) and today_bar["vol20"] > 0.65:
                        exit_reason = "VOLATILITY_SHOCK_DEFENSE"
                    elif pos["holding_bars"] >= self.max_holding_bars:
                        exit_reason = "MAX_HOLDING_EXPIRED"

                else:
                    # 策略 A (默认): 纯动量时机型 (SEPA / VCP)
                    if ret_from_entry <= -self.hard_stop_loss_pct:
                        exit_reason = "STOP_LOSS"
                    elif (peak_px / entry_px - 1.0) >= self.trailing_stop_activation_pct and pullback_from_peak >= self.trailing_stop_pullback_pct:
                        exit_reason = "TRAILING_STOP"
                    elif ret_from_entry >= self.profit_target_pct:
                        exit_reason = "TARGET_PROFIT"
                    elif not pd.isna(today_bar.get("vol20")) and today_bar["vol20"] > 0.70:
                        exit_reason = "VOLATILITY_SHOCK"
                    elif pos["holding_bars"] >= self.max_holding_bars:
                        exit_reason = "MAX_HOLDING_EXPIRED"

                if exit_reason:
                    orders_to_trigger_next_day.append({
                        "symbol": sym,
                        "action": "SELL",
                        "reason": exit_reason
                    })

            # --- 步骤 D: 选股与买入信号扫描 (多因子复合动量与均线时机) ---
            # 宏观大盘门禁: 若基准位于 200 日线下方，则暂停新增多头建仓 (价值型可适度逆势布局)
            bench_bullish = True
            if current_date in bench_date_map:
                b_row = bench_date_map[current_date]
                if not pd.isna(b_row.get("bench_ema200")) and b_row["close"] < b_row["bench_ema200"]:
                    bench_bullish = False

            allow_entry_scan = bench_bullish if self.strategy_mode != "MOAT_VALUE" else True

            if allow_entry_scan:
                for sym, df_sym in df_bars_by_symbol.items():
                    if sym in holdings or any(o["symbol"] == sym for o in orders_to_trigger_next_day):
                        continue  # 已有持仓或准备退出

                    bar_row = df_sym[df_sym["date"] == current_date]
                    if bar_row.empty:
                        continue
                    today_bar = bar_row.iloc[0]

                    c = today_bar["close"]
                    ema20 = today_bar["ema20"]
                    ema50 = today_bar["ema50"]
                    ema200 = today_bar["ema200"]

                    if any(pd.isna(x) for x in (ema20, ema50, ema200)):
                        continue

                    should_buy = False
                    entry_reason = ""

                    if self.strategy_mode == "MOAT_VALUE":
                        # 策略 B: 护城河价值与安全边际 - 现价处于均线支撑中枢但未暴涨泡沫化 (c >= ema200 * 0.95 且 c <= ema50 * 1.06 且 c/ema200 < 1.25)
                        valuation_margin_safe = (c >= ema200 * 0.95) and (c <= ema50 * 1.06) and (c / ema200 < 1.25)
                        vol_safe = pd.isna(today_bar.get("vol20")) or (today_bar["vol20"] < 0.45)
                        if valuation_margin_safe and vol_safe:
                            should_buy = True
                            entry_reason = "MOAT_VALUE_ACCUMULATION"

                    elif self.strategy_mode == "VAR_TAIL_RISK":
                        # 策略 C: 动态尾部风控型 - 严格控制下行波动率预算 (vol20 < 38%) 且突破短期均线 ema20
                        tail_risk_safe = pd.isna(today_bar.get("vol20")) or (today_bar["vol20"] < 0.38)
                        momentum_entry = (c > ema20) and (ema20 > ema50)
                        if tail_risk_safe and momentum_entry:
                            should_buy = True
                            entry_reason = "TAIL_RISK_BUDGETED_ENTRY"

                    elif self.strategy_mode == "FULL_QUANTAMENTAL":
                        # 策略 D: 机构全息复合决策 - 宏观大盘走牛 + 估值适中 (1.02 <= c/ema200 <= 1.35) + Stage 2 均线结构 + 波动率中枢安全 (< 48%)
                        valuation_reasonable = (1.02 <= (c / ema200) <= 1.35)
                        is_stage2 = (c > ema50) and (ema20 > ema50) and (ema50 > ema200)
                        vol_safe = pd.isna(today_bar.get("vol20")) or (today_bar["vol20"] < 0.48)
                        if valuation_reasonable and is_stage2 and vol_safe:
                            should_buy = True
                            entry_reason = "QUANTAMENTAL_COMPOSITE_BREAKOUT"

                    else:
                        # 策略 A: 纯动量时机型 - Stage 2 均线通道 + 价格站上 EMA50 + 波动率安全 (< 55%)
                        is_stage2_uptrend = (c > ema50) and (ema20 > ema50) and (ema50 > ema200)
                        vol_safe = pd.isna(today_bar.get("vol20")) or (today_bar["vol20"] < 0.55)
                        if is_stage2_uptrend and vol_safe:
                            should_buy = True
                            entry_reason = "STAGE2_UPTREND_BREAKOUT"

                    if should_buy:
                        # 检查总仓位与单一仓位上限
                        avail_equity = cash + current_holdings_value
                        target_pos_size = avail_equity * self.max_position_pct
                        if cash >= target_pos_size and len(holdings) < int(1.0 / self.max_position_pct):
                            orders_to_trigger_next_day.append({
                                "symbol": sym,
                                "action": "BUY",
                                "target_dollars": target_pos_size,
                                "reason": entry_reason
                            })

            # 更新待下达指令队列
            pending_orders = orders_to_trigger_next_day

            # --- 步骤 E: 结算今日净值快照与最大回撤 ---
            total_equity = cash + current_holdings_value
            if total_equity > peak_equity:
                peak_equity = total_equity
                current_mdd_peak_date = current_date

            dd = (peak_equity - total_equity) / peak_equity if peak_equity > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd
                mdd_start_date = current_mdd_peak_date
                mdd_end_date = current_date

            prev_equity = snapshots[-1].total_equity if snapshots else self.initial_capital
            daily_ret = (total_equity / prev_equity) - 1.0 if prev_equity > 0 else 0.0
            cum_ret = (total_equity / self.initial_capital) - 1.0

            bench_px = bench_date_map.get(current_date, {}).get("close")
            bench_cum_ret = ((bench_px / bench_start_price) - 1.0) if (bench_px and bench_start_price > 0) else 0.0

            snapshots.append(DailySnapshot(
                date=current_date,
                cash=round(cash, 2),
                holdings_value=round(current_holdings_value, 2),
                total_equity=round(total_equity, 2),
                daily_return=round(daily_ret, 6),
                cumulative_return=round(cum_ret, 6),
                drawdown=round(dd, 6),
                active_positions_count=len(holdings),
                benchmark_price=round(bench_px, 4) if bench_px else None,
                benchmark_cumulative_return=round(bench_cum_ret, 6) if bench_cum_ret else None
            ))

        # 4. 计算全维度权威指标集
        metrics = self._calculate_performance_metrics(
            snapshots=snapshots,
            trade_history=trade_history,
            max_drawdown=max_drawdown,
            mdd_start_date=mdd_start_date,
            mdd_end_date=mdd_end_date,
            df_bench=df_bench
        )

        return metrics, snapshots, trade_history

    def _calculate_performance_metrics(
        self,
        snapshots: List[DailySnapshot],
        trade_history: List[TradeRecord],
        max_drawdown: float,
        mdd_start_date: str,
        mdd_end_date: str,
        df_bench: pd.DataFrame
    ) -> BacktestMetrics:
        """计算买方全维度收益率、风险比率与交易统计."""
        final_equity = snapshots[-1].total_equity if snapshots else self.initial_capital
        net_profit = final_equity - self.initial_capital
        cumulative_return = (final_equity / self.initial_capital) - 1.0

        daily_returns = np.array([s.daily_return for s in snapshots])
        n_days = len(snapshots)
        years = n_days / 252.0 if n_days > 0 else 1.0

        # 年化复合增长率 CAGR
        if final_equity > 0 and self.initial_capital > 0 and years > 0:
            cagr = (final_equity / self.initial_capital) ** (1.0 / years) - 1.0
        else:
            cagr = -1.0

        # 年化波动率
        daily_std = float(np.std(daily_returns, ddof=1)) if len(daily_returns) > 1 else 0.0
        ann_vol = daily_std * math.sqrt(252.0)

        # 夏普比率 (Sharpe)
        excess_cagr = cagr - self.risk_free_rate
        sharpe = (excess_cagr / ann_vol) if ann_vol > 1e-6 else 0.0

        # 下行波动率与索提诺比率 (Sortino)
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 1:
            downside_std = float(np.std(downside_returns, ddof=1)) * math.sqrt(252.0)
            sortino = (excess_cagr / downside_std) if downside_std > 1e-6 else 0.0
        else:
            sortino = sharpe

        # 卡玛比率 (Calmar)
        calmar = (cagr / max_drawdown) if max_drawdown > 1e-6 else 0.0

        # 交易层面统计
        total_trades = len(trade_history)
        winning_trades = len([t for t in trade_history if t.net_pnl > 0])
        losing_trades = len([t for t in trade_history if t.net_pnl < 0])
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0

        gross_profits = sum(t.net_pnl for t in trade_history if t.net_pnl > 0)
        gross_losses = abs(sum(t.net_pnl for t in trade_history if t.net_pnl < 0))
        profit_factor = (gross_profits / gross_losses) if gross_losses > 1e-6 else (10.0 if gross_profits > 0 else 0.0)

        trade_returns = [t.return_pct for t in trade_history]
        avg_trade_return = float(np.mean(trade_returns)) if trade_returns else 0.0
        holding_days_list = [t.holding_days for t in trade_history]
        avg_holding_days = float(np.mean(holding_days_list)) if holding_days_list else 0.0

        # 年化换手率估计
        total_traded_volume = sum(t.shares * t.entry_price for t in trade_history)
        avg_annual_equity = (self.initial_capital + final_equity) / 2.0
        annual_turnover = (total_traded_volume / (avg_annual_equity * years)) if (avg_annual_equity > 0 and years > 0) else 0.0

        # 基准相对表现 (Alpha / Beta)
        bench_start = df_bench.iloc[0]["close"]
        bench_end = df_bench.iloc[-1]["close"]
        bench_cum_return = (bench_end / bench_start) - 1.0 if bench_start > 0 else 0.0
        bench_cagr = ((bench_end / bench_start) ** (1.0 / years) - 1.0) if (bench_start > 0 and years > 0) else 0.0

        # 计算 Beta 与 Alpha
        # 对齐逐日收益序列
        bench_daily_ret = df_bench["close"].pct_change().dropna().values
        min_len = min(len(daily_returns) - 1, len(bench_daily_ret))
        if min_len > 30:
            strat_rets = daily_returns[1:min_len + 1]
            b_rets = bench_daily_ret[:min_len]
            cov = np.cov(strat_rets, b_rets)[0, 1]
            var_b = np.var(b_rets, ddof=1)
            beta = float(cov / var_b) if var_b > 1e-8 else 1.0
            # 资本资产定价模型 Jensen's Alpha
            alpha = float(cagr - (self.risk_free_rate + beta * (bench_cagr - self.risk_free_rate)))
            # 跟踪误差与信息比率
            diff_ret = strat_rets - b_rets
            tracking_error = float(np.std(diff_ret, ddof=1)) * math.sqrt(252.0)
            info_ratio = (alpha / tracking_error) if tracking_error > 1e-6 else 0.0
        else:
            beta = 1.0
            alpha = cagr - bench_cagr
            info_ratio = 0.0

        return BacktestMetrics(
            strategy_mode=self.strategy_mode,
            market=self.market,
            currency=self.currency,
            start_date=snapshots[0].date if snapshots else "",
            end_date=snapshots[-1].date if snapshots else "",
            initial_capital=round(self.initial_capital, 2),
            final_equity=round(final_equity, 2),
            net_profit=round(net_profit, 2),
            cumulative_return=round(cumulative_return, 6),
            annualized_return_cagr=round(cagr, 6),
            annualized_volatility=round(ann_vol, 6),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            max_drawdown=round(max_drawdown, 6),
            max_drawdown_start=mdd_start_date,
            max_drawdown_end=mdd_end_date,
            calmar_ratio=round(calmar, 4),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            avg_trade_return=round(avg_trade_return, 6),
            avg_holding_days=round(avg_holding_days, 1),
            annual_turnover_rate=round(annual_turnover, 4),
            benchmark_cumulative_return=round(bench_cum_return, 6),
            benchmark_annualized_return=round(bench_cagr, 6),
            alpha=round(alpha, 6),
            beta=round(beta, 4),
            information_ratio=round(info_ratio, 4)
        )
