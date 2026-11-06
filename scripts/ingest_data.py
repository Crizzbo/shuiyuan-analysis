"""免费数据接入 CLI：状态、计划、断点执行、原文审计。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_ingestion.core import Archive, HTTP, IngestionError, encode, project_path, utcnow
from data_ingestion.providers import Providers

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def read(relative):
    return json.loads(project_path(relative).read_text(encoding="utf-8-sig"))


def run_plan(plan, archive, sources, refresh=False, offline=False):
    """每项任务独立失败；成功项按任务定义摘要恢复，失败项下次重试。"""
    if plan.get("schema_version") != "1.0.0" or not isinstance(plan.get("jobs"), list):
        raise ValueError("任务计划版本或 jobs 错误")
    if len(plan["jobs"]) > 200:
        raise ValueError("每次最多 200 项任务，请分批")
    runner = Providers(HTTP(archive, sources))
    results = []
    ids = set()
    for job in plan["jobs"]:
        if not isinstance(job, dict) or set(job) - {"id", "provider", "dataset", "params"}:
            raise ValueError("任务字段错误")
        if not isinstance(job.get("id"), str) or not job["id"] or job["id"] in ids:
            raise ValueError("任务 id 必须非空且不重复")
        ids.add(job["id"])
        if job.get("provider") not in sources or not isinstance(job.get("dataset"), str) or not isinstance(job.get("params", {}), dict):
            raise ValueError("来源、数据集或参数错误")
    for job in plan["jobs"]:
        key = hashlib.sha256(encode(job)).hexdigest()
        if sources[job["provider"]].get("enabled") is False or sources[job["provider"]].get("env"):
            results.append({"id": job["id"], "provider": job["provider"], "dataset": job["dataset"],
                            "status": "browser_required", "message": "用户停用需配置来源，使用 AI 浏览器检索官方原文",
                            "search_context": job.get("params", {})})
            continue
        previous = archive.db.execute("SELECT result FROM jobs WHERE job_id=?", (key,)).fetchone()
        if previous and not refresh:
            saved = json.loads(previous[0])
            # 成功定义来自业务校验，原文和规范化结果都需核验摘要。
            if saved["status"] in ("collected", "no_data"):
                try:
                    for artifact in saved.get("artifacts", []):
                        if hashlib.sha256(project_path(artifact["source_path"]).read_bytes()).hexdigest() != artifact["sha256"]:
                            raise IngestionError("integrity_error", "历史任务原文被篡改")
                    result_path = project_path(saved["result_path"])
                    if hashlib.sha256(result_path.read_bytes()).hexdigest() != saved["result_sha256"]:
                        raise IngestionError("integrity_error", "历史任务结果被篡改")
                    results.append(dict(saved, resumed=True))
                    continue
                except OSError:
                    raise IngestionError("integrity_error", "历史任务文件丢失") from None
        if offline:
            results.append({"id": job["id"], "status": "offline_miss"})
            continue
        try:
            result = runner.execute(job)
        except IngestionError as exc:
            result = {"status": exc.status, "message": str(exc), "artifacts": runner.artifacts}
        except (ValueError, KeyError, TypeError):
            result = {"status": "invalid_request_or_response", "message": "请求参数或上游结构不符合预期", "artifacts": runner.artifacts}
        result.update(id=job["id"], provider=job["provider"], dataset=job["dataset"], completed_at=utcnow())
        # 规范化结果仍在 staging：未经字段口径审核，不自动进入六步研究事实。
        raw = encode(result)
        sha = hashlib.sha256(raw).hexdigest()
        path = archive.base / "results" / f"{sha}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
        summary = {k: v for k, v in result.items() if k != "records"}
        summary.update(result_path=path.relative_to(ROOT).as_posix(), result_sha256=sha, record_count=len(result.get("records", [])))
        archive.db.execute("INSERT OR REPLACE INTO jobs VALUES(?,?,?)", (key, encode(summary).decode(), utcnow()))
        archive.db.commit()
        results.append(summary)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="data/ingestion-sources.json")
    parser.add_argument("--store", default="data/ingestion")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    run = sub.add_parser("run")
    run.add_argument("plan")
    run.add_argument("--refresh", action="store_true", help="重新检查任务，HTTP 缓存按 TTL 控制")
    run.add_argument("--offline", action="store_true", help="只恢复本地成功结果，不发请求")
    sub.add_parser("audit")
    args = parser.parse_args()
    archive = None
    try:
        config = read(args.config)
        if config.get("policy", {}).get("free_only") is not True or config["policy"].get("automatic_paid_fallback") is not False:
            raise ValueError("接入配置必须启用免费策略并关闭收费回退")
        sources = config["sources"]
        if args.command == "status":
            output = [{"provider": key, "configuration": "disabled_by_user" if value.get("enabled") is False or value.get("env") else "ready",
                       "fallback": "ai_browser_search" if value.get("enabled") is False or value.get("env") else None,
                       "connection_test": "not_tested_by_status_command", "notes": value["notes"]} for key, value in sources.items()]
        else:
            archive = Archive(args.store)
            if args.command == "run":
                output = run_plan(read(args.plan), archive, sources, args.refresh, args.offline)
            else:
                errors = []
                for row in archive.db.execute("SELECT path,sha256 FROM responses"):
                    try:
                        if hashlib.sha256(project_path(row["path"]).read_bytes()).hexdigest() != row["sha256"]:
                            errors.append(row["path"])
                    except OSError:
                        errors.append(row["path"])
                output = {"ok": not errors, "invalid_artifacts": errors, "responses": archive.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if args.command == "run" and any(x["status"] not in ("collected", "no_data") for x in output):
            raise SystemExit(2)
        if args.command == "audit" and not output["ok"]:
            raise SystemExit(2)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    finally:
        if archive:
            archive.close()


if __name__ == "__main__":
    main()
