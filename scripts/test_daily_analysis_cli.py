"""旧无证据日报入口必须拒绝生成。"""
import unittest
from scripts.run_daily_analysis import compute_company_analysis
class DailyAnalysisCliTests(unittest.TestCase):
    def test_unregistered_inputs_fail_closed(self):
        """【UT-DAILYCLI-01: 未注册输入无证据日报生成物理熔断阻断(Fail-Closed)】

        1. 测试功能与测试点:
           - 验证历史旧版 compute_company_analysis 在面对空字典与未建档标的输入时，执行绝对防御性 Fail-Closed 熔断。
           - 严禁在缺失证据底账时凭空捏造日报内容。

        2. 正常函数业务边界与参数契约:
           - 任何未注册或未对账输入均拒绝生成并抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 传入空字典 company={} 与上下文 None。

        4. 预期断言与结果验证:
           - 刚性断言抛出 ValueError。
        """
        with self.assertRaises(ValueError): compute_company_analysis({},None)
