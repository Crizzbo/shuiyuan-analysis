# -*- coding: utf-8 -*-
"""全量美日万家标的金融模型收益全息验证与自适应切换回测引擎 (run_full_universe_data_max_backtest.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 数据源规范：严格读取并落地在 data_max/ 空间中；
2. 时序隔离纪律 (Strict Point-in-Time)：
   - 120 个月度调仓截面，T日收盘提取特征，严禁任何前视未来数据；
   - 订单撮合严格于 T+1 日实际开盘价加滑点执行；
3. 真实交易摩擦成本：
   - 计提 10 bps 单边佣金 + 10 bps 单边滑点 (往返摩擦 40 bps)；
4. 五大买方配置全息对撞：
   - 模型 A (MOMENTUM_SEPA - 纯动量时机)
   - 模型 B (MOAT_VALUE - 护城河价值)
   - 模型 C (VAR_TAIL_RISK - 动态尾部风控)
   - 模型 D (FULL_QUANTAMENTAL - 机构全息复合)
   - 自适应动态切换组合 (ADAPTIVE_REGIME - 买方宏观状态机驱动)
5. 密码学存证：
   - 结果写入 HistoryValidationLedger，SHA-256 签名链自检验签。
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from financial_core.engines.market_regime_switching_engine import (
    MarketRegimeSwitchingEngine,
    MarketRegime,
    MarketRegimeVerdict,
)
from financial_core.engines.dynamic_universe_screener import (
    DynamicUniverseScreener,
    StockScreeningScore,
)
from financial_core.engines.portfolio_backtest_engine import (
    DailySnapshot,
    TradeRecord,
    BacktestMetrics,
)
from scripts.history_validation_ledger import HistoryValidationLedger
from scripts.run_four_models_dynamic_comparison import (
    execute_single_model_backtest,
    calculate_model_metrics,
)

DATA_MAX_DIR = ROOT / "data_max"
if not (DATA_MAX_DIR / "normalized" / "us").exists() or not any((DATA_MAX_DIR / "normalized" / "us").glob("*_bars.json")):
    candidate_alt = Path("C:/Users/zhibo/Desktop/金融测试/data_max")
    if candidate_alt.exists() and (candidate_alt / "normalized" / "us").exists():
        DATA_MAX_DIR = candidate_alt

NORMALIZED_US_DIR = DATA_MAX_DIR / "normalized" / "us"
NORMALIZED_JP_DIR = DATA_MAX_DIR / "normalized" / "jp"
REPORTS_DIR = ROOT / "reports" / "data_max_backtest"

STRATEGY_CONFIGS = {
    "MODEL_A_MOMENTUM": {
        "name_zh": "模型 A: 纯动量时机型 (MOMENTUM_SEPA)",
        "strategy_model": "MOMENTUM_SEPA",
        "description": "追逐相对强弱主升浪与均线发散，严格刚性硬止损，高弹性顺势跟踪",
        "stop_loss_pct": -0.07,
        "trailing_stop_pct": 0.15,
        "take_profit_target": None,
    },
    "MODEL_B_MOAT_VALUE": {
        "name_zh": "模型 B: 护城河价值与安全边际型 (MOAT_VALUE)",
        "strategy_model": "MOAT_VALUE",
        "description": "均线中枢支撑吸筹，低估值折价保护，安全垫防守，目标估值修复退出",
        "stop_loss_pct": -0.10,
        "trailing_stop_pct": 0.20,
        "take_profit_target": 0.25,
    },
    "MODEL_C_VAR_TAIL_RISK": {
        "name_zh": "模型 C: 动态尾部风控型 (VAR_TAIL_RISK)",
        "strategy_model": "VAR_TAIL_RISK",
        "description": "极度厌恶波动率与下行极端肥尾，严控波动率预算，极紧止损闪电防守",
        "stop_loss_pct": -0.05,
        "trailing_stop_pct": 0.10,
        "take_profit_target": 0.15,
    },
    "MODEL_D_QUANTAMENTAL": {
        "name_zh": "模型 D: 机构全息复合决策型 (FULL_QUANTAMENTAL)",
        "strategy_model": "FULL_QUANTAMENTAL",
        "description": "宏观牛熊过滤 + 估值悬空防御 + RS动量与Stage2顺势均线四维复合配置",
        "stop_loss_pct": -0.07,
        "trailing_stop_pct": 0.15,
        "take_profit_target": None,
    },
}


def load_data_max_universe(market: str = "US") -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]], List[str]]:
    """从 data_max 中分市场加载纯正股标准化日线与对应本地基准 (物理隔离币种，防止日元/美元混淆)."""
    universe_bars: Dict[str, List[Dict[str, Any]]] = {}
    divs_map: Dict[str, List[Dict[str, Any]]] = {}
    splits_map: Dict[str, List[Dict[str, Any]]] = {}
    bench_bars: List[Dict[str, Any]] = []

    market = market.upper()

    if market == "US":
        # 纯美股正股池 (USD 计价，标的为全量美股正股股票，零期权)
        spy_file = NORMALIZED_US_DIR / "SPY_bars.json"
        if spy_file.exists():
            spy_data = json.loads(spy_file.read_text(encoding="utf-8"))
            bench_bars = spy_data.get("bars", [])

        for fpath in NORMALIZED_US_DIR.glob("*_bars.json"):
            sym = fpath.stem.replace("_bars", "")
            if sym == "SPY":
                continue
            data = json.loads(fpath.read_text(encoding="utf-8"))
            bars = data.get("bars", [])
            if len(bars) >= 60:
                universe_bars[sym] = bars
                divs_map[sym] = data.get("dividends", [])
                splits_map[sym] = data.get("splits", [])
    elif market == "JP":
        # 纯日股正股池 (JPY 计价，标的为东证全量日股正股股票，零期权)
        topix_file = NORMALIZED_JP_DIR / "1306_T_bars.json"
        if not topix_file.exists():
            topix_file = NORMALIZED_JP_DIR / "1306_bars.json"
        if topix_file.exists():
            topix_data = json.loads(topix_file.read_text(encoding="utf-8"))
            bench_bars = topix_data.get("bars", [])

        for fpath in NORMALIZED_JP_DIR.glob("*_bars.json"):
            sym = fpath.stem.replace("_bars", "").replace("_T", ".T")
            if sym in ("1306.T", "1306"):
                continue
            data = json.loads(fpath.read_text(encoding="utf-8"))
            bars = data.get("bars", [])
            if len(bars) >= 60:
                universe_bars[sym] = bars
                divs_map[sym] = data.get("dividends", [])
                splits_map[sym] = data.get("splits", [])
    else:
        raise ValueError(f"不支持的市场类型: {market}")

    symbols = sorted(list(universe_bars.keys()))
    return universe_bars, bench_bars, divs_map, splits_map, symbols


def run_adaptive_regime_simulation(
    universe_bars: Dict[str, List[Dict[str, Any]]],
    bench_bars: List[Dict[str, Any]],
    divs_map: Dict[str, List[Dict[str, Any]]],
    splits_map: Dict[str, List[Dict[str, Any]]],
    initial_capital: float = 100_000.0,
    top_k: int = 12,
    max_position_pct: float = 0.10,
    min_cash_pct: float = 0.05,
    commission_bps: float = 10.0,
    slippage_bps: float = 10.0,
) -> Tuple[BacktestMetrics, List[DailySnapshot], List[TradeRecord], List[Dict[str, Any]]]:
    """执行自适应宏观状态机驱动的 10 年全息动态选股回测 (融入 Top12 容量、滞后缓冲与动态 ATR 止损)."""
    all_trading_dates_set = set()
    bar_lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for s, bars in universe_bars.items():
        bar_lookup[s] = {}
        for b in bars:
            d = str(b["date"])
            all_trading_dates_set.add(d)
            bar_lookup[s][d] = b

    for b in bench_bars:
        all_trading_dates_set.add(str(b["date"]))

    all_trading_dates = sorted(list(all_trading_dates_set))
    all_trading_dates = [d for d in all_trading_dates if "2015-01-01" <= d <= "2024-12-31"]

    # 月度调仓日提取
    month_to_last: Dict[str, str] = {}
    for d in all_trading_dates:
        m = d[:7]
        month_to_last[m] = d
    monthly_rebalance_dates = set(month_to_last.values())

    regime_engine = MarketRegimeSwitchingEngine()
    cash = initial_capital
    active_positions: Dict[str, Dict[str, Any]] = {}
    snapshots: List[DailySnapshot] = []
    trades: List[TradeRecord] = []
    regime_logs: List[Dict[str, Any]] = []

    pending_target_symbols: Optional[List[str]] = None
    pending_execution_date: Optional[str] = None
    pending_score_lookup: Dict[str, Any] = {}
    current_strategy_model = "MOMENTUM_SEPA"
    current_stop_loss = -0.07
    current_trailing_stop = 0.15
    current_take_profit = None

    peak_equity = initial_capital
    trade_id_seq = 0

    comm_rate = commission_bps / 10000.0
    slip_rate = slippage_bps / 10000.0
    last_screen_year = ""

    for day_idx, today in enumerate(all_trading_dates):
        curr_year = today[:4]
        if curr_year != last_screen_year:
            last_screen_year = curr_year
            print(f"      [ADAPTIVE_REGIME] 宏观仿真推进至 {curr_year} 年 (持仓: {len(active_positions)} 只, 当前策略: {current_strategy_model})...", flush=True)

        # 1. 公司行动除权除息
        for s in list(active_positions.keys()):
            pos = active_positions[s]
            for dv in divs_map.get(s, []):
                if dv.get("date") == today or dv.get("ex_date") == today:
                    div_amount = float(dv.get("amount", 0.0)) * pos["shares"]
                    cash += div_amount
            for sp in splits_map.get(s, []):
                if sp.get("date") == today or sp.get("split_date") == today:
                    ratio = float(sp.get("ratio", 1.0))
                    if ratio > 0 and ratio != 1.0:
                        pos["shares"] = int(pos["shares"] * ratio)
                        pos["entry_price"] = pos["entry_price"] / ratio
                        pos["peak_price"] = pos["peak_price"] / ratio

        # 2. 执行 T+1 日开盘价撮合 (结合滞后缓冲防洗与逆波动率风险平价加权)
        if pending_target_symbols is not None and today == pending_execution_date:
            # 卖出不在目标池的标的 (仅清理跌破 Top 40 或破位 EMA50 的标的)
            for s in list(active_positions.keys()):
                if s not in pending_target_symbols:
                    pos = active_positions[s]
                    b_today = bar_lookup.get(s, {}).get(today)
                    if b_today:
                        exec_price = float(b_today["open"]) * (1.0 - slip_rate)
                        gross = pos["shares"] * exec_price
                        comm = gross * comm_rate
                        net_cash = gross - comm
                        cash += net_cash

                        gross_pnl = (exec_price - pos["entry_price"]) * pos["shares"]
                        net_pnl = gross_pnl - comm
                        ret_pct = (exec_price - pos["entry_price"]) / pos["entry_price"]
                        trade_id_seq += 1

                        trades.append(TradeRecord(
                            trade_id=f"TR-{trade_id_seq:05d}",
                            symbol=s,
                            market="US" if ".T" not in s else "JP",
                            action="SELL",
                            entry_date=pos["entry_date"],
                            exit_date=today,
                            shares=pos["shares"],
                            entry_price=round(pos["entry_price"], 2),
                            exit_price=round(exec_price, 2),
                            commission_paid=round(comm, 2),
                            slippage_paid=round(pos["shares"] * float(b_today["open"]) * slip_rate, 2),
                            gross_pnl=round(gross_pnl, 2),
                            net_pnl=round(net_pnl, 2),
                            return_pct=round(ret_pct, 4),
                            holding_days=day_idx - pos["entry_day_idx"],
                            exit_reason=f"HYSTERESIS_ROTATION ({current_strategy_model})"
                        ))
                        del active_positions[s]

            # 买入新标的 (逆波动率风险平价分配，单票上限 10%)
            tot_eq_est = cash + sum(
                p["shares"] * (float(bar_lookup[s][today]["open"]) if s in bar_lookup and today in bar_lookup[s] else p["entry_price"])
                for s, p in active_positions.items()
            )
            avail_budget = max(0.0, tot_eq_est * (1.0 - min_cash_pct))
            needed = [s for s in pending_target_symbols if s not in active_positions]
            if needed:
                # 逆波动率风险平价加权计算
                inv_vols = {}
                for s in needed:
                    sc = pending_score_lookup.get(s)
                    vol_ref = getattr(sc, "downside_vol20", 0.25) if sc else 0.25
                    if vol_ref <= 0.05:
                        vol_ref = 0.25
                    inv_vols[s] = 1.0 / max(0.08, float(vol_ref))

                total_inv_vol = sum(inv_vols.values())
                weights = {s: min(max_position_pct, (inv_vols[s] / total_inv_vol)) for s in needed}
                w_sum = sum(weights.values())
                if w_sum > 0:
                    weights = {s: min(max_position_pct, w / w_sum * min(1.0, len(needed) * max_position_pct)) for s, w in weights.items()}

                for s in needed:
                    b_today = bar_lookup.get(s, {}).get(today)
                    if not b_today:
                        continue
                    exec_price = float(b_today["open"]) * (1.0 + slip_rate)
                    stock_budget = avail_budget * weights.get(s, max_position_pct)
                    buy_val = min(stock_budget, cash * 0.95)
                    shares = int(buy_val / (exec_price * (1.0 + comm_rate)))
                    if shares > 0:
                        total_cost = shares * exec_price * (1.0 + comm_rate)
                        cash -= total_cost
                        sc = pending_score_lookup.get(s)
                        atr_val = getattr(sc, "atr20", exec_price * 0.035) if sc else (exec_price * 0.035)
                        active_positions[s] = {
                            "shares": shares,
                            "entry_price": exec_price,
                            "entry_date": today,
                            "entry_day_idx": day_idx,
                            "peak_price": exec_price,
                            "atr20": atr_val,
                        }

            pending_target_symbols = None
            pending_execution_date = None

        # 3. 盘中止损止盈监控 (2.5 * ATR20 动态自适应止损替代死板 -7%)
        for s in list(active_positions.keys()):
            pos = active_positions[s]
            b_today = bar_lookup.get(s, {}).get(today)
            if not b_today:
                continue

            o_p = float(b_today.get("open", b_today["close"]))
            h_p = float(b_today["high"])
            l_p = float(b_today["low"])
            c_p = float(b_today["close"])

            if h_p > pos["peak_price"]:
                pos["peak_price"] = h_p

            exit_reason = None
            exec_price = 0.0

            # 动态 ATR20 止损与跟踪止盈
            pos_atr = pos.get("atr20", pos["entry_price"] * 0.035)
            atr_stop_pct = min(-0.05, max(-0.12, -(2.5 * pos_atr / pos["entry_price"])))
            stop_loss_px = pos["entry_price"] * (1.0 + atr_stop_pct)

            # 刚性自适应硬止损
            if l_p <= stop_loss_px:
                exit_reason = f"ATR_DYNAMIC_STOP_LOSS ({atr_stop_pct:.1%})"
                base_px = o_p if o_p <= stop_loss_px else stop_loss_px
                exec_price = base_px * (1.0 - slip_rate)
            # 动态移动止盈 (Trailing Stop): 浮盈超过 +15% 时启动 2.5 * ATR 锁定利润
            elif pos["peak_price"] >= pos["entry_price"] * 1.15:
                trail_lvl = pos["peak_price"] - (2.5 * pos_atr)
                if l_p <= trail_lvl:
                    trail_ret = (trail_lvl - pos["entry_price"]) / pos["entry_price"]
                    exit_reason = f"ATR_TRAILING_STOP_LOCK (+{trail_ret:.1%})"
                    base_px = o_p if o_p <= trail_lvl else trail_lvl
                    exec_price = base_px * (1.0 - slip_rate)
            # 目标估值止盈
            elif current_take_profit and h_p >= pos["entry_price"] * (1.0 + current_take_profit):
                target_px = pos["entry_price"] * (1.0 + current_take_profit)
                exit_reason = f"TAKE_PROFIT_TARGET (+{current_take_profit:.1%})"
                base_px = o_p if o_p >= target_px else target_px
                exec_price = base_px * (1.0 - slip_rate)

            if exit_reason:
                gross = pos["shares"] * exec_price
                comm = gross * comm_rate
                net_cash = gross - comm
                cash += net_cash

                gross_pnl = (exec_price - pos["entry_price"]) * pos["shares"]
                net_pnl = gross_pnl - comm
                ret_pct = (exec_price - pos["entry_price"]) / pos["entry_price"]
                trade_id_seq += 1

                trades.append(TradeRecord(
                    trade_id=f"TR-{trade_id_seq:05d}",
                    symbol=s,
                    market="US" if ".T" not in s else "JP",
                    action="SELL",
                    entry_date=pos["entry_date"],
                    exit_date=today,
                    shares=pos["shares"],
                    entry_price=round(pos["entry_price"], 2),
                    exit_price=round(exec_price, 2),
                    commission_paid=round(comm, 2),
                    slippage_paid=round(pos["shares"] * exec_price * slip_rate, 2),
                    gross_pnl=round(gross_pnl, 2),
                    net_pnl=round(net_pnl, 2),
                    return_pct=round(ret_pct, 4),
                    holding_days=day_idx - pos["entry_day_idx"],
                    exit_reason=exit_reason
                ))
                del active_positions[s]

        # 4. 记录当日净值
        h_val = sum(
            p["shares"] * (float(bar_lookup[s][today]["close"]) if s in bar_lookup and today in bar_lookup[s] else p["entry_price"])
            for s, p in active_positions.items()
        )
        total_equity = cash + h_val
        if total_equity > peak_equity:
            peak_equity = total_equity
        dd = (total_equity - peak_equity) / peak_equity if peak_equity > 0 else 0.0

        prev_eq = snapshots[-1].total_equity if snapshots else initial_capital
        daily_ret = (total_equity / prev_eq) - 1.0 if prev_eq > 0 else 0.0
        cum_ret = (total_equity / initial_capital) - 1.0

        snapshots.append(DailySnapshot(
            date=today,
            cash=round(cash, 2),
            holdings_value=round(h_val, 2),
            total_equity=round(total_equity, 2),
            daily_return=round(daily_ret, 6),
            cumulative_return=round(cum_ret, 6),
            drawdown=round(dd, 6),
            active_positions_count=len(active_positions)
        ))

        # 5. 月度调仓决策
        if today in monthly_rebalance_dates:
            if day_idx + 1 < len(all_trading_dates):
                pending_execution_date = all_trading_dates[day_idx + 1]

                # 宏观状态判定
                bench_hist = [b for b in bench_bars if str(b["date"]) <= today]
                verdict = regime_engine.detect_regime(as_of_date=today, historical_benchmark_bars=bench_hist)
                current_strategy_model = verdict.selected_strategy_model
                current_stop_loss = verdict.stop_loss_pct
                current_trailing_stop = verdict.trailing_stop_pct
                current_take_profit = 0.20 if verdict.regime == MarketRegime.RANGE_BOUND_VALUE else None

                regime_logs.append({
                    "as_of_date": today,
                    "execution_date": pending_execution_date,
                    "regime": verdict.regime.value,
                    "active_model": current_strategy_model,
                    "spy_close": verdict.benchmark_close,
                    "ema50": verdict.ema50,
                    "ema200": verdict.ema200,
                    "vol20": verdict.vol20_annualized,
                    "description": verdict.rationale_zh,
                })

                # 运行多因子筛选打分 (获取前45名大池以支持Top 40滞后缓冲保护)
                screener = DynamicUniverseScreener(
                    strategy_model=current_strategy_model,
                    min_lookback_bars=60
                )
                candidate_pool_size = max(top_k * 4, 45)
                scores, _ = screener.screen_universe_at_date(
                    as_of_date=today,
                    historical_universe_bars=universe_bars,
                    historical_benchmark_bars=bench_bars,
                    top_k=candidate_pool_size
                )
                to_buy, to_keep = screener.filter_with_hysteresis(
                    current_holdings=list(active_positions.keys()),
                    ranked_scores=scores,
                    top_k=top_k,
                    buffer_rank=40,
                    holding_bars_map=universe_bars,
                    as_of_date=today
                )
                pending_target_symbols = to_keep + to_buy
                pending_score_lookup = {s.symbol: s for s in scores}

    mdd_start = snapshots[0].date if snapshots else "2015-01-02"
    mdd_end = snapshots[-1].date if snapshots else "2024-12-31"
    peak = initial_capital
    max_d = 0.0
    for s in snapshots:
        if s.total_equity > peak:
            peak = s.total_equity
        d = (peak - s.total_equity) / peak if peak > 0 else 0.0
        if d > max_d:
            max_d = d
            mdd_end = s.date

    metrics = calculate_model_metrics(
        initial_capital=initial_capital,
        snapshots=snapshots,
        trades=trades,
        bench_bars=bench_bars,
        mdd_start=mdd_start,
        mdd_end=mdd_end,
        strategy_mode="ADAPTIVE_REGIME"
    )
    return metrics, snapshots, trades, regime_logs


def main() -> None:
    """主程序：执行五大策略对撞与自适应切换全量纯正股现货回测."""
    target_market = "US"
    for arg in sys.argv:
        if arg.startswith("--market="):
            target_market = arg.split("=")[1].upper()
        elif arg in ("--market-jp", "-jp"):
            target_market = "JP"
        elif arg in ("--market-us", "-us"):
            target_market = "US"

    initial_capital = 100_000.0 if target_market == "US" else 10_000_000.0
    currency_symbol = "$" if target_market == "US" else "¥"

    print(f">>> 启动 data_max 【{target_market} 纯正股股票现货池】 10 年金融模型全息回测与自适应验证 (零期权合约)...", flush=True)
    universe_bars, bench_bars, divs_map, splits_map, symbols = load_data_max_universe(market=target_market)
    bench_name = "标普500基准 (SPY)" if target_market == "US" else "东证指数基准 (TOPIX 1306.T)"
    print(f"数据加载就绪: {len(symbols)} 只 {target_market} 纯正股标的, {bench_name} 日线数: {len(bench_bars)}", flush=True)

    comparison_results: Dict[str, Any] = {}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out_dir = REPORTS_DIR / f"{timestamp}_{target_market.lower()}_pure_equity"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 回测四大独立金融模型
    for m_key, spec in STRATEGY_CONFIGS.items():
        print(f"--> 正在运行 {spec['name_zh']} 回测...", flush=True)
        metrics, daily, trades, _ = execute_single_model_backtest(
            model_key=m_key,
            spec=spec,
            universe_bars=universe_bars,
            bench_bars=bench_bars,
            divs_map=divs_map,
            splits_map=splits_map,
            initial_capital=initial_capital,
        )
        comparison_results[m_key] = {
            "name_zh": spec["name_zh"],
            "asset_class": "CASH_EQUITY_SHARES",
            "market": target_market,
            "currency": "USD" if target_market == "US" else "JPY",
            "metrics": asdict(metrics),
            "trade_count": len(trades),
        }
        print(f"    完成: 期末权益 {currency_symbol}{metrics.final_equity:,.2f}, CAGR: {metrics.annualized_return_cagr:+.2%}, MDD: {metrics.max_drawdown:.2%}, Sharpe: {metrics.sharpe_ratio}", flush=True)

    # 2. 回测买方宏观市场状态机自适应切换组合
    print("--> 正在运行 自适应动态切换组合 (ADAPTIVE_REGIME) 回测...", flush=True)
    adapt_metrics, adapt_daily, adapt_trades, adapt_logs = run_adaptive_regime_simulation(
        universe_bars=universe_bars,
        bench_bars=bench_bars,
        divs_map=divs_map,
        splits_map=splits_map,
        initial_capital=initial_capital,
    )
    comparison_results["ADAPTIVE_REGIME"] = {
        "name_zh": "自适应动态切换组合 (ADAPTIVE_REGIME)",
        "asset_class": "CASH_EQUITY_SHARES",
        "market": target_market,
        "currency": "USD" if target_market == "US" else "JPY",
        "metrics": asdict(adapt_metrics),
        "trade_count": len(adapt_trades),
        "regime_transitions_count": len(adapt_logs),
    }
    print(f"    完成: 期末权益 {currency_symbol}{adapt_metrics.final_equity:,.2f}, CAGR: {adapt_metrics.annualized_return_cagr:+.2%}, MDD: {adapt_metrics.max_drawdown:.2%}, Calmar: {adapt_metrics.calmar_ratio}")

    # 3. 保存明细流水文件
    with open(out_dir / "full_universe_metrics_summary.json", "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, ensure_ascii=False, indent=2)

    with open(out_dir / "regime_switching_history.json", "w", encoding="utf-8") as f:
        json.dump(adapt_logs, f, ensure_ascii=False, indent=2)

    with open(out_dir / "adaptive_daily_equity.csv", "w", encoding="utf-8") as f:
        f.write("date,cash,portfolio_value,total_equity,drawdown,active_positions\n")
        for s in adapt_daily:
            f.write(f"{s.date},{s.cash},{s.holdings_value},{s.total_equity},{s.drawdown},{s.active_positions_count}\n")

    with open(out_dir / "adaptive_trades.csv", "w", encoding="utf-8") as f:
        f.write("trade_id,symbol,market,action,entry_date,exit_date,shares,entry_price,exit_price,commission_paid,slippage_paid,gross_pnl,net_pnl,return_pct,holding_days,exit_reason\n")
        for t in adapt_trades:
            f.write(f"{t.trade_id},{t.symbol},{t.market},{t.action},{t.entry_date},{t.exit_date},{t.shares},{t.entry_price},{t.exit_price},{t.commission_paid},{t.slippage_paid},{t.gross_pnl},{t.net_pnl},{t.return_pct},{t.holding_days},{t.exit_reason}\n")

    # 4. 存证入 HistoryValidationLedger
    print("--> 正在执行 HistoryValidationLedger 密码学签名存证...")
    ledger = HistoryValidationLedger(root=ROOT, db_path=ROOT / "data/ledger/history_validation_ledger.db")
    record_hash = ledger.append_validation(
        artifacts=[
            out_dir / "full_universe_metrics_summary.json",
            out_dir / "adaptive_daily_equity.csv",
            out_dir / "adaptive_trades.csv",
            out_dir / "regime_switching_history.json",
        ],
        metadata={
            "validation_id": f"data_max_full_universe_{timestamp}",
            "validation_type": "DATA_MAX_FULL_UNIVERSE_MULTI_MODEL_BACKTEST",
            "period_start": "2015-01-02",
            "period_end": "2024-12-31",
            "market_coverage": "US_SEC_10445_AND_JPX_4447_UNIVERSE",
            "friction_bps": 40.0,
            "execution_policy": "T_PLUS_1_OPEN_WITH_SLIPPAGE",
            "adaptive_final_equity": adapt_metrics.final_equity,
            "adaptive_cagr": adapt_metrics.annualized_return_cagr,
            "adaptive_mdd": adapt_metrics.max_drawdown,
            "adaptive_sharpe": adapt_metrics.sharpe_ratio,
            "adaptive_sortino": adapt_metrics.sortino_ratio,
            "adaptive_calmar": adapt_metrics.calmar_ratio,
        }
    )
    integrity = ledger.verify_integrity()
    print(f"存证成功！区块哈希: {record_hash[:16]}..., 链完整性验签: {integrity.is_valid}")
    print(f"全量回测底账已全部安全落盘至: {out_dir}")


if __name__ == "__main__":
    main()
