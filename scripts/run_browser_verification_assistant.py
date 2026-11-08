"""AI 浏览器定向核验助手命令行工具 (Run Browser Verification Assistant CLI).

严格遵循《2026-10-11 最新数据来源策略》与《AGENTS.md》买方防伪鉴真准则:
1. 提供买方研究员一键扫描、定向检索匹配与官方公报验签闭环的交互接口;
2. 支持预览官方检索式 (--list, --dry-run) 与批量/指定事件熔断解除 (--event-id, --batch);
3. 联动 EvidenceVerificationPipeline 完成 SHA-256 哈希计算与存证记账;
4. 严格去工程符号化，以自然商业语义输出权威核验报告与买方决策直觉。
"""

import argparse
import json
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.browser_verification_assistant import BrowserVerificationAssistant


def setup_logger(verbose: bool = False) -> None:
    """初始化控制台日志器."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_banner() -> None:
    """打印买方机构级定向核验助手标题."""
    print("=" * 80)
    print("【突发事件雷达 · AI 浏览器定向核验助手与法定鉴真中枢】")
    print("=" * 80)


def handle_list(assistant: BrowserVerificationAssistant) -> None:
    """列出当前所有待核验重大传闻及其官方检索方案."""
    print_banner()
    pending = assistant.scan_pending_rumors()
    if not pending:
        print("\n🟢 当前事件雷达总账中无待核验的重大传闻事件 (P0/P1 均已核实或处于监控门禁通过状态)。\n")
        return

    print(f"\n📊 扫描完成: 发现 {len(pending)} 项待核查的重大传闻事件需定向获取官方监管凭证:\n")
    for idx, e in enumerate(pending, 1):
        task = assistant.build_verification_task(e)
        print(f"[{idx}] 事件识别编号 : {task.event_id}")
        print(f"    • 事件简要标题 : {task.title}")
        print(f"    • 涉案核心实体 : {task.entity}")
        print(f"    • 业务所属维度 : {task.category} (烈度: {task.severity_level})")
        print(f"    • 当前门禁状态 : {task.current_status} ({task.current_tier})")
        print(f"    • 官方监管机构 : {task.authority}")
        print(f"    • 推荐检索公式 : {task.recommended_query}")
        print(f"    • 预期公报类型 : {task.document_type}")
        print(f"    • 证据目标文件 : {task.expected_filename}")
        print("-" * 80)


def handle_verify_single(
    assistant: BrowserVerificationAssistant,
    event_id: str,
    custom_content: str = None,
    dry_run: bool = False,
) -> None:
    """处理单一事件的定向核验与熔断解除."""
    print_banner()
    print(f"🎯 正在为指定事件 [{event_id}] 执行官方公报定向核验闭环 (试运行={dry_run})...\n")

    res = assistant.verify_single_event(event_id, custom_content=custom_content, dry_run=dry_run)

    if dry_run:
        task = res["task"]
        print("【试运行预览模式 - 未实际修改磁盘与数据库】")
        print(f"• 事件识别编号 : {task['event_id']}")
        print(f"• 官方发布机构 : {task['authority']}")
        print(f"• 推荐定向检索 : {task['recommended_query']}")
        print(f"• 预期入库文件 : {task['expected_filename']}")
        print(f"• 预计解除熔断 : {'是' if res['will_lift_breaker'] else '否 (已处于核实状态)'}")
    else:
        print("【官方信源鉴真成功 · 传闻熔断门禁已成功解除】")
        print(f"• 事件识别编号 : {res['event_id']}")
        print(f"• 凭证归档路径 : {res['evidence_file']}")
        print(f"• SHA-256 指纹 : {res['sha256']}")
        print(f"• 状态跃迁轨迹 : {res['original_status']} ➔ 【{res['new_status']}】")
        print(f"• 权威层级跃迁 : {res['original_tier']} ➔ 【{res['new_tier']}】")
        print(f"• 熔断锁止状态 : 【已彻底解除】(下游 SOTP 因果穿透计算已自动放行)")

    print("=" * 80 + "\n")


def handle_batch(
    assistant: BrowserVerificationAssistant,
    dry_run: bool = False,
) -> None:
    """批量核验所有未决传闻并全盘解封."""
    print_banner()
    print(f"🚀 启动全盘未决重大传闻批量定向核验流水线 (试运行={dry_run})...\n")

    summary = assistant.batch_verify_all(dry_run=dry_run)
    total = summary["total_pending"]
    verified = summary["verified_count"]

    if dry_run:
        print(f"📋 试运行完成: 共匹配到 {total} 项待核验重大传闻任务清单。")
    else:
        print("=" * 80)
        print("【批量法定鉴真与熔断解除汇总报告】")
        print("=" * 80)
        print(f"• 待核事件总数 : {total} 项")
        print(f"• 成功解封总数 : {verified} 项")
        print("-" * 80)
        for r in summary["results"]:
            icon = "✅" if r["circuit_breaker_lifted"] else "ℹ️"
            print(f"  {icon} [{r['event_id']}] {r['title']} ➔ 状态: {r['new_status']}")
        print("=" * 80 + "\n")


def main() -> int:
    """命令行主执行入口."""
    parser = argparse.ArgumentParser(
        description="AI 浏览器定向核验助手: 针对待核传闻生成官方检索式并自动执行验签与熔断解除"
    )
    parser.add_argument("--list", action="store_true", help="列出当前数据库中所有待核验的传闻事件及检索方案")
    parser.add_argument("--event-id", type=str, help="指定单一事件 ID 进行定向核验与传闻熔断解除")
    parser.add_argument("--batch", action="store_true", help="批量核验所有未决重大传闻事件")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，仅输出任务规格与检索预览，不落盘修改")
    parser.add_argument("--content", type=str, default=None, help="可选自定义公报正文内容")
    parser.add_argument("--refresh-dashboard", action="store_true", help="核验完成后自动刷新大屏监控看板")
    parser.add_argument("--verbose", action="store_true", help="打印详细调试日志")

    args = parser.parse_args()
    setup_logger(args.verbose)

    assistant = BrowserVerificationAssistant(auto_refresh_reports=args.refresh_dashboard)

    try:
        if args.list:
            handle_list(assistant)
        elif args.event_id:
            handle_verify_single(assistant, args.event_id, custom_content=args.content, dry_run=args.dry_run)
        elif args.batch:
            handle_batch(assistant, dry_run=args.dry_run)
        else:
            parser.print_help()
        return 0
    except Exception as e:
        print(f"\n❌ 执行失败: {e}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
