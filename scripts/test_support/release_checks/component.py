"""发布契约探针 component。"""

from contextlib import closing, contextmanager
import ast
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from dataclasses import replace
from unittest.mock import patch
from .common import check, new_ledger, prediction, require, ROOT


@check("B09", "batch", "P1", "scripts/run_567_universe_batch_pipeline.py", "CT-05")
def resume_recovers_missing_artifact(work):
    from scripts.run_567_universe_batch_pipeline import BatchUniversePipelineRunner, UniversePipelineStateManager
    runner = BatchUniversePipelineRunner.__new__(BatchUniversePipelineRunner)
    runner.state_mgr = UniversePipelineStateManager(work / "state.json")
    runner.get_batches = lambda **_: [("batch_001", [{"overview": {"ticker": "AUDIT"}}])]
    artifact = work / "missing.json"

    def rebuild(*_, **__):
        artifact.write_text("{}", encoding="utf-8")
        return {"ticker": "AUDIT", "market": "US", "json_path": artifact.relative_to(ROOT).as_posix()}

    runner.process_single_company = rebuild
    with state_commit_for_probe(work):
        runner.state_mgr.record_ticker_completed(
            "batch_001", "AUDIT", {"market": "US", "json_path": artifact.relative_to(ROOT).as_posix()},
        )
        result = runner.run_pipeline(resume=True)
    return require(artifact.is_file() and result["processed_count"] == 1, "产物已缺失，恢复仍跳过标记完成的任务")


@check("L06", "ledger", "P0", "financial_core/engines/prediction_ledger.py", "CT-04")
def concurrent_prediction_chain_remains_valid(work):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    ledger = new_ledger(work)
    barrier = Barrier(6)

    def record(index):
        barrier.wait(timeout=10)
        return ledger.record_prediction(replace(prediction(), prediction_id=f"AUDIT-{index}"))

    with ThreadPoolExecutor(max_workers=6) as pool:
        digests = list(pool.map(record, range(6)))
    integrity = ledger.verify_integrity()
    return require(len(set(digests)) == 6 and ledger.get_stats()["total_predictions"] == 6 and integrity.is_valid,
                   f"并发追加后的账本不完整或链不连续，验签 {integrity.error}")


@check("F08", "finance", "P0", "financial_core/engines/financial_statement_facade.py", "CT-02")
def filing_facade_keeps_currency_and_period(_):
    from financial_core.engines.financial_statement_facade import FinancialStatementFacade
    raw = {"ticker": "AUDIT", "currency": "JPY", "fiscal_period": "FY2025",
           "total_assets": "100百万円", "total_liabilities": "60百万円", "equity": "40百万円",
           "revenue": "80百万円", "net_income": "5百万円"}
    profile = FinancialStatementFacade().process_company_filing(raw, industry_code="semiconductors")
    return require((profile.total_assets, profile.total_liabilities, profile.currency, profile.fiscal_period)
                   == (100_000_000, 60_000_000, "JPY", "FY2025"),
                   "日股财报标准化丢失金额量纲、原币或财期")


@check("R10", "report", "P0", "financial_reporting/ai_dossier_synthesizer.py", "CT-07")
def dossier_does_not_assert_undisclosed_debt_maturity(_):
    from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
    result = AIDossierSynthesizer.synthesize_dossier(
        "AUDIT", "US", "隔离样本", "semiconductors", "半导体",
        ai_analysis={}, evidence_manifest=[], report_date="2026-10-16",
    )
    debt_wall = result["financial_statement_deep_dive"]["debt_structure_and_solvency"].get("debt_wall_24m")
    return require("无重大偿债集中到期墙" not in str(debt_wall),
                   "没有偿债披露时仍声明未来 24 个月无重大集中到期")


@check("A03", "architecture", "P1", "financial_core/engines/knowledge_graph_engine.py", "CT-08")
def graph_links_resolve(_):
    from financial_core.engines.knowledge_graph_engine import KnowledgeGraphEngine
    result = KnowledgeGraphEngine().verify_graph_disk_integrity()
    return require(result["total_checked"] > 0 and result["all_valid"],
                   f"图谱绑定缺失 {result['missing_items'][:8]}")


@check("B08", "batch", "P1", "scripts/run_567_universe_batch_pipeline.py", "CT-06")
def batch_identity_contains_market(work):
    from scripts.run_567_universe_batch_pipeline import UniversePipelineStateManager
    path = work / "state.json"
    state = UniversePipelineStateManager(path)
    with state_commit_for_probe(work):
        state.record_ticker_completed("US001", "AUDIT", {"market": "US"})
        state.record_ticker_completed("JP001", "AUDIT", {"market": "JP"})
    records = UniversePipelineStateManager(path).data["tickers"].values()
    return require({row["market"] for row in records} == {"US", "JP"}, "跨市场同代码覆盖另一条进度记录")


