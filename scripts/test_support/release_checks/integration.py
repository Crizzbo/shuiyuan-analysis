"""发布契约探针 integration。"""

from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from subprocess import CompletedProcess
from unittest.mock import patch
from .common import check, dossier_sample, load, new_ledger, prediction, require, ROOT, run_cloud


def batch_transports(work, upload_exit=0):
    """只模拟外部渲染器和 Drive，保留批次真实文件及收据。"""
    from scripts import run_batch_dossier_pipeline as batch
    order = []

    def transport(command, **_):
        if command[0] == "fixture-edge":
            destination = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--print-to-pdf=")))
            destination.write_bytes(b"%PDF-1.4\nfixture")
            order.append(("render", destination.name))
            return CompletedProcess(command, 0, "", "")
        order.append(("upload", Path(command[-1]).name))
        return CompletedProcess(command, upload_exit, '{"id":"fixture-file"}', "")

    with patch.object(batch, "ROOT", work), patch.object(batch.subprocess, "run", side_effect=transport):
        batch.process_single_batch("fixture", [dossier_sample("US"), dossier_sample("JP")],
                                   edge_exe="fixture-edge", gdrive_exe="fixture-drive")
    receipt = load(work / "data/audits/unified_batch_receipts/fixture_receipt.json")
    return order, receipt["receipts"]


@check("I05", "cloud", "P1", "scripts/run_batch_dossier_pipeline.py", "IT-07")
def ready_dossier_uploads_before_next_render(work):
    order, receipts = batch_transports(work)
    expected = [("render", receipts[0]["file_name"]), ("upload", receipts[0]["file_name"]),
                ("render", receipts[1]["file_name"]), ("upload", receipts[1]["file_name"])]
    return require(order == expected and all(row["status"] == "UPLOADED" for row in receipts),
                   f"渲染和上传调用顺序或收据不符合逐件流水线 {order}")


@check("I06", "cloud", "P0", "scripts/run_batch_dossier_pipeline.py", "IT-07", "IT-12")
def upload_failure_with_file_id_is_not_success(work):
    _, receipts = batch_transports(work, upload_exit=1)
    return require(all(row["status"] != "UPLOADED" and not row["cloud_id"] for row in receipts),
                   f"上传命令失败仍被记录为成功 {[row['status'] for row in receipts]}")


@check("I07", "batch", "P0", "scripts/sync_phase2_expansion.py", "IT-09")
def expansion_cannot_complete_without_phase1_eligibility(work):
    from scripts import sync_phase2_expansion as phase2
    universe = work / "data/universe/phase2_expansion_universe.json"
    universe.parent.mkdir(parents=True)
    universe.write_text('{"status":"PENDING","categories":{}}', encoding="utf-8")
    receipts = work / "data/audits/drive-deep-analysis-20261012"
    receipts.mkdir(parents=True)
    try:
        with patch.object(phase2, "ROOT", work):
            phase2.main()
    except (ValueError, FileNotFoundError):
        pass
    return require(load(universe)["status"] != "COMPLETED", "没有首期合格证据且目标数为零，扩展仍标记完成")


@check("I08", "governance", "P0", "scripts/import_browser_source.py", "IT-10")
def browser_download_receipt_roundtrip(work):
    from data_ingestion.core import Archive
    from scripts import import_browser_source as importer
    raw = b"%PDF-1.4\nsynthetic receipt fixture"
    download = work / "filing.pdf"
    download.write_bytes(raw)
    receipt = load(ROOT / "examples/browser-sony-pdf-receipt.json")
    receipt.update(id="fixture-browser", verification_notes="仅测试归档与证据传递")
    target = work / "receipts"
    with closing(Archive((work / "archive").relative_to(ROOT).as_posix())) as archive, \
         patch.object(importer, "project_path", return_value=target):
        imported = importer.import_document(download, receipt, archive)
        repeated = importer.import_document(download, receipt, archive)
        for change in ({"document_url": "https://example.invalid/forged.pdf"}, {"publication_precision": "instant"}):
            count = len(list(target.glob("*.json")))
            try:
                importer.import_document(download, receipt | change, archive)
            except ValueError:
                require(len(list(target.glob("*.json"))) == count, "坏回执仍写出结果")
            else:
                raise AssertionError(f"错误浏览器回执被接受 {change}")
    require(imported["status"] == "archived" and imported["sha256"] == repeated["sha256"] == sha256(raw).hexdigest(),
            "原文字节与导入/重复导入回执的哈希不一致")
    archived = load(ROOT / imported["receipt_path"])
    return require(archived["artifact"]["quality_status"] == "unreviewed", "归档原文被直接标为已审核事实")


