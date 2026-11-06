"""高级投研分析形式单元测试与断言验证."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.advanced_analytics import (
    AdvancedAnalyticsEngine,
    SensitivityCell,
    DuPontDiagnosis,
)


class TestAdvancedAnalytics(unittest.TestCase):
    def test_dupont_3stage_and_5stage(self):
        """【UT-ANALYTICS-01: 杜邦三阶段与五阶段拆解及商业模式质量诊断(A~C评级)】

        1. 测试功能与测试点:
           - 验证 AdvancedAnalyticsEngine.compute_dupont_analysis 杜邦三阶段 (净利率、周转率、权益乘数) 与五阶段拆解。
           - 商业模式质量诊断:
             - 场景 1: 高净利、高周转、低杠杆 -> 诊断为 '双轮驱动'，质量评级 'A'；
             - 场景 2: 高负债、低周转、高杠杆 (乘数 > 4.0x) -> 诊断为 '高杠杆驱动'，质量评级 'C'。

        2. 正常函数业务边界与参数契约:
           - net_income, revenue, total_assets, equity > 0。
           - 返回 DuPontDiagnosis 强类型数据类。

        3. 测试数据与模拟场景说明:
           - 场景 1 (优质龙头): 净利润 5.3万，营收 9.6万，总资产 8.5万，净资产 6.1万，息税前利润 6.0万，利息 300。
           - 场景 2 (杠杆驱动): 净利润 200，营收 2000，总资产 10000，净资产 2000 (权益乘数 5.0x)。

        4. 预期断言与结果验证:
           - 场景 1: net_margin ≈ 55.21%，asset_turnover ≈ 1.13，multiplier ≈ 1.39，roe ≈ 86.89%，grade == 'A'。
           - 场景 2: quality_grade == 'C'，primary_driver_zh 包含 '高杠杆'。
        """
        # 1. 样板企业：高毛利高周转优质龙头
        diag = AdvancedAnalyticsEngine.compute_dupont_analysis(
            net_income=53000.0,
            revenue=96000.0,
            total_assets=85000.0,
            equity=61000.0,
            ebit=60000.0,
            interest_expense=300.0,
        )
        self.assertAlmostEqual(diag.net_margin, 55.21, delta=0.5)
        self.assertAlmostEqual(diag.asset_turnover, 1.13, delta=0.1)
        self.assertAlmostEqual(diag.equity_multiplier, 1.39, delta=0.1)
        self.assertAlmostEqual(diag.roe, 86.89, delta=1.0)
        self.assertEqual(diag.quality_grade, "A")
        self.assertIn("双轮驱动", diag.primary_driver_zh)

        # 2. 样板企业：高负债金融杠杆型 (乘数 > 4.0)
        leveraged = AdvancedAnalyticsEngine.compute_dupont_analysis(
            net_income=200.0,
            revenue=2000.0,
            total_assets=10000.0,
            equity=2000.0, # 乘数 5.0x
        )
        self.assertEqual(leveraged.quality_grade, "C")
        self.assertIn("高杠杆", leveraged.primary_driver_zh)

    def test_dcf_sensitivity_matrix(self):
        """【UT-ANALYTICS-02: 二维DCF敏感度矩阵构建(WACC与永续增长率双向单调性)】

        1. 测试功能与测试点:
           - 验证 AdvancedAnalyticsEngine.compute_dcf_sensitivity_matrix 构建 5x5 贴现率与永续增长率敏感度矩阵。
           - 严格断言数学单调性公理:
             1. 纵向单调性: 贴现率 (WACC) 上升时，每股公允估值单调递减；
             2. 横向单调性: 永续终值增长率 (g) 上升时，每股公允估值单调递增。

        2. 正常函数业务边界与参数契约:
           - cash_flow > 0, base_wacc > base_terminal_growth (收敛条件)。
           - 返回矩阵包含 5 行 WACC x 5 列 Terminal Growth。

        3. 测试数据与模拟场景说明:
           - 自由现金流 1000，5 年复合增长率梯队 [15%, 12%, 10%, 8%, 6%]。
           - 基准 WACC 9.0%，基准永续增长率 2.5%，总股数 100，现价 120，净债务 500。

        4. 预期断言与结果验证:
           - 矩阵行数与列数均为 5。
           - 每一列随 WACC 增大估值逐行递减 (val[i] >= val[i+1])。
           - 每一行随 g 增大估值逐列递增 (val[i] <= val[i+1])。
        """
        matrix_result = AdvancedAnalyticsEngine.compute_dcf_sensitivity_matrix(
            cash_flow=1000.0,
            base_growth_rates=[0.15, 0.12, 0.10, 0.08, 0.06],
            base_wacc=0.09,
            base_terminal_growth=0.025,
            shares=100.0,
            current_price=120.0,
            net_debt=500.0,
        )
        matrix = matrix_result["matrix"]
        self.assertEqual(len(matrix), 5)  # 5 行 WACC
        self.assertEqual(len(matrix[0]), 5)  # 5 列 Terminal Growth

        # 验证单调性：随着 WACC 增加（贴现率上升），同列估值应单调下降
        col_0_vals = [matrix[r][0]["fair_value"] for r in range(5)]
        for i in range(len(col_0_vals) - 1):
            self.assertGreaterEqual(col_0_vals[i], col_0_vals[i + 1])

        # 验证单调性：随着永续增长率 g 增加，同行估值应单调上升
        row_0_vals = [matrix[0][c]["fair_value"] for c in range(5)]
        for i in range(len(row_0_vals) - 1):
            self.assertLessEqual(row_0_vals[i], row_0_vals[i + 1])

    def test_key_driver_elasticity_tornado(self):
        """【UT-ANALYTICS-03: 关键驱动因子弹性排序与龙卷风图分析(利润率主导)】

        1. 测试功能与测试点:
           - 验证 AdvancedAnalyticsEngine.compute_key_driver_elasticity 计算核心财务变量对企业公允估值的边际敏感弹性。
           - 输出排序后的龙卷风敏感度条目 (Tornado Chart)，识别对估值影响最剧烈的核心胜负手。

        2. 正常函数业务边界与参数契约:
           - 输入基准营收、利润率、贴现率与永续增长率。
           - 返回按绝对弹性降序排列的因子列表。

        3. 测试数据与模拟场景说明:
           - 现价 100，基准公允价 125，营收 5000，营业利润率 25%，基准 WACC 9.0%，永续增长率 2.5%。

        4. 预期断言与结果验证:
           - 驱动因子数量为 4。
           - 排序第 1 名因子为利润率 (rank == 1，driver_name_zh 包含 '利润率')。
        """
        drivers = AdvancedAnalyticsEngine.compute_key_driver_elasticity(
            current_price=100.0,
            base_fair_value=125.0,
            base_revenue=5000.0,
            base_margin=0.25,
            base_wacc=0.09,
            base_terminal_g=0.025,
        )
        self.assertEqual(len(drivers), 4)
        # 弹性排序第一名必须为 Margin
        self.assertEqual(drivers[0]["elasticity_rank"], 1)
        self.assertIn("利润率", drivers[0]["driver_name_zh"])

    def test_short_squeeze_potential(self):
        """【UT-ANALYTICS-04: 做空比例/借贷费率与空头挤压(Short Squeeze)爆发力评分】

        1. 测试功能与测试点:
           - 验证 AdvancedAnalyticsEngine.evaluate_short_squeeze_potential 评估轧空风险爆发力。
           - 结合空头持仓比例 (Short Interest %)、平仓天数 (Days To Cover) 与借贷融券成本 (Borrow Fee Rate) 多因子综合评分。

        2. 正常函数业务边界与参数契约:
           - short_interest_pct, days_to_cover, borrow_fee_rate >= 0。
           - 返回评分 squeeze_score (0~100) 及定性评级 squeeze_level_zh。

        3. 测试数据与模拟场景说明:
           - 场景 1 (极高轧空潜能): 空头比例 28%，回补天数 6.5 天，借券费率 12%；
           - 场景 2 (低博弈): 空头比例 2%，回补天数 1.2 天，借券费率 1%。

        4. 预期断言与结果验证:
           - 场景 1: squeeze_score >= 70.0，包含 '极高潜能'；
           - 场景 2: squeeze_score <= 30.0，包含 '低空头博弈'。
        """
        # 高空头挤压案例 (SI 28%, DTC 6.5 天)
        high_sq = AdvancedAnalyticsEngine.evaluate_short_squeeze_potential(
            short_interest_pct=0.28,
            days_to_cover=6.5,
            borrow_fee_rate=0.12,
        )
        self.assertGreaterEqual(high_sq["squeeze_score"], 70.0)
        self.assertIn("极高潜能", high_sq["squeeze_level_zh"])

        # 低空头案例 (SI 2%, DTC 1.2 天)
        low_sq = AdvancedAnalyticsEngine.evaluate_short_squeeze_potential(
            short_interest_pct=0.02,
            days_to_cover=1.2,
            borrow_fee_rate=0.01,
        )
        self.assertLessEqual(low_sq["squeeze_score"], 30.0)
        self.assertIn("低空头博弈", low_sq["squeeze_level_zh"])

    def test_catalyst_timeline(self):
        """【UT-ANALYTICS-05: 关键催化剂与里程碑时间轴时序对齐与格式化】

        1. 测试功能与测试点:
           - 验证 AdvancedAnalyticsEngine.generate_catalyst_timeline 格式化关键催化事件流。
           - 保证时间轴按事件日期对齐，输出标准化展示结构。

        2. 正常函数业务边界与参数契约:
           - 输入包含 date, type, headline 的事件字典列表。

        3. 测试数据与模拟场景说明:
           - 事件 1: 2026-11-15 Q3 财报公布；事件 2: 2026-12-10 临床二期数据读出。

        4. 预期断言与结果验证:
           - 时间轴长度为 2。
           - 首个事件日期为 '2026-11-15'。
        """
        events = [
            {"date": "2026-11-15", "type": "Q3 财报公布", "headline": "确认在手订单交付情况"},
            {"date": "2026-12-10", "type": "临床二期数据读出", "headline": "REC-994 关键终点有效性读出"},
        ]
        timeline = AdvancedAnalyticsEngine.generate_catalyst_timeline(events)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["date"], "2026-11-15")


if __name__ == "__main__":
    unittest.main()
