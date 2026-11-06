"""全市场分批平账常态化引擎 (normalized_reconciliation_engine.py).

遵循项目内数据接入策略、2026-10-12 全盘资产池规范与 2026-10-15 架构防劣变准则：
1. 四层架构严格解耦：属于 financial_core 纯净底层引擎，零外层逆向依赖；
2. 覆盖全盘万家企业资产池：美股（10,445 家）与日股（4,447 家）共计全量 14,892 家上市主体；
3. 多会计准则与跨申报表对齐：支持 US-GAAP (10-K/A)、IFRS (20-F/A)、MJDS (6-K FY / 40-F) 及日股原币种对齐；
4. 刚性平账自检：执行 Assets = Liabilities + Equity 会计恒等式检验（容差 <= 0.1%），缺失/破损坚决阻断；
5. 进程并发防锁：基于操作系统 PID 与排他文件锁机制，杜绝定时任务多重并发破坏底账；
6. 智能频率节流与退避重试：严格遵守 SEC EDGAR 访问准则 (<= 10 req/s)，实现指数退避与抖动保护；
7. 原子化断点续传状态机：支持批次切片 (Batch Chunking)、行业轮动调度与增量无损恢复。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .filing_mapper import (
    OfficialFilingMapper,
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)
from .sec_edgar_collector import (
    OfficialSecEdgarCollector,
    SecExtractedFinancialFacts,
)
from .tiered_universe_manager import (
    TieredUniverseManager,
    UniverseCompanyRecord,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = ROOT / "data" / "pipeline_state" / "universe_reconciliation_progress.json"
LEGACY_SEC_STATE_PATH = ROOT / "data" / "pipeline_state" / "sec_collection_progress.json"
DEFAULT_LOCK_PATH = ROOT / "data" / "pipeline_state" / "reconciliation_pipeline.lock"
DEFAULT_GAP_MANIFEST_PATH = ROOT / "data" / "browser-search" / "replenishment_tasks.json"


class ProcessLockError(RuntimeError):
    """流水线进程锁冲突异常 (已有其他任务在并发执行或存在未清理死锁)."""
    pass


def is_pid_alive(pid: int) -> bool:
    """跨平台探测指定进程 ID 是否真实存活."""
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle == 0:
                return False
            kernel32.CloseHandle(handle)
            return True
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


class ReconciliationProcessLock:
    """原子化文件排他锁管理器，防止定时任务并发冲突与网络风暴."""

    def __init__(self, lock_path: Optional[Path] = None, max_age_seconds: float = 7200.0):
        self.lock_path = lock_path or DEFAULT_LOCK_PATH
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_age_seconds = max_age_seconds
        self.lock_token = f"{os.getpid()}_{random.randint(100000, 999999)}_{time.time_ns()}"
        self._acquired = False

    def acquire(self, timeout_sec: float = 5.0) -> bool:
        start_t = time.time()
        while True:
            if not self.lock_path.exists():
                try:
                    lock_info = {
                        "pid": os.getpid(),
                        "token": self.lock_token,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "timestamp": time.time(),
                        "host_platform": sys.platform,
                    }
                    tmp_file = self.lock_path.with_suffix(f".lock_{os.getpid()}_{time.time_ns()}.tmp")
                    tmp_file.write_text(json.dumps(lock_info, indent=2), encoding="utf-8")
                    tmp_file.replace(self.lock_path)
                    self._acquired = True
                    return True
                except Exception:
                    pass

            # 锁已存在，检查是否为残留死锁
            try:
                raw = json.loads(self.lock_path.read_text(encoding="utf-8"))
                lock_pid = int(raw.get("pid", 0))
                lock_token = raw.get("token", "")
                lock_t = float(raw.get("timestamp", 0.0))
                now_t = time.time()

                # 若创建进程已死，或锁已超时，自动释放死锁
                if not is_pid_alive(lock_pid) or (now_t - lock_t > self.max_age_seconds):
                    try:
                        self.lock_path.unlink()
                        continue
                    except Exception:
                        pass
                else:
                    if lock_pid == os.getpid() and lock_token == self.lock_token:
                        self._acquired = True
                        return True
            except Exception:
                # 破损锁文件，清除
                try:
                    self.lock_path.unlink()
                    continue
                except Exception:
                    pass

            if time.time() - start_t > timeout_sec:
                raise ProcessLockError(
                    f"平账调度任务被锁定阻断: 锁文件 {self.lock_path} 被正在运行的任务占用。"
                )
            time.sleep(0.1)

    def release(self) -> None:
        if self._acquired and self.lock_path.exists():
            try:
                raw = json.loads(self.lock_path.read_text(encoding="utf-8"))
                if int(raw.get("pid", 0)) == os.getpid() and raw.get("token") == self.lock_token:
                    self.lock_path.unlink()
            except Exception:
                pass
            self._acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


@dataclass
class ReconciliationRecord:
    """企业全生命周期平账事实状态记录."""
    ticker: str
    market: str
    company_name: str
    tier: str
    cik: str = ""
    jpx_code: str = ""
    sector: str = ""
    status: str = "PENDING"               # "COMPLETED", "DEFICIENT", "SKIPPED"
    fiscal_year: int = 0
    fiscal_year_end: str = ""
    form: str = ""
    accounting_standard: str = "US-GAAP"  # "US-GAAP", "IFRS", "MJDS", "LOCAL_GAAP"
    currency: str = "USD"
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    stockholders_equity: float = 0.0
    revenue: float = 0.0
    gross_profit: float = 0.0
    operating_income: float = 0.0
    net_income: float = 0.0
    operating_cash_flow: float = 0.0
    capex: float = 0.0
    free_cash_flow: float = 0.0
    is_balanced: bool = False
    balance_sheet_diff: float = 0.0
    balance_sheet_rel_ratio: float = 0.0
    deficiency_reason: str = ""
    source_filing: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NormalizedReconciliationStateManager:
    """全盘万家企业平账断点续传状态机管理器."""

    def __init__(self, state_path: Optional[Path] = None, sync_legacy: Optional[bool] = None):
        self.state_path = state_path or DEFAULT_STATE_PATH
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if sync_legacy is None:
            self.sync_legacy = True if (state_path is None or state_path == DEFAULT_STATE_PATH) else False
        else:
            self.sync_legacy = sync_legacy
        self.records: Dict[Tuple[str, str], ReconciliationRecord] = {}
        self.metadata: Dict[str, Any] = {
            "version": "2.0.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_attempted": 0,
                "balanced_count": 0,
                "unbalanced_or_deficient": 0,
            },
        }
        self._load()

    def _load(self) -> None:
        # 1. 尝试从主状态文件加载
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                self.metadata = data.get("metadata", self.metadata)
                for k, v in data.get("records", {}).items():
                    mkt, tick = k.split(":", 1) if ":" in k else ("US", k)
                    rec = ReconciliationRecord(**v)
                    self.records[(mkt.upper(), tick.upper())] = rec
            except Exception:
                pass

        # 2. 检查是否有历史 SEC 收集底账未迁移，若有且开启迁移则自动对齐合并
        if self.sync_legacy and not self.records:
            if LEGACY_SEC_STATE_PATH.exists():
                try:
                    univ_mgr = TieredUniverseManager.get_instance()
                    legacy_data = json.loads(LEGACY_SEC_STATE_PATH.read_text(encoding="utf-8"))
                    for tick, item in legacy_data.get("records", {}).items():
                        key = ("US", tick.upper())
                        if key not in self.records:
                            status = item.get("status", "PENDING")
                            univ_rec = univ_mgr.lookup(tick.upper(), "US")
                            rec_tier = univ_rec.tier if univ_rec else item.get("tier", "TIER_3")
                            comp_name = (univ_rec.company_name if (univ_rec and univ_rec.company_name) else item.get("company_name", tick))
                            sec_val = univ_rec.sector if univ_rec else ""

                            src = item.get("source_filing", "")
                            if "20-F" in src:
                                std = "IFRS"
                            elif "6-K" in src or "40-F" in src:
                                std = "MJDS"
                            else:
                                std = "US-GAAP"

                            rec = ReconciliationRecord(
                                ticker=tick.upper(),
                                market="US",
                                company_name=comp_name,
                                tier=rec_tier,
                                sector=sec_val,
                                cik=item.get("cik", ""),
                                status=status,
                                fiscal_year=int(item.get("fiscal_year", 0)),
                                fiscal_year_end=item.get("fiscal_year_end", ""),
                                form=src.split()[2] if len(src.split()) >= 3 else "10-K",
                                accounting_standard=std,
                                currency=item.get("currency", "USD"),
                                total_assets=float(item.get("total_assets", 0.0)),
                                revenue=float(item.get("revenue", 0.0)),
                                is_balanced=bool(item.get("is_balanced", status == "COMPLETED")),
                                balance_sheet_diff=float(item.get("balance_sheet_diff", 0.0)),
                                source_filing=src,
                                deficiency_reason=item.get("reason", ""),
                                updated_at=item.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            )
                            self.records[key] = rec
                except Exception:
                    pass

            # 自动基于本地已有官方 CIK 底账全科目补齐财务三表，消灭全0字段
            try:
                self.enrich_from_local_filings()
                self.reconcile_from_local_filings()
            except Exception:
                pass

        self._refresh_summary()

    def enrich_from_local_filings(self, cache_dir: Optional[Path] = None) -> int:
        """从本地已归档的官方 CIK CompanyFacts 底账全量补齐财务三表全科目事实.

        消除早期简单镜像同步导致的负债、股东权益、净利润、现金流等字段为 0 的历史遗留缺陷。
        """
        sec_dir = cache_dir or (ROOT / "data" / "official_filings" / "sec")
        if not sec_dir.exists():
            return 0

        enriched_count = 0
        for (mkt, tick), r in list(self.records.items()):
            if mkt == "US" and r.status == "COMPLETED" and (r.total_liabilities == 0.0 or r.stockholders_equity == 0.0 or r.operating_cash_flow == 0.0 or r.revenue == 0.0):
                cik = str(r.cik or "").strip().zfill(10)
                if not cik or cik == "0000000000":
                    continue
                cik_file = sec_dir / f"CIK{cik}.json"
                if cik_file.exists():
                    try:
                        filing_data = json.loads(cik_file.read_text(encoding="utf-8"))
                        facts = OfficialSecEdgarCollector.extract_aligned_financial_facts(filing_data, ticker=r.ticker)
                        r.total_assets = facts.total_assets
                        r.total_liabilities = facts.total_liabilities
                        r.stockholders_equity = facts.stockholders_equity
                        r.revenue = facts.revenue
                        r.gross_profit = facts.gross_profit
                        r.operating_income = facts.operating_income
                        r.net_income = facts.net_income
                        r.operating_cash_flow = facts.operating_cash_flow
                        r.capex = facts.capex
                        r.free_cash_flow = facts.free_cash_flow
                        r.is_balanced = facts.is_balanced
                        r.balance_sheet_diff = facts.balance_sheet_diff
                        r.balance_sheet_rel_ratio = facts.balance_sheet_rel_ratio
                        r.fiscal_year = facts.fiscal_year
                        r.fiscal_year_end = facts.fiscal_year_end
                        r.form = facts.form
                        r.currency = facts.currency
                        r.source_filing = facts.source_filing
                        r.updated_at = datetime.now(timezone.utc).isoformat()
                        enriched_count += 1
                    except Exception:
                        pass

        if enriched_count > 0:
            self._refresh_summary()
        return enriched_count

    def reconcile_from_local_filings(self, cache_dir: Optional[Path] = None) -> int:
        """扫描本地 CIK 文件，将所有已有本地官方底账但未完成平账入库的标的一键平账入库."""
        sec_dir = cache_dir or (ROOT / "data" / "official_filings" / "sec")
        if not sec_dir.exists():
            return 0
        univ_mgr = TieredUniverseManager.get_instance()
        univ_mgr.load_universe()

        cik_to_companies: Dict[str, List[UniverseCompanyRecord]] = {}
        for c in univ_mgr._us_companies.values():
            if c.cik:
                clean_cik = str(c.cik).strip().zfill(10)
                cik_to_companies.setdefault(clean_cik, []).append(c)

        reconciled = 0
        for f in sec_dir.glob("CIK*.json"):
            cik_str = f.stem.replace("CIK", "").strip().zfill(10)
            target_comps = cik_to_companies.get(cik_str, [])
            if not target_comps:
                continue

            try:
                filing_data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue

            # 遍历该 CIK 关联的所有上市主体 (涵盖普通股与成份股别名)
            target_comps.sort(key=lambda c: (1 if "-" in c.ticker else 0, len(c.ticker)))
            for primary_c in target_comps:
                key = ("US", primary_c.ticker.upper())
                rec = self.records.get(key)
                if rec and rec.status == "COMPLETED" and rec.total_liabilities > 0:
                    continue

                try:
                    facts = OfficialSecEdgarCollector.extract_aligned_financial_facts(filing_data, ticker=primary_c.ticker)

                    std = "US-GAAP"
                    if "20-F" in facts.form:
                        std = "IFRS"
                    elif "6-K" in facts.form or "40-F" in facts.form:
                        std = "MJDS"

                    new_rec = ReconciliationRecord(
                        ticker=primary_c.ticker.upper(),
                        market="US",
                        company_name=facts.company_name or primary_c.company_name,
                        tier=primary_c.tier,
                        cik=cik_str,
                        sector=primary_c.sector,
                        status="COMPLETED",
                        fiscal_year=facts.fiscal_year,
                        fiscal_year_end=facts.fiscal_year_end,
                        form=facts.form,
                        accounting_standard=std,
                        currency=facts.currency,
                        total_assets=facts.total_assets,
                        total_liabilities=facts.total_liabilities,
                        stockholders_equity=facts.stockholders_equity,
                        revenue=facts.revenue,
                        gross_profit=facts.gross_profit,
                        operating_income=facts.operating_income,
                        net_income=facts.net_income,
                        operating_cash_flow=facts.operating_cash_flow,
                        capex=facts.capex,
                        free_cash_flow=facts.free_cash_flow,
                        is_balanced=facts.is_balanced,
                        balance_sheet_diff=facts.balance_sheet_diff,
                        balance_sheet_rel_ratio=facts.balance_sheet_rel_ratio,
                        source_filing=facts.source_filing,
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    )
                    self.records[key] = new_rec
                    reconciled += 1
                except Exception:
                    pass

        if reconciled > 0:
            self._refresh_summary()
        return reconciled

    def _refresh_summary(self) -> None:
        tot = len(self.records)
        bal = sum(1 for r in self.records.values() if r.status == "COMPLETED")
        defic = sum(1 for r in self.records.values() if r.status == "DEFICIENT")
        self.metadata["summary"] = {
            "total_attempted": tot,
            "balanced_count": bal,
            "unbalanced_or_deficient": defic,
        }

    def is_completed(self, ticker: str, market: str = "US") -> bool:
        key = (market.upper(), ticker.upper())
        rec = self.records.get(key)
        return rec is not None and rec.status == "COMPLETED"

    def get_record(self, ticker: str, market: str = "US") -> Optional[ReconciliationRecord]:
        return self.records.get((market.upper(), ticker.upper()))

    def record_success(self, record: ReconciliationRecord) -> None:
        record.status = "COMPLETED"
        record.updated_at = datetime.now(timezone.utc).isoformat()
        self.records[(record.market.upper(), record.ticker.upper())] = record
        self._refresh_summary()

    def record_deficient(
        self,
        ticker: str,
        market: str,
        cik: str,
        reason: str,
        company_name: str = "",
        tier: str = "TIER_3",
        jpx_code: str = "",
        sector: str = "",
    ) -> None:
        rec = ReconciliationRecord(
            ticker=ticker.upper(),
            market=market.upper(),
            company_name=company_name or ticker.upper(),
            tier=tier,
            cik=cik,
            jpx_code=jpx_code,
            sector=sector,
            status="DEFICIENT",
            deficiency_reason=reason,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.records[(market.upper(), ticker.upper())] = rec
        self._refresh_summary()

    def save(self) -> None:
        self.metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._refresh_summary()
        payload = {
            "metadata": self.metadata,
            "records": {f"{mkt}:{t}": r.to_dict() for (mkt, t), r in self.records.items()},
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

        # 仅在生产默认路径下才保持向后兼容镜像更新旧状态文件，避免测试自定义路径污染生产底账
        if self.state_path == DEFAULT_STATE_PATH:
            try:
                legacy_payload = {
                    "version": "1.0.0",
                    "last_updated": self.metadata["last_updated"],
                    "summary": self.metadata["summary"],
                    "records": {
                        t: {
                            "status": r.status,
                            "cik": r.cik,
                            "company_name": r.company_name,
                            "fiscal_year": r.fiscal_year,
                            "fiscal_year_end": r.fiscal_year_end,
                            "revenue": r.revenue,
                            "total_assets": r.total_assets,
                            "is_balanced": r.is_balanced,
                            "balance_sheet_diff": r.balance_sheet_diff,
                            "source_filing": r.source_filing,
                            "reason": r.deficiency_reason,
                            "updated_at": r.updated_at,
                        }
                        for (mkt, t), r in self.records.items()
                        if mkt == "US"
                    },
                }
                tmp_leg = LEGACY_SEC_STATE_PATH.with_suffix(".tmp")
                tmp_leg.write_text(json.dumps(legacy_payload, indent=2, ensure_ascii=False), encoding="utf-8")
                tmp_leg.replace(LEGACY_SEC_STATE_PATH)
            except Exception:
                pass

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """生成全生命周期全息看板统计指标."""
        self._refresh_summary()
        by_tier = {"TIER_0": 0, "TIER_1": 0, "TIER_2": 0, "TIER_3": 0}
        by_market = {"US": 0, "JP": 0}
        by_standard = {"US-GAAP": 0, "IFRS": 0, "MJDS": 0, "LOCAL_GAAP": 0, "OTHER": 0}
        by_curr = {}

        for r in self.records.values():
            if r.status == "COMPLETED":
                by_tier[r.tier] = by_tier.get(r.tier, 0) + 1
                by_market[r.market] = by_market.get(r.market, 0) + 1
                by_standard[r.accounting_standard] = by_standard.get(r.accounting_standard, 0) + 1
                c = r.currency.upper()
                by_curr[c] = by_curr.get(c, 0) + 1

        return {
            "summary": self.metadata["summary"],
            "tier_breakdown": by_tier,
            "market_breakdown": by_market,
            "accounting_standard_breakdown": by_standard,
            "currency_breakdown": by_curr,
            "last_updated": self.metadata["last_updated"],
        }


class NormalizedReconciliationEngine:
    """全市场常态化平账调度引擎."""

    JP_TOP_CROSS_BORDER_CIKS = {
        "TM": "0001094517",    # Toyota Motor Corp (20-F)
        "SONY": "0000313838",  # Sony Group Corp (20-F)
        "MUFG": "0001140440",  # Mitsubishi UFJ Financial Group (20-F)
        "SMFG": "0001481177",  # Sumitomo Mitsui Financial Group (20-F)
        "HMC": "0000048203",   # Honda Motor Co Ltd (20-F)
        "TAK": "0001750244",   # Takeda Pharmaceutical Co (20-F)
        "NMR": "0001163653",   # Nomura Holdings Inc (20-F)
        "MFG": "0001270985",   # Mizuho Financial Group (20-F)
    }

    def __init__(
        self,
        state_mgr: Optional[NormalizedReconciliationStateManager] = None,
        universe_mgr: Optional[TieredUniverseManager] = None,
        lock: Optional[ReconciliationProcessLock] = None,
    ):
        self.state_mgr = state_mgr or NormalizedReconciliationStateManager()
        self.universe_mgr = universe_mgr or TieredUniverseManager.get_instance()
        self.lock = lock or ReconciliationProcessLock()

    def build_candidate_queue(
        self,
        market: str = "US",
        tier: Optional[str] = None,
        sector: Optional[str] = None,
        target_group: str = "all_sec",
        tickers_override: Optional[List[str]] = None,
        prioritize_core: bool = True,
    ) -> List[UniverseCompanyRecord]:
        """构建待平账目标标的优先级队列."""
        self.universe_mgr.load_universe()
        candidates: List[UniverseCompanyRecord] = []

        if tickers_override:
            for t in tickers_override:
                rec = self.universe_mgr.lookup(t, market)
                if rec:
                    candidates.append(rec)
                else:
                    candidates.append(
                        UniverseCompanyRecord(
                            ticker=t.upper(),
                            company_name=t.upper(),
                            market=market.upper(),
                            tier=tier or "TIER_3",
                            cik="",
                        )
                    )
            return candidates

        if target_group == "sp500":
            candidates = self.universe_mgr.get_sp500_priority_collection_list(unarchived_only=False)
        elif target_group == "missing_tier1":
            # 优先选取尚未完成平账的 TIER_0 与 TIER_1 核心中坚标的
            candidates = [
                c for c in self.universe_mgr._us_companies.values()
                if c.tier in ("TIER_0", "TIER_1") and c.cik and not self.state_mgr.is_completed(c.ticker, c.market)
            ]
        else:  # all_sec 或 全市场
            if market.upper() in ("US", "ALL"):
                # 优先聚焦普通股经营实体，剔除短横线优先股 (如 BAC-PB)
                us_items = [
                    c for c in self.universe_mgr._us_companies.values()
                    if "-" not in c.ticker and c.cik
                ]
                candidates.extend(us_items)

            if market.upper() in ("JP", "ALL"):
                jp_items = list(self.universe_mgr._jp_companies.values())
                # 优先匹配已知在美提交 20-F 的龙头企业
                for jp_c in jp_items:
                    clean_t = jp_c.ticker.replace("TYO:", "").upper()
                    if clean_t in self.JP_TOP_CROSS_BORDER_CIKS and not jp_c.cik:
                        jp_c.cik = self.JP_TOP_CROSS_BORDER_CIKS[clean_t]
                candidates.extend(jp_items)

        # 筛选 Tier
        if tier and tier.upper() != "ALL":
            candidates = [c for c in candidates if c.tier.upper() == tier.upper()]

        # 筛选 Sector
        if sector:
            candidates = [
                c for c in candidates
                if sector.lower() in (c.sector or "").lower() or sector.lower() in (c.industry or "").lower()
            ]

        # 优先级重排序
        if prioritize_core:
            tier_weights = {"TIER_0": 0, "TIER_1": 1, "TIER_2": 2, "TIER_3": 3}
            # 普通股优先于字母衍生股
            candidates.sort(key=lambda c: (tier_weights.get(c.tier, 4), len(c.ticker), c.ticker))

        return candidates

    def reconcile_company(
        self,
        record: UniverseCompanyRecord,
        force_refresh: bool = False,
        timeout: float = 15.0,
        max_retries: int = 2,
    ) -> ReconciliationRecord:
        """对单个标的执行权威数据拉取与刚性平账自检."""
        ticker = record.ticker
        market = record.market.upper()
        cik = record.cik

        # 日股若有对应的美国 20-F 登记 CIK，优先对齐官方 20-F 底账
        if market == "JP" and not cik:
            clean_t = ticker.replace("TYO:", "").upper()
            if clean_t in self.JP_TOP_CROSS_BORDER_CIKS:
                cik = self.JP_TOP_CROSS_BORDER_CIKS[clean_t]

        if not cik:
            raise IncompleteFilingFactError(
                f"标的 [{ticker}] 暂未登记官方公共 SEC/EDINET 索引标识，需转入人工/AI浏览器核验。"
            )

        # 带退避的官方拉取
        raw_facts = None
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                raw_facts = OfficialSecEdgarCollector.fetch_company_facts_by_cik(
                    cik=cik,
                    timeout=timeout,
                    force_refresh=force_refresh,
                )
                break
            except FileNotFoundError as e:
                # 404 表明确无 XBRL 数据，直接阻断
                raise e
            except Exception as e:
                last_exc = e
                if attempt < max_retries:
                    # 指数退避加抖动
                    backoff = (0.5 * (2 ** attempt)) + (random.uniform(0.1, 0.3))
                    time.sleep(backoff)
                else:
                    raise last_exc

        if not raw_facts:
            raise IncompleteFilingFactError(f"标的 [{ticker}] 获取官方底账为空。")

        # 提取并对齐三表平衡底账
        facts = OfficialSecEdgarCollector.extract_aligned_financial_facts(
            companyfacts=raw_facts,
            ticker=ticker,
        )

        # 会计准则判定
        std = "US-GAAP"
        if "20-F" in facts.form:
            std = "IFRS"
        elif "6-K" in facts.form or "40-F" in facts.form:
            std = "MJDS"
        elif market == "JP":
            std = "IFRS" if "20-F" in facts.form else "LOCAL_GAAP"

        return ReconciliationRecord(
            ticker=ticker,
            market=market,
            company_name=facts.company_name or record.company_name,
            tier=record.tier,
            cik=cik,
            jpx_code=record.jpx_code,
            sector=record.sector,
            status="COMPLETED",
            fiscal_year=facts.fiscal_year,
            fiscal_year_end=facts.fiscal_year_end,
            form=facts.form,
            accounting_standard=std,
            currency=facts.currency,
            total_assets=facts.total_assets,
            total_liabilities=facts.total_liabilities,
            stockholders_equity=facts.stockholders_equity,
            revenue=facts.revenue,
            gross_profit=facts.gross_profit,
            operating_income=facts.operating_income,
            net_income=facts.net_income,
            operating_cash_flow=facts.operating_cash_flow,
            capex=facts.capex,
            free_cash_flow=facts.free_cash_flow,
            is_balanced=facts.is_balanced,
            balance_sheet_diff=facts.balance_sheet_diff,
            balance_sheet_rel_ratio=facts.balance_sheet_rel_ratio,
            source_filing=facts.source_filing,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def run_reconciliation_batch(
        self,
        market: str = "US",
        tier: Optional[str] = None,
        sector: Optional[str] = None,
        target_group: str = "all_sec",
        tickers_override: Optional[List[str]] = None,
        batch_size: int = 50,
        batch_index: Optional[int] = None,
        limit: Optional[int] = None,
        delay_sec: float = 0.15,
        resume: bool = True,
        force_refresh: bool = False,
        dry_run: bool = False,
        gap_manifest_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """执行常态化分批平账作业主流程."""
        with self.lock:
            candidates = self.build_candidate_queue(
                market=market,
                tier=tier,
                sector=sector,
                target_group=target_group,
                tickers_override=tickers_override,
            )

            # 过滤断点续传
            if resume:
                pending_targets = [c for c in candidates if not self.state_mgr.is_completed(c.ticker, c.market)]
            else:
                pending_targets = list(candidates)

            # 切片控制
            if batch_index is not None:
                start = batch_index * batch_size
                end = start + batch_size
                pending_targets = pending_targets[start:end]
            elif limit is not None and limit > 0:
                pending_targets = pending_targets[:limit]

            if dry_run:
                return {
                    "status": "DRY_RUN_COMPLETED",
                    "total_candidates": len(candidates),
                    "pending_targets_count": len(pending_targets),
                    "preview": [
                        {"ticker": c.ticker, "market": c.market, "tier": c.tier, "cik": c.cik, "name": c.company_name}
                        for c in pending_targets[:10]
                    ],
                }

            # 分批流水线执行
            total_processed = 0
            balanced_this_run = 0
            deficient_this_run = 0
            deficient_items: List[Dict[str, Any]] = []

            for i in range(0, len(pending_targets), batch_size):
                chunk = pending_targets[i : i + batch_size]
                batch_no = (i // batch_size) + 1
                total_batches = (len(pending_targets) + batch_size - 1) // batch_size

                for rec in chunk:
                    total_processed += 1
                    try:
                        recon_res = self.reconcile_company(
                            record=rec,
                            force_refresh=force_refresh,
                        )
                        self.state_mgr.record_success(recon_res)
                        balanced_this_run += 1
                    except (BalanceSheetIdentityError, IncompleteFilingFactError, FileNotFoundError, RuntimeError) as e:
                        err_msg = str(e)
                        self.state_mgr.record_deficient(
                            ticker=rec.ticker,
                            market=rec.market,
                            cik=rec.cik,
                            reason=err_msg,
                            company_name=rec.company_name,
                            tier=rec.tier,
                            jpx_code=rec.jpx_code,
                            sector=rec.sector,
                        )
                        deficient_this_run += 1
                        deficient_items.append({
                            "ticker": rec.ticker,
                            "market": rec.market,
                            "company_name": rec.company_name,
                            "cik": rec.cik,
                            "jpx_code": rec.jpx_code,
                            "reason": err_msg,
                        })

                    # 速率控制延迟加抖动
                    if delay_sec > 0:
                        jitter = random.uniform(0.01, 0.05)
                        time.sleep(delay_sec + jitter)

                # 批次保存状态机
                self.state_mgr.save()

            # 同步补数清单 (单一事实来源 SSOT：剔除已平账完成企业，合并新增阻断项)
            self._sync_replenishment_manifest(deficient_items, gap_manifest_path)

            return {
                "status": "COMPLETED",
                "processed_this_run": total_processed,
                "balanced_this_run": balanced_this_run,
                "deficient_this_run": deficient_this_run,
                "total_balanced_all_time": self.state_mgr.metadata["summary"]["balanced_count"],
                "total_deficient_all_time": self.state_mgr.metadata["summary"]["unbalanced_or_deficient"],
                "dashboard": self.state_mgr.get_dashboard_metrics(),
            }

    def sync_replenishment_manifest(
        self,
        manifest_path: Optional[Path] = None,
    ) -> int:
        """主动全量同步补数清单并剔除已在主账本中平账的企业 (返回剩余真正缺数企业数量)."""
        return self._sync_replenishment_manifest(None, manifest_path)

    def _sync_replenishment_manifest(
        self,
        deficient_items: Optional[List[Dict[str, Any]]] = None,
        manifest_path: Optional[Path] = None,
    ) -> int:
        """同步官方财报底账缺失任务清单 (单一事实来源 SSOT 机制).

        任何已在主账本达到 COMPLETED 且 is_balanced 的企业，均自动从待补数清单中剔除。
        """
        target_path = manifest_path or DEFAULT_GAP_MANIFEST_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)

        existing_tasks = []
        if target_path.exists() and target_path.stat().st_size > 0:
            try:
                old_data = json.loads(target_path.read_text(encoding="utf-8"))
                existing_tasks = old_data.get("tasks", [])
            except Exception:
                existing_tasks = []

        # 1. 过滤已在主账本中平账合规的企业 (已平账移出补数清单)
        filtered_existing = []
        for x in existing_tasks:
            t = x.get("ticker", "").upper().strip()
            m = x.get("market", "US").upper().strip()
            if not t:
                continue
            rec = self.state_mgr.get_record(t, m)
            if rec is not None and rec.status == "COMPLETED" and rec.is_balanced:
                continue
            filtered_existing.append(x)

        seen_keys = {(x.get("market", "US"), x.get("ticker", "").upper().strip()) for x in filtered_existing}
        tasks = list(filtered_existing)

        # 2. 追加本次新增的阻断缺数项 (若未在主账本平账)
        if deficient_items:
            for item in deficient_items:
                t = item.get("ticker", "").upper().strip()
                m = item.get("market", "US").upper().strip()
                if not t or (m, t) in seen_keys:
                    continue
                rec = self.state_mgr.get_record(t, m)
                if rec is not None and rec.status == "COMPLETED" and rec.is_balanced:
                    continue
                seen_keys.add((m, t))

                name = item.get("company_name", t)
                cik = item.get("cik", "")
                jpx_code = item.get("jpx_code", "")

                if m == "US":
                    official_url = f"https://www.sec.gov/edgar/browse/?CIK={cik}" if cik else f"https://www.sec.gov/edgar/searchedgar/companysearch?company={t}"
                    filing_target = "SEC EDGAR Form 10-K / Form 10-Q 官方原始披露原文 (PDF/XBRL)"
                else:
                    official_url = "https://www.release.tdnet.info/inbs/I_main_00.html"
                    filing_target = "东证 TDnet 決算短信 / EDINET 有価証券報告書官方原文 (PDF)"

                tasks.append({
                    "ticker": t,
                    "market": m,
                    "company_name": name,
                    "cik": cik,
                    "jpx_code": jpx_code,
                    "official_search_url": official_url,
                    "target_filing": filing_target,
                    "required_line_items": [
                        "营业收入 (Revenue / Operating Revenue)",
                        "营业利润 (Operating Income / Operating Profit)",
                        "净利润 (Net Income)",
                        "资产总计 (Total Assets)",
                        "负债合计 (Total Liabilities)",
                        "股东权益合计 (Total Stockholders' Equity)",
                        "经营现金流量净额 (Operating Cash Flow)",
                        "存货与周转天数 (Inventory & DIO)",
                    ],
                    "replenishment_action": "由 AI 浏览器打开官方监管页面，核对后下载原版财报并调用 scripts/import_browser_source.py 登记入库",
                })

        manifest = {
            "title": "官方财报底账缺失企业 AI 浏览器补数任务清单",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "policy": "坚决执行真实数据准则。未取得官方权威财务三表原文前严禁生成伪造报表。本清单供 AI 浏览器专项补数使用。",
            "total_pending_companies": len(tasks),
            "tasks": tasks,
        }
        target_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(tasks)
