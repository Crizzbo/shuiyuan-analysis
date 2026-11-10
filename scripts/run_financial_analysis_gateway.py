# -*- coding: utf-8 -*-
"""金融计算与细分行业分析统一调度入口 (run_financial_analysis_gateway.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 单一事实来源 (SSOT)：统一调度 FinancialAnalysisGateway 门面；
2. 纯本地 0-Token 秒级执行，零网络外围硬依赖；
3. 支持按需调度模式：
   --mode industry    : 细分行业结构化知识与敏感性因果分析
   --mode physics     : 商业物理动力学分析 (质量/动量/动能势能比/逃逸速度)
   --mode forensics   : 法务会计 Beneish M-Score 防粉饰造假排查
   --mode credit      : KMV-Merton 结构化信用违约与破产预警
   --mode liquidity   : Amihud 微观流动性冲击与非线性动态滑点
   --mode options     : 期权偏度与主力大单异动分析
   --mode regime      : 宏观市场 3 状态 HMM 识别与配置预算
   --mode all         : 一键全景买方金融与行业融合诊断
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.governance_and_pipeline.financial_analysis_gateway import (
    FinancialAnalysisGateway,
)


def _generate_synthetic_bars(symbol: str, count: int = 60, base_price: float = 120.0) -> List[Dict[str, Any]]:
    """生成合规标准点时日线样本 (供本地免网测试与快速诊断)."""
    bars = []
    p = float(base_price)
    for i in range(1, count + 1):
        p = round(p * (1.002 if i % 2 == 0 else 0.999), 2)
        bars.append({
            "date": f"2024-01-{(i % 28) + 1:02d}",
            "open": round(p * 0.995, 2),
            "high": round(p * 1.015, 2),
            "low": round(p * 0.99, 2),
            "close": p,
            "volume": 100_000.0 + i * 1000,
            "turnover": (100_000.0 + i * 1000) * p,
        })
    return bars


def main() -> None:
    parser = argparse.ArgumentParser(description="水源分析 - 金融计算与行业因果分析统一网关")
    parser.add_argument(
        "--mode",
        choices=["industry", "physics", "forensics", "credit", "liquidity", "options", "regime", "timing", "all"],
        default="all",
        help="分析模式选择",
    )
    parser.add_argument("--ticker", "--target", dest="target", default="NVDA", help="股票代码或行业名称/ID")
    parser.add_argument("--market", default="US", choices=["US", "JP"], help="交易所市场")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--order-value", type=float, default=50_000.0, help="拟买入金额 ($)")
    parser.add_argument(
        "--profile",
        choices=["institutional", "small_cap"],
        default="institutional",
        help="操盘与资金属性画像 (institutional: 机构稳健; small_cap: 小资金高爆发极紧止损与倒金字塔加仓)",
    )
    parser.add_argument(
        "--small-cap",
        dest="small_cap_flag",
        action="store_true",
        help="快捷开关：启用小资金高爆发倒金字塔加仓与 1.5R 极速保本模式",
    )

    args = parser.parse_args()
    gateway = FinancialAnalysisGateway.get_instance()
    target = args.target.strip()

    # 解析资金画像模式
    if args.small_cap_flag or args.profile == "small_cap":
        profile_mode = "Aggressive_Small_Cap"
    else:
        profile_mode = "Standard_Institutional"

    result: Dict[str, Any] = {}

    if args.mode == "industry":
        report = gateway.analyze_industry(target)
        result = {
            "mode": "industry",
            "target": target,
            "data": {
                "industry_id": report.industry_id,
                "industry_name_zh": report.industry_name_zh,
                "sector_name_zh": report.sector_name_zh,
                "macro_sector_name_zh": report.macro_sector_name_zh,
                "key_drivers": report.key_drivers,
                "accounting_focus": report.accounting_focus,
                "moat_types": report.moat_types,
                "risk_factors": report.risk_factors,
                "representative_tickers": report.representative_tickers,
                "causal_sensitivities": report.causal_sensitivities,
            }
        }

    elif args.mode == "physics":
        bars = _generate_synthetic_bars(target, 60, 130.0)
        res = gateway.analyze_physics(target, bars)
        result = {"mode": "physics", "target": target, "data": res}

    elif args.mode == "forensics":
        raw_fin = {
            "TotalRevenue": 1000.0,
            "CostOfRevenue": 550.0,
            "AccountsReceivableNetCurrent": 180.0,
            "TotalAssets": 2200.0,
            "NetIncomeCommonStockholders": 200.0,
            "OperatingCashFlow": 220.0,
        }
        res = gateway.analyze_forensics(target, raw_fin)
        result = {"mode": "forensics", "target": target, "data": res}

    elif args.mode == "credit":
        raw_fin = {
            "ShortTermDebt": 80.0,
            "LongTermDebtNoncurrent": 320.0,
        }
        res = gateway.analyze_credit(
            symbol=target,
            raw_financials=raw_fin,
            equity_market_cap=2_500_000_000_000.0,
            equity_volatility=0.45,
        )
        result = {"mode": "credit", "target": target, "data": res}

    elif args.mode == "liquidity":
        bars = _generate_synthetic_bars(target, 60, 130.0)
        res = gateway.analyze_liquidity(
            symbol=target,
            raw_bars=bars,
            intended_order_value=args.order_value,
            market=args.market,
        )
        result = {"mode": "liquidity", "target": target, "data": res}

    elif args.mode == "options":
        raw_deriv = {
            "call_volume": 12000.0,
            "put_volume": 8500.0,
            "call_open_interest": 95000.0,
            "put_open_interest": 75000.0,
            "iv_25d_put": 0.32,
            "iv_25d_call": 0.27,
            "iv_front_month_atm": 0.29,
            "iv_back_month_atm": 0.28,
        }
        res = gateway.analyze_options(target, 130.0, raw_deriv)
        result = {"mode": "options", "target": target, "data": res}

    elif args.mode == "regime":
        res = gateway.analyze_macro_regime("SPY")
        result = {"mode": "regime", "data": res}

    elif args.mode == "timing":
        bars = _generate_synthetic_bars(target, 60, 130.0)
        res = gateway.analyze_timing_and_execution(
            symbol=target,
            raw_bars=bars,
            profile=profile_mode,
        )
        result = {"mode": "timing", "target": target, "profile": profile_mode, "data": res}

    elif args.mode == "all":
        bars = _generate_synthetic_bars(target, 60, 130.0)
        comp = gateway.analyze_comprehensive(
            symbol=target,
            raw_bars=bars,
            market=args.market,
            equity_market_cap=2_500_000_000_000.0,
            profile=profile_mode,
        )
        result = {
            "mode": "all",
            "symbol": comp.symbol,
            "as_of_date": comp.as_of_date,
            "market": comp.market,
            "profile": profile_mode,
            "actionable_verdict": comp.actionable_verdict,
            "executive_summary_zh": comp.executive_summary_zh,
            "industry": {
                "id": comp.industry_report.industry_id if comp.industry_report else "",
                "name": comp.industry_report.industry_name_zh if comp.industry_report else "",
                "drivers": comp.industry_report.key_drivers if comp.industry_report else [],
            },
            "physics": comp.physics_report,
            "forensics": comp.forensics_report,
            "credit": comp.credit_report,
            "liquidity": comp.liquidity_report,
            "options": comp.option_report,
            "regime": comp.regime_report,
            "timing": comp.timing_report,
        }

    # 呈现结果
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 72)
        print(f"【水源买方金融与行业分析网关】执行模式: {args.mode.upper()} | 目标: {target}")
        print("=" * 72)
        if args.mode == "all":
            print(result.get("executive_summary_zh", ""))
            print("-" * 72)
            print(f"终局行动裁决: 【{result.get('actionable_verdict')}】")
        else:
            print(json.dumps(result.get("data", result), ensure_ascii=False, indent=2))
        print("=" * 72)


if __name__ == "__main__":
    main()
