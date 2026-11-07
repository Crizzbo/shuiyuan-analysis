"""AI 浏览器定向补数与信源法定鉴真命令行交互工具 (Evidence Verification CLI).

严格遵循《2026-10-11 最新数据来源策略》:
1. 支持 --scan-inbox 自动扫描收件箱中的法定公报并批量验签入库;
2. 支持 --event-id 与 --file 手动指定单个官方文件进行 SHA-256 验签并解除熔断;
3. 支持 --list-pending 打印所有待补数/熔断中事件及 AI 浏览器定向检索提示;
4. 支持 --receipts 查验不可篡改的防伪核验收据总账。
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.evidence_verification_pipeline import EvidenceVerificationPipeline


def print_receipt_card(rcp: dict) -> None:
    print("\n" + "=" * 78)
    print("【突发事件雷达 · 官方信源核验证明与传闻熔断解除收据】")
    print("=" * 78)
    print(f"收据流水编号    : {rcp.get('receipt_id')}")
    print(f"事件识别编号    : {rcp.get('event_id')}")
    print(f"事件标题        : {rcp.get('title')}")
    print(f"所属业务维度    : {rcp.get('category')}")
    print(f"原始核验状态    : {rcp.get('previous_status')} -> 【{rcp.get('new_status')}】")
    print(f"原始信源等级    : {rcp.get('previous_credibility')} -> 【{rcp.get('new_credibility')}】")
    print(f"深研分析门禁    : 传闻熔断已彻底解除 (已允许业务分部 SOTP 深度穿透计算)")
    print(f"本地证据归档    : {rcp.get('evidence_path')} ({rcp.get('file_size_bytes')} 字节)")
    print(f"证据指纹验签    : SHA-256 {rcp.get('evidence_sha256')}")
    print(f"核验时间戳 (UTC): {rcp.get('verified_at')}")
    print(f"核验备注说明    : {rcp.get('verification_note')}")
    print("=" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(description="AI 浏览器定向补数与信源法定鉴真 CLI")
    parser.add_argument("--scan-inbox", action="store_true", help="扫描收件箱自动匹配并批量验签入库")
    parser.add_argument("--event-id", type=str, default=None, help="目标核验事件编号 (如 EVT_755CB46A8923)")
    parser.add_argument("--file", type=str, default=None, help="已下载归档的本地官方公报/8-K原文路径")
    parser.add_argument("--note", type=str, default=None, help="分析师核验备考说明")
    parser.add_argument("--list-pending", action="store_true", help="列出当前所有待补法定公报或熔断中的事件")
    parser.add_argument("--receipts", action="store_true", help="查看历史法定鉴真与熔断解除收据账本")
    parser.add_argument("--db-path", type=str, default="data/ledger/event_radar.sqlite3", help="雷达数据库路径")

    args = parser.parse_args()
    pipeline = EvidenceVerificationPipeline(db_path=args.db_path)

    if args.scan_inbox:
        print("\n>>> 正在扫描官方证据收件箱 (data_sources/official_filings/inbox/)...")
        receipts = pipeline.scan_and_process_inbox()
        if not receipts:
            print("收件箱中未发现带有 EVT_ 前缀的新证据文件。")
        else:
            print(f"成功自动验签并解封 {len(receipts)} 项重大事件！")
            for r in receipts:
                print_receipt_card(r)

    elif args.event_id and args.file:
        file_p = Path(args.file)
        if not file_p.is_absolute():
            file_p = PROJECT_ROOT / args.file
        print(f"\n>>> 启动针对事件 {args.event_id} 的法定公报验签与熔断解除...")
        rcp = pipeline.verify_single_event(
            event_id=args.event_id,
            evidence_file=file_p,
            note=args.note,
        )
        print_receipt_card(rcp)

    elif args.list_pending:
        pending = pipeline.list_pending_verification_events()
        print("\n" + "=" * 78)
        print(f"【突发事件雷达 · 待补数与熔断中事实清单 (共 {len(pending)} 项)】")
        print("=" * 78)
        if not pending:
            print("当前所有事件均已达到最高 Tier 1 官方监管级，无待核实条目。")
        for idx, item in enumerate(pending, 1):
            is_rumor = item.get("current_status") == "Unverified_Rumor"
            status_flag = "[熔断锁定中]" if is_rumor else "[待补公报]"
            print(f"\n{idx:02d}. [{item.get('severity_level')}] {status_flag} {item.get('title')}")
            print(f"    - 事件编号: {item.get('event_id')} | 所属维度: {item.get('category')}")
            print(f"    - 当前信源: {item.get('current_tier')} | 状态: {item.get('current_status')}")
            print(f"    - 涉及标的: {', '.join(item.get('involved_entities', []))}")
            print(f"    - 物理影响: {item.get('micro_physical_impact')}")
        print("\n" + "=" * 78 + "\n")

    elif args.receipts:
        receipts = pipeline.load_receipts()
        print("\n" + "=" * 78)
        print(f"【突发事件雷达 · 历史法定鉴真与熔断解除收据总账 (共 {len(receipts)} 项)】")
        print("=" * 78)
        if not receipts:
            print("暂未生成历史核验收据。")
        for r in receipts:
            print_receipt_card(r)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
