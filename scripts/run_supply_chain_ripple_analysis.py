"""多标的产业链上下游涟漪效应传导分析终端 CLI (Supply Chain Ripple Analysis CLI).

严格遵循 Google Python 编程风格指南与去工程符号化买方准则:
1. 提供买方研究员一键穿透突发事件在整条产业链 (上游 ➔ 中枢 ➔ 下游) 涟漪受损的实战工具;
2. 支持按事件 ID 穿透 (--event-id)、批量重大事件全景推演 (--batch) 与拓扑字典查阅 (--list-topologies);
3. 动态展示各核心节点的存货周转天数 (DIO) 缓冲期、定价转嫁权 (PT) 与营业利润预估损益 (ΔEBIT);
4. 输出去工程符号化、自然商业语义的买方战术决策直觉。
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.supply_chain_ripple_analyzer import SupplyChainRippleAnalyzer
from financial_core.engines.supply_chain_ripple_engine import SupplyChainRippleReport


def setup_logger(verbose: bool = False) -> None:
    """初始化控制台日志配置."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_banner() -> None:
    """打印买方机构级产业链涟漪效应终端横幅."""
    print("=" * 86)
    print("【买方全球核心产业链 · 突发物理事件上下游涟漪效应传导矩阵】")
    print("=" * 86)


def handle_list_topologies(analyzer: SupplyChainRippleAnalyzer) -> None:
    """展示当前已注册的全量产业链拓扑图谱."""
    print_banner()
    topologies = analyzer.list_topologies()
    print(f"\n📊 当前底层知识库已注册 {len(topologies)} 条全球核心战略产业链拓扑模型:\n")

    for idx, t in enumerate(topologies, 1):
        print(f"[{idx}] 产业链标识 : {t['topology_id']}")
        print(f"    • 产业商业名称 : {t['name_zh']}")
        print(f"    • 业务归属维度 : {t['industry_category']}")
        print(f"    • 核心中枢标的 : {t['core_hub']} ({t['core_hub_ticker']})")
        print(f"    • 节点覆盖规模 : 上游 {t['upstream_count']} 个节点 | 下游 {t['downstream_count']} 个客户群")
        print(f"    • 传导机理简述 : {t['description']}")
        print("-" * 86)


def format_node_row(role: str, node: dict) -> str:
    """格式化单一产业链节点指标行."""
    ticker_str = f"({node['ticker']})" if node.get("ticker") else "(非上市原料/机构)"
    name_str = f"{node['name_zh']} {ticker_str}"
    dio_str = f"{node['buffer_dio_days']:.0f}天"
    pt_str = f"{node['pricing_power_pt']*100:.0f}%"
    loss_str = f"{node['ebit_impact_pct']:+.2f}%"
    return f"{role:<8} | {name_str:<32} | DIO: {dio_str:<5} | 转嫁权: {pt_str:<4} | 利润冲击: {loss_str:<7} | 【{node['vulnerability_level']}】"


def print_ripple_report(report: SupplyChainRippleReport) -> None:
    """以买方自然商业语言与结构化拓扑呈现涟漪传导研判报告."""
    data = report.to_dict()
    print("=" * 86)
    print(f"🔗 产业链图谱 : 【{data['topology_name_zh']}】 ({data['topology_id']})")
    print(f"⚡ 突发物理事件 : [{data['event_id']}] {data['event_title']}")
    print(f"⏱️ 预估影响天数 : {data['disruption_duration_days']:.0f} 天 | 全链脆弱度: 【{data['chain_vulnerability_level']}】")
    print("=" * 86)

    print("\n【产业链上下游拓扑因果受损矩阵】")
    print("-" * 86)
    print(f"{'生态位':<8} | {'实体名称与代码':<32} | {'存货缓冲':<10} | {'定价转嫁':<9} | {'利润损益':<11} | 评级")
    print("-" * 86)

    # 1. 上游
    for u in data["upstream_impacts"]:
        print(format_node_row("上游供应", u))

    # 2. 核心中枢
    print("-" * 86)
    print(format_node_row("核心中枢", data["core_hub_impact"]))
    print("-" * 86)

    # 3. 下游
    for d in data["downstream_impacts"]:
        print(format_node_row("下游大客户", d))

    print("-" * 86)
    print("\n【买方战术决策直觉与因果推演通报】")
    print(f"• 核心中枢研判 : {data['core_hub_impact']['buyer_verdict_zh']}")
    print(f"  推演理由 : {data['core_hub_impact']['rationale_zh']}")

    for d in data["downstream_impacts"]:
        print(f"• 下游 {d['name_zh']} ({d['ticker']}) : {d['buyer_verdict_zh']}")
        print(f"  推演理由 : {d['rationale_zh']}")

    print("\n" + "=" * 86 + "\n")


def handle_event_ripple(
    analyzer: SupplyChainRippleAnalyzer,
    event_id: str,
    topology_id: Optional[str] = None,
    disruption_days: Optional[float] = None,
) -> None:
    """分析单一指定事件的产业链涟漪效应."""
    print_banner()
    print(f"🎯 正在为突发事件 [{event_id}] 执行产业链全息因果穿透推演...\n")
    report = analyzer.analyze_event_ripple(
        event_id=event_id,
        topology_id=topology_id,
        disruption_days=disruption_days,
    )
    print_ripple_report(report)


def handle_batch(analyzer: SupplyChainRippleAnalyzer) -> None:
    """批量推演数据库中所有重大事件的产业链涟漪传导."""
    print_banner()
    print("🚀 启动全盘重大突发事件产业链涟漪效应批量排查...\n")
    reports = analyzer.analyze_all_major_events()

    if not reports:
        print("🟢 当前数据库中暂无待分析的 P0/P1 重大事件。")
        return

    print(f"📋 共对 {len(reports)} 项重大事件完成全产业链因果穿透:\n")
    for rep in reports:
        print_ripple_report(rep)


def main() -> int:
    """终端主执行入口."""
    parser = argparse.ArgumentParser(
        description="买方产业链上下游涟漪效应传导分析工具: 穿透突发事件在产业链各巨头的非对称受损"
    )
    parser.add_argument("--list-topologies", action="store_true", help="列出当前注册的全量战略产业链拓扑模型")
    parser.add_argument("--event-id", type=str, help="指定突发事件识别编号进行穿透推演 (如 EVT_E095B7243F76)")
    parser.add_argument("--topology", type=str, default=None, help="可选显式强制指定的产业链拓扑标识")
    parser.add_argument("--disruption-days", type=float, default=None, help="自定义事件物理断供天数 (默认为60天)")
    parser.add_argument("--batch", action="store_true", help="批量分析全量重大突发事件的产业链传导")
    parser.add_argument("--verbose", action="store_true", help="打印详细调试日志")

    args = parser.parse_args()
    setup_logger(args.verbose)

    analyzer = SupplyChainRippleAnalyzer()

    try:
        if args.list_topologies:
            handle_list_topologies(analyzer)
        elif args.event_id:
            handle_event_ripple(
                analyzer,
                args.event_id,
                topology_id=args.topology,
                disruption_days=args.disruption_days,
            )
        elif args.batch:
            handle_batch(analyzer)
        else:
            parser.print_help()
        return 0
    except Exception as e:
        print(f"\n❌ 推演执行异常: {e}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
