#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""万家股票初筛资产池数据构建与收集调度 CLI (Collect Screening Universe Data CLI).

用法:
    python scripts/collect_screening_universe_data.py --status
    python scripts/collect_screening_universe_data.py --build-samples
    python scripts/collect_screening_universe_data.py --build-all
"""

import argparse
import json
from pathlib import Path
import sys

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.data_readiness_tracker import get_data_readiness_banner
from finance_tools.screening_universe_builder import ScreeningUniverseBuilder


def main() -> int:
    parser = argparse.ArgumentParser(description="全盘万家美股与日股初筛资产池构建与收集调度")
    parser.add_argument("--status", action="store_true", help="显示全量资产池与初筛数据完备度总账")
    parser.add_argument("--build-samples", action="store_true", help="先打样：构建重点标的 Golden POC 初筛样例库")
    parser.add_argument("--build-all", action="store_true", help="全量分块构建美股 10,445 家与日股 4,447 家初筛底账")
    parser.add_argument("--chunk-size", type=int, default=100, help="全盘分块大小 (默认 100 家/批次)")
    args = parser.parse_args()

    builder = ScreeningUniverseBuilder()

    # 每次前置打印最新数据拉取完备度与时效提醒
    print(get_data_readiness_banner())
    print("\n" + "=" * 80)
    print("【全盘万家上市主体初筛资产池构建中枢 (14,892+ Multi-Thousand Universe)】")
    print("=" * 80)

    if args.build_samples or (not args.status and not args.build_all):
        sample_path = builder.build_and_save_samples()
        print(f"\n[打样成功] 已生成核心标的黄金初筛基准样本: {sample_path}")
        samples_data = json.loads(sample_path.read_text(encoding="utf-8"))
        print(f"  • 打样样本覆盖数: {samples_data['total_samples']} 家核心旗舰标的")
        for s in samples_data["samples"]:
            q = s["sepa_qualification"]
            p = s["price_and_moving_averages"]
            v = s["vcp_pattern_footprints"]
            print(f"    - [{s['market']}] {s['ticker']:<5} ({s['company_name'][:25]}): 现价 ${p['latest_price']} | VCP {v['vcp_code']} | 判定: {q['decision_action']}")

    if args.build_all:
        manifest = builder.build_universe_manifest_and_chunks(chunk_size=args.chunk_size)
        print(f"\n[全量分块构建成功] 资产池总账已落盘至 data/screening/screening_manifest.json")
        print(f"  • 全盘上市主体总数 : {manifest['total_companies']} 家")
        print(f"  • 美股 SEC EDGAR   : {manifest['market_summary']['US_SEC_EDGAR']['total_count']} 家 (分块: {manifest['market_summary']['US_SEC_EDGAR']['total_chunks']} 批)")
        print(f"  • 日股 东证全市场   : {manifest['market_summary']['JP_TOKYO_JPX']['total_count']} 家 (分块: {manifest['market_summary']['JP_TOKYO_JPX']['total_chunks']} 批)")
        print(f"  • 初筛技术底账约束 : {manifest['zero_token_contract']}")

    if args.status:
        manifest_file = PROJECT_ROOT / "data/screening/screening_manifest.json"
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            print(f"\n[当前总账状态] 数据基准时间: {manifest.get('updated_at')}")
            print(f"  • 登记企业规模: {manifest.get('total_companies')} 家")
            print(f"  • 美股批次: {manifest['market_summary']['US_SEC_EDGAR']['total_chunks']} chunks in {manifest['market_summary']['US_SEC_EDGAR']['chunk_dir']}")
            print(f"  • 日股批次: {manifest['market_summary']['JP_TOKYO_JPX']['total_chunks']} chunks in {manifest['market_summary']['JP_TOKYO_JPX']['chunk_dir']}")
        else:
            print("\n[提示] 尚未运行全量构建，请执行 --build-all 建立万家资产池分块底账。")

    print("\n" + "=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
