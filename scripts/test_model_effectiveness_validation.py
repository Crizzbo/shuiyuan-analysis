"""验证核验工具能发现偏差，不将工具自测包装为金融模型效果。"""
import math
from pathlib import Path
import tempfile
import unittest
from scripts.model_validation_lab import bsm_reference, compare, inventory, require_rejection, render_markdown


class ValidationToolTests(unittest.TestCase):
    """工具的独立参照、异常判定和缺失数据行为。"""

    def test_reference_put_call_parity(self):
        """【UT-VAL-01】独立参照满足零分红欧式看涨看跌平价。"""
        call = bsm_reference(100, 105, .03, .2, 1)
        put = bsm_reference(100, 105, .03, .2, 1, False)
        self.assertAlmostEqual(call - put, 100 - 105 * math.exp(-.03))

    def test_known_reference(self):
        """【UT-VAL-02】标准合成参数的解析参考防止符号和比例错误。"""
        self.assertAlmostEqual(bsm_reference(100, 100, .05, .2, 1), 10.450583572185565)

    def test_zero_volatility(self):
        """【UT-VAL-03】零波动参考不引入人为波动率下限。"""
        self.assertEqual(bsm_reference(100, 100, 0, 0, 1), 0)

    def test_corrupted_value_fails(self):
        """【UT-VAL-04】刻意扰动结果必须被判为失败。"""
        self.assertEqual(compare("X", "test", "mutation", 11, 10, .01).status, "FAIL")

    def test_nonfinite_fails(self):
        """【UT-VAL-05】非有限值不能误算为通过。"""
        for value in (float("nan"), float("inf")):
            self.assertEqual(compare("X", "test", "nonfinite", value, 0).status, "FAIL")

    def test_silent_acceptance_fails(self):
        """【UT-VAL-06】静默接受非法值不能算保护成功。"""
        self.assertEqual(require_rejection("X", "test", "bad input", lambda: None).status, "FAIL")

    def test_unrelated_exception_is_error(self):
        """【UT-VAL-07】导入/运行错误不得算作输入保护通过。"""
        def bad():
            raise RuntimeError("unexpected")
        self.assertEqual(require_rejection("X", "test", "unexpected", bad).status, "ERROR")

    def test_missing_ledger_insufficient(self):
        """【UT-VAL-08】缺历史样本返回证据不足且不创建账本。"""
        cache = Path(__file__).resolve().parents[1] / ".cache"
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            root = Path(folder)
            self.assertEqual(inventory(root)["status"], "INSUFFICIENT_EVIDENCE")
            self.assertFalse((root / "data").exists())

    def test_report_preserves_failures(self):
        """【UT-VAL-09】报告展示失败与证据边界。"""
        report = {"generated_at": "test", "counts": {"FAIL": 1}, "snapshot_stable": True,
                  "checks": [compare("X", "test", "mutation", 2, 1).__dict__], "inventory": {"status": "INSUFFICIENT_EVIDENCE"}}
        text = render_markdown(report)
        self.assertIn("FAIL", text)
        self.assertIn("证据不足", text)


if __name__ == "__main__":
    unittest.main()
