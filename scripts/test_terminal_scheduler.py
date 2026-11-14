"""覆盖队列并行、定时去重及异常重启恢复。"""

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.terminal_scheduler import TOKYO, TerminalScheduler, due_slots


class TerminalSchedulerTest(unittest.TestCase):
    def test_schedule_slots_cross_tokyo_midnight(self):
        monday = dict(due_slots(datetime(2026, 11, 16, 16, tzinfo=TOKYO)))
        saturday = dict(due_slots(datetime(2026, 11, 14, 7, tzinfo=TOKYO)))
        self.assertIn("JP_DAILY", monday)
        self.assertNotIn("US_DAILY", monday)
        self.assertIn("US_DAILY", saturday)
        self.assertNotIn("JP_DAILY", saturday)

    def test_two_workers_and_persisted_runs(self):
        barrier = threading.Barrier(2, timeout=5)

        def run(_):
            barrier.wait()
            return "SUCCESS", {"message": "完成"}

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False, handlers={"US_DAILY": run, "JP_DAILY": run})
            first = scheduler.submit("US_DAILY", "2026-11-13")
            self.assertIsNone(scheduler.submit("US_DAILY", "2026-11-13"))
            self.assertEqual(scheduler.submit("US_DAILY"), first)
            second = scheduler.submit("JP_DAILY")
            with scheduler._connect() as conn:
                conn.execute("UPDATE runs SET status='RUNNING' WHERE run_id=?", (first,))

            scheduler.start()
            try:
                for _ in range(100):
                    runs = {row["run_id"]: row["status"] for row in scheduler.snapshot()["runs"]}
                    if runs == {first: "SUCCESS", second: "SUCCESS"}:
                        break
                    threading.Event().wait(0.05)
                self.assertEqual(runs, {first: "SUCCESS", second: "SUCCESS"})
            finally:
                scheduler.close()

            reopened = TerminalScheduler(directory, None, False)
            self.assertIsNone(reopened.submit("US_DAILY", "2026-11-13"))
            self.assertEqual(len(reopened.snapshot()["runs"]), 2)

    def test_source_checkpoint_survives_partial_run(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False)
            path = Path(directory, "response.json")
            path.write_text('{"records": [1]}', encoding="utf-8")
            result = {
                "status": "collected", "record_count": 1, "artifacts": [],
                "result_path": path.relative_to(Path.cwd()).as_posix(),
                "result_sha256": sha256(path.read_bytes()).hexdigest(),
            }
            jobs = [{"id": "first"}, {"id": "second"}]
            with patch("scripts.terminal_scheduler.Archive"):
                with patch("scripts.terminal_scheduler.run_plan", side_effect=[[result], RuntimeError("中断")]):
                    with self.assertRaisesRegex(RuntimeError, "中断"):
                        scheduler._collect_jobs("test-run", jobs, {})
                reopened = TerminalScheduler(directory, None, False)
                with patch("scripts.terminal_scheduler.run_plan", return_value=[result]) as fetch:
                    self.assertEqual(reopened._collect_jobs("test-run", jobs, {}), [result, result])
                    fetch.assert_called_once()
                    self.assertEqual(fetch.call_args.args[0]["jobs"], [jobs[1]])
                path.write_text(json.dumps({"records": [2]}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "摘要不匹配"):
                    reopened._collect_jobs("test-run", jobs, {})

    def test_stock_screening_and_finance_calc_tasks(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False)
            status, res = scheduler._execute({"task": "STOCK_SCREENING", "run_id": "test-screen", "slot": None})
            self.assertEqual(status, "SUCCESS")
            self.assertIn("stage_2_candidates", res)
            self.assertEqual(res["total_universe_scale"], 14892)
            self.assertGreater(res["scanned_count"], 1000)
            self.assertGreater(res["stage2_count"], 0)
            self.assertIn("batch_valuations", res)
            self.assertIn("NVDA", res["batch_valuations"])

            status_ind, res_ind = scheduler._execute({"task": "INDICATOR_UPDATE", "run_id": "test-ind", "slot": None})
            self.assertEqual(status_ind, "SUCCESS")
            self.assertIn("indicators", res_ind)

            status_calc, res_calc = scheduler._execute({"task": "FINANCE_CALC", "run_id": "test-calc", "slot": None})
            self.assertEqual(status_calc, "SUCCESS")
            self.assertIn("calculations", res_calc)

            status_inc, res_inc = scheduler._execute({"task": "INCREMENTAL_COLLECT", "run_id": "test-inc", "slot": None})
            self.assertEqual(status_inc, "SUCCESS")
            self.assertIn("catalog_indexed_count", res_inc)

    def test_official_news_ai_distillation_and_sqlite_persistence(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False)
            status, res = scheduler._execute({"task": "OFFICIAL_NEWS", "run_id": "test-news", "slot": None})
            self.assertIn(status, ("SUCCESS", "PARTIAL_SUCCESS"))
            self.assertIn("total_in_db", res)
            self.assertGreaterEqual(res["total_in_db"], 1)

            news_items = scheduler.news()
            self.assertIsInstance(news_items, list)
            self.assertGreater(len(news_items), 0)
            sample = news_items[0]
            self.assertIn("title", sample)
            self.assertIn("severity_level", sample)
            self.assertIn("micro_physical_impact", sample)
            self.assertIn("involved_entities", sample)


if __name__ == "__main__":
    unittest.main()

