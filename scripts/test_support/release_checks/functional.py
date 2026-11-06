"""发布契约探针 functional。"""

from collections import Counter
import re
from unittest.mock import patch
from .common import check, dossier_sample, load, require, ROOT, run_cloud


@check("R14", "report", "P1", "scripts/build_institutional_workbook.py", "FT-06")
def documented_institutional_workbook_entry_exists(_):
    entry = ROOT / "scripts/build_institutional_workbook.py"
    return require(entry.is_file(), "SPEC-01 与 SPEC-02 声明的工作簿入口在仓库中缺失")


@check("R13", "report", "P0", "scripts/cloud_daily_pipeline.py", "FT-02")
def every_recommendation_is_checked(work):
    from copy import deepcopy
    from scripts.run_daily_briefing_and_deep_dossiers_pipeline import BRIEFING_DATA_US
    from .common import new_ledger
    data = deepcopy(BRIEFING_DATA_US)
    first, stale = data["recommended_stocks"][:2]
    first["current_price"] = "$100.00 [2026-10-16 16:00 EDT]"
    stale["current_price"] = "$100.00 [2000-01-03 10:00 EST]"
    data["recommended_stocks"] = [first, stale]
    ledger = new_ledger(work)
    try:
        run_cloud(work, "2026-10-16", ledger=ledger, briefing=data)
    except ValueError:
        pass
    prediction = ledger.get_prediction(f"PRED-20261016-US-{stale['ticker']}")
    reports = (work / "reports").glob("*_US_*.json")
    stale_published = any(stale["ticker"] == card["ticker"] for path in reports
                          for card in load(path)["recommended_stocks"])
    return require(prediction is None and not stale_published, "首张新鲜报价掩盖了第二张过期卡片")


@check("R12", "report", "P0", "scripts/cloud_daily_pipeline.py", "FT-06")
def untrusted_headline_is_escaped(_):
    from copy import deepcopy
    from scripts.cloud_daily_pipeline import render_briefing_html
    from scripts.run_daily_briefing_and_deep_dossiers_pipeline import BRIEFING_DATA_US
    report = deepcopy(BRIEFING_DATA_US)
    marker = "<img src=x onerror=fixture()>"
    report["market_moving_news"][0]["headline"] = marker
    html = render_briefing_html(report)
    return require(marker not in html and "fixture()" in html, "不可信新闻 HTML 原样进入渲染，或文本被静默丢弃")


@check("R11", "report", "P0", "financial_reporting/excel_dossier_builder.py", "FT-04")
def company_dossier_workbook_roundtrip(work):
    from contextlib import closing
    from jsonschema import validate
    from openpyxl import load_workbook
    from financial_reporting.excel_dossier_builder import ExcelDossierBuilder
    schema = load(ROOT / "schemas/deep_dossier.schema.json")
    for market in ("US", "JP"):
        dossier = dossier_sample(market)
        validate(dossier, schema)
        require(dossier["overview"]["market"] == market and dossier["evidence_manifest"]
                and dossier["financial_statements"]["total_assets"] == 1000, f"{market} 合成底稿或证据缺失")
        path = ExcelDossierBuilder(work).build_workbook(dossier)
        with closing(load_workbook(path, read_only=True)) as workbook:
            require([name[:2] for name in workbook.sheetnames] == ["00", "01", "02", "03", "04"],
                    f"{market} 实际工作簿缺失五类页签")
            memo_cells = [str(cell) for row in workbook.worksheets[0].values for cell in row if cell is not None]
            audit_cells = {str(cell) for row in workbook.worksheets[4].values for cell in row if cell is not None}
            ticker = dossier["overview"]["ticker"]
            require(any(re.search(rf"\b{re.escape(ticker)}\b", cell) for cell in memo_cells), f"{market} 备忘录缺少标的")
            require(dossier["evidence_manifest"][0]["sha256"] in audit_cells, f"{market} 审计页未保留证据哈希")
    return "美日合成档案通过 Schema，实际五页工作簿保留标的及证据哈希"