@check("C03", "cloud", "P1", ".github/workflows/daily_market_pipeline.yml", "IT-08")
def workflow_artifact_scope(_):
    workflow = (ROOT / ".github/workflows/daily_market_pipeline.yml").read_text(encoding="utf-8")
    broad_globs = re.findall(r"reports/daily_briefings/\*\*/\*\.\w+", workflow)
    return require(not broad_globs, f"工作流会归档整个历史日报目录 {broad_globs}，未按本次交付清单归档")


@check("C04", "cloud", "P1", "financial_reporting/daily_briefing_engine.py", "IT-12")
def missing_remote_receipt_is_not_success(work):
    from financial_reporting.daily_briefing_engine import DailyBriefingEngine
    executable = work / "gdrive-fixture"
    executable.touch()
    report = work / "report.pdf"
    report.write_bytes(b"%PDF-1.4\n")
    engine = DailyBriefingEngine(gdrive_exe=str(executable), edge_exe="unused")
    replies = [CompletedProcess([], 1, "", "rate limited"), CompletedProcess([], 0, "{}"),
               CompletedProcess([], 0, '{"id": "fixture-receipt"}')]
    with patch("financial_reporting.daily_briefing_engine.subprocess.run", side_effect=replies) as remote:
        results = [engine.upload_to_drive(report, "fixture-folder") for _ in replies]
    return require(results == [None, None, "fixture-receipt"] and remote.call_count == 3,
                   f"失败、缺文件 ID、有效回执三种情况返回 {results}")


@check("I03", "report", "P0", "financial_reporting/ai_dossier_synthesizer.py", "IT-04")
def unknown_valuation_model_is_blocked(_):
    from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
    args = ("AUDIT", "US", "隔离样本", "semiconductors", "半导体")
    require(AIDossierSynthesizer.synthesize_dossier(*args)["overview"]["industry_id"] == "semiconductors",
            "已知行业无法进入合成器")
    try:
        AIDossierSynthesizer.synthesize_dossier(*args, ai_analysis={"valuation_model": "AUDIT_UNKNOWN_MODEL"})
    except ValueError as error:
        return require("知识图谱" in str(error), f"错误模型被无关异常拦截 {error}")
    raise AssertionError("AI 指定的未知估值模型绕过图谱边界")


@check("I04", "ledger", "P0", "financial_core/engines/prediction_ledger.py", "IT-06")
def outcome_cannot_precede_prediction(work):
    from financial_core.engines.retrospective_review_engine import ActualMarketOutcome
    ledger = new_ledger(work)
    snapshot = prediction()
    ledger.record_prediction(snapshot)
    outcome = ActualMarketOutcome(outcome_date="2026-10-15", current_price=100,
                                  quote_timestamp="2026-10-15T20:00:00Z",
                                  benchmark_return_pct=0, realized_catalysts=[])
    try:
        ledger.record_outcome(snapshot.prediction_id, outcome)
    except ValueError:
        pass
    return require(ledger.get_outcome(snapshot.prediction_id) is None, "早于预测时点的行情仍登记为实际结果")


@check("I01", "finance", "P0", "financial_core/engines/filing_mapper.py → finance_tools/valuation.py", "IT-02")
def mapped_financials_keep_dcf_units(_):
    from financial_core.engines.filing_mapper import OfficialFilingMapper
    from finance_tools.valuation import multistage_dcf
    results = []
    for unit, scale in (("usd", 1), ("usd_million", 1_000_000)):
        monetary = {"reported_revenue": 100_000_000, "total_assets": 100_000_000,
                    "total_liabilities": 50_000_000, "equity": 50_000_000, "total_debt": 40_000_000,
                    "reported_cash": 10_000_000, "reported_operating_cash_flow": 20_000_000,
                    "reported_capex": 5_000_000}
        facts = {key: value / scale for key, value in monetary.items()}
        facts.update(market_price=100, quote_timestamp="2026-10-16 16:00 EDT", shares_outstanding=1_000_000)
        normalized = OfficialFilingMapper.map_to_company_input({"ticker": "AUDIT", "financial_unit": unit, "facts": facts})
        results.append(multistage_dcf(
            normalized.reported_operating_cash_flow - normalized.reported_capex,
            [0.0], 0.10, 0.0, normalized.shares_outstanding, "FCFF",
            normalized.total_debt - normalized.reported_cash,
        )["value_per_share"])
    return require(abs(results[0] - results[1]) < 1e-8, f"同一财报经两种量纲进入 DCF 后得到 {results}")


