"""将实际任务账本导出为本地验收记录，不发网络请求或读取密钥值。"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_ingestion.core import Archive, encode, project_path, utcnow
import hashlib


def main():
    archive = Archive()
    try:
        current = {}
        for row in archive.db.execute("SELECT result FROM jobs ORDER BY updated_at"):
            item = json.loads(row[0])
            current[item["id"]] = item
        jobs = []
        for item in current.values():
            # 验证完整结果及原文存在，再将 collected 标为实测成功。
            valid = hashlib.sha256(project_path(item["result_path"]).read_bytes()).hexdigest() == item["result_sha256"]
            valid = valid and all(hashlib.sha256(project_path(a["source_path"]).read_bytes()).hexdigest() == a["sha256"] for a in item.get("artifacts", []))
            jobs.append({"id": item["id"], "provider": item["provider"], "dataset": item["dataset"],
                         "status": item["status"], "record_count": item["record_count"],
                         "completed_at": item["completed_at"], "result_path": item["result_path"],
                         "result_sha256": item["result_sha256"], "integrity_ok": valid})
        config = json.loads((ROOT / "data/ingestion-sources.json").read_text(encoding="utf-8"))
        result = {"schema_version": "1.0.0", "recorded_at": utcnow(), "free_only": True,
                  "notes": ["实测仅代表本次请求，不能证明长期稳定或全市场完整覆盖", "最新策略：需配置的 6 个接口停用，改由 AI 浏览器检索公开原文", "record_count 为顶层对象数，非每个内嵌数据点总数；jobs 保留历史验收状态"],
                  "providers": [{"id": key, "selection": "disabled_by_user" if value.get("env") or value.get("enabled") is False else "active", "live_test": "passed_sample" if any(x["provider"] == key and x["status"] == "collected" and x["integrity_ok"] for x in jobs) else "not_verified"} for key, value in config["sources"].items()],
                  "browser_receipts": [p.relative_to(ROOT).as_posix() for p in (ROOT / "data/browser-search/receipts").glob("*.json")],
                  "jobs": jobs}
        (ROOT / "data/ingestion-verification.json").write_bytes(encode(result) + b"\n")
        print(f"Recorded {len(jobs)} current jobs; {sum(x['status']=='collected' for x in jobs)} collected")
    finally:
        archive.close()


if __name__ == "__main__":
    main()
