"""覆盖队列并行、定时去重及异常重启恢复。"""

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.terminal_scheduler import NEW_YORK, TOKYO, TerminalScheduler, due_slots, provider_symbol


class TerminalSchedulerTest(unittest.TestCase):
    def test_schedule_slots_cross_tokyo_midnight(self):
        self.assertEqual(dict(due_slots(datetime(2026, 11, 16, 7, 30, tzinfo=TOKYO)))["JP_DAILY"], "2026-11-16")
        for month, day, tokyo_hour in ((7, 13, 21), (11, 16, 22)):
            tokyo_time = datetime(2026, month, day, tokyo_hour, tzinfo=TOKYO)
            self.assertEqual(dict(due_slots(tokyo_time))["US_DAILY"], tokyo_time.date().isoformat())
        self.assertNotIn("US_DAILY", dict(due_slots(datetime(2026, 11, 16, 9, 30, tzinfo=NEW_YORK))))
        self.assertNotIn("JP_DAILY", dict(due_slots(datetime(2026, 11, 14, 7, 30, tzinfo=TOKYO))))

    def test_daily_budget_rotation_survives_restart(self):
        def collect(run_id, jobs, sources, **kwargs):
            return [dict(job, status="collected", record_count=250) for job in jobs]

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False)
            codes = [f"{n:04d}" for n in range(1300, 1400)]
            with patch("scripts.terminal_scheduler.market_symbols", return_value=codes):
                first = scheduler.submit("JP_DAILY", "2026-11-16")
                with patch.object(scheduler, "_collect_jobs", side_effect=collect) as execute:
                    scheduler._run({"task": "JP_DAILY", "run_id": first, "slot": "2026-11-16"})
                request = execute.call_args.args[1][0]
                self.assertEqual(request["params"]["end"], "2026-11-16")
                self.assertEqual(request["params"]["symbol"], "1300.T")
                result = scheduler.snapshot()["runs"][0]["result"]
                self.assertEqual((result["universe_count"], result["archived_symbols"]), (100, 43))
                reopened = TerminalScheduler(directory, None, False)
                with patch.object(reopened, "_collect_jobs", side_effect=collect) as execute:
                    reopened._execute_market_daily({"task": "JP_DAILY", "run_id": "next", "slot": "2026-11-17"})
                self.assertEqual(execute.call_args.args[1][0]["id"], "1343")
        self.assertEqual(provider_symbol("JP", "130A"), "130A.T")
        self.assertEqual(provider_symbol("US", "BRK.B"), "BRK-B")

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

    def test_screening_and_finance_missing_inputs_are_blocked(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, lambda: ("BLOCKED", {"message": "账本未通过"}), False)
            with patch.object(scheduler, "_archived_records", return_value=[]):
                status, result = scheduler._execute({"task": "STOCK_SCREENING", "run_id": "screen"})
                self.assertEqual((status, result["trend_inputs"]), ("BLOCKED", {}))
            status, result = scheduler._execute({"task": "FINANCE_CALC", "run_id": "calc"})
            self.assertEqual((status, result["message"]), ("BLOCKED", "账本未通过"))

    def test_reconciliation_summary_and_target_day_derivation(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False)
            codes = ["AAPL", "MSFT", "NONE."]
            with patch("scripts.terminal_scheduler.market_symbols", return_value=codes):
                recon = scheduler.reconciliation_summary("US", target_date="2026-11-13")
                self.assertEqual(recon["universe_count"], 3)
                self.assertEqual(recon["unmapped_count"], 1)
                self.assertEqual(recon["unmapped_symbols"], ["NONE."])
                self.assertTrue(recon["is_balanced"])
                self.assertEqual(recon["target_trading_day"], "2026-11-13")

    def test_news_keeps_unverified_headline_and_archive_source(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None, False)
            result = {"status": "collected", "record_count": 1}
            sources = {"sources": {"rss": {"feeds": [{"authority": "official", "url": "https://example.test/feed"}]}}}
            with patch("scripts.terminal_scheduler.read", return_value=sources):
                with patch.object(scheduler, "_collect_jobs", return_value=[result]) as collect:
                    status, summary = scheduler._execute({"task": "OFFICIAL_NEWS", "run_id": "news"})
            self.assertEqual((status, summary["items"]), ("SUCCESS", [result]))
            self.assertEqual(collect.call_args.args[0], "news")
            item = {"artifacts": [{"origin_url": "https://example.test/feed"}]}
            with patch.object(scheduler, "_archived_records", return_value=[(item, [{"title": "公告"}])]):
                article, = scheduler.news()
            self.assertEqual(article["verification_status"], "Pending_Verification")
            self.assertEqual(article["source"], "https://example.test/feed")

    def test_automatic_switch_and_manual_batch_logs_persist(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, None)
            scheduled_run = scheduler.submit("US_DAILY", "2026-11-13")
            scheduler.set_enabled("__automatic__", False)
            self.assertIsNone(scheduler.submit("JP_DAILY", "2026-11-13"))
            batch = scheduler.start_batch()
            reopened = TerminalScheduler(directory, None)
            snapshot = reopened.snapshot()
            runs = {row["run_id"]: row["status"] for row in snapshot["runs"]}
            self.assertFalse(snapshot["automatic_enabled"])
            self.assertEqual(runs[scheduled_run], "CANCELLED")
            self.assertEqual({row["task"] for row in batch["runs"]},
                             {"LOCAL_AUDIT", "US_DAILY", "JP_DAILY", "OFFICIAL_NEWS"})
            self.assertTrue(all(runs[row["run_id"]] == "QUEUED" for row in batch["runs"]))
            self.assertTrue(all(reopened.logs("ALL", row["run_id"], 10) for row in batch["runs"]))


if __name__ == "__main__":
    unittest.main()

