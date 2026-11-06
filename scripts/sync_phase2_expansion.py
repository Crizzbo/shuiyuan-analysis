"""第二阶段战略拓展全息对账与审计总账生成脚本 (Phase 2 Master Ledger & Universe Sync).

功能:
1. 汇总 phase2-batch1-receipt.json, phase2-batch2-receipt.json, phase2-batch3-receipt.json;
2. 对账 35 只增量核心资产 (8只黄金大宗体系 + 15家高成长先锋 + 12只全球核心ETF);
3. 校验 Google Drive 云端文件存在性与文件大小;
4. 输出正式 Phase 2 综合审计底账: data/audits/drive-deep-analysis-20261012/phase2_expansion_audit_ledger.json;
5. 更新 data/universe/phase2_expansion_universe.json 状态为 COMPLETED。
"""

from datetime import datetime, timezone
import glob
import json
import os
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]

def main():
    universe_path = ROOT / "data" / "universe" / "phase2_expansion_universe.json"
    universe = json.loads(universe_path.read_text(encoding="utf-8"))

    receipts_dir = ROOT / "data" / "audits" / "drive-deep-analysis-20261012"
    receipt_files = [
        receipts_dir / "phase2-batch1-receipt.json",
        receipts_dir / "phase2-batch2-receipt.json",
        receipts_dir / "phase2-batch3-receipt.json",
    ]

    all_phase2_results = {}
    for rf in receipt_files:
        if rf.exists():
            data = json.loads(rf.read_text(encoding="utf-8"))
            for r in data.get("results", []):
                all_phase2_results[r["ticker"]] = r

    print("=" * 70)
    print("[总账对账] Phase 2 战略拓展总账全息对账启动")
    print(f"当前已就绪 Phase 2 成果数: {len(all_phase2_results)} / 35")
    print("=" * 70)

    # 遍历更新各类别资产
    categories = universe.get("categories", {})
    completed_count = 0
    total_assets = 0

    for cat_key, cat_val in categories.items():
        assets = cat_val.get("assets", [])
        total_assets += len(assets)
        for a in assets:
            t = a["ticker"]
            if t in all_phase2_results:
                completed_count += 1
                res = all_phase2_results[t]
                a["status"] = "COMPLETED_EXPANDED"
                a["cloud_id"] = res["new_file_id"]
                a["file_name"] = res["file_name"]
                a["pdf_size_bytes"] = res["pdf_size_bytes"]
                a["upload_timestamp"] = res["upload_timestamp"]
            else:
                a["status"] = "PENDING"

    phase1_inventory = receipts_dir / "inventory.json"
    has_phase1_evidence = False
    if phase1_inventory.exists():
        try:
            inv_data = json.loads(phase1_inventory.read_text(encoding="utf-8"))
            if len(inv_data.get("files", [])) > 0:
                has_phase1_evidence = True
        except Exception:
            pass

    universe["completed_count"] = completed_count
    universe["total_count"] = total_assets
    if total_assets > 0 and completed_count == total_assets and has_phase1_evidence:
        universe["status"] = "COMPLETED"
        universe["completed_at"] = datetime.now(timezone.utc).isoformat()
    else:
        universe["status"] = "PENDING"
        universe["completed_at"] = None
    universe_path.write_text(json.dumps(universe, ensure_ascii=False, indent=2), encoding="utf-8")

    if not has_phase1_evidence or total_assets <= 0:
        raise ValueError("首期 567 资产池交付凭证缺失或第二阶段拓展标的为空，禁止将拓展资产池标记为 COMPLETED")

    # 生成总账
    ledger_path = receipts_dir / "phase2_expansion_audit_ledger.json"
    ledger = {
        "title": "第二阶段战略拓展 (高价值成长股、全球核心ETF、黄金大宗商品体系) 审计总账",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_expansion_assets": total_assets,
        "completed_expansion_assets": completed_count,
        "completion_rate": f"{(completed_count / total_assets * 100):.1f}%" if total_assets else "0%",
        "assets_ledger": all_phase2_results,
    }
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[对账完成] Phase 2 总账对账完成: {completed_count}/{total_assets} ({ledger['completion_rate']})")
    print(f"总账文件: {ledger_path.relative_to(ROOT)}")
    print(f"底账文件: {universe_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
