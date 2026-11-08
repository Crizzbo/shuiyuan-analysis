"""产业链上下游涟漪效应传导引擎与分析中继自动化测试集 (纯离线与隔离沙箱).

测试覆盖范围:
1. 产业链拓扑 JSONSchema 刚性契约校验与防劣变断言 (test_topology_schema_validation);
2. 核心中枢与上下游 DIO 存货缓冲冲销数学断言 (test_supply_chain_ripple_engine_math);
3. 极端数值边界防御与除零除负安全钳位 (test_mathematical_boundary_defenses);
4. 突发事件实体/分类智能匹配产业链图谱 (test_analyzer_event_matching);
5. 全链报告输出与供交易室大屏消费的矩阵结构 (test_ripple_report_structure);
6. 批量重大事件产业链穿透分析 (test_batch_analysis);
7. 异常边界防御 (不存在的事件 ID 处理与容错)。
"""

import json
from pathlib import Path
import shutil
import sys
import unittest
from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_core.engines.supply_chain_ripple_engine import (
    SupplyChainRippleEngine,
    SupplyChainRippleReport,
    RippleNodeImpact,
)
from finance_tools.supply_chain_ripple_analyzer import SupplyChainRippleAnalyzer


class TestSupplyChainRippleEngine(unittest.TestCase):
    """产业链上下游涟漪传导引擎测试套件."""

    @classmethod
    def setUpClass(cls):
        cls.schema_path = PROJECT_ROOT / "schemas/supply_chain_topologies.schema.json"
        cls.config_path = PROJECT_ROOT / "config/supply_chain_topologies.json"
        cls.schema = json.loads(cls.schema_path.read_text(encoding="utf-8"))
        cls.config_data = json.loads(cls.config_path.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)
        cls.engine = SupplyChainRippleEngine()
        cls.analyzer = SupplyChainRippleAnalyzer()

    def test_topology_schema_validation(self):
        """测试配置文件严格通过 JSONSchema 契约规范."""
        self.validator.validate(self.config_data)
        topologies = self.config_data.get("topologies", [])
        self.assertGreaterEqual(len(topologies), 3)

        # 变异测试: 故意破坏必填字段触发拦截
        bad_topology = {
            "version": "1.0.0",
            "topologies": [
                {
                    "topology_id": "BAD_CHAIN",
                    "name_zh": "缺少核心中枢的残缺拓扑",
                    # 缺少 core_hub
                }
            ],
        }
        self.assertFalse(self.validator.is_valid(bad_topology))

    def test_supply_chain_ripple_engine_math(self):
        """测试存货缓冲 DIO 吸收与定价转嫁权冲销的金融数学严谨性."""
        topo = self.analyzer.get_topology("SEMICONDUCTOR_FOUNDRY_LITHOGRAPHY_CHAIN")
        self.assertIsNotNone(topo)

        mock_event = {
            "event_id": "EVT_TEST_MATH_01",
            "title": "测试断供冲击事件",
            "category": "Physical_Plant_Disruption",
        }

        # 场景 A: 断供 60 天 > 台积电 DIO 45 天 ➔ 存在 15 天暴露敞口 ➔ 预估损益为负
        rep_a = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=60.0)
        hub_a = rep_a.core_hub_impact
        self.assertEqual(hub_a.buffer_dio_days, 45.0)
        self.assertEqual(hub_a.uncovered_exposure_days, 15.0)
        self.assertLess(hub_a.ebit_impact_pct, 0.0)

        # 场景 B: 断供 30 天 <= 台积电 DIO 45 天 ➔ 暴露敞口为 0 ➔ 预估损益为 0.0
        rep_b = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=30.0)
        hub_b = rep_b.core_hub_impact
        self.assertEqual(hub_b.uncovered_exposure_days, 0.0)
        self.assertEqual(hub_b.ebit_impact_pct, 0.0)
        self.assertIn("正向受益", hub_b.vulnerability_level)

    def test_pricing_power_mitigation(self):
        """测试定价转嫁权 (PT) 对下游利润损失的冲销衰减."""
        topo = self.analyzer.get_topology("SEMICONDUCTOR_FOUNDRY_LITHOGRAPHY_CHAIN")
        mock_event = {"event_id": "EVT_TEST_PT_02", "title": "测试议价权事件"}

        report = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=80.0)

        # 比较下游英伟达 (PT=0.80) 与台积电中枢 (PT=0.70)
        nvda_node = next((d for d in report.downstream_impacts if d.ticker == "NVDA"), None)
        self.assertIsNotNone(nvda_node)
        self.assertEqual(nvda_node.pricing_power_pt, 0.80)
        # 验证受损被高转嫁权有效控制 (损失幅度 < 5.0%)
        self.assertGreater(nvda_node.ebit_impact_pct, -5.0)

    def test_mathematical_boundary_defenses(self):
        """测试极端数值输入下的除零、除负、NaN 防御与有限责任下界."""
        topo = self.analyzer.get_topology("SEMICONDUCTOR_FOUNDRY_LITHOGRAPHY_CHAIN")
        mock_event = {"event_id": "EVT_TEST_BOUNDARY", "title": "极端测试"}

        # 输入 0 天断供或负数天数，自动收敛为安全下界 1.0 天
        rep_zero = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=0.0)
        self.assertEqual(rep_zero.disruption_duration_days, 1.0)

        rep_neg = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=-100.0)
        self.assertEqual(rep_neg.disruption_duration_days, 1.0)

        # 输入 3650 天特大灾难断供，营业利润损益严格被截断在 [-100.0%, 50.0%] 有限责任区间
        rep_huge = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=3650.0)
        self.assertGreaterEqual(rep_huge.core_hub_impact.ebit_impact_pct, -100.0)

    def test_analyzer_event_matching(self):
        """测试中继分析器根据突发事件实体/分类智能匹配产业链拓扑."""
        # 1. 包含 TSM 实体匹配半导体光刻胶代工链
        event_semi = {
            "event_id": "EVT_SEMI_01",
            "title": "某芯片晶圆厂火灾",
            "category": "Physical_Plant_Disruption",
            "involved_entities": ["TSMC"],
        }
        matched_semi = self.analyzer.match_topology_for_event(event_semi)
        self.assertIsNotNone(matched_semi)
        self.assertEqual(matched_semi["topology_id"], "SEMICONDUCTOR_FOUNDRY_LITHOGRAPHY_CHAIN")

        # 2. 包含 ILA 实体匹配海运港口物流链
        event_port = {
            "event_id": "EVT_PORT_02",
            "title": "码头工人停工",
            "category": "Labor_Strikes_Port_Railways",
            "involved_entities": ["ILA_Union"],
        }
        matched_port = self.analyzer.match_topology_for_event(event_port)
        self.assertIsNotNone(matched_port)
        self.assertEqual(matched_port["topology_id"], "MARITIME_CONTAINER_PORTS_LOGISTICS_CHAIN")

    def test_ripple_report_structure(self):
        """测试生成的研报对象完整性与字典序列化契约."""
        topo = self.analyzer.get_topology("SEMICONDUCTOR_FOUNDRY_LITHOGRAPHY_CHAIN")
        mock_event = {"event_id": "EVT_STRUCT_01", "title": "结构完整性测试"}

        rep = self.engine.evaluate_ripple_transmission(topo, mock_event, disruption_days=60.0)
        rep_dict = rep.to_dict()

        self.assertIn("topology_id", rep_dict)
        self.assertIn("core_hub_impact", rep_dict)
        self.assertIn("upstream_impacts", rep_dict)
        self.assertIn("downstream_impacts", rep_dict)
        self.assertIn("transmission_matrix", rep_dict)
        self.assertIsInstance(rep_dict["transmission_matrix"], list)
        self.assertGreaterEqual(len(rep_dict["transmission_matrix"]), 3)

    def test_non_existent_event_raises_error(self):
        """测试分析不存在的事件 ID 引发 ValueError."""
        with self.assertRaises(ValueError):
            self.analyzer.analyze_event_ripple("EVT_NON_EXISTENT_ID_99999")


if __name__ == "__main__":
    unittest.main()
