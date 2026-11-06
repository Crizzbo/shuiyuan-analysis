"""一键执行水源股票系统性投研分析主管道 (Run Systemic Equity Analysis).

贯彻 2026-10-15 工程整改规范：
1. 彻底拔除“默认通用假数据模板”暗门，缺少底账时刚性阻断；
2. 正式模式禁止未经声明运行演示样本，必须显式传入 --allow-demo；
3. 支持通过 --input-json 载入经核准的官方三表底账；
4. 严格通过 Stage 1 平账门禁与时效核验。

用法:
    python scripts/run_systemic_equity_analysis.py --ticker RXRX --allow-demo
    python scripts/run_systemic_equity_analysis.py --ticker 000858 --allow-demo
    python scripts/run_systemic_equity_analysis.py --input-json path/to/official_inputs.json
"""

import argparse
from pathlib import Path
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.api import FinancialAnalysisSystem
from financial_core.contracts import AnalysisMode
from financial_core.pipeline import SystemicCompanyInput
from skill_gateway.gateway import default_gateway


def get_preset_company_input(ticker: str, allow_demo: bool = False) -> SystemicCompanyInput:
    """提供经过法证核验的基准测试样本底账 (严格受控)."""
    t = ticker.upper().strip()
    if not allow_demo:
        raise PermissionError(
            f"[安全准入阻断] 标的 '{t}' 属于测试演示样本。"
            f"依据工程整改 Task 02 规范，正式模式严禁静默加载预置样本伪装真实投研。"
            f"若用于测试或演示，请显式传入 --allow-demo 参数。"
        )

    fin_sys = FinancialAnalysisSystem()
    inp = fin_sys.get_preset_sample_input(t)
    if inp is not None:
        return inp

    # 刚性阻断：严禁制造假数据
    raise ValueError(
        f"[安全阻断] 标的 '{t}' 暂无经官方审计核准的三表底账。"
        f"系统已彻底废除‘默认通用假数据模板’，拒绝捏造假数据进行虚假估值。"
        f"请通过 --input-json 传入经核实的官方财报底稿。"
    )


def load_input_from_json(json_path: Path) -> SystemicCompanyInput:
    """从外部结构化 JSON 文件加载官方底账."""
    if not json_path.exists():
        raise FileNotFoundError(f"底账文件不存在: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    # 支持从 inputs.json 或标准 dict 反序列化
    return SystemicCompanyInput(
        ticker=data["ticker"],
        company_name=data.get("company_name", data["ticker"]),
        sector=data.get("sector", "General"),
        quote_timestamp=data.get("quote_timestamp", "2026-10-14 16:00:00 EDT"),
        market_session=data.get("market_session", "closed"),
        current_price=float(data["current_price"]),
        baseline_reference_price=float(data.get("baseline_reference_price", data["current_price"])),
        reported_cash=float(data.get("reported_cash", 0.0)),
        restricted_cash=float(data.get("restricted_cash", 0.0)),
        debt_covenant_min_cash=float(data.get("debt_covenant_min_cash", 0.0)),
        total_debt=float(data.get("total_debt", 0.0)),
        total_assets=float(data["total_assets"]),
        total_liabilities=float(data["total_liabilities"]),
        stockholders_equity=float(data["stockholders_equity"]),
        reported_operating_cash_flow=float(data.get("reported_operating_cash_flow", 0.0)),
        reported_capex=float(data.get("reported_capex", 0.0)),
        maintenance_capex_ratio=float(data.get("maintenance_capex_ratio", 0.75)),
        stock_based_compensation=float(data.get("stock_based_compensation", 0.0)),
        reported_revenue=float(data.get("reported_revenue", 0.0)),
        reported_operating_income=float(data.get("reported_operating_income", 0.0)),
        reported_net_income=float(data.get("reported_net_income", 0.0)),
        shares_outstanding=float(data["shares_outstanding"]),
        pipeline_rnpv_value=float(data.get("pipeline_rnpv_value", 0.0)),
        us_10y_yield=float(data.get("us_10y_yield", 0.045)),
        usdjpy_rate=float(data.get("usdjpy_rate", 150.0)),
        vix_index=float(data.get("vix_index", 20.0)),
        usdjpy_daily_change_pct=float(data.get("usdjpy_daily_change_pct", 0.0)),
        company_beta=float(data.get("company_beta", 1.0)),
        short_interest_shares=float(data.get("short_interest_shares", 0.0)),
        free_float_shares=float(data.get("free_float_shares", data["shares_outstanding"])),
        cost_to_borrow_pct=float(data.get("cost_to_borrow_pct", 1.0)),
        average_volume_30d=float(data.get("average_volume_30d", 1_000_000.0)),
        option_target_strike=float(data.get("option_target_strike", 0.0)),
        option_expiry_days=int(data.get("option_expiry_days", 30)),
        option_implied_vol=float(data.get("option_implied_vol", 0.3)),
    )


def main():
    parser = argparse.ArgumentParser(description="水源股票系统性投研分析主管道执行器 (严格准入安全版)")
    parser.add_argument("--ticker", type=str, default="RXRX", help="股票代码 (如 RXRX 或 000858)")
    parser.add_argument("--allow-demo", action="store_true", help="显式允许加载经核验的基准测试样本")
    parser.add_argument("--input-json", type=str, default=None, help="外部官方三表底账 JSON 文件路径")
    parser.add_argument("--ai-journal", type=str, default=None, help="可选的 AI 定性投研日记")
    args = parser.parse_args()

    print(f"[管线启动] 启动系统性投研分析主管道: 目标标的 {args.ticker.upper()}")

    # 1. 获取输入底账
    if args.input_json:
        inp = load_input_from_json(Path(args.input_json))
        allow_demo = False
    else:
        try:
            inp = get_preset_company_input(args.ticker, allow_demo=args.allow_demo)
            allow_demo = args.allow_demo
        except Exception as e:
            print(f"\n{str(e)}")
            sys.exit(1)

    # 2. 调度网关执行分析与决策卡片生成
    res = default_gateway.handle_equity_analysis(
        ticker=inp.ticker,
        company_input=inp,
        mode="full_systemic",
        allow_demo=allow_demo,
        ai_journal=args.ai_journal,
    )

    print("\n" + res["markdown_card"])

    # 3. 持久化分析结果
    if res["status"] == "success":
        out_dir = ROOT / "reports" / "systemic_audits"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{res['ticker']}_systemic_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(res["result_data"], f, ensure_ascii=False, indent=2)
        print(f"\n[结果持久化] 全息系统性分析结果已持久化: {out_file.relative_to(ROOT)}\n")
    else:
        print(f"\n[执行阻断] 执行阻断: {res.get('message', '未知错误')}\n")


if __name__ == "__main__":
    main()