@check("I02", "ledger", "P0", "financial_core/pipeline/canyon_linear_pipeline.py", "IT-03")
def stale_quote_cannot_enter_decision_pipeline(work):
    from financial_core.pipeline.canyon_linear_pipeline import CanyonLinearPipeline, CanyonStationInput, QuoteFreshnessError
    ledger = new_ledger(work)
    data = CanyonStationInput(ticker="AUDIT", company_name="隔离样本", current_price=100,
                              quote_timestamp="2000-01-03 10:00 EST", market_session="regular_trading")
    pipeline = CanyonLinearPipeline(ledger=ledger)
    try:
        pipeline.station_1_quote_freshness(data)
    except QuoteFreshnessError:
        return require(ledger.get_stats()["total_predictions"] == 0, "行情阻断仍写入预测")
    raise AssertionError("陈旧行情按输入的盘中标记通过 Canyon 门禁，可进入期权与估值工位")


@check("R01", "report", "P0", "scripts/cloud_daily_pipeline.py", 'IT-01')
def stale_daily_publish(work):
    ledger = new_ledger(work)
    output = work / "reports"
    try:
        receipt, _, _ = run_cloud(work, "2030-01-15", ledger=ledger)
        status = receipt["status"]
    except ValueError:
        status = "REJECTED"
    published = list(output.glob("*_US_*"))
    count = ledger.get_stats()["total_predictions"]
    return require(not published and not count and status != "SUCCESS",
                   f"远离历史样本的报告日得到 {status}，正式文件={len(published)}，预测={count}")



@check("R03", "report", "P0", "scripts/cloud_daily_pipeline.py", 'IT-05')
def invalid_ledger_blocks_publish(work):
    ledger = new_ledger(work)
    ledger.record_prediction(prediction())
    with closing(sqlite3.connect(ledger.db_path)) as db, db:
        db.execute("UPDATE predictions SET baseline_price = 999")
    require(not ledger.verify_integrity().is_valid, "篡改样本应触发真实哈希错误")
    output = work / "reports"
    try:
        receipt, _, _ = run_cloud(work, "2026-10-16", ledger=ledger)
        status = receipt["status"]
    except (ValueError, RuntimeError) as error:
        require("账本" in str(error) or "ledger" in str(error).lower(), f"日报因无关错误失败 {error}")
        status = "REJECTED"
    published = list(output.glob("*_US_*"))
    count = ledger.get_stats()["total_predictions"]
    return require(status != "SUCCESS" and not published and count == 1,
                   f"坏账本得到 {status}，正式文件={len(published)}，追加预测={count - 1}")



@check("D01", "artifacts", "P1", "reports/ai_dossiers/", 'IT-11')
def dossier_shape(_):
    from jsonschema.validators import validator_for
    schema = load(ROOT / "schemas/deep_dossier.schema.json")
    validator = validator_for(schema)(schema)
    files = sorted((ROOT / "reports/ai_dossiers").glob("*/*_deep_dossier.json"))
    require(files, "公司档案目录无审计样本")
    invalid = []
    for path in files:
        error = next(validator.iter_errors(load(path)), None)
        if error is not None:
            invalid.append(f"{path.stem} {error.json_path} {error.message}")
    return require(not invalid, f"扫描 {len(files)} 份档案，Schema 失败 {len(invalid)} 份，示例 {invalid[:3]}",
                   f"{len(files)} 份档案全部通过 Schema 结构校验")



@check("D02", "artifacts", "P0", "reports/ai_dossiers/", 'IT-11')
def dossier_publication_quality(_):
    files = sorted((ROOT / "reports/ai_dossiers").glob("*/*_deep_dossier.json"))
    require(files, "公司档案目录无审计样本")
    gaps = Counter()
    for path in files:
        data = load(path)
        decision = data.get("decision_summary", {})
        for field in ("evidence_manifest", "material_events", "dcf_model"):
            if not data.get(field):
                gaps[field] += 1
        if "阻断" in str(decision.get("freshness_status", "")) and decision.get("rating"):
            gaps["行情阻断仍有评级"] += 1
        margin = decision.get("margin_of_safety_pct")
        if isinstance(margin, (int, float)) and margin < 0 and "买入" in str(decision.get("rating", "")):
            gaps["负安全边际且买入"] += 1
    return require(not gaps, f"扫描 {len(files)} 份档案，缺口 {dict(gaps)}")
