"""真实历史回放工具的无前视、评分、原文解析和账本防篡改测试。"""
from io import BytesIO
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from scripts.collect_model_validation_history import validate_url
from scripts.history_validation_ledger import HistoryValidationLedger, local_path
from scripts.run_historical_model_validation import (
    parse_factor_zip, training_window, quantile_loss, block_mean_interval,
    longest_run, parse_microsoft_cash_flow, cashflow_baselines,
)


def zipped(text):
    """仅用于解析器自测的合成CSV，不登记为真实历史。"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("sample.csv", text)
    return buffer.getvalue()


class HistoricalValidationTests(unittest.TestCase):
    """验证工具的数值口径和证据边界。"""

    def test_percent_conversion(self):
        """【UT-HIST-01】超额收益加无风险收益，百分数转换不能遗漏。"""
        rows, _ = parse_factor_zip(zipped("Source\n,Mkt-RF,SMB,HML,RF\n20200102,1.00,0,0,0.02\n"), "2020-01-01", "2020-12-31")
        self.assertAlmostEqual(rows[0]["total_market_return"], .0102)

    def test_missing_sentinel_not_return(self):
        """【UT-HIST-02】缺失哨兵不得变成巨大亏损或0收益。"""
        rows, info = parse_factor_zip(zipped(",Mkt-RF,SMB,HML,RF\n20200102,-99.99,0,0,0.02\n20200103,1,0,0,.02\n"), "2020-01-01", "2020-12-31")
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(info["excluded"]), 1)

    def test_duplicate_dates_rejected(self):
        """【UT-HIST-03】重复日期不能当作独立样本。"""
        with self.assertRaises(ValueError):
            parse_factor_zip(zipped(",Mkt-RF,SMB,HML,RF\n20200102,1,0,0,.02\n20200102,2,0,0,.02\n"), "2020-01-01", "2020-12-31")

    def test_future_perturbation_cannot_change_window(self):
        """【UT-HIST-04】改变被预测日及未来标签，不得改变已选择的训练输入。"""
        values = list(range(30))
        original = training_window(values, 20, 10).tolist()
        values[20:] = [999] * 10
        self.assertEqual(training_window(values, 20, 10).tolist(), original)
        self.assertEqual(original, list(range(10, 20)))

    def test_warmup_not_silently_shortened(self):
        """【UT-HIST-05】历史不足必须拒绝，不能缩短窗口蒙混通过。"""
        with self.assertRaises(ValueError):
            training_window(list(range(20)), 5, 10)

    def test_quantile_scoring_known_losses(self):
        """【UT-HIST-06】超限/未超限的分位数损失按独立手算对照。"""
        self.assertAlmostEqual(float(quantile_loss(.05, .03, .95)), .019)
        self.assertAlmostEqual(float(quantile_loss(.01, .03, .95)), .001)

    def test_constant_block_interval(self):
        """【UT-HIST-07】常数差值的区块重采样区间必须退化到该常数。"""
        self.assertEqual(block_mean_interval([2.] * 100, 20, 100, 42), [2., 2.])

    def test_bootstrap_reproducibility(self):
        """【UT-HIST-08】相同输入与种子必须可复现。"""
        self.assertEqual(block_mean_interval(range(100), 20, 100, 42), block_mean_interval(range(100), 20, 100, 42))

    def test_breach_clustering(self):
        """【UT-HIST-09】连续超限长度不等于总超限数。"""
        self.assertEqual(longest_run([True, False, True, True, False, True]), 2)

    def test_cashflow_table_units_and_sign(self):
        """【UT-HIST-10】定位当年列，Mapper解析括号负号，CFO加负资本开支。"""
        html = """<table><tr><td>(In millions)</td><td></td><td></td></tr>
        <tr><td>Year Ended June 30,</td><td>2024</td><td>2023</td></tr>
        <tr><td>Net cash from operations</td><td>1,000</td><td>900</td></tr>
        <tr><td>Additions to property and equipment</td><td>(400)</td><td>(300)</td></tr></table>"""
        row = parse_microsoft_cash_flow(html, 2024)
        self.assertEqual(row["fcf_proxy"], 600)
        self.assertEqual(row["unit"], "million")

    def test_cashflow_baseline_no_future_fit(self):
        """【UT-HIST-11】下一年预测只能用此前一年现金流。"""
        cases, _ = cashflow_baselines([{"fiscal_year": 2020, "fcf_proxy": 100}, {"fiscal_year": 2021, "fcf_proxy": 200}])
        self.assertEqual(cases[0]["prediction"], 100)
        self.assertAlmostEqual(cases[1]["prediction"], 110)

    def test_cashflow_gaps_not_pretended_annual(self):
        """【UT-HIST-12】缺一年不能假称一年期预测。"""
        cases, _ = cashflow_baselines([{"fiscal_year": 2020, "fcf_proxy": 100}, {"fiscal_year": 2022, "fcf_proxy": 200}])
        self.assertEqual(cases, [])

    def test_source_host_allowlist(self):
        """【UT-HIST-13】下载限制为明确配置的HTTPS公开来源。"""
        for url in ("http://www.microsoft.com/a", "https://evil.invalid/a", "https://user:password@www.microsoft.com/a"):
            with self.assertRaises(ValueError):
                validate_url(url, ["www.microsoft.com"])

    def test_local_boundaries(self):
        """【UT-HIST-14】归档引用拒绝绝对路径、URI与上级越界。"""
        root = Path(__file__).resolve().parents[1]
        for value in ("../escape", "https://example.com", "C:\\outside", "\\\\server\\share"):
            with self.assertRaises(ValueError):
                local_path(root, value)

    def test_ledger_artifact_tampering(self):
        """【UT-HIST-15】原文变更后PredictionLedger兼容链验签必须失败。"""
        cache = Path(__file__).resolve().parents[1] / ".cache"
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            root = Path(folder).resolve()
            artifact = root / "input.txt"
            artifact.write_text("original", encoding="utf8")
            ledger = HistoryValidationLedger(root, root / "audit.sqlite3")
            ledger.append_validation([artifact], {"data_origin": "synthetic_test_only"})
            self.assertTrue(ledger.verify_integrity().is_valid)
            artifact.write_text("tampered", encoding="utf8")
            self.assertFalse(ledger.verify_integrity().is_valid)
            with self.assertRaises(ValueError):
                ledger.append_validation([artifact], {})

    def test_ledger_payload_tampering(self):
        """【UT-HIST-16】即使文件未变，更改链内元数据也必须验签失败。"""
        cache = Path(__file__).resolve().parents[1] / ".cache"
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            root = Path(folder).resolve()
            artifact = root / "input.txt"
            artifact.write_text("original", encoding="utf8")
            ledger = HistoryValidationLedger(root, root / "audit.sqlite3")
            ledger.append_validation([artifact], {})
            with closing(sqlite3.connect(root / "audit.sqlite3")) as conn:
                conn.execute("UPDATE validation_artifacts SET payload='{}'")
                conn.commit()
            self.assertFalse(ledger.verify_integrity().is_valid)


if __name__ == "__main__":
    unittest.main()