@check("X04", "multi_asset", "P1", "financial_reporting/etf_penetration.py / commodity_gold_framework.py", "FT-10")
def asset_specific_dossier_contracts(_):
    from jsonschema import Draft7Validator
    from financial_reporting.commodity_gold_framework import CommodityGoldFramework, GoldMacroContext
    from financial_reporting.etf_penetration import ETFPenetrationEngine
    reports = (
        ("etf_dossier", ETFPenetrationEngine.analyze_etf_dossier("SPY")),
        ("commodity_gold", CommodityGoldFramework.evaluate_gold_macro_valuation(GoldMacroContext())),
    )
    errors = []
    for name, report in reports:
        validator = Draft7Validator(load(ROOT / f"schemas/{name}.schema.json"))
        errors.extend(f"{name} {error.json_path} {error.message}" for error in validator.iter_errors(report))
    return require(not errors, "多资产档案违约 " + "；".join(errors[:5]))


@check("R09", "report", "P0", "financial_reporting/ai_dossier_synthesizer.py", "FT-05")
def unsupported_rating_cannot_be_published(_):
    from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
    try:
        result = AIDossierSynthesizer.synthesize_dossier(
            "AUDIT", "US", "隔离样本", "semiconductors", "半导体",
            market_quote={"current_price": 100, "fair_anchor": 70, "freshness_status": "【阻断】"},
            ai_analysis={"rating": "买入"}, report_date="2026-10-16",
        )
    except ValueError:
        return "档案明确拒绝缺证据或阻断行情的研判"
    decision = result["decision_summary"]
    return require("买入" not in str(decision.get("rating")), "行情阻断及负安全边际下仍生成买入评级")


@check("R08", "report", "P0", "scripts/cloud_daily_pipeline.py", "FT-01")
def daily_cards_preserve_market_and_scenarios(work):
    receipt, output, _ = run_cloud(work, "2026-10-16")
    documents = list(output.glob("*_US_*.json"))
    require(receipt["status"] == "SUCCESS" and len(documents) == 1, "有效报告样本未生成单份美股日报")
    report = load(documents[0])
    require(report["header"]["market"] == "US", "日报落盘市场与任务不一致")
    cards = report["recommended_stocks"]
    required = {"pessimistic_deduction", "neutral_deduction", "optimistic_deduction", "margin_of_safety_trigger"}
    return require(cards and all(required <= card.keys() for card in cards), "独立推荐卡缺少三态情景或买点")


@check("G03", "governance", "P0", "scripts/validate_research.py", "FT-08")
def research_rejects_reordered_steps(_):
    from scripts.validate_research import ValidationError, validate
    sample = load(ROOT / "examples/completed.synthetic.json")
    validate(sample)
    sample["steps"].reverse()
    try:
        validate(sample)
    except ValidationError:
        return "完整研究通过，六步倒序被拒绝"
    raise AssertionError("研究步骤倒序仍通过")


@check("B07", "batch", "P1", "financial_reporting/data_collection_gateway.py", "FT-12")
def replenishment_is_idempotent(work):
    from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway
    path = work / "pending.json"
    targets = [{"ticker": "AUDIT", "market": market} for market in ("US", "JP")]
    for _ in range(2):
        UnifiedDataCollectionGateway.generate_replenishment_gap_manifest(targets, output_path=path)
    data = load(path)
    tasks = data["tasks"]
    return require(data["total_pending_companies"] == len(tasks) == 2
                   and {task["market"] for task in tasks} == {"US", "JP"}
                   and all(task["required_line_items"] for task in tasks),
                   "重复补数未按市场去重，或待补工作单缺少所需科目")


@check("R02", "report", "P0", "scripts/cloud_daily_pipeline.py", 'FT-03')
def daily_dry_run(work):
    _, output, ledger = run_cloud(work, "2026-10-16", dry_run=True)
    files = list(output.glob("*.*"))
    count = ledger.get_stats()["total_predictions"]
    return require(not files and not count, f"试运行写出 {len(files)} 个文件和 {count} 条预测")



@check("R04", "report", "P1", "financial_reporting/daily_briefing_engine.py", 'FT-07')
def committee_entrypoint(_):
    from financial_reporting.daily_briefing_engine import DailyBriefingEngine
    from scripts.run_daily_briefing_and_deep_dossiers_pipeline import BRIEFING_DATA_US
    try:
        result = DailyBriefingEngine(gdrive_exe="unused", edge_exe="unused").render_committee_memo_markdown(BRIEFING_DATA_US)
    except ModuleNotFoundError as error:
        raise AssertionError(f"投委会简报运行时依赖缺失 {error.name}") from error
    return require(isinstance(result, str) and bool(result.strip()), "投委会简报未生成 Markdown")



