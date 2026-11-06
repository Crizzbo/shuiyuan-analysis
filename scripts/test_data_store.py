"""数据治理关键场景回归；临时存储与测试资料全部位于项目内。"""
import copy
import json
import sqlite3
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from data_store import LocalStore, destination, verify_backup
from validate_knowledge_structure import ROOT
from validate_research import load
from data_quality import report

def run_governance_suite():
    parent = destination(".cache")
    parent.mkdir(parents=True, exist_ok=True)
    count = 0
    def rejected(operation):
        nonlocal count
        try:
            operation()
        except (ValueError, sqlite3.IntegrityError):
            count += 1
        else:
            raise AssertionError("非法操作未拒绝")
    # TemporaryDirectory 仅清理已确认属于项目的本次生成目录。
    with tempfile.TemporaryDirectory(dir=parent, prefix="governance-") as temp:
        area = Path(temp).resolve()
        assert area.is_relative_to(parent) and area.is_relative_to(ROOT)
        source = area / "input.txt"
        source.write_text("original source", encoding="utf-8")
        manifest = load(ROOT / "examples/source.synthetic.manifest.json")
        manifest["source_path"] = source.relative_to(ROOT).as_posix()
        store = LocalStore((area.relative_to(ROOT) / "store").as_posix())
        try:
            first = store.register_source(manifest)
            assert store.register_source(manifest)["idempotent"]
            assert store.source_as_of(manifest["source_id"], "2026-10-10T11:59:59Z") is None
            assert store.source_as_of(manifest["source_id"], "2026-10-10T12:00:00Z")["manifest"]["revision"] == 1
            source.write_text("revised source", encoding="utf-8")
            rejected(lambda: store.register_source(manifest))
            second = copy.deepcopy(manifest)
            second.update(revision=2, supersedes_revision=1, available_at="2026-10-11T12:00:00Z", acquired_at="2026-10-11T12:00:00Z")
            store.register_source(second)
            assert store.source_as_of(manifest["source_id"], "2026-10-10T23:00:00Z")["manifest"]["revision"] == 1
            assert store.source_as_of(manifest["source_id"], "2026-10-12T00:00:00Z")["manifest"]["revision"] == 2
            rejected(lambda: store.register_source({**second, "revision": 4}))
            rejected(lambda: store.register_source({**second, "revision": 3, "supersedes_revision": 2, "available_at": "2026-10-10T12:00:00Z"}))
            rejected(lambda: store.register_source({**manifest, "source_id": "outside", "source_path": "../outside.txt"}))
            rejected(lambda: LocalStore("../outside"))
            rejected(lambda: LocalStore("C:/outside"))
            rejected(lambda: store.db.execute("UPDATE sources SET source_id='tampered'"))
            rejected(lambda: store.db.execute("DELETE FROM artifacts"))
            record = load(ROOT / "examples/completed.synthetic.json")
            quality = report(record)
            assert quality["status"] == "synthetic_only"
            assert len([i for i in quality["issues"] if i["kind"] == "missing_industry_driver"]) == 3
            stale = copy.deepcopy(record)
            for e in stale["evidence"]:
                for key in ("published_at", "available_at", "acquired_at"):
                    e[key] = "2026-01-01T00:00:00Z"
            stale["observations"][0]["available_at"] = "2026-01-01T00:00:00Z"
            stale["observations"][0]["period"].update(start="2025-12-31", end="2025-12-31")
            assert any(i["kind"] == "stale_observation" for i in report(stale)["issues"])
            fixture_manifest = load(ROOT / "examples/source.synthetic.manifest.json")
            fixture_manifest["source_id"] = "linked_fixture"
            store.register_source(fixture_manifest)
            fixture_record = copy.deepcopy(record)
            fixture_record["research_id"] = "linked_fixture_record"
            fixture_map = {e["id"]: {"source_id": "linked_fixture", "revision": 1} for e in fixture_record["evidence"]}
            store.save_research(fixture_record, fixture_map)
            assert store.save_research(fixture_record, fixture_map)["idempotent"]
            wrong_binding = copy.deepcopy(fixture_map)
            wrong_binding["e_main"] = {"source_id": manifest["source_id"], "revision": 1}
            rejected(lambda: store.save_research({**fixture_record, "research_id": "wrong_binding"}, wrong_binding))
            snapshot = store.save_research(record)
            assert store.save_research(record)["idempotent"]
            saved = store.get_research(record["research_id"], 1)
            assert saved["evidence"][0]["source_path"] != record["evidence"][0]["source_path"]
            assert store.research_as_of(record["research_id"], "2026-10-10T23:00:00Z") is None
            assert store.research_as_of(record["research_id"], "2026-10-11T00:00:00Z")["revision"] == 1
            conflict = copy.deepcopy(record)
            conflict["steps"][0]["notes"].append("different content")
            rejected(lambda: store.save_research(conflict))
            revision = copy.deepcopy(record)
            revision["revision"] = 2
            revision["steps"][0]["output"]["research_priorities"].append("new research priority")
            rejected(lambda: store.save_research(revision))
            revision["steps"][0]["version"] = 2
            for step in revision["steps"][1:]:
                step["version"] = 2
                for dep in step["inputs"]["dependencies"]:
                    dep["version"] = 2
            store.save_research(revision)
            assert store.get_research(record["research_id"])["revision"] == 2
            assert store.get_research(record["research_id"], 1)["steps"][0]["version"] == 1
            inputs_changed = copy.deepcopy(revision)
            inputs_changed["revision"] = 3
            inputs_changed["claims"][0]["statement"] = "changed assumption registry"
            rejected(lambda: store.save_research(inputs_changed))
            invalidated = copy.deepcopy(record)
            invalidated["research_id"] = "changed_file_test"
            for e in invalidated["evidence"]:
                e["source_path"] = source.relative_to(ROOT).as_posix()
            store.save_research(invalidated)
            source.write_text("input changed again", encoding="utf-8")
            rejected(lambda: store.save_research(invalidated))
            assert store.get_research("changed_file_test")["revision"] == 1
            assert store.audit()["ok"]
            context = store._research_context(record["research_id"], 1)
            assert context and set(context) == {"schema", "industries", "business_models", "metrics", "industry_rules", "quality_policy"}
            backup = (area.relative_to(ROOT) / "backup").as_posix()
            store.backup(backup)
            assert verify_backup(backup)["ok"]
            rejected(lambda: store.backup(backup))
            rejected(lambda: store.backup("../outside"))
            backup_manifest = load(area / "backup/backup-manifest.json")
            backup_file = area / "backup" / backup_manifest["files"][0]["relative_path"]
            content = backup_file.read_bytes()
            backup_file.write_bytes(b"tampered backup")
            rejected(lambda: verify_backup(backup))
            backup_file.write_bytes(content)
            assert verify_backup(backup)["ok"]
            raw = ROOT / first["archived_path"]
            content = raw.read_bytes()
            raw.write_bytes(b"tampered object")
            assert not store.audit()["ok"]
            rejected(lambda: store.source_as_of(manifest["source_id"], "2026-10-10T12:00:00Z"))
            raw.write_bytes(content)
            assert store.audit()["ok"]
            snapshot_file = ROOT / snapshot["snapshot_path"]
            content = snapshot_file.read_bytes()
            snapshot_file.write_bytes(b"{}")
            rejected(lambda: store.get_research(record["research_id"], 1))
            snapshot_file.write_bytes(content)
            assert store.audit()["ok"]
            # 合成资料不能静默变为真实研究；真实待填记录可存但仍未开始。
            pending = load(ROOT / "knowledge/templates/research.pending.json")
            assert report(pending)["status"] == "needs_review"
            store.save_research(pending)
            bad_link = {"e_main": {"source_id": "missing", "revision": 1}}
            new_record = {**record, "research_id": "bad_source_link"}
            rejected(lambda: store.save_research(new_record, bad_link))
            # 在独立目录恢复完整备份，并验证恢复操作未触碰原库。
            restored_base = area / "restored"
            shutil.copytree(area / "backup", restored_base)
            restored = LocalStore(restored_base.relative_to(ROOT).as_posix())
            try:
                assert restored.audit()["ok"]
                assert restored.get_research(record["research_id"], 1)["revision"] == 1
                assert restored.source_as_of(manifest["source_id"], "2026-10-10T12:00:00Z")["manifest"]["revision"] == 1
                assert store.audit()["ok"]
            finally:
                restored.close()
        finally:
            store.close()
    return count

