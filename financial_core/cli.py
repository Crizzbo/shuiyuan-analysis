"""金融分析核心独立命令行入口 (Financial Analysis Core CLI).

提供独立的量化分析与投研决策 CLI，脱离任何 Agent/Skill 即可单机运行：
    python -m financial_core.cli --ticker RXRX --allow-demo-sample
    python -m financial_core.cli --ticker 000858 --allow-demo-sample --json
"""

import argparse
import json
import sys
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .api import FinancialAnalysisSystem
from .contracts import AnalysisMode


def main():
    parser = argparse.ArgumentParser(
        description="金融分析核心系统 (Standalone Financial Analysis Engine CLI)"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="标的代码 (如 RXRX, 000858, NVDA)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full_systemic",
        choices=["full_systemic", "forensic_only", "valuation_dcf", "macro_stress", "option_tree"],
        help="分析模式",
    )
    parser.add_argument(
        "--allow-demo-sample",
        action="store_true",
        help="显式声明允许在未提供官方底账时使用测试演示样本",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出原始数据",
    )
    args = parser.parse_args()

    engine = FinancialAnalysisSystem()
    mode = AnalysisMode(args.mode)

    try:
        result = engine.analyze_equity(
            ticker=args.ticker,
            mode=mode,
            allow_demo_sample=args.allow_demo_sample,
        )
    except Exception as e:
        print(f"[ERROR] 金融分析执行异常: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    if not result.execution_success:
        print("\n" + "=" * 70)
        print(f"[分析阻断] 标的: {result.ticker} | 状态: {result.execution_status}")
        print("=" * 70)
        print(f"阻断原因: {result.block_reason}")
        print("=" * 70 + "\n")
        sys.exit(1)

    card = result.decision_card
    sym = card.currency_symbol
    print("\n" + "=" * 70)
    print(f"  机构级独立金融分析系统报告: {card.company_name} ({card.ticker})")
    if result.is_demo_sample:
        print("  [演示模式] 注意: 本次分析基于内置测试底账运行 (DEMO_MODE)")
    print("=" * 70)
    print(f"市场/币种: {card.market} ({card.currency}) | 行情时间: {card.quote_timestamp} ({card.market_session})")
    print(f"现行报价: {sym}{card.current_price:.2f} | 基准参考价: {sym}{card.baseline_reference_price:.2f}")
    print(f"量化客观信号: 【{card.objective_signal}】")
    print(f"现金跑道状态: {card.hard_runway_desc}")
    print(f"内在公允价值 (中性): {sym}{card.neutral_fair_value:.2f} (现价安全边际: {card.margin_of_safety_pct:+.1f}%)")
    print(f"悲观清算底价: {sym}{card.pessimistic_floor:.2f} | 乐观目标价: {sym}{card.optimistic_target:.2f}")
    print(f"法证体检信号: 红牌 {card.forensic_red_flags_count} 项, 黄牌 {card.forensic_yellow_flags_count} 项")

    print("\n[多情景估值矩阵 (复算参数)]")
    for sc in result.valuation_scenarios:
        w_str = f", WACC: {sc.wacc*100:.1f}%" if sc.wacc else ""
        print(f"  - {sc.scenario_name.upper():<12}: {sym}{sc.fair_value:>7.2f} (空间: {sc.implied_upside_downside_pct:>+6.1f}%{w_str}, 模型: {sc.valuation_model_used})")

    print("\n[法证穿透审计发现]")
    if result.forensic_findings:
        for ff in result.forensic_findings:
            print(f"  [{ff.alert_level}] {ff.dimension:<25}: 证据: {ff.evidence}")
    else:
        print("  [正常] 未发现重大报表粉饰或表外毒性红旗。")

    if result.macro_stress:
        ms = result.macro_stress
        print(f"\n[宏观压力测试: {ms.scenario_name}]")
        print(f"  传导路径: {ms.transmission_channel}")
        print(f"  宏观估值折价: {ms.equity_shock_pct:+.1f}% -> 承压公允价: {sym}{ms.target_price_under_stress:.2f} (加压折现率 WACC: {ms.shocked_wacc_pct:.1f}%)")

    if result.option_pricing:
        op = result.option_pricing
        m_call = f"{sym}{op.merton_jump_call:.2f}" if op.merton_jump_call is not None else "N/A"
        print(f"\n[CRR 美式期权二叉树 / Merton 跳跃 (Strike: {sym}{op.strike}, IV: {op.implied_volatility*100:.1f}%)]")
        print(f"  CRR 美式看涨: {sym}{op.crr_american_call:.2f} (提前行权溢价: +{sym}{op.early_exercise_premium:.4f})")
        print(f"  CRR 美式看跌: {sym}{op.crr_american_put:.2f}")
        print(f"  Merton 跳跃补偿 Call: {m_call}")

    print("\n[客观事实与数据总结]")
    print(f"  {card.summary_verdict}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
