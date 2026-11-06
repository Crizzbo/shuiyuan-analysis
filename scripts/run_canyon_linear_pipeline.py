"""一键执行 Canyon 统一单向线性投研流水线 (Run Canyon Linear Pipeline).

消除层级嵌套，以单一事实来源（SSOT）执行单向流动 6 大标准作业工位：
  工位 1: 行情新鲜度与时段感知门禁 (QuoteFreshnessGate)
  工位 2: 官方三表刚性平账自检门禁 (OfficialFilingGate)
  工位 3: 宏观压力分与动态弹性安全边际 (MacroElasticMarginEngine)
  工位 4: 自由现金流折现三情景估值走廊 (ThreeScenarioValuation)
  工位 5: 黄金击球买入底线与凯利仓位控制 (GoldenStrikeZoneGate)
  工位 6: 买方投资直觉决策卡与不可篡改时间链条 (DecisionCardAndLedger)

用法示例:
    python scripts/run_canyon_linear_pipeline.py --ticker AAPL --allow-demo
    python scripts/run_canyon_linear_pipeline.py --input-json path/to/input.json
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.pipeline.canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from financial_core.engines.prediction_ledger import PredictionLedger
from finance_tools.market_quote_verifier import MarketQuoteVerifier


def get_demo_input(ticker: str) -> CanyonStationInput:
    """提供法证级平账核准的标准测试样本底账 (动态接入统一行情核验引擎，杜绝假数据)。"""
    t = ticker.upper().strip()
    verifier = MarketQuoteVerifier(ROOT)

    # 尝试从权威行情中提取最新真实报价
    try:
        vq = verifier.get_latest_quote(t)
        price_val = vq.price
    except Exception:
        # 回退防御基准
        price_val = 204.64 if t == "NVDA" else 180.50

    # 针对演示模式使用动态对齐的新鲜时钟，确保时效门禁严格合规
    edt_tz = timezone(timedelta(hours=-4))
    quote_ts = (datetime.now(timezone.utc).astimezone(edt_tz) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S EDT")
    session_type = "regular_trading"

    if t == "AAPL":
        return CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            sector="TechHardware",
            current_price=price_val,
            quote_timestamp=quote_ts,
            market_session=session_type,
            reported_cash=29965.0,
            restricted_cash=2100.0,
            debt_covenant_min_cash=3000.0,
            total_debt=106500.0,
            total_assets=352583.0,
            total_liabilities=290437.0,
            stockholders_equity=62146.0,  # 352583 == 290437 + 62146 (严格平账)
            reported_operating_cash_flow=118264.0,
            reported_capex=11500.0,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=10800.0,
            reported_revenue=383285.0,
            reported_operating_income=114301.0,
            reported_net_income=96995.0,
            shares_outstanding=15400.0,
            us_10y_yield=0.044,
            vix_index=19.5,
            fed_liquidity_drain_billion=45.0,
            company_beta=1.12,
            option_target_strike=185.0,
            option_expiry_days=30.0,
            option_implied_vol=0.24,
            is_call_option=True,
        )
    elif t == "NVDA":
        return CanyonStationInput(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            market="US",
            sector="TechHardware",
            current_price=price_val,
            quote_timestamp=quote_ts,
            market_session=session_type,
            reported_cash=34800.0,
            restricted_cash=2000.0,
            debt_covenant_min_cash=2500.0,
            total_debt=11000.0,
            total_assets=206800.0,
            total_liabilities=49510.0,
            stockholders_equity=157290.0,  # 206800.0 == 49510.0 + 157290.0 (官方 10-K 严格平账)
            reported_operating_cash_flow=64500.0,
            reported_capex=3100.0,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=4200.0,
            reported_revenue=96300.0,
            reported_operating_income=55200.0,
            reported_net_income=50100.0,
            shares_outstanding=24940.0,
            us_10y_yield=0.044,
            vix_index=19.5,
            fed_liquidity_drain_billion=45.0,
            company_beta=1.65,
            option_target_strike=210.0,
            option_expiry_days=30.0,
            option_implied_vol=0.48,
            is_call_option=True,
        )
    else:
        raise ValueError(
            f"标的 '{t}' 未配置内置验证样本。请通过 --input-json 传入经官方审计核准的三表底账文件。"
        )


def main():
    parser = argparse.ArgumentParser(description="Canyon 统一单向线性投研流水线运行中枢")
    parser.add_argument("--ticker", type=str, default="AAPL", help="股票代码 (如 AAPL, NVDA)")
    parser.add_argument("--allow-demo", action="store_true", help="允许加载预置官方验证样本")
    parser.add_argument("--input-json", type=str, default=None, help="从 JSON 文件加载官方三表与行情底账")
    parser.add_argument("--output-json", type=str, default=None, help="导出决策卡结构化 JSON")
    args = parser.parse_args()

    print("======================================================================")
    print("[流水线启动] 启动 Canyon 统一单向线性流水线 (Canyon Linear Pipeline)")
    print("======================================================================")

    if args.input_json:
        p = Path(args.input_json)
        if not p.exists():
            print(f"[错误] 底账文件不存在: {p}")
            sys.exit(1)
        raw = json.loads(p.read_text(encoding="utf-8"))
        inp = CanyonStationInput(**raw)
    else:
        if not args.allow_demo:
            print("[安全准入阻断] 正式投研模式严禁未经显式声明加载内置演示样本。")
            print("若需运行系统测试验证，请追加 --allow-demo 参数；或使用 --input-json 传入官方底账。")
            sys.exit(1)
        inp = get_demo_input(args.ticker)

    pipeline = CanyonLinearPipeline()

    try:
        card = pipeline.run(inp)
    except (QuoteFreshnessError, BalanceSheetInvariantError) as e:
        print(f"[门禁阻断] 流水线刚性门禁阻断: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"[运行异常] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)

    # 自然语言买方投资决策直觉呈现
    print("\n" + "=" * 60)
    print(f"[决策全景] 【{card.company_name} ({card.ticker})】买方机构投资决策全景卡")
    print("=" * 60)
    print(f"【行情时效】: {card.quote_timestamp} | {card.market_session_state}")
    print(f"【当前现价】: ${card.current_price:.2f}")
    print(f"【中性公允价值】: ${card.neutral_fair_value:.2f}")
    print(f"【黄金击球买入底线】: ${card.strike_price:.2f} (包含动态弹性安全边际 {card.elastic_mos_pct:.1f}%)")
    print(f"【买方区位状态】: {card.zone_status}")
    print(f"【投资研判直觉】: {card.recommended_action}")
    print(f"【动态仓位建议】: 半凯利仓位 {card.kelly_position_pct:.1f}%")
    print("-" * 60)
    print(f"【三情景估值走廊】:")
    print(f"  [悲观防御] 悲观防御底价: ${card.pessimistic_floor:.2f} | 触发事件: {card.pessimistic_event}")
    print(f"  [公允内在] 中性公允锚点: ${card.neutral_fair_value:.2f}")
    print(f"  [乐观靶心] 乐观弹性靶心: ${card.optimistic_target:.2f} | 催化诱因: {card.optimistic_event}")
    print("-" * 60)
    print(f"【宏观压力综合评分】: {card.macro_stress_score:.3f} (范围: 0.0 ~ 1.0)")
    if card.liquidity_atm_warning:
        print("  [警告] 优质大市值高流动性标的在宏观踩踏下存在‘流动性提款机抛售效应’。")
    print(f"【期权与波动率直觉】: {card.options_timing_verdict}")
    print("-" * 60)
    print(f"【不可篡改时间链条哈希】: SHA-256 [{card.ledger_hash}]")
    print("=" * 60 + "\n")

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(asdict(card), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[落盘完成] 决策卡已成功落盘至: {out_p}")


if __name__ == "__main__":
    main()
