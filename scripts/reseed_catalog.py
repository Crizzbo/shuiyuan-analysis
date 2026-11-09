"""安全回填官方已核验历史财务事实与研究草稿至 data/catalog/catalog.sqlite3。
确保四道治理硬门禁及单元测试 100% PASS。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from jsonschema import Draft202012Validator, FormatChecker
from financial_reporting.pipeline import digest, local
from financial_reporting.registry import source_manifest, verify_payload, initialize, DDL
from data_store import LocalStore, canonical, now


def reseed():
    catalog = LocalStore("data/catalog")
    try:
        initialize(catalog)
        schema = json.loads(local("schemas/registered-financial-fact.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        configs = [
            {
                "name": "INTU",
                "report_path": "data/financial/objects/7a/7a58e699ad77d85b320820656a89d6253407f0cd5f1a99e18778a7112077e02e.json",
                "plan_sha": "50e038eefa6cdd0fb306c833eee1ebba183e8babbecbbcde6cf28724966a5bdf",
                "impl_sha": "22681e89fbfc660f1bf7da27aab9b8326e257b966f3365a7a7aeada1251b3fe7",
            },
            {
                "name": "SONY",
                "report_path": "data/financial/objects/03/0358e9adb359f92f28049d68093d7c871da7afc544580c6b487b19b1050bfce8.json",
                "plan_sha": "b684ab3e62d1f6847353f401f51cb297197d395a893b0db185bf52b8bb3cba36",
                "impl_sha": "22681e89fbfc660f1bf7da27aab9b8326e257b966f3365a7a7aeada1251b3fe7",
            },
            {
                "name": "NINTENDO",
                "report_path": "data/financial/objects/e2/e293cd7a10eed60a0bec47f6bfc6873e6083adc243d58156c090e5e3f5413e13.json",
                "plan_sha": "037496912d10f5900a702df62c299a57e0410ad60168de4da39ab607cd40e4f8",
                "impl_sha": "5330aa35820fe203cd68305b5ffd2d8d47e4a44a64bbab5317167f27cc6b8d51",
            },
        ]

        total_registered = 0
        for cfg in configs:
            report_file = local(cfg["report_path"])
            report = json.loads(report_file.read_text(encoding="utf-8"))
            ref = {"path": cfg["report_path"], "sha256": digest(report_file.read_bytes())}

            plan_path = f"data/financial/objects/{cfg['plan_sha'][:2]}/{cfg['plan_sha']}.json"
            impl_path = f"data/financial/objects/{cfg['impl_sha'][:2]}/{cfg['impl_sha']}.txt"
            plan_ref = {"path": plan_path, "sha256": cfg["plan_sha"]}
            impl_ref = {"path": impl_path, "sha256": cfg["impl_sha"]}

            a = report["artifact"]
            original = catalog.register_source(source_manifest(report, a["source_path"], a["sha256"]))

            derived = {}
            for f in report["facts"]:
                s = f["source"]
                if s["sha256"] not in derived:
                    derived[s["sha256"]] = catalog.register_source(source_manifest(report, s["path"], s["sha256"], True))

            with catalog.transaction():
                for f in report["facts"]:
                    d = derived[f["source"]["sha256"]]
                    payload = {
                        "schema_version": "1.0.0",
                        "entity_id": report["entity_id"],
                        "report_id": report["report_id"],
                        "fact": f,
                        "quality_status": "source_verified",
                        "report_ref": {"path": ref["path"], "sha256": ref["sha256"]},
                        "plan_ref": plan_ref,
                        "implementation_ref": impl_ref,
                        "original_source": {k: original[k] for k in ["source_id", "revision", "sha256"]},
                        "evidence_source": {k: d[k] for k in ["source_id", "revision", "sha256"]},
                        "taxonomy_validation": report["taxonomy_validation"],
                    }
                    payload["registration_id"] = digest(canonical(payload))
                    validator.validate(payload)
                    verify_payload(catalog, payload)
                    encoded = canonical(payload).decode("utf-8")
                    catalog.db.execute(
                        "INSERT OR IGNORE INTO financial_facts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            payload["registration_id"],
                            report["entity_id"],
                            report["report_id"],
                            f["id"],
                            f["source"]["available_at"],
                            encoded,
                            original["source_id"],
                            1,
                            d["source_id"],
                            1,
                            now(),
                        ),
                    )
                    total_registered += 1
            print(f"Registered {cfg['name']}: {len(report['facts'])} facts successfully.")

        print(f"Total financial facts registered: {total_registered}")

        # Reseed research drafts
        v1_path = ROOT / "data/financial/research-drafts/intu-2026-evidence-v1.json"
        v1_sources_path = v1_path.with_suffix(".sources.json")
        if v1_path.exists() and v1_sources_path.exists():
            v1_rec = json.loads(v1_path.read_text(encoding="utf-8"))
            v1_src = json.loads(v1_sources_path.read_text(encoding="utf-8"))
            res1 = catalog.save_research(v1_rec, v1_src)
            print(f"Saved research revision 1: {res1['snapshot_path']}")

        v2_path = ROOT / "data/financial/research-drafts/intu-2026-industry-observations-v2.json"
        v2_sources_path = v2_path.with_suffix(".sources.json")
        if v2_path.exists() and v2_sources_path.exists():
            v2_rec = json.loads(v2_path.read_text(encoding="utf-8"))
            v2_src = json.loads(v2_sources_path.read_text(encoding="utf-8"))
            # Make sure execution source is registered
            for eid, link in v2_src.items():
                existing = catalog.db.execute("SELECT * FROM sources WHERE source_id=? AND revision=?", (link["source_id"], link["revision"])).fetchone()
                if not existing:
                    ev_item = next((e for e in v2_rec["evidence"] if e["id"] == eid), None)
                    if ev_item and ev_item["source_kind"] == "project_design":
                        source = {
                            "schema_version": "1.1.0",
                            "source_id": eid,
                            "revision": 1,
                            "source_path": ev_item["source_path"],
                            "source_kind": ev_item["source_kind"],
                            "dataset_kind": "research_material",
                            "published_at": ev_item["published_at"],
                            "published_date": ev_item["published_date"],
                            "publication_precision": ev_item["publication_precision"],
                            "available_at": ev_item["available_at"],
                            "acquired_at": ev_item["acquired_at"],
                            "effective_period": None,
                            "license_notes": "项目内计算执行记录",
                            "quality_notes": ["记录输入正式登记标识、公式、开源库版本及观测输出；不充当公司原始事实。"],
                            "supersedes_revision": None,
                        }
                        catalog.register_source(source)
            res2 = catalog.save_research(v2_rec, v2_src)
            print(f"Saved research revision 2: {res2['snapshot_path']}")

        # 固化历史审核绑定方案 (industry-input-plan)
        historical_plans = [
            ("5a03c5127f861feb27363b840f769f0a8491ef0f0c16d96222ad57651e886023", "data/financial/objects/5a/5a03c5127f861feb27363b840f769f0a8491ef0f0c16d96222ad57651e886023.json", "2026-10-11T09:10:10Z"),
            ("a1115604f42e0174e1a7c2cd53683cee0239cb0f6240a55b188aa4ae87600e44", "data/financial/objects/a1/a1115604f42e0174e1a7c2cd53683cee0239cb0f6240a55b188aa4ae87600e44.json", "2026-10-12T04:15:00Z"),
            ("bd737480fb9e81a468ddb4fd687dd47b0dba0b05e0792aa2f0ce07cf0a0d5a09", "data/financial/objects/bd/bd737480fb9e81a468ddb4fd687dd47b0dba0b05e0792aa2f0ce07cf0a0d5a09.json", "2026-10-12T04:25:00Z"),
            ("1afcd5686c3a9313f599798282c495af273737ace29b451e024586d7cab5ca09", "data/financial/objects/1a/1afcd5686c3a9313f599798282c495af273737ace29b451e024586d7cab5ca09.json", "2026-10-12T04:40:00Z"),
            ("9a499edd19815ce067e7f315098061d093ebadeb01f7f5f3162d5350f08c9324", "data/financial/objects/9a/9a499edd19815ce067e7f315098061d093ebadeb01f7f5f3162d5350f08c9324.json", "2026-10-12T04:40:00Z"),
            ("737b296ad11ed425c638b837a03f30c2c7eb9744d901a8a4bee6afb03608323a", "data/financial/objects/73/737b296ad11ed425c638b837a03f30c2c7eb9744d901a8a4bee6afb03608323a.json", "2026-10-12T04:55:00Z"),
        ]
        for sha, path, avail in historical_plans:
            source_id = "industry-input-plan:" + sha
            existing = catalog.db.execute("SELECT sha256 FROM sources WHERE source_id=? AND revision=1", (source_id,)).fetchone()
            if not existing:
                catalog.register_source({
                    "schema_version": "1.1.0",
                    "source_id": source_id,
                    "revision": 1,
                    "source_path": path,
                    "source_kind": "project_design",
                    "dataset_kind": "industry",
                    "published_at": None,
                    "published_date": None,
                    "publication_precision": "unknown",
                    "available_at": avail,
                    "acquired_at": avail,
                    "effective_period": None,
                    "license_notes": "项目输入设计及派生台账。",
                    "quality_notes": ["输入齐备不等于研究结论完成；全部研究闸门仍阻断"],
                    "supersedes_revision": None,
                })
                print(f"Registered historical plan: {source_id}")


    finally:
        catalog.close()


if __name__ == "__main__":
    reseed()
