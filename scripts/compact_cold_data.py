#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""冷热数据分层加工、打样归档与秒级唤醒 CLI 工具 (compact_cold_data.py).

云端(GitHub)存放本加工方法，本地执行数据时效分级与高倍压缩：
- 热数据 (Hot Tier) : data/hot/filings_sec/   (近1~2年核心财报速查快照)
- 温数据 (Warm Tier): data/warm/filings_sec/  (近3年12季度标准对比底账 + 轻量索引清单)
- 冷数据 (Cold Tier): data/cold/filings_sec/  (3年以上历史老旧事实 .json.gz 高倍压缩归档)

常用命令:
    python scripts/compact_cold_data.py --status
    python scripts/compact_cold_data.py --sample-ticker NVDA
    python scripts/compact_cold_data.py --restore-check CIK0001045810
    python scripts/compact_cold_data.py --batch-sec --limit 50
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.governance_and_pipeline.data_lifecycle_manager import (
    DataLifecycleEngine,
    LifecyclePolicyConfig,
    TIER_METADATA_REGISTRY,
)


def _resolve_ticker_to_cik_stem(ticker: str, data_root: Path) -> Optional[str]:
    """根据本地证券底账映射表将股票代码 (如 NVDA) 解析为 CIK0001045810."""
    target = ticker.strip().upper()
    if target.startswith("CIK") and target[3:].isdigit():
        return f"CIK{int(target[3:]):010d}"

    universe_file = data_root / "universe" / "sec_company_tickers.json"
    if universe_file.is_file():
        try:
            mapping = json.loads(universe_file.read_text(encoding="utf-8"))
            items = mapping.values() if isinstance(mapping, dict) else mapping
            for row in items:
                if str(row.get("ticker", "")).upper() == target:
                    cik_num = int(row["cik_str"])
                    return f"CIK{cik_num:010d}"
        except Exception:
            pass

    # 常用核心旗舰备用保底映射
    fallback_map: Dict[str, str] = {
        "NVDA": "CIK0001045810",
        "AAPL": "CIK0000320193",
        "MSFT": "CIK0000789019",
        "GOOGL": "CIK0001652044",
        "META": "CIK0001326801",
        "AMD": "CIK0000002488",
        "AVGO": "CIK0001730168",
        "PLTR": "CIK0001321655",
    }
    return fallback_map.get(target)


def _fmt_mb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def _fmt_kb(num_bytes: int) -> str:
    return f"{num_bytes / 1024:.1f} KB"


def print_workspace_status(engine: DataLifecycleEngine, data_root: Path) -> None:
    """输出全盘冷热层级与原始未分层底账空间占用看板."""
    summary = engine.inspect_workspace_tiers(data_root)
    print("=" * 72)
    print("本地数据工作站 — 冷热温三层存储空间分布巡检")
    print("=" * 72)
    labels = {
        "hot": "🔥 热数据层 (data/hot)",
        "warm": "🌤️ 温数据层 (data/warm)",
        "cold": "❄️ 冷数据层 (data/cold)",
        "legacy_raw_sec": "📦 原始待分层财报底账 (data/official_filings/sec)",
    }
    for k, label in labels.items():
        info = summary[k]
        status = "就绪" if info["exists"] else "未初始化"
        print(f"  {label:<46} | {status:<6} | {info['file_count']:>5} 个文件 | {info['size_mb']:>8.2f} MB")
    print("-" * 72)
    for tier_key, meta in TIER_METADATA_REGISTRY.items():
        print(f"  {meta['badge']} {meta['zh_name']}: {meta['retention_rule']}")
        print(f"     商业用途: {meta['business_purpose']}")
    print("=" * 72)


