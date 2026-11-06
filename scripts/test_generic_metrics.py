"""通用财务指标类单元测试 (Generic Financial Metrics Test Suite)

覆盖范围：
1. 盈利能力指标（ROE、ROA、毛利率、营业利润率、净利率）；
2. 流动性与短期偿债比率（流动比率、速动比率、现金比率）；
3. 资本结构与长期偿债（资产负债率、产权比率、利息保障倍数）；
4. 现金流与收益质量（FCF Yield、经营现金流净利润比）；
5. 市场估值倍数（PE、PB、PS）；
6. 边界与除零防御拦截（零分母、负分母、非法数值阻断）；
7. 综合财务体检批处理计算（compute_health_profile）；
8. 离线网络隔离（严禁任何网络外联）。
"""

import math
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 严禁任何网络连接
def deny_network(*args, **kwargs):
    raise AssertionError("测试执行过程中禁止网络访问")

socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

from financial_reporting.generic_metrics import GenericFinancialMetrics, MetricResult


class GenericFinancialMetricsTests(unittest.TestCase):
    """通用指标封装类单元测试。"""

    def test_profitability_metrics(self):
        """【UT-GENMETRIC-01: 核心盈利能力比率推导(ROE/ROA/毛利率/营业利润率/净利率)】

        1. 测试功能与测试点:
           - 验证 GenericFinancialMetrics 5 大盈利指标的计算保真度。
           - 验证数值精度、格式化显示字符串 (display_value) 及强类型 MetricResult 封装。

        2. 正常函数业务边界与参数契约:
           - 分母必须为正实数，计算结果映射为对应百分比格式。

        3. 测试数据与模拟场景说明:
           - 净利润 150，净资产 1000，总资产 3000，营业收入 1000，毛利 400，营业利润 250。

        4. 预期断言与结果验证:
           - ROE == 0.15 (15.00%)，ROA == 0.05 (5.00%)。
           - Gross Margin == 0.40 (40.00%)，Operating Margin == 0.25 (25.00%)，Net Margin == 0.15 (15.00%)。
        """
        # 1. ROE: 净利润 150，净资产 1000 -> 15.00%
        res = GenericFinancialMetrics.roe(150, 1000)
        self.assertAlmostEqual(res.value, 0.15)
        self.assertEqual(res.display_value, "15.00%")
        self.assertEqual(res.metric_id, "roe")

        # 2. ROA: 净利润 150，总资产 3000 -> 5.00%
        res_roa = GenericFinancialMetrics.roa(150, 3000)
        self.assertAlmostEqual(res_roa.value, 0.05)
        self.assertEqual(res_roa.display_value, "5.00%")

        # 3. Gross Margin: 毛利 400，收入 1000 -> 40.00%
        gm = GenericFinancialMetrics.gross_margin(400, 1000)
        self.assertAlmostEqual(gm.value, 0.40)
        self.assertEqual(gm.display_value, "40.00%")

        # 4. Operating Margin: 营业利润 250，收入 1000 -> 25.00%
        om = GenericFinancialMetrics.operating_margin(250, 1000)
        self.assertAlmostEqual(om.value, 0.25)
        self.assertEqual(om.display_value, "25.00%")

        # 5. Net Margin: 净利润 150，收入 1000 -> 15.00%
        nm = GenericFinancialMetrics.net_margin(150, 1000)
        self.assertAlmostEqual(nm.value, 0.15)
        self.assertEqual(nm.display_value, "15.00%")

    def test_liquidity_metrics(self):
        """【UT-GENMETRIC-02: 流动性与短期防暴跌清偿比率(流动比率/速动比率/现金比率)】

        1. 测试功能与测试点:
           - 验证短期偿债防暴跌三道防线: 流动比率 (Current Ratio)、速动比率 (Quick Ratio)、超速动现金比率 (Cash Ratio)。
           - 验证格式化倍数显示 'X.XXx'。

        2. 正常函数业务边界与参数契约:
           - 流动负债 current_liabilities > 0。

        3. 测试数据与模拟场景说明:
           - 流动负债 250，流动资产 500，速动资产 375，现金 200。

        4. 预期断言与结果验证:
           - 流动比率 2.00x，速动比率 1.50x，现金比率 0.80x。
        """
        # 流动资产 500，流动负债 250 -> 2.00x
        cr = GenericFinancialMetrics.current_ratio(500, 250)
        self.assertAlmostEqual(cr.value, 2.0)
        self.assertEqual(cr.display_value, "2.00x")

        # 速动资产 375，流动负债 250 -> 1.50x
        qr = GenericFinancialMetrics.quick_ratio(375, 250)
        self.assertAlmostEqual(qr.value, 1.5)
        self.assertEqual(qr.display_value, "1.50x")

        # 现金 200，流动负债 250 -> 0.80x
        cash_r = GenericFinancialMetrics.cash_ratio(200, 250)
        self.assertAlmostEqual(cash_r.value, 0.8)
        self.assertEqual(cash_r.display_value, "0.80x")

    def test_solvency_metrics(self):
        """【UT-GENMETRIC-03: 长期偿债与资本结构安全垫(资产负债率/产权比率/利息保障倍数)】

        1. 测试功能与测试点:
           - 验证长期资本杠杆与财务脆弱性比率: 资产负债率 (Debt-to-Assets)、产权比率 (Debt-to-Equity) 与利息保障倍数 (Interest Coverage)。

        2. 正常函数业务边界与参数契约:
           - 总资产与净资产大于零，利息费用 > 0。

        3. 测试数据与模拟场景说明:
           - 总负债 1200，总资产 3000，净资产 1000，息税前利润 EBIT 300，利息支出 50。

        4. 预期断言与结果验证:
           - 资产负债率 40.00%，产权比率 1.20x，利息保障倍数 6.00x。
        """
        # 总负债 1200，总资产 3000 -> 40.00%
        da = GenericFinancialMetrics.debt_to_assets(1200, 3000)
        self.assertAlmostEqual(da.value, 0.40)
        self.assertEqual(da.display_value, "40.00%")

        # 产权比率: 总负债 1200，净资产 1000 -> 1.20x
        de = GenericFinancialMetrics.debt_to_equity(1200, 1000)
        self.assertAlmostEqual(de.value, 1.2)
        self.assertEqual(de.display_value, "1.20x")

        # 利息保障倍数: EBIT 300，利息 50 -> 6.00x
        ic = GenericFinancialMetrics.interest_coverage(300, 50)
        self.assertAlmostEqual(ic.value, 6.0)
        self.assertEqual(ic.display_value, "6.00x")

    def test_cash_flow_and_valuation_metrics(self):
        """【UT-GENMETRIC-04: 买方现金流收益率与市场估值倍数(FCF Yield/PE/PB/PS)】

        1. 测试功能与测试点:
           - 验证真实现金流回报率 (FCF Yield) 与净利润现金含量 (OCF Ratio)。
           - 验证买方常用乘数: 市盈率 (PE)、市净率 (PB)、市销率 (PS)。

        2. 正常函数业务边界与参数契约:
           - 市值、EPS、BPS 及营收均为正实数。

        3. 测试数据与模拟场景说明:
           - FCF 80，市值 1000；OCF 200，净利润 150；股价 100，EPS 5，BPS 25，营收 500。

        4. 预期断言与结果验证:
           - FCF Yield == 8.00%，OCF Ratio ≈ 1.33x。
           - PE == 20.00x，PB == 4.00x，PS == 4.00x。
        """
        # 自由现金流收益率: FCF 80，市值 1000 -> 8.00%
        fcf_y = GenericFinancialMetrics.fcf_yield(80, 1000)
        self.assertAlmostEqual(fcf_y.value, 0.08)
        self.assertEqual(fcf_y.display_value, "8.00%")

        # 净利润现金含量: OCF 200，净利润 150 -> 1.33x
        ocf_r = GenericFinancialMetrics.operating_cash_flow_ratio(200, 150)
        self.assertAlmostEqual(ocf_r.value, 1.3333, places=3)

        # PE: 股价 100，EPS 5 -> 20.00x
        pe_res = GenericFinancialMetrics.pe(100, 5)
        self.assertAlmostEqual(pe_res.value, 20.0)
        self.assertEqual(pe_res.display_value, "20.00x")

        # PB: 股价 100，BPS 25 -> 4.00x
        pb_res = GenericFinancialMetrics.pb(100, 25)
        self.assertAlmostEqual(pb_res.value, 4.0)
        self.assertEqual(pb_res.display_value, "4.00x")

        # PS: 市值 2000，收入 500 -> 4.00x
        ps_res = GenericFinancialMetrics.ps(2000, 500)
        self.assertAlmostEqual(ps_res.value, 4.0)
        self.assertEqual(ps_res.display_value, "4.00x")

    def test_defensive_zero_and_negative_handling(self):
        """【UT-GENMETRIC-05: 底层除零/负分母/资不抵债畸形ROE及NaN非数刚性拦截】

        1. 测试功能与测试点:
           - 验证金融数学防守底线:
             1. 分母为 0 刚性抛出 ValueError；
             2. 资不抵债 (equity < 0) 时严禁计算输出畸形的正 ROE；
             3. 亏损企业 (EPS < 0) 禁止输出伪正 PE；
             4. 任何 NaN 污染数据直接阻断。

        2. 正常函数业务边界与参数契约:
           - 非法参数抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - ROE(100, 0), ROE(100, -500), PE(50, -2.5), NetMargin(NaN, 100)。

        4. 预期断言与结果验证:
           - 4 种违规场景全部抛出 ValueError。
        """
        # 分母为零
        with self.assertRaises(ValueError):
            GenericFinancialMetrics.roe(100, 0)

        # 净资产为负（资不抵债时禁止输出畸形正 ROE）
        with self.assertRaises(ValueError):
            GenericFinancialMetrics.roe(100, -500)

        # EPS 为负时不适用常规正 PE
        with self.assertRaises(ValueError):
            GenericFinancialMetrics.pe(50, -2.5)

        # 非数 / NaN
        with self.assertRaises(ValueError):
            GenericFinancialMetrics.net_margin(float("nan"), 100)

    def test_compute_health_profile(self):
        """【IT-GENMETRIC-06: 综合财务体检全息批处理流水线与16项核心指标健康扫描】

        1. 测试功能与测试点:
           - 验证 GenericFinancialMetrics.compute_health_profile 对单家企业原始全量科目的批处理解析。
           - 一次性派发并推导出 16 项关键核心财务比率，自动统计计算成功数与跳过数。

        2. 正常函数业务边界与参数契约:
           - 输入包含财务三表底稿与行情字段的字典。
           - 返回包含 computed_metrics_count, omitted_or_error_count 及 metrics 字典。

        3. 测试数据与模拟场景说明:
           - 样本企业：营收 10000，营业利润 2100，净利润 1600，净资产 8000，总资产 15000，负债 7000。

        4. 预期断言与结果验证:
           - computed_metrics_count == 16，omitted_or_error_count == 0。
           - ROE == 20.00%，流动比率 == 2.00x，PE == 17.00x，利息保障倍数 == 14.00x。
        """
        sample_company = {
            "revenue": 10000.0,
            "gross_profit": 4200.0,
            "operating_income": 2100.0,
            "net_income": 1600.0,
            "equity": 8000.0,
            "average_equity": 8000.0,
            "total_assets": 15000.0,
            "average_total_assets": 15000.0,
            "total_liabilities": 7000.0,
            "current_assets": 6000.0,
            "current_liabilities": 3000.0,
            "quick_assets": 4500.0,
            "cash_and_equivalents": 2500.0,
            "total_debt": 3200.0,
            "ebit": 2100.0,
            "interest_expense": 150.0,
            "free_cash_flow": 1200.0,
            "operating_cash_flow": 1900.0,
            "price": 85.0,
            "eps": 5.0,
            "bps": 25.0,
            "market_cap": 27200.0,
        }

        profile = GenericFinancialMetrics.compute_health_profile(sample_company)
        self.assertEqual(profile["computed_metrics_count"], 16)
        self.assertEqual(profile["omitted_or_error_count"], 0)

        metrics = profile["metrics"]
        self.assertEqual(metrics["roe"]["display_value"], "20.00%")
        self.assertEqual(metrics["current_ratio"]["display_value"], "2.00x")
        self.assertEqual(metrics["pe"]["display_value"], "17.00x")
        self.assertEqual(metrics["interest_coverage"]["display_value"], "14.00x")


if __name__ == "__main__":
    unittest.main()