@check("R06", "report", "P1", "scripts/cloud_daily_pipeline.py", 'FT-02')
def daily_schema_requires_valid_date(_):
    from jsonschema import ValidationError
    from scripts.cloud_daily_pipeline import validate_briefing_schema
    from scripts.run_daily_briefing_and_deep_dossiers_pipeline import BRIEFING_DATA_US
    validate_briefing_schema(BRIEFING_DATA_US)
    invalid = dict(BRIEFING_DATA_US, header=dict(BRIEFING_DATA_US["header"], report_date="../../escape"))
    try:
        validate_briefing_schema(invalid)
    except ValidationError:
        return "日报契约拒绝非法报告日期"
    raise AssertionError("日报契约接受路径片段作为报告日期")



@check("R07", "report", "P1", "scripts/cloud_daily_pipeline.py", 'FT-06')
def pdf_must_be_created_by_current_run(work):
    from subprocess import CompletedProcess
    from scripts import cloud_daily_pipeline
    html, pdf = work / "report.html", work / "report.pdf"
    html.write_text("<html>audit</html>", encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4\n" + b"older run" * 200)
    # 外部进程报告退出码 0，本次实际没有生成文件。
    with patch.object(cloud_daily_pipeline.subprocess, "run", return_value=CompletedProcess([], 0)):
        ok = cloud_daily_pipeline.compile_html_to_pdf(html, pdf, "unused")
    return require(not ok, "渲染器未生成新文件，旧 PDF 仍被记录为本次成功")



@check("B03", "batch", "P1", "data/pipeline_state/567_universe_progress.json", 'FT-09')
def progress_totals(_):
    state = load(ROOT / "data/pipeline_state/567_universe_progress.json")
    counts = Counter(row["status"] for row in state["tickers"].values())
    summary = state["summary"]
    consistent = (summary["total_targets"] == summary["completed_count"] + summary["failed_count"] + summary["pending_count"]
                  and summary["completed_count"] == counts["COMPLETED"] and summary["failed_count"] == counts["FAILED"])
    return require(consistent, f"进度摘要 {summary}，记录状态 {dict(counts)}")



@check("B04", "batch", "P1", "data/universe/universe_10k_manifest.json", 'FT-09')
def universe_identity_counts(_):
    folder = ROOT / "data/universe"
    expected = load(folder / "universe_10k_manifest.json")
    counts = {"US_SEC_EDGAR": len(load(folder / "sec_company_tickers.json")),
              "JP_JPX_TOKYO": len(load(folder / "jpx_company_tickers.json"))}
    detail = f"身份索引 {counts}，清单状态 {expected['status']}"
    return require(counts == expected["market_breakdown"] and sum(counts.values()) == expected["total_companies"],
                   detail, detail)



@check("C01", "cloud", "P1", ".github/workflows/daily_market_pipeline.yml", 'FT-11')
def workflow_interpolation(_):
    workflow = (ROOT / ".github/workflows/daily_market_pipeline.yml").read_text(encoding="utf-8")
    unsafe = [line.strip() for line in workflow.splitlines()
              if re.search(r"\$\{\{\s*inputs\.as_of\s*\}\}", line) and not re.match(r"\s*[A-Z_]+\s*:", line)]
    return require(not unsafe, f"自由文本 as_of 插入 shell 程序文本，共 {len(unsafe)} 处")



@check("C02", "cloud", "P1", ".github/workflows/daily_market_pipeline.yml", 'FT-11')
def workflow_schedule(_):
    workflow = (ROOT / ".github/workflows/daily_market_pipeline.yml").read_text(encoding="utf-8")
    entries = set(re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", workflow))
    hours = {entry.split()[1] for entry in entries}
    minutes = {entry.split()[0] for entry in entries}
    return require({"22", "7"} <= hours and minutes == {"0"} and "github.event.schedule" in workflow,
                   f"定时触发 {sorted(entries)}，按触发区分市场={('github.event.schedule' in workflow)}，要求 JST 07:00 / 16:00")