def run_sample_poc(
    engine: DataLifecycleEngine,
    data_root: Path,
    ticker: Optional[str],
    sample_file: Optional[str],
    reference_year: Optional[int],
    prune_original: bool,
) -> int:
    """执行单标的冷热分层加工与无损唤醒验证打样."""
    if sample_file:
        src_path = Path(sample_file)
        if not src_path.is_absolute():
            src_path = PROJECT_ROOT / src_path
    else:
        t = ticker or "NVDA"
        cik_stem = _resolve_ticker_to_cik_stem(t, data_root)
        if not cik_stem:
            print(f"[失败] 未能在证券底账中找到股票代码 '{t}' 对应的官方 CIK 编号。")
            return 1
        src_path = data_root / "official_filings" / "sec" / f"{cik_stem}.json"

    if not src_path.is_file():
        print(f"[失败] 目标原始财报文件不存在: {src_path}")
        return 1

    print("=" * 72)
    print(f"启动冷热数据分层加工打样 (Sampling POC) -> {src_path.name}")
    print("=" * 72)

    report = engine.compact_sec_filing_file(
        source_file=src_path,
        data_root=data_root,
        reference_year=reference_year,
        prune_original=prune_original,
    )

    print(f"公司主体       : {report.entity_name} ({report.cik})")
    print(f"原文件体积     : {_fmt_mb(report.original_size_bytes)} (包含历史全周期 {report.total_original_items:,} 条事实记录)")
    print("-" * 72)
    print(f"🔥 热数据层    : {_fmt_kb(report.hot_size_bytes):>10} | {report.hot_items_count:>6,} 条 (近1~2年高频速查快照)")
    print(f"🌤️ 温数据层    : {_fmt_kb(report.warm_size_bytes):>10} | {report.warm_items_count:>6,} 条 (近3年12季度标准对比底账)")
    print(f"❄️ 冷数据层    : {_fmt_kb(report.cold_compressed_bytes):>10} | {report.cold_items_count:>6,} 条 (3年以上历史 .json.gz 高压归档)")
    print(f"📋 轻量索引清单: {_fmt_kb(report.manifest_size_bytes):>10} | 记录全量校验指纹 SHA-256")
    print("-" * 72)
    long_term_archive_bytes = report.warm_size_bytes + report.cold_compressed_bytes + report.manifest_size_bytes
    archive_saved_pct = round((1 - long_term_archive_bytes / report.original_size_bytes) * 100.0, 2)
    print(f"三层总占用     : {_fmt_mb(report.total_tiered_size_bytes)} (整体净压缩省空间: {report.space_saved_pct:.2f}%)")
    print(f"温+冷主干占用  : {_fmt_mb(long_term_archive_bytes)} (相对原始大文件节省: {archive_saved_pct:.2f}%)")
    print(f"无损唤醒验签   : {'[100% 通过] SHA-256 规范指纹与条目数完全吻合' if report.lossless_verified else '[校验失败]'}")
    print(f"原文件状态     : {'已安全清理腾出磁盘空间' if prune_original else '打样安全模式：完整保留原文件未删除'}")
    print("=" * 72)
    return 0 if report.lossless_verified else 1


def run_batch_sec(
    engine: DataLifecycleEngine,
    data_root: Path,
    limit: Optional[int],
    reference_year: Optional[int],
    prune_original: bool,
) -> int:
    """防阻塞批量加工全盘 SEC 官方财报底账."""
    sec_dir = data_root / "official_filings" / "sec"
    if not sec_dir.is_dir():
        print(f"[失败] 原始 SEC 财报目录不存在: {sec_dir}")
        return 1

    files = sorted(sec_dir.glob("CIK*.json"))
    if limit and limit > 0:
        files = files[:limit]

    total_orig = 0
    total_tiered = 0
    success = 0
    blocked = 0

    print(f"启动批量冷热分层处理，共待加工 {len(files)} 家上市公司财报底账...")
    for idx, src in enumerate(files, 1):
        try:
            rep = engine.compact_sec_filing_file(
                source_file=src,
                data_root=data_root,
                reference_year=reference_year,
                prune_original=prune_original,
            )
            total_orig += rep.original_size_bytes
            total_tiered += rep.total_tiered_size_bytes
            success += 1
            if idx % 25 == 0 or idx == len(files):
                print(f"  进度 [{idx}/{len(files)}] 已成功={success}, 隔离跳过={blocked}")
        except Exception as exc:
            blocked += 1
            print(f"  [故障隔离跳过] {src.name}: {exc}")

    saved_mb = (total_orig - total_tiered) / (1024 * 1024)
    saved_pct = ((total_orig - total_tiered) / total_orig * 100.0) if total_orig > 0 else 0.0
    print("=" * 72)
    print(f"批量冷热处理完成：成功 {success} 家，故障隔离 {blocked} 家")
    print(f"原始总体积: {_fmt_mb(total_orig)} -> 三层总体积: {_fmt_mb(total_tiered)} (累计节省 {saved_mb:.2f} MB / {saved_pct:.2f}%)")
    print("=" * 72)
    return 0 if blocked == 0 else 1


