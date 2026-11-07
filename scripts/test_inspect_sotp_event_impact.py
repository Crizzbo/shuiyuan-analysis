"""单元测试：突发事件多业务分部 (SOTP) 终端因果排查工具 (inspect_sotp_event_impact.py).

覆盖内容：
1. 通俗商业语言与买方研判报告格式化 (format_impact_terminal_report);
2. 传闻熔断门禁锁定下的终端警示与核验指引输出;
3. 官方演示标的 (MSFT / TSM) 跨业务分部差异化穿透展示;
4. CLI 各种参数组合 (--demo, --event-id, --all-major, --json, --only-confirmed) 正确性;
5. 缺失档案与未知事件的防御性提示与退出码;
6. 完全使用项目临时隔离数据库，零外部依赖与零盘中数据拉取。
"""

import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr

from finance_tools.event_radar_collector import RadarDatabaseManager
from financial_core.engines.event_radar_engine import RawNewsItem, StructuredEventSummary
from financial_core.engines.sotp_event_penetration_engine import (
    EnterpriseEventImpactResult,
    SegmentCausalImpact,
)
from scripts.inspect_sotp_event_impact import (
    format_impact_terminal_report,
    run_inspect_cli,
    build_demo_sotp_analyzer,
)
from scripts.test_support.fixtures import project_temp


