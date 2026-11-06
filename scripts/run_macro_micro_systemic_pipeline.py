"""运行宏微观大贯通全盘投研决算流水线并导出买方 4-Sheet Excel 报告书.

涵盖：
1. 世界国民经济核算体系 (SNA) $110T~$115T 基准与外生冲击一般均衡；
2. 行星吸收平衡律自检 ($C + I + G == World GDP$)；
3. OECD 12 大宏观产业列昂惕夫投入产出网络增加值与内生 ROIC 测算；
4. 全量 320+ 家通过官方平账自检微观标的 (Tier 0 核心池) 两阶段收敛 DCF 估值穿透；
5. 价值洼地击球区与高估泡沫排雷清单筛选；
6. 导出 FAST/CFI 标准买方 4-Sheet Excel 深度研报工作簿；
7. 写入 PredictionLedger SHA-256 密码学不可篡改审计链条。
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_reporting.macro_micro_systemic_orchestrator import MacroMicroSystemicOrchestrator
from financial_reporting.excel_macro_micro_builder import ExcelMacroMicroReportBuilder


def main():
    parser = argparse.ArgumentParser(description="宏微观大贯通全盘计算流水线与 Excel 导出")
    parser.add_argument("--as-of-date", type=str, default=None, help="估值基准日期 (YYYY-MM-DD)")
    parser.add_argument("--no-ledger", action="store_true", help="跳过密码学账本存证")
    parser.add_argument("--output-excel", type=str, default=None, help="自定义 Excel 导出路径")
    parser.add_argument("--output-json", type=str, default=None, help="自定义 JSON 快照导出路径")
    args = parser.parse_args()

    as_of_date = args.as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("=" * 110)
    print(f"启动宏微观大贯通全盘投研决算流水线 (Macro-Micro Systemic Pipeline: {as_of_date})")
    print("=" * 110)

    orchestrator = MacroMicroSystemicOrchestrator()

    # 1. 执行端到端宏微观全回路闭环计算
    print("[1/4] 正在加载全量官方已核验标的并执行资产负债表刚性平账自检...")
    pipeline_res = orchestrator.run_systemic_pipeline(
        as_of_date=as_of_date,
        record_to_ledger=not args.no_ledger,
    )

    meta = pipeline_res["meta"]
    n_firms = meta["total_verified_firms_evaluated"]
    is_conserved = meta["planetary_absorption_strictly_conserved"]
    base = pipeline_res["scenario1_baseline"]
    sec_base = base["step2_middle_industry_leontief"]["sector_totals"]
    p_base = base["step5_reverse_aggregation_and_equilibrium"]["world_financial_asset_pricing"]

    print(f" -> 成功接入并核验企业数量: {n_firms} 家 (100% 满足 Assets = Liabilities + Equity)")
    print(f" -> 世界生产总值 (World GDP): ${sec_base['total_value_added_trillion']:.2f} 万亿美元")
    print(f" -> 资本营业盈余: ${sec_base['total_capital_operating_surplus_trillion']:.2f}T | 劳动报酬: ${sec_base['total_labor_wages_trillion']:.2f}T")
    print(f" -> 行星吸收平衡律严格闭环守恒: {is_conserved} (杜绝任何虚假宏观外生溢出)")
    print(f" -> 全球股票现存市值: ${p_base['current_global_equity_market_cap_trillion']:.2f}T | 两阶段公允值: ${sec_base['two_stage_total_fair_listed_equity_value_trillion']:.2f}T (偏离度: {p_base['bottom_up_valuation_gap_pct']:+.2f}%)")

    # 2. 导出 FAST/CFI 买方机构级 4-Sheet Excel 报告书
    print("\n[2/4] 正在根据 FAST/CFI 规范构建买方 4-Sheet Excel 深度研报工作簿...")
    excel_path = ExcelMacroMicroReportBuilder.build_workbook(
        pipeline_data=pipeline_res,
        output_path=args.output_excel,
    )
    print(f" -> Excel 工作簿导出成功: {excel_path.relative_to(ROOT) if excel_path.is_relative_to(ROOT) else excel_path}")

    # 3. 导出 JSON 决算快照
    print("\n[3/4] 正在持久化系统级 JSON 决算快照...")
    if args.output_json:
        json_path = Path(args.output_json).resolve()
    else:
        json_dir = ROOT / "reports" / "macro_micro" / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        json_path = json_dir / f"macro_micro_systemic_snapshot_{as_of_date}.json"

    # 序列化 dataclass 对象
    serializable_data = {
        "meta": meta,
        "scenario1_baseline": {
            "sector_totals": sec_base,
            "world_financial_asset_pricing": p_base,
            "sector_valuations_count": len(base["step2_middle_industry_leontief"]["sector_intrinsic_valuations"]),
        },
        "statistics": {
            "total_evaluated_firms": n_firms,
            "undervalued_count": len(pipeline_res["undervalued_batting_zone"]),
            "overvalued_count": len(pipeline_res["overvalued_bubble_mines"]),
            "quality_compounders_count": len(pipeline_res["quality_core_compounders"]),
            "ledger_recorded_count": len(pipeline_res["ledger_hashes"]),
        },
        "top_undervalued_batting_zone": [
            {
                "ticker": f.ticker,
                "name": f.company_name,
                "market": f.market,
                "market_cap_bil": f.market_cap_billion,
                "two_stage_fair_bil": f.two_stage_fair_value_billion,
                "margin_of_safety_pct": f.margin_of_safety_pct,
                "implied_roic_pct": f.implied_roic_pct,
                "cash_runway": f.cash_runway_desc,
                "catalyst": f.catalyst_events,
            }
            for f in pipeline_res["undervalued_batting_zone"][:15]
        ],
        "top_overvalued_bubble_mines": [
            {
                "ticker": f.ticker,
                "name": f.company_name,
                "market": f.market,
                "market_cap_bil": f.market_cap_billion,
                "two_stage_fair_bil": f.two_stage_fair_value_billion,
                "margin_of_safety_pct": f.margin_of_safety_pct,
                "annual_fcf_mil": f.annual_fcf_million,
                "risk_notes": f.risk_notes,
            }
            for f in pipeline_res["overvalued_bubble_mines"][:15]
        ],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)
    print(f" -> JSON 快照保存成功: {json_path.relative_to(ROOT) if json_path.is_relative_to(ROOT) else json_path}")

    # 4. 打印买方核心投资决算看板
    print("\n[4/4] 买方实战投资走廊核心决策看板")
    print("-" * 110)
    print(f"{'分类':<18} | {'标的数量':<10} | {'核心准入与风控界定标准'}")
    print("-" * 110)
    print(f"{'价值洼地击球区':<18} | {len(pipeline_res['undervalued_batting_zone']):<10} | 安全边际率 >= 25.0%，净现金跑道坚挺，具备明确上行催化事实")
    print(f"{'高估泡沫排雷标的':<18} | {len(pipeline_res['overvalued_bubble_mines']):<10} | 溢价严重透支超过 25.0%，或年度自由现金流持续失血")
    print(f"{'高质量稳健复利底仓':<18} | {len(pipeline_res['quality_core_compounders']):<10} | 隐含真实 ROIC >= 20.0%，超越行业资本成本，估值合理")
    print("-" * 110)

    print("\n【精选优先建仓候选清单 (Top 5 价值洼地)】")
    for idx, f in enumerate(pipeline_res["undervalued_batting_zone"][:5], 1):
        print(f" {idx}. [{f.market}] {f.ticker:<6} {f.company_name[:16]:<18} | 市值: ${f.market_cap_billion:.1f}B | 两阶段公允值: ${f.two_stage_fair_value_billion:.1f}B | 安全边际: +{f.margin_of_safety_pct:.1f}% | 催化剂: {f.catalyst_events[:25]}")

    print("\n【重点规避排雷清单 (Top 5 高估泡沫)】")
    for idx, f in enumerate(pipeline_res["overvalued_bubble_mines"][:5], 1):
        over_pct = ((f.market_cap_billion - f.two_stage_fair_value_billion) / max(0.01, f.two_stage_fair_value_billion)) * 100.0
        print(f" {idx}. [{f.market}] {f.ticker:<6} {f.company_name[:16]:<18} | 市值: ${f.market_cap_billion:.1f}B | 两阶段公允值: ${f.two_stage_fair_value_billion:.1f}B | 溢价透支: +{over_pct:.1f}% | 风险: {f.risk_notes[:25]}")

    print("\n" + "=" * 110)
    print("宏微观大贯通全盘计算流水线圆满完成！成果物已成功归档。")
    print("=" * 110)


if __name__ == "__main__":
    main()