def run_restore_check(engine: DataLifecycleEngine, data_root: Path, cik_or_ticker: str) -> int:
    """对指定标的执行冷数据秒级唤醒与 SHA-256 无损还原检验."""
    cik_stem = _resolve_ticker_to_cik_stem(cik_or_ticker, data_root) or cik_or_ticker.strip()
    warm_path = data_root / "warm" / "filings_sec" / f"{cik_stem}.warm.json"
    cold_path = data_root / "cold" / "filings_sec" / f"{cik_stem}.cold.json.gz"
    manifest_path = data_root / "warm" / "manifests" / f"{cik_stem}.lifecycle_manifest.json"

    for p in (warm_path, cold_path, manifest_path):
        if not p.is_file():
            print(f"[失败] 缺少分层文件: {p}（请先运行 --sample-ticker 对该标的进行冷热加工）")
            return 1

    res = engine.restore_and_verify_from_tiers(warm_path, cold_path, manifest_path)
    print("=" * 72)
    print(f"冷数据唤醒还原验签报告 -> {res.entity_name} ({res.cik})")
    print(f"还原条目数   : {res.restored_items_count:,} / {res.expected_items_count:,}")
    print(f"预期指纹哈希 : {res.expected_canonical_sha256}")
    print(f"实测还原哈希 : {res.restored_canonical_sha256}")
    print(f"完整性结论   : {'[通过] ' + res.message if res.integrity_passed else '[失败] ' + res.message}")
    print("=" * 72)
    return 0 if res.integrity_passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="冷热数据分层加工、打样归档与秒级唤醒 CLI 工具 (GitHub 云端只放工具，本地处理数据)"
    )
    parser.add_argument("--data-root", default="data", help="本地数据根目录 (默认: data)")
    parser.add_argument("--ref-year", type=int, default=2026, help="时间切片基准年份 (默认: 2026)")
    parser.add_argument("--status", action="store_true", help="查看当前本地冷/温/热三层数据空间分布")
    parser.add_argument("--sample-ticker", help="执行单只股票的冷热分层打样 (如 NVDA, AAPL)")
    parser.add_argument("--sample-file", help="指定单个原始 SEC JSON 文件执行打样")
    parser.add_argument("--batch-sec", action="store_true", help="批量执行全盘 SEC 原始财报冷热分层")
    parser.add_argument("--limit", type=int, help="批量处理最大文件数限制")
    parser.add_argument("--restore-check", help="唤醒并验证指定股票/CIK 的冷热无损还原完整性")
    parser.add_argument(
        "--prune-original",
        action="store_true",
        help="谨慎选项：确认无损验签通过后清理原始未分层大文件（默认 False 保留原文件）",
    )

    args = parser.parse_args()
    data_root = Path(args.data_root)
    if not data_root.is_absolute():
        data_root = PROJECT_ROOT / data_root

    engine = DataLifecycleEngine(policy=LifecyclePolicyConfig())

    if args.status:
        print_workspace_status(engine, data_root)
        return 0
    if args.restore_check:
        return run_restore_check(engine, data_root, args.restore_check)
    if args.sample_ticker or args.sample_file:
        return run_sample_poc(
            engine=engine,
            data_root=data_root,
            ticker=args.sample_ticker,
            sample_file=args.sample_file,
            reference_year=args.ref_year,
            prune_original=args.prune_original,
        )
    if args.batch_sec:
        return run_batch_sec(
            engine=engine,
            data_root=data_root,
            limit=args.limit,
            reference_year=args.ref_year,
            prune_original=args.prune_original,
        )

    print_workspace_status(engine, data_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
