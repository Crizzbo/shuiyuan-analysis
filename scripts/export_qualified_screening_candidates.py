#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""万家股票初筛候选池排序与聚合导出 CLI (Export Qualified Screening Candidates CLI).

用法:
    python scripts/export_qualified_screening_candidates.py --top 20
    python scripts/export_qualified_screening_candidates.py --market US --top 10
    python scripts/export_qualified_screening_candidates.py --market JP --top 10
"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.data_readiness_tracker import get_data_readiness_banner
from finance_tools.screening_candidate_ranker import ScreeningCandidateRanker


def main() -> int:
    parser = argparse.ArgumentParser(description="全盘万家美股与日股初筛优质候选池优选与导出")
    parser.add_argument("--top", type=int, default=15, help="展示各市场前 N 名核心枢轴买点标的")
    parser.add_argument("--market", choices=["US", "JP", "ALL"], default="ALL", help="指定筛选市场")
    args = parser.parse_args()

    ranker = ScreeningCandidateRanker()

    print(get_data_readiness_banner())
    print("\n" + "=" * 80)
    print("【万家股票初筛准入池优选排序与输出 (Qualified Screening Candidates)】")
    print("=" * 80)

    data = ranker.aggregate_and_rank_candidates()

    pivots = data.get("pivot_ready_candidates", [])
    watchlists = data.get("watchlist_candidates", [])

    print(f"\n[全盘初筛聚合统计]")
    print(f"  • 已聚合分块结果文件: {data['source_result_chunks_count']} 批次")
    print(f"  • 准入全票通过买点标的 (Stage_2_Pivot_Ready): {data['tier0_pivot_ready_count']} 家")
    print(f"  • 主升形态收敛观察标的 (Watchlist_Forming)   : {data['tier1_watchlist_count']} 家")
    print(f"  • 候选总账已持久化至: data/screening/qualified_candidates.json")

    def display_candidates(candidates, title, max_n):
        print(f"\n" + "-" * 80)
        print(f"★ {title} (Top {max_n})")
        print("-" * 80)
        filtered = candidates
        if args.market != "ALL":
            filtered = [c for c in filtered if c["market"] == args.market]

        if not filtered:
            print("  (暂无符合筛选条件的标的)")
            return

        for idx, c in enumerate(filtered[:max_n], 1):
            mkt = c["market"]
            tkr = c["ticker"]
            name = c["company_name"][:28]
            lp = c["latest_price"]
            pp = c["pivot_price"]
            vcp = c["vcp_code"]
            dry = c["dryup_ratio"] * 100
            gain = c["gain_from_52w_low_pct"]
            pull = c["pullback_from_52w_high_pct"]

            print(
                f"  {idx:>2}. [{mkt}] {tkr:<6} ({name:<28}) "
                f"| 现价: ${lp:>8.2f} "
                f"| 突破买点: ${pp:>8.2f} "
                f"| VCP: {vcp:<12} "
                f"| 抽干比: {dry:>4.1f}% "
                f"| 距低点: +{gain:>5.1f}% "
                f"| 距高点: -{pull:>4.1f}%"
            )

    display_candidates(pivots, "核心旗舰买点池 · 枢轴突破就绪 (Tier 0 / Tier 1 准入)", args.top)
    display_candidates(watchlists, "主升浪跟踪池 · 极窄形态形成中 (等待末端收敛与地量)", 10)

    print("\n" + "=" * 80)
    print("【买方决策建议】")
    print("  1. 核心买点标的已全票满足 Minervini SEPA 8 大趋势硬指标与 VCP 地量收敛，建议立即接入官方三表法证与情景 DCF 估值；")
    print("  2. 形态收敛中标的列入重点盯盘自选池，待末端收缩幅度 <= 5% 且成交量萎缩至 50% 日均量以下时触发买点告警。")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
