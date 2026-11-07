"""突发事件多业务分部 (SOTP) 穿透决策排查命令行工具 (Inspect SOTP Event Impact CLI).

严格遵循买方机构投资决策逻辑与自然语言汇报规范:
1. 严禁暴露复杂数学符号与生硬公式，全面转化为通俗商业语言与投资直觉;
2. 穿透企业各业务分部，展示具体哪个分部受损、哪些主营业务完全不受波及;
3. 动态呈现库存缓冲天数 (DIO) 吸收与成本转嫁能力冲销效果;
4. 严格响应传闻熔断门禁：对未经官方核实的社交快讯展示锁止警示与核验指引;
5. 提供企业级经营利润变动 (ΔEBIT) 与每股收益变动 (ΔEPS) 的综合研判。
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 将工程根目录纳入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.sotp_event_analyzer import SotpEventAnalyzer
from financial_core.engines.sotp_event_penetration_engine import (
    EnterpriseEventImpactResult,
    SegmentCausalImpact,
)
from scripts.test_support.sotp_fixtures import SYNTHETIC_PROFILES

# 投资动作商业自然语言映射表
ACTION_ZH_MAP = {
    "BUY_ON_OVERSOLD_NOISE": "🟢 恐慌错杀买入机会 (业务韧性强，全公司受损极微)",
    "MONITOR_INVENTORY_BUFFER": "🟡 密切监控库存抵御天数 (短期有缓冲，关注抢修进展)",
    "EXPEDITE_EXPANSION_OVERWEIGHT": "🚀 结构性利好增配机会 (直接增厚关键分部利润)",
    "DOWNGRADE_AND_HEDGE": "🔴 利润实质承压，启动对冲保护 (核心分部受创且缺乏转嫁权)",
    "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER": "🛑 待核传闻熔断锁定中 (信源等级低，已阻断深度测算)",
}

# 16 大信息收集维度中文自然语言映射
CATEGORY_ZH_MAP = {
    "Geopolitical_CrossStrait": "地缘海峡博弈与实体清单",
    "State_Policy_Regulatory": "各州产业政策与公用负荷",
    "Physical_Plant_Disruption": "核心物理设施破坏与停产",
    "Supply_Chain_Chokepoint": "供应链咽喉要道绕航中断",
    "Labor_Strikes_Port_Railways": "码头铁路工会罢工",
    "Antitrust_Litigation": "反垄断诉讼与337专利纠纷",
    "Commodity_Physical_Squeeze": "实物大宗现货逼仓倒挂",
    "CentralBank_Liquidity_FX_Shock": "央行流动性与套息平仓冲击",
    "Energy_Grid_Blackout_Rationing": "能源电网跳闸与工业限电",
    "Cyber_Critical_Infrastructure": "要害工控网络瘫痪",
    "Biosecurity_Export_Embargo": "生物安全法案与原药查扣",
    "Critical_Minerals_Export_Permit": "战略矿产出口管制与配额",
    "Defense_Procurement_Authorization": "国防军工采购授权变动",
    "Climate_Catastrophe_Insurance": "极端气象与再保险巨灾理赔",
    "Maritime_Insurance_Sanctions": "海运保赔与制裁扣押",
    "Sovereign_Debt_Liquidity": "主权债务上限与国债流动性",
    "Other_Macro_Event": "宏观常规参考事件",
}


def format_impact_terminal_report(result: EnterpriseEventImpactResult, category_key: str = "") -> str:
    """以通俗商业语言格式化单家企业的 SOTP 穿透结果."""
    lines = []
    cat_zh = CATEGORY_ZH_MAP.get(category_key, category_key or "未分类突发事件")
    action_zh = ACTION_ZH_MAP.get(result.recommended_action, result.recommended_action)

    lines.append("=" * 78)
    lines.append(f"【标的因果穿透简报】：{result.company_name} ({result.ticker})")
    lines.append("=" * 78)
    lines.append(f"关联突发事件 : [{result.severity_level}] {result.event_title}")
    lines.append(f"所属业务维度 : {cat_zh}")
    lines.append(f"买方决策研判 : {action_zh}")
    lines.append("-" * 78)

    # 1. 传闻熔断特殊处理
    if result.recommended_action == "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER":
        lines.append("【🛑 传闻熔断保护机制已激活】")
        lines.append(f"研判评述 : {result.focal_summary}")
        lines.append("")
        lines.append("买方风控提示 :")
        lines.append("  当前事件信源评级为待核传闻 (Tier 4)，买方多业务分部 (SOTP) 引擎已坚决阻断")
        lines.append("  任何利润折让测算与调仓信号，防范社交网络快讯噪音误导投资组合。")
        lines.append("处置指引 :")
        lines.append(f"  请使用 `python scripts/confirm_event_verification.py --event-id {result.event_id} --evidence <公报路径>`")
        lines.append("  导入官方监管公报并完成 SHA-256 验签后，系统将自动解除熔断并输出全分部测算。")
        lines.append("=" * 78)
        return "\n".join(lines)

    # 2. 正常穿透结果
    is_positive = result.total_operating_income_impact > 0
    ebit_sign = "+" if is_positive else ""
    lines.append("【企业级财务损益加总】:")
    lines.append(f"  全公司营业利润净影响 (ΔEBIT) : {ebit_sign}{result.total_operating_income_impact:,.1f} 百万美元 ({ebit_sign}{result.ebit_impact_percentage * 100:.2f}%)")
    lines.append(f"  摊薄每股净利润影响 (ΔEPS)    : {ebit_sign}{result.eps_impact:.3f} 美元/股 (已扣除企业所得税)")
    lines.append(f"  DCF 估值靶心中枢折让幅度    : {result.valuation_target_discount_pct * 100:+.2f}%")
    lines.append(f"  情景决策信号代码            : {result.scenario_signal}")
    lines.append("")

    # 3. 业务分部抗压与韧性拆解
    total_segs = len(result.segment_impacts)
    immune_segs = [s for s in result.segment_impacts if s.exposure_score < 0.10]
    hit_segs = [s for s in result.segment_impacts if s.exposure_score >= 0.10]

    lines.append(f"【多业务分部 (SOTP) 穿透拆解】 (共 {total_segs} 个主营分部，其中 {len(immune_segs)} 个完全未受波及):")
    lines.append("-" * 78)
    lines.append(f"{'分部名称':<16} | {'暴露度':<8} | {'库存缓冲吸收':<12} | {'净成本冲击':<10} | {'营业利润变动':<14}")
    lines.append("-" * 78)

    for seg in result.segment_impacts:
        exp_str = f"{seg.exposure_score * 100:.0f}%"
        dio_str = f"吸收 {seg.inventory_absorption_factor * 100:.0f}%" if seg.exposure_score > 0 else "无暴露"
        shock_str = f"{seg.net_cost_shock_pct * 100:+.1f}%" if seg.exposure_score > 0 else "-"
        ebit_str = f"{seg.operating_income_impact:+,.1f} M$" if seg.exposure_score > 0 else "0.0 M$ (完全独立)"
        lines.append(f"{seg.segment_name:<16} | {exp_str:<8} | {dio_str:<12} | {shock_str:<10} | {ebit_str:<14}")
        if seg.exposure_score > 0:
            lines.append(f"  └─ 因果推演: {seg.rationale}")

    lines.append("-" * 78)
    lines.append("【买方核心逻辑评述】:")
    lines.append(f"  {result.focal_summary}")
    lines.append("=" * 78)

    return "\n".join(lines)


def build_demo_sotp_analyzer(db_path: str = "data/ledger/event_radar.sqlite3") -> SotpEventAnalyzer:
    """在项目安全缓存目录内生成演示用 SOTP 档案与密码学指纹."""
    demo_dir = PROJECT_ROOT / ".cache" / "demo_sotp"
    demo_dir.mkdir(parents=True, exist_ok=True)
    source = demo_dir / "filing.synthetic.txt"
    source.write_text("SYNTHETIC DEMO INPUT ONLY\n" + json.dumps(SYNTHETIC_PROFILES), encoding="utf-8")
    ref = {
        "source_path": f".cache/demo_sotp/{source.name}",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "locator": "synthetic demo fields",
    }
    profiles = {}
    for ticker, old in SYNTHETIC_PROFILES.items():
        facts = {
            key: old[key]
            for key in (
                "company_name",
                "fiscal_year",
                "total_revenue",
                "total_operating_income",
                "effective_tax_rate",
                "diluted_shares",
            )
        }
        facts.update(
            financial_unit="usd_million",
            shares_unit="million_shares",
            unallocated_operating_income=old["total_operating_income"]
            - sum(s["operating_income"] for s in old["segments"]),
        )
        facts["segments"] = [
            {key: segment[key] for key in ("segment_id", "name_zh", "name_en", "revenue", "operating_income")}
            for segment in old["segments"]
        ]
        fields = [
            "total_revenue",
            "total_operating_income",
            "effective_tax_rate",
            "diluted_shares",
            "unallocated_operating_income",
        ]
        fields += [
            f"segments.{segment['segment_id']}.{name}"
            for segment in old["segments"]
            for name in ("revenue", "operating_income")
        ]
        profiles[ticker] = {
            "data_origin": "synthetic",
            "facts": facts,
            "fact_evidence": {key: dict(ref) for key in fields},
            "assumptions": {
                "assumption_id": "synthetic-scenario-v1",
                "rationale": "买方演示场景基准",
                "calibration_status": "uncalibrated_scenario",
                "segments": {
                    segment["segment_id"]: {
                        key: segment[key]
                        for key in ("cost_pass_through_power", "inventory_buffer_days", "relevant_keywords")
                    }
                    for segment in old["segments"]
                },
            },
            "quote": {
                "price": old["current_share_price"],
                "timestamp": "2026-10-16T14:00:00Z",
                "market": "US",
                "currency": "USD",
                "source": dict(ref),
            },
        }

    registry = demo_dir / "profiles.json"
    registry.write_text(json.dumps({"schema_version": "1.0.0", "profiles": profiles}), encoding="utf-8")

    return SotpEventAnalyzer(
        root_dir=PROJECT_ROOT,
        profiles_path=".cache/demo_sotp/profiles.json",
        db_path=db_path,
        allow_synthetic=True,
        current_time_iso="2026-10-16T14:05:00Z",
    )


def run_inspect_cli(
    event_id: Optional[str] = None,
    ticker: Optional[str] = None,
    all_major: bool = False,
    only_confirmed: bool = False,
    as_json: bool = False,
    demo: bool = False,
    profiles_path: Optional[str] = None,
    allow_synthetic: bool = False,
    db_path: str = "data/ledger/event_radar.sqlite3",
) -> int:
    """CLI 执行主入口."""
    if demo:
        analyzer = build_demo_sotp_analyzer(db_path=db_path)
    else:
        analyzer = SotpEventAnalyzer(
            db_path=db_path,
            profiles_path=profiles_path or "config/sotp_profiles.json",
            allow_synthetic=allow_synthetic,
        )

    if len(analyzer.profiles) == 0:
        print("\n" + "=" * 78)
        print("【买方研究提示】：当前尚未加载公司多业务分部 (SOTP) 财报底账")
        print("=" * 78)
        print("原因说明 : 系统当前严格遵循“暂时不要拉取公司数据”硬约束，")
        print("          config/sotp_profiles.json 保持纯净未预置未核实公司财报。")
        print("演示指引 : 若需体验多业务分部穿透研判（覆盖微软云计算与台积电晶圆代工），")
        print("          请追加 `--demo` 参数运行演示，例如:")
        print("          python scripts/inspect_sotp_event_impact.py --all-major --demo")
        print("=" * 78 + "\n")
        return 0

    target_tickers = [ticker.upper()] if ticker else None

    # 模式 A: 扫描所有重大事件
    if all_major or not event_id:
        results_by_event = analyzer.analyze_all_verified_major_events(
            target_tickers=target_tickers,
            only_confirmed_facts=only_confirmed,
        )
        if not results_by_event:
            print("未在数据库中检索到符合条件的重大突发事件。")
            return 0

        if as_json:
            serializable = {
                evt_id: [r.to_dict() for r in r_list]
                for evt_id, r_list in results_by_event.items()
            }
            print(json.dumps(serializable, ensure_ascii=False, indent=2))
            return 0

        # 查询事件元数据用于展示分类
        all_raw_events = {e["event_id"]: e for e in analyzer.db_mgr.query_events()}

        print(f"\n>>> 成功扫描到 {len(results_by_event)} 起重大突发事件，开始输出买方分部穿透结果:\n")
        for evt_id, r_list in results_by_event.items():
            raw_evt = all_raw_events.get(evt_id, {})
            cat_key = raw_evt.get("category", "")
            for res in r_list:
                print(format_impact_terminal_report(res, category_key=cat_key))
                print()
        return 0

    # 模式 B: 指定特定事件 ID 进行深度排查
    try:
        results = analyzer.analyze_stored_event_by_id(event_id, target_tickers=target_tickers)
    except KeyError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
        return 0

    raw_event = analyzer.db_mgr.get_event_by_id(event_id)
    cat_key = raw_event.get("category", "") if raw_event else ""

    print(f"\n>>> 正在呈现事件 [{event_id}] 的企业多业务分部 (SOTP) 因果穿透研判:\n")
    for res in results:
        print(format_impact_terminal_report(res, category_key=cat_key))
        print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="突发事件多业务分部 (SOTP) 穿透决策排查工具 (支持传闻熔断与分部损益加总)",
    )
    parser.add_argument(
        "--event-id",
        type=str,
        default=None,
        help="待穿透分析的突发事件唯一编号 (如 EVT_CALIF_GRID_01)",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="目标公司股票代码 (如 MSFT, TSM)，默认分析所有已登记标的",
    )
    parser.add_argument(
        "--all-major",
        action="store_true",
        help="自动扫描数据库中所有 P0/P1 或已核实的重大事件",
    )
    parser.add_argument(
        "--only-confirmed",
        action="store_true",
        help="仅分析已由官方公报核验解除熔断的真实事实 (排除待核传闻)",
    )
    parser.add_argument(
        "--demo",
        "--fixture",
        dest="demo",
        action="store_true",
        help="启用官方打样标的 (MSFT / TSM) 进行业务分部因果穿透演示",
    )
    parser.add_argument(
        "--profiles-path",
        type=str,
        default=None,
        help="自定义 SOTP 公司分部档案 JSON 路径",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="明确允许加载合成演示档案",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以机器可读的标准 JSON 格式输出穿透结果",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/ledger/event_radar.sqlite3",
        help="SQLite 事件账本相对路径",
    )

    args = parser.parse_args()
    ret_code = run_inspect_cli(
        event_id=args.event_id,
        ticker=args.ticker,
        all_major=args.all_major,
        only_confirmed=args.only_confirmed,
        as_json=args.json,
        demo=args.demo,
        profiles_path=args.profiles_path,
        allow_synthetic=args.allow_synthetic,
        db_path=args.db_path,
    )
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
