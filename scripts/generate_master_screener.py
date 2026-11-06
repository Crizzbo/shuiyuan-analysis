"""千家资产池“顶层动态雷达与价值洼地主看板”自动化扫描与生成调度器 (Master Living Screener Generator).

职责：
1. 扫描 1,047 家上市公司建档状态机 (data/pipeline_state/567_universe_progress.json)；
2. 跨层级关联 reports/ai_dossiers/ 下的微观商业模型与 41 细分行业中文映射；
3. 动态计算估值安全边际折价率，识别 Top-30 深度击球区标的；
4. 调用 ExcelMasterScreenerBuilder 编译生成 reports/excel_dossiers/千家资产池_顶层动态雷达与价值洼地主看板.xlsx；
5. 打印清晰、严肃的买方投研控制台汇总标牌。
"""

import argparse
from datetime import date
import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

# 确保项目根目录在 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from financial_reporting.excel_master_screener_builder import ExcelMasterScreenerBuilder


def load_universe_targets(
    progress_file: str,
    dossiers_dir: str,
    excel_dir: str,
) -> List[Dict[str, Any]]:
    """从建档状态机和 AI 深度档案提取全量标的指标事实."""
    if not os.path.exists(progress_file):
        print(f"[警告] 状态机文件不存在: {progress_file}")
        return []

    with open(progress_file, "r", encoding="utf-8") as f:
        progress_data = json.load(f)

    tickers_dict = progress_data.get("tickers", {})
    targets: List[Dict[str, Any]] = []

    # 预先扫描 excel_dossiers 下所有现存的 .xlsx 文件以快速索引
    excel_lookup: Dict[str, str] = {}
    for fpath in glob.glob(os.path.join(excel_dir, "**", "*.xlsx"), recursive=True):
        fname = os.path.basename(fpath)
        # 提取前缀 ticker (如 "AAPL_..." 或 "7203_...")
        parts = fname.split("_")
        if parts:
            excel_lookup[parts[0].upper()] = fpath

    # 预先扫描 ai_dossiers 下所有现存的 .json 文件
    json_lookup: Dict[str, str] = {}
    for fpath in glob.glob(os.path.join(dossiers_dir, "**", "*_deep_dossier.json"), recursive=True):
        fname = os.path.basename(fpath)
        parts = fname.split("_")
        if parts:
            json_lookup[parts[0].upper()] = fpath

    print(f"[扫描] 发现已建立 Excel 底账 {len(excel_lookup)} 份，AI 深度档案 {len(json_lookup)} 份")

    for ticker, t_info in tickers_dict.items():
        status = t_info.get("status", "")
        if status != "COMPLETED":
            continue

        market = str(t_info.get("market", "US")).upper()
        ticker_upper = str(ticker).upper()

        # 补全 Excel 路径
        excel_path = t_info.get("excel_path")
        if not excel_path and ticker_upper in excel_lookup:
            excel_path = excel_lookup[ticker_upper]

        # 尝试读取 AI 深度档案获取精准行业与催化要件
        industry_id = "general_tech"
        industry_name = "科技与先进制造"
        catalyst = ""

        json_path = t_info.get("json_path")
        if not json_path and ticker_upper in json_lookup:
            json_path = json_lookup[ticker_upper]

        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    d_json = json.load(jf)
                    overview = d_json.get("overview", {})
                    industry_id = overview.get("industry_id") or industry_id
                    industry_name = overview.get("industry_name_zh") or industry_name

                    # 提取乐观催化剂或核心逻辑
                    dec = d_json.get("decision_summary", {})
                    scenario_cards = dec.get("scenario_cards", {})
                    pess_card = scenario_cards.get("pessimistic_floor", {})
                    opt_card = scenario_cards.get("optimistic_target", {})
                    triggers = opt_card.get("trigger_events") or pess_card.get("trigger_events") or []
                    if triggers:
                        catalyst = "; ".join(triggers[:2])
                    else:
                        catalyst = opt_card.get("rationale") or pess_card.get("rationale") or ""
            except Exception:
                pass

        if not catalyst:
            catalyst = "官方经审计三表平衡，常态自由现金流具备稳固的重置成本安全防线。"

        target_record = {
            "ticker": ticker,
            "company_name": t_info.get("company_name", ticker),
            "market": market,
            "industry_id": industry_id,
            "industry_name": industry_name,
            "current_price": t_info.get("current_price", 0.0),
            "pessimistic_floor": t_info.get("pessimistic_floor", 0.0),
            "neutral_fair_value": t_info.get("neutral_fair_value", 0.0),
            "optimistic_target": t_info.get("optimistic_target", 0.0),
            "margin_of_safety_pct": t_info.get("margin_of_safety_pct", 0.0),
            "objective_signal": t_info.get("objective_signal", "FAIR_VALUE"),
            "quote_timestamp": t_info.get("quote_timestamp", "前收盘基准"),
            "freshness_status": t_info.get("freshness_status", "前收盘基准"),
            "catalyst_summary": catalyst,
            "excel_path": excel_path,
        }
        targets.append(target_record)

    return targets