@check("Q04", "quote", "P0", "finance_tools/market_quote_verifier.py", 'CT-01')
def archive_respects_stale(work):
    from finance_tools.market_quote_verifier import MarketQuoteVerifier, QuoteVerificationError
    reader = MarketQuoteVerifier(work)
    reader.raw_dir.mkdir(parents=True, exist_ok=True)
    (reader.raw_dir / "fixture.json").write_text(json.dumps({
        "quotes": {"AUDIT": {"current_price": 100.0, "timestamp_iso": "2026-10-01T20:00:00Z"}}
    }), encoding="utf-8")
    try:
        result = reader.get_latest_quote("AUDIT", as_of_iso="2026-10-16T20:00:00Z")
    except QuoteVerificationError:
        return "过期归档被拒绝"
    return require(not result.is_valid, f"过期归档得到 is_valid={result.is_valid}, freshness={result.freshness_status}")



@check("L01", "ledger", "P0", "financial_core/engines/prediction_ledger.py", 'CT-04')
def hashes_protect_payload(work):
    ledger = new_ledger(work)
    ledger.record_prediction(prediction())
    require(ledger.verify_integrity().is_valid, "完整样本账本未通过验签")
    with closing(sqlite3.connect(ledger.db_path)) as db, db:
        db.execute("UPDATE predictions SET tactical_action = ?", ("篡改",))
    return require(not ledger.verify_integrity().is_valid, "篡改交易行动后账本仍验签通过")



@check("L02", "ledger", "P0", "financial_core/engines/prediction_ledger.py", 'CT-04')
def idempotence_conflict(work):
    ledger = new_ledger(work)
    snapshot = prediction()
    digest = ledger.record_prediction(snapshot)
    require(ledger.record_prediction(snapshot) == digest, "相同载荷重试没有返回同一哈希")
    try:
        revised = ledger.record_prediction(replace(snapshot, baseline_price=101))
    except (ValueError, sqlite3.IntegrityError):
        return "相同载荷可重试，冲突载荷被拒绝"
    return require(revised != digest, "同一预测 ID 的不同载荷静默返回旧哈希")



@check("L03", "ledger", "P0", "financial_core/engines/prediction_ledger.py", 'CT-04')
def outcomes_are_audited(work):
    from financial_core.engines.retrospective_review_engine import ActualMarketOutcome
    ledger = new_ledger(work)
    snapshot = prediction()
    ledger.record_prediction(snapshot)
    ledger.record_outcome(snapshot.prediction_id, ActualMarketOutcome(
        outcome_date="2026-10-19", current_price=110, quote_timestamp="2026-10-19T20:00:00Z",
        benchmark_return_pct=1.0, realized_catalysts=[],
    ))
    with closing(sqlite3.connect(ledger.db_path)) as db, db:
        db.execute("UPDATE outcomes SET current_price = 999")
    return require(not ledger.verify_integrity().is_valid, "修改对账结果价格后账本仍验签通过")



@check("L04", "ledger", "P0", "data/ledger/predictions_ledger.sqlite3", 'CT-04')
def existing_ledger(work):
    from financial_core.engines.prediction_ledger import PredictionLedger
    db = ROOT / "data/ledger/predictions_ledger.sqlite3"
    for suffix in ("", "-wal"):
        source = db.with_name(db.name + suffix)
        if source.exists():
            shutil.copyfile(source, work / source.name)
    require((work / db.name).is_file(), "正式账本缺失")
    ledger = PredictionLedger(work / db.name)
    result = ledger.verify_integrity()
    return require(result.is_valid, f"现有预测链副本验签失败 {result.error}",
                   f"现有预测链副本验签通过，条数 {ledger.get_stats()['total_predictions']}")



@check("R05", "report", "P1", "financial_reporting/daily_briefing_engine.py", "CT-09")
def missing_schema_fails_closed(work):
    from financial_reporting import daily_briefing_engine
    with patch.object(daily_briefing_engine, "ROOT", work):
        try:
            engine = daily_briefing_engine.DailyBriefingEngine(gdrive_exe="unused", edge_exe="unused")
            ok, message = engine.validate_briefing_data({})
        except FileNotFoundError:
            return "缺失日报 Schema 时阻断"
    return require(not ok, f"缺失 Schema 时空研报仍通过，返回 {message}")



@contextmanager
def state_commit_for_probe(work):
    """在禁用原子替换的 Windows 沙箱中，仍可单独验证状态机的业务语义。"""
    replace_file = Path.replace

    def replace_state(source, target):
        try:
            return replace_file(source, target)
        except PermissionError as error:
            if getattr(error, "winerror", None) != 5 or source.parent != work or Path(target).parent != work:
                raise
            target = Path(target)
            target.write_bytes(source.read_bytes())
            source.unlink()
            return target

    with patch.object(Path, "replace", replace_state):
        yield



