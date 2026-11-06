"""宏观经济分析模块离线回归测试套件 (Macro Indicators Test Suite).

验证宏观指标规范、微观传导矩阵、数据登记、防前视机制与快照确定性。

测试覆盖范围:
1. 【UT-MACRO-IND-01】: 宏观17项标准指标规范定义与微观传导矩阵闭环核验
2. 【UT-MACRO-IND-02】: 官方发布事实摘录对账、单位转换与防篡改物理拦截
3. 【IT-MACRO-IND-03】: 宏观底账快照密码学哈希确定性、幂等生成与防前视时效门禁
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_reporting.macro_indicators import (
    verify_macro_specs,
    verify_macro_observation,
    register_macro_samples,
    verify_macro_snapshot,
)


def rejects(fn, expected_exceptions=(ValueError, AssertionError)):
    try:
        fn()
    except expected_exceptions:
        return
    raise AssertionError("预期异常未发生，违规输入未被正确拦截")


class TestMacroIndicators(unittest.TestCase):
    """【单元与集成测试】宏观指标体系与底账快照生成回归测试集."""

    def test_macro_specs(self):
        """【UT-MACRO-IND-01: 宏观17项标准指标规范定义与微观传导矩阵闭环核验】

        1. 测试功能与测试点:
           - 验证系统覆盖的 17 项标准宏观经济指标元数据规范。
           - 验证四大核心宏观支柱 (Pillars): 利率与信用 (rates_and_credit)、外汇与汇率 (foreign_exchange)、劳动力市场 (labor_market)、通胀与货币政策 (inflation_and_policy)。
           - 验证防过度拟合硬约束: 在没有足够历史样本校准前，所有指标的 threshold 强制为 None，严禁盲目启用未校准硬编码阈值。
           - 验证微观传导矩阵 (Macro Transmission Matrix) 的有效性，确保宏观因子能准确映射到行业驱动、估值参数或通用财务模型中。

        2. 正常函数业务边界与参数契约:
           - verify_macro_specs() 无需外部参数，纯离线解析项目内宏观指标契约规范。
           - 返回 tuple (spec_map, transmissions)。
           - 每个指标必须包含 source_agency 发布机构以及合法的更新频率 (daily, monthly, quarterly)。

        3. 测试数据与模拟场景说明:
           - 检验项目内置官方宏观指标注册表，断言规范数量与支柱完整度。

        4. 预期断言与结果验证:
           - 断言 len(spec_map) == 17。
           - 断言支柱集合完整包含四大类别。
           - 断言所有指标 threshold 均为 None。
           - 断言 transmissions 数量 >= 8，且目标类型与步骤门槛合法。
        """
        spec_map, transmissions = verify_macro_specs()
        # 断言包含 17 个标准宏观指标
        self.assertEqual(len(spec_map), 17, f"预期 17 个宏观指标，实际得到 {len(spec_map)}")
        pillars = {s["pillar"] for s in spec_map.values()}
        self.assertEqual(pillars, {"rates_and_credit", "foreign_exchange", "labor_market", "inflation_and_policy"})

        # 验证全部指标的 threshold 为 null（无历史样本不启用数值阈值）
        for ind in spec_map.values():
            self.assertIsNone(ind["threshold"], f"指标 {ind['id']} 不得硬编码未校准阈值")
            self.assertTrue(ind["source_agency"], f"指标 {ind['id']} 缺失发布机构")
            self.assertIn(ind["frequency"], ("daily", "monthly", "quarterly"))

        # 断言传导矩阵包含有效传导规则
        self.assertGreaterEqual(len(transmissions), 8, f"预期至少 8 条传导规则，实际得到 {len(transmissions)}")
        for t in transmissions:
            self.assertIn(t["macro_indicator_id"], spec_map, f"传导矩阵引用未知宏观指标 {t['macro_indicator_id']}")
            self.assertIn(t["target_type"], ("industry_driver", "valuation_parameter", "generic_financial"))
            self.assertIn(t["sensitivity_direction"], ("positive", "negative", "curvilinear", "context_dependent"))
            self.assertIn(t["step_gate"], ("S3_industry_drivers", "S4_valuation_scenarios", "S5_margin_of_safety"))
            self.assertGreaterEqual(len(t["affected_industries"]), 1)

    def test_observation_validation_and_rejections(self):
        """【UT-MACRO-IND-02: 官方发布事实摘录对账、单位转换与防篡改物理拦截】

        1. 测试功能与测试点:
           - 验证 verify_macro_observation 的事实对账审计引擎。
           - 验证原始数值 (raw_value) 必须能在官方发布文本摘录 (excerpts) 中精确检索到，杜绝无事实来源凭空捏造数据。
           - 验证数值标准化转换公式的刚性对账 (如 percent_divided_by_100)。
           - 验证针对 4 大类违规数据的物理拦截能力:
             A) 摘录原文与原始数值不符；
             B) 标准化换算值与原始值不匹配；
             C) 使用未批准的非法转换算法；
             D) 单位定义冲突。

        2. 正常函数业务边界与参数契约:
           - source 字典包含 source_url, locator, excerpts。
           - observation 字典包含 indicator_id, period_end, raw_value, raw_unit, value, unit, conversion。
           - as_of_iso 必须晚于或等于 period_end。

        3. 测试数据与模拟场景说明:
           - 合法输入: 圣路易斯联储 FRED 10Y 国债收益率 4.42%，摘录包含 '4.42%'，转换为 ratio 为 0.0442。
           - 注入 4 种典型伪造与篡改数据变体进行反向拦截测试。

        4. 预期断言与结果验证:
           - 合法数据断言 quote 包含 '4.42%'。
           - 4 组非法数据变体断言全部抛出 ValueError 或 AssertionError 阻断。
        """
        source = {
            "source_url": "https://fred.stlouisfed.org/series/DGS10",
            "locator": "Series DGS10",
            "excerpts": [
                "10-Year Treasury Constant Maturity Rate: 4.42% as of December 31, 2025."
            ]
        }
        valid_obs = {
            "indicator_id": "us_treasury_10y_yield",
            "period_end": "2025-12-31",
            "raw_value": "4.42",
            "raw_unit": "percent",
            "value": "0.0442",
            "unit": "ratio",
            "conversion": "percent_divided_by_100",
            "release_status": "final",
            "excerpt_indices": [0]
        }
        # 正常校验应通过
        quote = verify_macro_observation(source, valid_obs, "2026-10-12T00:00:00Z")
        self.assertIn("4.42%", quote)

        # 负例 1: 摘录中不含 raw_value
        bad_obs1 = copy.deepcopy(valid_obs)
        bad_obs1["raw_value"] = "5.50"
        with self.assertRaises((ValueError, AssertionError)):
            verify_macro_observation(source, bad_obs1, "2026-10-12T00:00:00Z")

        # 负例 2: 转换数值不匹配
        bad_obs2 = copy.deepcopy(valid_obs)
        bad_obs2["value"] = "0.0550"
        with self.assertRaises((ValueError, AssertionError)):
            verify_macro_observation(source, bad_obs2, "2026-10-12T00:00:00Z")

        # 负例 3: 转换规则非法
        bad_obs3 = copy.deepcopy(valid_obs)
        bad_obs3["conversion"] = "unapproved_formula"
        with self.assertRaises((ValueError, AssertionError)):
            verify_macro_observation(source, bad_obs3, "2026-10-12T00:00:00Z")

        # 负例 4: 单位不匹配
        bad_obs4 = copy.deepcopy(valid_obs)
        bad_obs4["unit"] = "points"
        with self.assertRaises((ValueError, AssertionError)):
            verify_macro_observation(source, bad_obs4, "2026-10-12T00:00:00Z")

    def test_snapshot_generation_and_idempotence(self):
        """【IT-MACRO-IND-03: 宏观底账快照密码学哈希确定性、幂等生成与防前视时效门禁】

        1. 测试功能与测试点:
           - 验证 register_macro_samples 快照生成与归档功能。
           - 验证密码学确定性与强幂等性: 在输入数据不变的前提下，多次执行生成的快照 SHA-256 哈希值恒定不变。
           - 验证防前视偏差硬约束 (Look-Ahead Bias Prevention Gate):
             当回测或分析时点 as_of 早于快照实际生成时点时，引擎必须刚性阻断，严禁未来宏观信息泄露到历史时点。

        2. 正常函数业务边界与参数契约:
           - snapshot 字典遵循宏观快照 Schema 契约，版本号为 '1.0.0'。
           - verify_macro_snapshot(as_of) 要求 as_of >= snapshot_generated_at。

        3. 测试数据与模拟场景说明:
           - 生成并注册宏观底账快照。
           - 模拟穿越测试: 传入 2020-01-01 (历史时点) 断言被防前视逻辑拦截；传入 2026-12-31 断言正常通过。

        4. 预期断言与结果验证:
           - 断言两次快照生成的 sha256 完全相等。
           - 断言 early as_of 抛出异常拦截。
           - 断言 legal as_of 返回有效快照字典。
        """
        # 执行登记与快照生成
        res1 = register_macro_samples()
        self.assertEqual(res1["indicators_count"], 17)
        self.assertGreaterEqual(res1["observations_count"], 9)
        self.assertGreaterEqual(res1["transmissions_count"], 8)

        # 再次执行，断言哈希完全一致（幂等性）
        res2 = register_macro_samples()
        self.assertEqual(res1["sha256"], res2["sha256"], "同一输入快照哈希不一致，违反确定性")
        self.assertEqual(res1["snapshot_path"], res2["snapshot_path"])

        # 快照读取与只读校验
        snap = verify_macro_snapshot(res1["snapshot_path"])
        self.assertEqual(snap["schema_version"], "1.0.0")
        self.assertEqual(len(snap["observations"]), res1["observations_count"])

        # 防前视测试：as_of 早于快照生成时点必须拒绝
        with self.assertRaises((ValueError, AssertionError)):
            verify_macro_snapshot(res1["snapshot_path"], as_of="2020-01-01T00:00:00Z")

        # 合法时点（晚于或等于快照时点）应正常通过
        valid_snap = verify_macro_snapshot(res1["snapshot_path"], as_of="2026-12-31T23:59:59Z")
        self.assertIsNotNone(valid_snap)


def test_macro_specs():
    TestMacroIndicators().test_macro_specs()

def test_observation_validation_and_rejections():
    TestMacroIndicators().test_observation_validation_and_rejections()

def test_snapshot_generation_and_idempotence():
    TestMacroIndicators().test_snapshot_generation_and_idempotence()


if __name__ == "__main__":
    unittest.main()