def main():
    count = run_governance_suite()
    print(f"PASS: archive/idempotency/as-of/revisions/tamper/quality/backup/restore; {count} invalid operations rejected; isolated project-local test directory cleaned.")


class DataStoreGovernanceTests(unittest.TestCase):
    """数据治理体系全息回归测试类。"""

    def test_governance_full_lifecycle_and_invariants(self):
        """【IT-STORE-01: 数据底账全生命周期治理(幂等注册/时点追溯/版本演进/篡改物理阻断/质量巡检/备份灾备)】

        1. 测试功能与测试点:
           - 验证 LocalStore 核心数据治理体系的 6 大核心支柱:
             1. 原始数据源注册与幂等去重 (register_source)；
             2. 时点追溯查询 (source_as_of / research_as_of)；
             3. 数据库底层 SQLite 只追加触发器 (禁止 UPDATE / DELETE)；
             4. 数据质量与评级审计 (report)；
             5. 研报六步因果依赖与修改冲突拦截；
             6. 物理二进制归档 (.blob) 与快照防篡改审计 (audit) 及热备还原 (backup / restore)。

        2. 正常函数业务边界与参数契约:
           - 路径必须为相对路径且必须位于项目根目录内 (ROOT)。
           - 版本号 revision 必须严格单调递增，版本覆盖必须显式声明 supersedes_revision。
           - 任何非法参数、非法时间戳、越界路径及篡改行为必须刚性抛出 (ValueError, sqlite3.IntegrityError)。

        3. 测试数据与模拟场景说明:
           - 模拟 19 组非法操作（越界路径 '../outside'、跨盘符 'C:/outside'、直接 SQL UPDATE/DELETE、时点穿越、内容篡改等）。

        4. 预期断言与结果验证:
           - 19 次非法操作全部被拒绝拦截；
           - 备份与恢复后 audit()["ok"] 为 True；
           - 时点查询返回预期版本的元数据快照。
        """
        count = run_governance_suite()
        self.assertEqual(count, 19)

    def test_path_boundary_enforcement(self):
        """【UT-STORE-02: 存储路径边界防御-绝对路径与上级越界拦截】

        1. 测试功能与测试点:
           - 验证 destination 与 LocalStore 强隔离校验机制。
           - 严禁传入项目根目录外的跨界路径 ('../outside') 或绝对盘符路径 ('C:/outside')。

        2. 正常函数业务边界与参数契约:
           - 非法路径必须引发 ValueError。

        3. 测试数据与模拟场景说明:
           - 传入 '../outside' 与 'C:/outside'。

        4. 预期断言与结果验证:
           - 均抛出 ValueError。
        """
        with self.assertRaises(ValueError):
            destination("../outside")
        with self.assertRaises(ValueError):
            destination("C:/outside")

    def test_data_quality_report_policy(self):
        """【UT-STORE-03: 数据质量报告评估(质量评级/合成数据标记/过期观测拦截)】

        1. 测试功能与测试点:
           - 验证 data_quality.report 对研究记录的质量策略校验。
           - 合成测试样例必须精准打标为 status == 'synthetic_only'。
           - 待填入模板必须标记为 status == 'needs_review'。

        2. 正常函数业务边界与参数契约:
           - 接收合法字典结构，返回 status 和 issues 列表。

        3. 测试数据与模拟场景说明:
           - completed.synthetic.json 与 research.pending.json。

        4. 预期断言与结果验证:
           - synthetic 样例状态为 'synthetic_only'。
           - pending 模板状态为 'needs_review'。
        """
        record = load(ROOT / "examples/completed.synthetic.json")
        q = report(record)
        self.assertEqual(q["status"], "synthetic_only")

        pending = load(ROOT / "knowledge/templates/research.pending.json")
        q_pending = report(pending)
        self.assertEqual(q_pending["status"], "needs_review")


if __name__ == "__main__":
    main()
