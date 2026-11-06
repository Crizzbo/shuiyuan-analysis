"""全盘数千家美股官方数据批量收集与平账管道 (run_multi_thousand_sec_collection.py).

严格遵循 2026-10-11 官方免费数据接入策略与 2026-10-12 全盘数千家资产池规范：
1. 采用 SEC EDGAR 官方免费公共开放接口 (无需任何 API Key、App ID 或账号认证)；
2. 遵守 SEC 官方访问规范 (合规声明 User-Agent，请求频率保护)；
3. 将远程抓取结果先行归档为项目内本地二级来源 (data/official_filings/sec/)，杜绝生成虚假财务数据；
4. 严格执行会计恒等式平账校验 (Assets = Liabilities + StockholdersEquity，容差 <= 0.1%)；
5. 缺失数据规范化生成 AI 浏览器补数清单 (Replenishment Gap Manifest)，严禁虚假填补；
6. 支持分批切片调度 (Batch Chunking)、并发防锁与增量断点续传。
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.sec_edgar_collector import (
    OfficialSecEdgarCollector,
    SecExtractedFinancialFacts,
)
from financial_core.engines.tiered_universe_manager import (
    TieredUniverseManager,
    UniverseCompanyRecord,
)
from financial_core.engines.filing_mapper import (
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)
from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway

DEFAULT_PROGRESS_PATH = ROOT / "data" / "pipeline_state" / "sec_collection_progress.json"


class SecCollectionProgressManager:
    """原子化 SEC 数据收集断点续传状态机."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "version": "1.0.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_attempted": 0,
                "balanced_count": 0,
                "unbalanced_or_deficient": 0,
            },
            "records": {},
        }

    def save(self) -> None:
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

    def is_completed(self, ticker: str) -> bool:
        rec = self.data["records"].get(ticker.upper())
        return rec is not None and rec.get("status") == "COMPLETED"

    def record_success(self, facts: SecExtractedFinancialFacts) -> None:
        self.data["records"][facts.ticker] = {
            "status": "COMPLETED",
            "cik": facts.cik,
            "company_name": facts.company_name,
            "fiscal_year": facts.fiscal_year,
            "fiscal_year_end": facts.fiscal_year_end,
            "revenue": facts.revenue,
            "total_assets": facts.total_assets,
            "is_balanced": facts.is_balanced,
            "balance_sheet_diff": facts.balance_sheet_diff,
            "source_filing": facts.source_filing,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.data["summary"]["balanced_count"] = sum(
            1 for r in self.data["records"].values() if r.get("status") == "COMPLETED"
        )
        self.data["summary"]["total_attempted"] = len(self.data["records"])

    def record_deficient(self, ticker: str, cik: str, reason: str) -> None:
        self.data["records"][ticker.upper()] = {
            "status": "DEFICIENT",
            "cik": cik,
            "reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.data["summary"]["unbalanced_or_deficient"] = sum(
            1 for r in self.data["records"].values() if r.get("status") == "DEFICIENT"
        )
        self.data["summary"]["total_attempted"] = len(self.data["records"])


def run_collection_pipeline(
    target_group: str = "missing_tier1",
    tickers_override: Optional[List[str]] = None,
    limit: Optional[int] = None,
    batch_size: int = 50,
    delay_sec: float = 0.15,
    resume: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """执行全盘数千家官方数据批量收集与平账管道."""
    print("=" * 80)
    print("【全盘数千家美股官方数据批量收集与平账管道】")
    print(f"执行时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"运行模式: 目标群体={target_group}, 批次大小={batch_size}, 速率延迟={delay_sec}秒, 断点续传={resume}")
    print("=" * 80)

    progress_mgr = SecCollectionProgressManager(DEFAULT_PROGRESS_PATH)
    universe_mgr = TieredUniverseManager.get_instance()
    universe_mgr.load_universe()

    # 1. 确定目标标的清单
    target_candidates: List[UniverseCompanyRecord] = []

    if tickers_override:
        for t in tickers_override:
            rec = universe_mgr.lookup(t, "US")
            if rec:
                target_candidates.append(rec)
            else:
                target_candidates.append(
                    UniverseCompanyRecord(
                        ticker=t.upper(),
                        company_name=t.upper(),
                        market="US",
                        tier="TIER_3",
                    )
                )
    elif target_group == "missing_tier1":
        # 针对 78 批次中已有定性画像但缺失三表底账的 371 家中坚标的
        all_v = UnifiedDataCollectionGateway.load_all_verified_dossiers_indexed()
        missing_tickers = [t for t, d in all_v.items() if not d.get("raw_financials_table")]
        for t in missing_tickers:
            rec = universe_mgr.lookup(t, "US")
            if rec and rec.cik:
                target_candidates.append(rec)
    elif target_group == "sp500":
        target_candidates = universe_mgr.get_sp500_priority_collection_list(unarchived_only=False)
    else:  # all_sec
        # 优先聚焦普通股经营实体，剔除优先股与债权衍生细分代码 (含短横线如 BAC-PB)
        target_candidates = [c for c in universe_mgr._us_companies.values() if "-" not in c.ticker]

    # 过滤出有 CIK 的标的
    valid_targets = [c for c in target_candidates if c.cik]

    if resume:
        pending_targets = [c for c in valid_targets if not progress_mgr.is_completed(c.ticker)]
    else:
        pending_targets = valid_targets

    if limit is not None and limit > 0:
        pending_targets = pending_targets[:limit]

    print(f"目标标的总数: {len(target_candidates)}, 具备有效CIK数: {len(valid_targets)}, 本次待处理数: {len(pending_targets)}")

    if dry_run:
        print("[DRY-RUN] 预览前 10 家待抓取标的:")
        for idx, item in enumerate(pending_targets[:10], start=1):
            print(f"  {idx}. {item.ticker} | CIK={item.cik} | {item.company_name} | 层级={item.tier}")
        return {"status": "DRY_RUN_COMPLETED", "pending_count": len(pending_targets)}

    # 2. 分批流水线执行
    total_processed = 0
    balanced_this_run = 0
    deficient_this_run = 0
    deficient_items: List[Dict[str, Any]] = []

    for i in range(0, len(pending_targets), batch_size):
        chunk = pending_targets[i : i + batch_size]
        batch_no = (i // batch_size) + 1
        total_batches = (len(pending_targets) + batch_size - 1) // batch_size
        print(f"\n--- 正在处理第 [{batch_no}/{total_batches}] 批 (规模: {len(chunk)} 家) ---")

        for rec in chunk:
            total_processed += 1
            ticker = rec.ticker
            cik = rec.cik

            try:
                # 1. 抓取并自动本地归档
                raw_facts = OfficialSecEdgarCollector.fetch_company_facts_by_cik(
                    cik=cik,
                    timeout=15.0,
                    force_refresh=False,
                )

                # 2. 提取并对齐三表平衡底账
                extracted = OfficialSecEdgarCollector.extract_aligned_financial_facts(
                    companyfacts=raw_facts,
                    ticker=ticker,
                )

                # 3. 记录平账成功
                progress_mgr.record_success(extracted)
                balanced_this_run += 1
                diff_str = f"${extracted.balance_sheet_diff:,.0f}" if extracted.balance_sheet_diff > 0 else "0.00"
                print(
                    f"  [OK] {ticker:5s} (CIK:{cik}) | FY{extracted.fiscal_year} | "
                    f"营收: ${extracted.revenue / 1e9:6.2f}B | 资产: ${extracted.total_assets / 1e9:6.2f}B | "
                    f"平账偏差: {diff_str} (完美平账)"
                )

            except (BalanceSheetIdentityError, IncompleteFilingFactError, FileNotFoundError, RuntimeError) as e:
                err_msg = str(e)
                progress_mgr.record_deficient(ticker, cik, err_msg)
                deficient_this_run += 1
                deficient_items.append({
                    "ticker": ticker,
                    "market": "US",
                    "company_name": rec.company_name,
                    "cik": cik,
                    "reason": err_msg,
                })
                print(f"  [DEFICIENT] {ticker:5s} (CIK:{cik}) | 阻断入库: {err_msg}")

            # 速率保护延迟
            if delay_sec > 0:
                time.sleep(delay_sec)

        # 批次保存进度
        progress_mgr.save()
        print(f"--- 第 [{batch_no}/{total_batches}] 批完成落盘，当前累计平账入库: {progress_mgr.data['summary']['balanced_count']} 家 ---")

    # 3. 若有缺失或破损数据，规范化追加至 AI 浏览器补数清单
    if deficient_items:
        UnifiedDataCollectionGateway.generate_replenishment_gap_manifest(deficient_items)
        print(f"\n已将 {len(deficient_items)} 家缺失/不平账标的规范化登记至 AI 浏览器补数清单 data/browser-search/replenishment_tasks.json")

    summary_res = {
        "status": "COMPLETED",
        "processed_this_run": total_processed,
        "balanced_this_run": balanced_this_run,
        "deficient_this_run": deficient_this_run,
        "total_balanced_all_time": progress_mgr.data["summary"]["balanced_count"],
        "total_deficient_all_time": progress_mgr.data["summary"]["unbalanced_or_deficient"],
    }

    print("\n" + "=" * 80)
    print("【批量收集与平账管道执行汇报】")
    print(f"本次扫描标的: {total_processed} 家")
    print(f"本次新入账平账标的: {balanced_this_run} 家")
    print(f"本次阻断缺数标的: {deficient_this_run} 家")
    print(f"系统累计官方平账底账总数: {summary_res['total_balanced_all_time']} 家")
    print(f"系统累计待补数底账总数: {summary_res['total_deficient_all_time']} 家")
    print("=" * 80)

    return summary_res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="全盘数千家美股官方数据批量收集与平账管道")
    parser.add_argument(
        "--target-group",
        choices=["missing_tier1", "sp500", "all_sec"],
        default="missing_tier1",
        help="目标群体类型: missing_tier1 (优先填补缺表企业), sp500 (标普500核心池), all_sec (全市场数千家)",
    )
    parser.add_argument("--tickers", type=str, default="", help="指定个股代码逗号分隔列表")
    parser.add_argument("--limit", type=int, default=None, help="本次抓取最大企业上限")
    parser.add_argument("--batch-size", type=int, default=20, help="每批次大小")
    parser.add_argument("--delay-sec", type=float, default=0.15, help="请求间隔节流秒数")
    parser.add_argument("--no-resume", action="store_true", help="禁用断点续传重新扫描")
    parser.add_argument("--dry-run", action="store_true", help="试运行预览，不发起真实网络请求")

    args = parser.parse_args()
    tickers_list = [x.strip().upper() for x in args.tickers.split(",") if x.strip()] if args.tickers else None

    run_collection_pipeline(
        target_group=args.target_group,
        tickers_override=tickers_list,
        limit=args.limit,
        batch_size=args.batch_size,
        delay_sec=args.delay_sec,
        resume=not args.no_resume,
        dry_run=args.dry_run,
    )
