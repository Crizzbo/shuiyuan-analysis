"""云端无头每日行情与研报自动化调度流水线单元与集成测试套件 (Unit & Integration Tests).

覆盖测试点：
1. 【UT-CP-01】无头浏览器环境探测与优先级回退测试；
2. 【UT-CP-02】大盘研报强类型 Schema 契约校验与残缺拦截测试；
3. 【UT-CP-03】行情时效性门禁感知与超期阻断测试；
4. 【UT-CP-04】现代化暗色交互 HTML 研报渲染与 Token 规范测试；
5. 【IT-CP-05】云端流水线沙箱端到端运行与密码学账本防伪验签测试。
"""

import json
from copy import deepcopy
import unittest
from unittest.mock import patch
from jsonschema import ValidationError

from scripts.cloud_daily_pipeline import (
    find_headless_browser,
    validate_briefing_schema,
    render_briefing_html,
    run_pipeline,
)
from financial_reporting.quote_freshness_gateway import QuoteFreshnessGateway
from financial_core.engines.prediction_ledger import PredictionLedger
from scripts.test_support.fixtures import project_temp


class CloudDailyPipelineTests(unittest.TestCase):
    """云端每日行情流水线全息测试集。"""

    def setUp(self):
        self.temp_dir = project_temp(self, "test-cloud-")
        self.sample_data = {
            "header": {
                "report_date": "2026-10-16",
                "market": "US",
                "market_name_zh": "美股市场 (US Equities)"
            },
            "macro_and_liquidity": {
                "us_10y_yield": "4.39%",
                "us_2y_yield": "4.14%",
                "yield_spread_10_2": "+25.0 bps",
                "dxy_index": "104.28",
                "usd_jpy_rate": "159.15",
                "effr_policy_rate": "4.58%"
            },
            "market_sentiment_and_options": {
                "vix_index": "18.25",
                "fear_greed_gauge": "中性偏多 (58)",
                "capital_flow_summary": "大型科技与核心芯片获主力资金净流入",
                "options_market_dynamics": "标普 500 看涨期权持仓上升",
                "put_call_ratio": "0.74"
            },
            "market_moving_news": [
                {
                    "headline": "全球 AI 算力中心用电需求持续攀升",
                    "impact_analysis": "清洁基荷电力与先进半导体产业链维持极高订单能见度"
                }
            ],
            "ai_executive_summary": "宏观流动性平稳，科技巨头基本面强劲，维持逢低吸纳策略。",
            "recommended_stocks": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA Corporation",
                    "current_price": "$132.80 [2026-10-15 16:00 EDT 前收盘基准]",
                    "margin_of_safety_trigger": "$118.00 以下坚决布局",
                    "rating": "强烈推荐买入 (Strong Buy)",
                    "business_intro": "全球 GPU 与加速计算绝对霸主。",
                    "pessimistic_deduction": {
                        "trigger_event": "先进制程供应扰动",
                        "implied_price": "$105.00",
                        "downside_gap": "-20.9%"
                    },
                    "neutral_deduction": {
                        "trigger_event": "Blackwell 架构全面量产交付",
                        "implied_price": "$160.00",
                        "upside_gap": "+20.5%"
                    },
                    "optimistic_deduction": {
                        "trigger_event": "主权 AI 与企业级推理算力爆发",
                        "implied_price": "$195.00",
                        "potential_gain": "+46.8%"
                    },
                    "tactical_action": "作为科技板块核心进攻旗舰仓位配置。"
                }
            ]
        }

    def test_browser_discovery(self):
        """【UT-CP-01】无头浏览器环境探测功能测试。"""
        # 用项目内夹具验证配置优先级，无需安装或启动浏览器。
        browser = self.temp_dir / "browser.exe"
        browser.touch()
        with patch.dict("os.environ", {"BROWSER_HEADLESS_PATH": str(browser)}), \
             patch("scripts.cloud_daily_pipeline.shutil.which") as discover:
            self.assertEqual(find_headless_browser(), str(browser))
        discover.assert_not_called()

    def test_schema_validation_pass_and_reject(self):
        """【UT-CP-02】大盘研报 Schema 契约合法通过与残缺拦截测试。"""
        # 1. 正常数据应平滑通过校验
        validate_briefing_schema(self.sample_data)

        # 2. 缺失必选键 header 必须拦截报错
        invalid_data = dict(self.sample_data)
        del invalid_data["header"]
        with self.assertRaises(ValidationError) as raised:
            validate_briefing_schema(invalid_data)
        self.assertEqual(raised.exception.validator, "required")

    def test_quote_freshness_in_pipeline(self):
        """【UT-CP-03】行情时效性门禁感知与超期阻断测试。"""
        # 1. 合法盘前/前收盘基准核验
        res_valid = QuoteFreshnessGateway.verify_quote(
            price=132.80,
            currency="$",
            quote_timestamp="2026-10-15 16:00 EDT",
            market="US",
            current_time_iso="2026-10-16T12:00:00Z"
        )
        self.assertTrue(res_valid.is_valid)
        self.assertEqual(res_valid.session_status, "previous_close_baseline")

        # 2. 超期 48 小时数据必须硬阻断
        res_stale = QuoteFreshnessGateway.verify_quote(
            price=132.80,
            currency="$",
            quote_timestamp="2026-10-10 16:00 EDT",
            market="US",
            current_time_iso="2026-10-16T12:00:00Z",
            max_staleness_hours=24.0
        )
        self.assertFalse(res_stale.is_valid)
        self.assertEqual(res_stale.session_status, "stale_blocked")

    def test_render_briefing_html(self):
        """【UT-CP-04】现代化暗色交互 HTML 研报渲染与 Token 规范测试。"""
        html_str = render_briefing_html(self.sample_data)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("美股市场 (US Equities)", html_str)
        self.assertIn("NVDA", html_str)
        self.assertIn("Blackwell 架构全面量产交付", html_str)
        self.assertIn("#0b0f19", html_str, "应采用深色买方投研背景底色")

    def test_pipeline_end_to_end(self):
        """【IT-CP-05】云端流水线沙箱端到端运行与密码学账本防伪验签测试。"""
        report_dir = self.temp_dir / "reports"
        ledger = PredictionLedger(self.temp_dir / "prediction.sqlite3")
        fixture = deepcopy(self.sample_data)
        with patch("scripts.cloud_daily_pipeline.PredictionLedger", return_value=ledger), \
             patch("scripts.cloud_daily_pipeline.get_gdrive_executable", return_value=None), \
             patch("scripts.run_daily_briefing_and_deep_dossiers_pipeline.BRIEFING_DATA_US", fixture):
            receipt = run_pipeline(market="US", as_of_date="2026-10-16", render_pdf=False, output_dir=report_dir)

        self.assertEqual(receipt["status"], "SUCCESS")
        self.assertIn("US", receipt["markets"])
        self.assertTrue(receipt["duration_seconds"] >= 0.0)

        # 验证输出产物落盘
        generated_html, = report_dir.glob("*.html")
        generated_json, = report_dir.glob("*_US_*.json")
        self.assertIn("NVDA", generated_html.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(generated_json.read_text(encoding="utf-8")), self.sample_data)
        self.assertEqual(receipt["artifacts_generated"][0]["cloud_delivery_status"], "LOCAL_ARCHIVED_PENDING_REMOTE_SYNC")

        # 验证密码学账本验签通过
        result = ledger.verify_integrity()
        self.assertTrue(result.is_valid, result.error)
        self.assertEqual(ledger.get_stats()["total_predictions"], 1)
        prediction = ledger.get_prediction("PRED-20261016-US-NVDA")
        self.assertEqual(prediction.baseline_price, 132.80)


if __name__ == "__main__":
    unittest.main()
