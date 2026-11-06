"""发布探针元数据、断言和隔离夹具。"""

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Callable
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Check:
    key: str
    group: str
    severity: str
    location: str
    points: tuple[str, ...]
    run: Callable[[Path], str]

    @property
    def layer(self):
        return self.points[0].partition("-")[0]


CHECKS = []


def check(key, group, severity, location, *points):
    def register(function):
        CHECKS.append(Check(key, group, severity, location, points, function))
        return function
    return register


def require(condition, detail, success="契约满足"):
    if not condition:
        raise AssertionError(detail)
    return success


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def install_isolation(workspace):
    """审计进程只允许在临时目录写入，禁止联网和启动外部程序。"""
    workspace = workspace.resolve()

    def require_scratch(path):
        if isinstance(path, int) or path is None:
            raise PermissionError("审计禁止通过文件描述符修改文件")
        target = Path(os.fsdecode(path)).resolve()
        if not target.is_relative_to(workspace):
            raise PermissionError(f"审计禁止写入临时目录以外的位置 {target}")

    def guard(event, args):
        if event in {
            "socket.connect", "socket.getaddrinfo", "socket.gethostbyname",
            "socket.sendto", "subprocess.Popen", "os.system", "os.exec", "os.spawn",
        }:
            raise PermissionError(f"离线审计禁止 {event}")
        if event == "open":
            flags = args[2]
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                require_scratch(args[0])
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.truncate", "os.utime"}:
            require_scratch(args[0])
        elif event in {"os.rename", "os.link", "os.symlink"}:
            require_scratch(args[0])
            require_scratch(args[1])
        elif event == "sqlite3.connect" and args[0] != ":memory:":
            require_scratch(args[0])

    sys.dont_write_bytecode = True
    sys.addaudithook(guard)


def prediction():
    from financial_core.engines.retrospective_review_engine import HistoricalPredictionSnapshot
    return HistoricalPredictionSnapshot(
        prediction_id="AUDIT-1", prediction_date="2026-10-16", market="US",
        ticker="AUDIT", company_name="测试样本", baseline_price=100, rating="Hold",
        safe_entry_trigger=85, pessimistic_floor=75, pessimistic_event="事件 A",
        neutral_fair_value=105, optimistic_target=130, optimistic_event="事件 B", tactical_action="观察",
    )



def new_ledger(work):
    from financial_core.engines.prediction_ledger import PredictionLedger
    return PredictionLedger(work / "audit.sqlite3")



def run_cloud(work, as_of, *, dry_run=False, ledger=None, briefing=None):
    from scripts import cloud_daily_pipeline
    from scripts import run_daily_briefing_and_deep_dossiers_pipeline as sample_source
    ledger = ledger or new_ledger(work)
    output = work / "reports"
    sample = sample_source.BRIEFING_DATA_US if briefing is None else briefing
    with patch.object(cloud_daily_pipeline, "PredictionLedger", return_value=ledger), \
         patch.object(cloud_daily_pipeline, "get_gdrive_executable", return_value=None), \
         patch.object(sample_source, "BRIEFING_DATA_US", deepcopy(sample)):
        receipt = cloud_daily_pipeline.run_pipeline(
            "US", as_of, render_pdf=False, output_dir=output, dry_run=dry_run,
        )
    return receipt, output, ledger


def dossier_sample(market="US"):
    """测试用合成三表与证据，供档案、工作簿和交付流程共用。"""
    from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
    ticker, currency = ("AUDIT", "USD") if market == "US" else ("9999", "JPY")
    facts = {"revenue": 800, "total_assets": 1000, "total_liabilities": 600,
             "equity": 400, "net_income": 55, "operating_cash_flow": 75,
             "capex": 20, "currency": currency, "fiscal_period": "FY2025"}
    evidence = {"source_id": f"fixture-{market}", "source": f"fixture-{market}", "sha256": "a" * 64}
    return AIDossierSynthesizer.synthesize_dossier(
        ticker, market, "合成档案会社", "semiconductors", "半导体",
        financial_statements=facts, ai_analysis={"business_model": "测试用半导体业务"},
        market_quote={"currency": currency, "current_price": 100, "fair_anchor": 100,
                      "pessimistic_floor": 75, "optimistic_target": 130,
                      "dcf_model": {"base_case": {"discount_rate": 0.1, "terminal_growth": 0.02}}},
        evidence_manifest=[evidence], material_events=[{"event": "合成披露"}], report_date="2026-10-16",
    )