@check("B01", "batch", "P0", "scripts/run_567_universe_batch_pipeline.py", 'CT-05')
def dry_run_cannot_complete_batch(work):
    from scripts.run_567_universe_batch_pipeline import BatchUniversePipelineRunner, UniversePipelineStateManager
    # 只隔离取数和分析器，使用真实 run_pipeline、进度文件和恢复状态判定。
    runner = BatchUniversePipelineRunner.__new__(BatchUniversePipelineRunner)
    runner.state_mgr = UniversePipelineStateManager(work / "state.json")
    runner.get_batches = lambda **_: [("batch_001", [{"overview": {"ticker": "AUDIT"}}])]
    runner.process_single_company = lambda *_, **__: {"ticker": "AUDIT", "status": "VALIDATED", "dry_run": True}
    with state_commit_for_probe(work):
        runner.run_pipeline(dry_run=True)
    reloaded = UniversePipelineStateManager(work / "state.json")
    return require(not reloaded.is_ticker_completed("AUDIT"), "试运行持久化 COMPLETED，正式恢复会跳过")



@check("B02", "batch", "P1", "scripts/run_567_universe_batch_pipeline.py", 'CT-05')
def batch_workers_keep_both_results(work):
    from scripts.run_567_universe_batch_pipeline import UniversePipelineStateManager
    path = work / "state.json"
    worker_a = UniversePipelineStateManager(path)
    worker_b = UniversePipelineStateManager(path)
    # 两个 worker 先读同一版本，再分别提交。固定交错顺序可重现覆盖，无需 sleep。
    with state_commit_for_probe(work):
        worker_a.record_ticker_completed("batch_001", "AUDIT-A", {"market": "US"})
        worker_b.record_ticker_completed("batch_002", "AUDIT-B", {"market": "US"})
    persisted = UniversePipelineStateManager(path).data["tickers"]
    return require(set(persisted) == {"AUDIT-A", "AUDIT-B"}, f"两次提交后进度仅保留 {sorted(persisted)}")



@check("B06", "batch", "P1", "scripts/run_567_universe_batch_pipeline.py", 'CT-11')
def real_atomic_checkpoint(work):
    from scripts.run_567_universe_batch_pipeline import UniversePipelineStateManager
    path = work / "state.json"
    state = UniversePipelineStateManager(path)
    state.record_ticker_completed("batch_001", "AUDIT-A", {"market": "US"})
    state.record_ticker_completed("batch_002", "AUDIT-B", {"market": "US"})
    reloaded = UniversePipelineStateManager(path)
    return require(set(reloaded.data["tickers"]) == {"AUDIT-A", "AUDIT-B"}, "原子保存后记录未完整恢复",
                   "两次真实原子保存均可恢复")



@check("A01", "architecture", "P1", "financial_reporting/, finance_tools/, financial_core/", 'CT-10')
def layer_dependencies(_):
    prohibited = {
        "financial_core": {"financial_core", "finance_tools", "financial_reporting", "scripts", "data_sources", "data_ingestion", "skill_gateway"},
        "finance_tools": {"financial_reporting", "scripts", "skill_gateway"},
        "financial_reporting": {"scripts", "skill_gateway"},
    }
    failures = []
    for layer, forbidden in prohibited.items():
        for path in sorted((ROOT / layer).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if name.partition(".")[0] in forbidden:
                        failures.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno} → {name}")
    return require(not failures, f"发现 {len(failures)} 处绝对自导入或逆向依赖 " + "；".join(failures))



@check("T01", "isolation", "P0", "scripts/audit_project_contracts.py", 'CT-12')
def audit_guard(work):
    # 直接触发审计事件，验证防护失败时也不会发起真实连接或修改文件。
    attempts = [
        ("open", str(ROOT / "data/ledger/predictions_ledger.sqlite3"), "wb", os.O_WRONLY),
        ("sqlite3.connect", str(ROOT / "data/ledger/predictions_ledger.sqlite3")),
        ("socket.connect", None, ("192.0.2.1", 443)),
        ("subprocess.Popen", "browser", [], None, None),
    ]
    for event, *args in attempts:
        try:
            sys.audit(event, *args)
        except PermissionError:
            continue
        raise AssertionError(f"隔离层允许 {event}")
    sample = work / "can-write"
    sample.write_text("audit", encoding="utf-8")
    return require(sample.read_text(encoding="utf-8") == "audit", "隔离目录读写结果不一致",
                   "隔离目录可写，正式账本、网络和外部程序操作被拦截")



@check("G02", "governance", "P0", "scripts/data_store.py", 'CT-03')
def catalog_append_only(work):
    from scripts.data_store import LocalStore
    with closing(LocalStore(work.relative_to(ROOT).as_posix())) as store:
        store.db.execute("INSERT INTO artifacts VALUES (?, ?, ?, ?)", ("fixture", "unused", 1, "2026-10-16"))
        for command in ("UPDATE artifacts SET size_bytes = 2", "DELETE FROM artifacts"):
            try:
                store.db.execute(command)
            except sqlite3.IntegrityError as error:
                require("append-only" in str(error), f"目录因无关约束拒绝修改 {error}")
                continue
            raise AssertionError(f"历史目录允许执行 {command}")
    return "历史目录拒绝覆盖和删除"