def main():
    parser = argparse.ArgumentParser(description="千家资产池顶层动态雷达与价值洼地主看板生成器")
    parser.add_argument(
        "--progress-file",
        default=os.path.join(PROJECT_ROOT, "data", "pipeline_state", "567_universe_progress.json"),
        help="标的建档状态机路径",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(PROJECT_ROOT, "reports", "excel_dossiers"),
        help="主看板输出目录",
    )
    parser.add_argument(
        "--output-filename",
        default="千家资产池_顶层动态雷达与价值洼地主看板.xlsx",
        help="主看板 Excel 文件名",
    )
    parser.add_argument(
        "--dossiers-dir",
        default=os.path.join(PROJECT_ROOT, "reports", "ai_dossiers"),
        help="AI 深度档案目录",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("  千家资产池【顶层动态雷达与价值洼地主看板 (Master Living Screener)】生成流水线")
    print(f"  执行基准日期: {date.today().isoformat()} | 架构规范: FAST Standard & CFI Model Rigor")
    print("=" * 80)

    # 1. 扫描与加载标的事实
    targets = load_universe_targets(
        progress_file=args.progress_file,
        dossiers_dir=args.dossiers_dir,
        excel_dir=args.output_dir,
    )

    if not targets:
        print("[错误] 未能加载到有效标的数据，终止生成。")
        sys.exit(1)

    us_count = sum(1 for t in targets if t.get("market") == "US")
    jp_count = sum(1 for t in targets if t.get("market") == "JP")
    buy_zone_count = sum(1 for t in targets if float(t.get("margin_of_safety_pct", 0) or 0) > 0)

    print(f"\n[数据统计汇总]:")
    print(f"  - 纳入全量标的: {len(targets)} 家")
    print(f"  - 美股上市公司: {us_count} 家")
    print(f"  - 东证日股公司: {jp_count} 家")
    print(f"  - 处于安全边际击球区 (折价率 > 0%): {buy_zone_count} 家 ({buy_zone_count / len(targets) * 100:.1f}%)")

    # 2. 编译 Excel 主看板
    out_file = os.path.join(args.output_dir, args.output_filename)
    print(f"\n[建造中枢] 正在编译 4-Sheet 联动工作簿...")

    builder = ExcelMasterScreenerBuilder(base_date=date.today().isoformat())
    wb = builder.build_master_screener(
        targets=targets,
        output_path=out_file,
    )

    file_size_kb = os.path.getsize(out_file) / 1024.0
    print(f"[交付成功] 主看板已生成落盘:")
    print(f"  - 文件路径: {out_file}")
    print(f"  - 文件体积: {file_size_kb:.1f} KB")
    print(f"  - 包含工作表: {wb.sheetnames}")
    print("=" * 80)


if __name__ == "__main__":
    main()
