"""验证四层发布探针注册和清单覆盖的运行入口。"""

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_project_contracts as audit


class ReleaseAuditTests(unittest.TestCase):
    def test_stage_matrix_assigns_every_probe(self):
        plan = audit.stage_plan()
        self.assertEqual([stage["id"] for stage in plan["stages"]],
                         ["inputs", "models", "state", "reports", "delivery"])
        self.assertEqual({spec["id"] for spec in plan["specs"]}, {f"SPEC-{i:02d}" for i in range(1, 13)})
        self.assertTrue(any(not row["checks"] for row in plan["scenarios"]))
        self.assertEqual({key for row in plan["scenarios"] for key in row["checks"]},
                         {case.key for case in audit.CHECKS})

    def test_staged_run_deduplicates_and_blocks_pending(self):
        from unittest.mock import Mock
        fixture = replace(next(case for case in audit.CHECKS if case.key == "T01"), run=Mock(return_value="通过"))
        template = {"stage": "state", "design": "docs", "scenario": "测试场景", "evidence": "测试证据"}
        scenarios = [dict(template, id=f"S-{index}", checks=checks)
                     for index, checks in enumerate((["T01"], ["T01"], []))]
        plan = {"stages": [{"id": "state", "title": "状态"}], "scenarios": scenarios}
        output = StringIO()
        with patch.object(audit, "stage_plan", return_value=plan), patch.object(audit, "CHECKS", [fixture]), \
             patch.object(audit, "install_isolation"), redirect_stdout(output):
            self.assertEqual(audit.main(["--stage", "all", "--json"]), 1)
        fixture.run.assert_called_once()
        report = json.loads(output.getvalue())
        self.assertEqual(report["pending_scenarios"], ["S-2"])
        self.assertEqual([row["status"] for row in report["scenarios"]], ["PASS", "PASS", "PENDING"])

    def test_registry_links_only_to_known_plan_points(self):
        rows = list(audit.coverage_rows())
        ids = {row["point"] for row in rows}
        self.assertEqual(len(rows), len(ids))
        self.assertGreaterEqual(len(rows), 50)
        self.assertEqual(len(audit.CHECKS), len({case.key for case in audit.CHECKS}))
        self.assertEqual(set(audit.LAYERS), {case.layer for case in audit.CHECKS})
        for case in audit.CHECKS:
            with self.subTest(check=case.key):
                self.assertTrue(case.points)
                self.assertLessEqual(set(case.points), ids)
                self.assertEqual({point.split("-")[0] for point in case.points}, {case.layer})

    def test_coverage_json_lists_unmapped_points_explicitly(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(audit.main(["--coverage", "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["coverage"], list(audit.coverage_rows()))

    def test_filter_returns_machine_readable_result(self):
        # 入口行为使用纯探针夹具，进程级隔离由真实发布探针 T01 验证。
        selected = next(case for case in audit.CHECKS if case.key == "T01")
        fixture = replace(selected, run=lambda _: "隔离测试夹具")
        other = next(case for case in audit.CHECKS if case.layer != selected.layer)
        output = StringIO()
        with patch.object(audit, "CHECKS", [fixture, other]), \
             patch.object(audit, "install_isolation") as isolate, redirect_stdout(output):
            self.assertEqual(audit.main(["--point", "CT-12", "--json"]), 0)
        isolate.assert_called_once()
        report = json.loads(output.getvalue())
        self.assertEqual(report["summary"], {"PASS": 1, "FAIL": 0, "ERROR": 0})
        self.assertEqual(report["checks"][0]["id"], "T01")
        self.assertEqual(report["checks"][0]["points"], ["CT-12"])
