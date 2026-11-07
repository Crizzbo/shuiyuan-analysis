"""SOTP 本地证据、口径、情景假设与报价的准入回归。"""

from copy import deepcopy
from pathlib import Path
import unittest

from finance_tools.sotp_event_analyzer import SotpEventAnalyzer
from jsonschema.exceptions import ValidationError
from scripts.test_support.sotp_fixtures import make_sotp_test_analyzer


class SotpProfileContractTests(unittest.TestCase):
    """每项用例只使用项目内的合成原文字节及隔离数据库。"""

    def setUp(self):
        self.analyzer = make_sotp_test_analyzer(self)

    def test_unknown_company_has_no_default_facts_or_database_side_effect(self):
        """默认没有已核实档案，查询未知标的返回缺失。"""
        default = SotpEventAnalyzer()
        self.assertIsNone(default.get_company_sotp_profile("NO_SUCH_SOTP_TEST_COMPANY"))
        self.assertIsNone(default._db_mgr)

    def test_synthetic_profiles_require_explicit_opt_in(self):
        """正式模式拒绝合成档案，调用方必须明确选择演示。"""
        self.analyzer.allow_synthetic = False
        with self.assertRaisesRegex(ValueError, "合成"):
            self.analyzer.get_company_sotp_profile("MSFT")

    def test_evidence_and_assumptions_survive_loading(self):
        """事实来源、假设依据及报价时段全部随档案保留。"""
        profile = self.analyzer.get_company_sotp_profile("MSFT")
        self.assertIn("segments.MSFT_CLOUD.revenue", profile.source_refs)
        self.assertIn("quote", profile.source_refs)
        self.assertEqual(profile.assumption_id, "synthetic-scenario-v1")
        self.assertEqual(profile.assumption_status, "uncalibrated_scenario")
        self.assertEqual(profile.evidence_status, "local_digest_verified_fact_review_required")
        self.assertEqual(profile.quote_session, "regular_trading")
        self.assertTrue(profile.quote_timestamp)
        self.assertIsNone(self.analyzer._db_mgr)

    def test_every_financial_field_needs_evidence(self):
        """总账和分部事实均不可缺失来源引用。"""
        for key in tuple(self.analyzer.profiles["MSFT"]["fact_evidence"]):
            with self.subTest(key=key):
                evidence = self.analyzer.profiles["MSFT"]["fact_evidence"]
                removed = evidence.pop(key)
                with self.assertRaisesRegex(ValueError, "逐项来源"):
                    self.analyzer.get_company_sotp_profile("MSFT")
                evidence[key] = removed

    def test_source_tampering_is_rejected(self):
        """登记后原文字节变化必须导致拒绝。"""
        source = self.analyzer.root_dir / "filing.synthetic.txt"
        source.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "摘要"):
            self.analyzer.get_company_sotp_profile("MSFT")

    def test_external_source_references_are_rejected(self):
        """拒绝绝对路径、URI、UNC 及越界相对路径。"""
        reference = self.analyzer.profiles["MSFT"]["fact_evidence"]["total_revenue"]
        for path in ("../outside", "C:/private/file", "/private/file", "https://example.com/file", "\\server\share"):
            with self.subTest(path=path):
                reference["source_path"] = path
                with self.assertRaises(ValueError):
                    self.analyzer.get_company_sotp_profile("MSFT")

    def test_stale_or_missing_quote_is_rejected(self):
        """陈旧报价和缺时间戳不能进入 SOTP 分析。"""
        quote = self.analyzer.profiles["MSFT"]["quote"]
        for timestamp in ("2000-01-01T14:00:00Z", ""):
            with self.subTest(timestamp=timestamp):
                quote["timestamp"] = timestamp
                with self.assertRaises(ValueError):
                    self.analyzer.get_company_sotp_profile("MSFT")

    def test_missing_segment_assumption_is_rejected(self):
        """分部没有独立情景假设时不得套用默认转嫁能力。"""
        self.analyzer.profiles["MSFT"]["assumptions"]["segments"].pop("MSFT_CLOUD")
        with self.assertRaisesRegex(ValueError, "情景假设"):
            self.analyzer.get_company_sotp_profile("MSFT")

    def test_invalid_values_and_ranges_are_rejected(self):
        """拒绝非有限数、零股数及越界转嫁比例。"""
        raw = self.analyzer.profiles["MSFT"]
        for value in (float("nan"), float("inf"), 0, -1):
            with self.subTest(value=value):
                raw["facts"]["diluted_shares"] = value
                with self.assertRaises(ValueError):
                    self.analyzer.get_company_sotp_profile("MSFT")
        raw["facts"]["diluted_shares"] = 7430
        raw["assumptions"]["segments"]["MSFT_CLOUD"]["cost_pass_through_power"] = 1.1
        with self.assertRaisesRegex(ValueError, "情景假设"):
            self.analyzer.get_company_sotp_profile("MSFT")

    def test_unallocated_income_is_required_for_profit_reconciliation(self):
        """分部 EBIT 加未分配项必须与合并 EBIT 一致。"""
        self.analyzer.profiles["TSM"]["facts"]["unallocated_operating_income"] = 0
        with self.assertRaisesRegex(ValueError, "合并利润"):
            self.analyzer.get_company_sotp_profile("TSM")

    def test_mixed_units_are_rejected_at_document_boundary(self):
        """明示百万单位后禁止混入带 B/M 后缀的数值或其他单位。"""
        import json
        raw = {"schema_version": "1.0.0", "profiles": deepcopy(self.analyzer.profiles)}
        for unit in ("jpy_million", "usd", "unknown"):
            with self.subTest(unit=unit):
                raw["profiles"]["MSFT"]["facts"]["financial_unit"] = unit
                path = self.analyzer.root_dir / "invalid.json"
                path.write_text(json.dumps(raw), encoding="utf-8")
                with self.assertRaises(ValidationError):
                    SotpEventAnalyzer(root_dir=self.analyzer.root_dir, profiles_path=path.name)
        raw["profiles"]["MSFT"]["facts"]["financial_unit"] = "usd_million"
        raw["profiles"]["MSFT"]["facts"]["total_revenue"] = "$1B"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(ValidationError):
            SotpEventAnalyzer(root_dir=self.analyzer.root_dir, profiles_path=path.name)

    def test_small_positive_share_count_is_not_clamped(self):
        """稀释股数单位为百万股，小于一百万股时仍使用原值计算。"""
        from financial_core.engines.event_radar_engine import StructuredEventSummary
        profile = self.analyzer.get_company_sotp_profile("MSFT")
        profile.diluted_shares = 0.5
        event = StructuredEventSummary(
            event_id="synthetic", timestamp="2026-10-16T14:00:00Z",
            category="State_Policy_Regulatory", involved_entities=["云基础设施"],
            micro_physical_impact="合成电力成本上涨 5%", estimated_duration="30天",
            affected_business_segments=["云基础设施"], severity_level="P1", requires_deep_analysis=True,
            raw_title="合成电力成本事件", source_name="synthetic",
        )
        result = self.analyzer.engine.analyze_company_impact(profile, event)
        self.assertAlmostEqual(result.eps_impact, result.net_income_impact / 0.5)
        self.assertFalse(result.is_actionable)
        self.assertEqual(result.recommended_action, "SCENARIO_REVIEW_REQUIRED")
        self.assertIn("quote", result.to_dict()["source_refs"])


if __name__ == "__main__":
    unittest.main()