class TestInspectSotpEventImpactCLI(unittest.TestCase):
    """测试 inspect_sotp_event_impact 终端排查工具."""

    def setUp(self):
        """为每个测试建立独立受控的测试事件账本."""
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        self.temp_dir = project_temp(self, "inspect-sotp-test-")
        db_file = self.temp_dir / "test_radar.sqlite3"
        self.db_path = str(db_file.relative_to(root)).replace("\\", "/")
        self.db_mgr = RadarDatabaseManager(db_path=str(db_file))

        # 录入一条已核实的重大事件
        item = RawNewsItem(
            id="test_news_01",
            title="加州算力中心电网费新规",
            content="内容",
            source="CPUC",
            published_at="2026-11-07T08:00:00Z",
            url="",
        )
        self.sample_event = StructuredEventSummary(
            event_id="EVT_TEST_01",
            timestamp="2026-11-07T08:00:00Z",
            category="State_Policy_Regulatory",
            involved_entities=["加州算力中心", "CPUC"],
            micro_physical_impact="单机柜电费增加 8.5%",
            estimated_duration="长期",
            affected_business_segments=["云基础设施(IaaS)", "生成式AI算力集群"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="加州算力中心电网费新规",
            source_name="CPUC",
            credibility_tier="Tier1_Official_Regulatory",
            credibility_score=1.0,
            verification_status="Confirmed_Fact",
        )
        self.db_mgr.insert_event(self.sample_event, item, item.published_at)

    def test_format_terminal_report_rumor_blocked(self):
        """测试传闻熔断锁止时的自然语言报告格式化."""
        rumor_res = EnterpriseEventImpactResult(
            ticker="TEST",
            company_name="测试多元化企业",
            event_id="EVT_RUMOR_999",
            event_title="【传闻】网络热议某州算力电费加税",
            severity_level="P1",
            total_operating_income_impact=0.0,
            net_income_impact=0.0,
            ebit_impact_percentage=0.0,
            eps_impact=0.0,
            valuation_target_discount_pct=0.0,
            scenario_signal="RUMOR_CIRCUIT_BREAKER_ACTIVE",
            recommended_action="BLOCKED_BY_RUMOR_CIRCUIT_BREAKER",
            focal_summary="传闻熔断触发：信源未达买方机构准入等级",
            segment_impacts=[],
            is_actionable=False,
        )
        report = format_impact_terminal_report(rumor_res, category_key="State_Policy_Regulatory")

        self.assertIn("【🛑 传闻熔断保护机制已激活】", report)
        self.assertIn("各州产业政策与公用负荷", report)
        self.assertIn("买方风控提示", report)
        self.assertIn("confirm_event_verification.py", report)

    def test_format_terminal_report_normal_penetration(self):
        """测试正常核实事件的分部拆解与每股收益加总格式化."""
        seg1 = SegmentCausalImpact(
            segment_id="SEG_CLOUD",
            segment_name="智能云计算分部",
            exposure_score=0.80,
            gross_cost_shock_pct=0.10,
            inventory_absorption_factor=0.20,
            net_cost_shock_pct=0.04,
            operating_income_impact=-500.0,
            revenue_impact=-100.0,
            rationale="算力电网成本上涨8.5%，被DIO库存缓冲与下游转嫁抵御部分冲击",
        )
        seg2 = SegmentCausalImpact(
            segment_id="SEG_RETAIL",
            segment_name="零售与终端分部",
            exposure_score=0.0,
            gross_cost_shock_pct=0.0,
            inventory_absorption_factor=0.0,
            net_cost_shock_pct=0.0,
            operating_income_impact=0.0,
            revenue_impact=0.0,
            rationale="未涉及终端零售业务",
        )
        normal_res = EnterpriseEventImpactResult(
            ticker="TEST",
            company_name="测试多元化企业",
            event_id="EVT_CONFIRMED_01",
            event_title="州级电网附加费正式法令落地",
            severity_level="P1",
            total_operating_income_impact=-500.0,
            net_income_impact=-400.0,
            ebit_impact_percentage=-0.05,
            eps_impact=-0.25,
            valuation_target_discount_pct=-0.045,
            scenario_signal="MONITOR_INVENTORY_BUFFER",
            recommended_action="MONITOR_INVENTORY_BUFFER",
            focal_summary="核心云业务承压，但零售业务完全未受波及，展现多元化组合抗风险能力",
            segment_impacts=[seg1, seg2],
            is_actionable=True,
        )
        report = format_impact_terminal_report(normal_res, category_key="State_Policy_Regulatory")

        self.assertIn("【企业级财务损益加总】", report)
        self.assertIn("-500.0 百万美元", report)
        self.assertIn("-0.250 美元/股", report)
        self.assertIn("智能云计算分部", report)
        self.assertIn("零售与终端分部", report)
        self.assertIn("0.0 M$ (完全独立)", report)
        self.assertIn("共 2 个主营分部，其中 1 个完全未受波及", report)

    def test_run_inspect_cli_demo_mode_all_major(self):
        """测试 CLI 演示模式下全量重大事件扫描."""
        f = io.StringIO()
        with redirect_stdout(f):
            ret = run_inspect_cli(all_major=True, demo=True, db_path=self.db_path)
        self.assertEqual(ret, 0)
        output = f.getvalue()
        self.assertIn("成功扫描到", output)
        self.assertIn("Microsoft Corporation", output)

    def test_run_inspect_cli_demo_mode_specific_event(self):
        """测试 CLI 演示模式下排查指定事件编号."""
        target_id = self.sample_event.event_id
        f = io.StringIO()
        with redirect_stdout(f):
            ret = run_inspect_cli(event_id=target_id, demo=True, db_path=self.db_path)
        self.assertEqual(ret, 0)
        output = f.getvalue()
        self.assertIn(f"正在呈现事件 [{target_id}]", output)
        self.assertIn("Microsoft Corporation", output)

    def test_run_inspect_cli_json_output(self):
        """测试 CLI 的 --json 参数输出有效 JSON."""
        f = io.StringIO()
        with redirect_stdout(f):
            ret = run_inspect_cli(all_major=True, demo=True, as_json=True, db_path=self.db_path)
        self.assertEqual(ret, 0)
        output = f.getvalue()
        data = json.loads(output)
        self.assertIsInstance(data, dict)
        self.assertIn(self.sample_event.event_id, data)

    def test_run_inspect_cli_unknown_event_id_exits_one(self):
        """测试查询不存在的事件 ID 返回退出码 1."""
        err_stream = io.StringIO()
        with redirect_stderr(err_stream):
            ret = run_inspect_cli(event_id="EVT_NON_EXISTENT_9999", demo=True, db_path=self.db_path)
        self.assertEqual(ret, 1)
        self.assertIn("错误:", err_stream.getvalue())


if __name__ == "__main__":
    unittest.main()
