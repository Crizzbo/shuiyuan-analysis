"""买方金融计算中继层工具箱基础测试集 (Finance Tools Unit Test Suite).

严格遵循敏捷测试工程规范:
1. 采用统一标准编号: 【UT-FT-01】~【UT-FT-26】;
2. 每一个测试用例配备标准化中文测试说明文档 (docstring):
   - 【测试点与功能定位】: 明确验证的具体函数、算法与数学定理;
   - 【输入数据与场景】: 显式标注参数、基准利率、现金流序列与假定;
   - 【预期断言与验证机制】: 明确断言条件、浮点容差与异常拦截类型;
3. 纯本地离线断言，严格禁止网络连接，支持独立手算复核。
"""

from datetime import date, timedelta
from pathlib import Path
import os
import json
import math
import hashlib
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache" / "matplotlib")


def deny_network(*args, **kwargs):
    raise AssertionError("测试禁止网络连接")


socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network
from finance_tools.service import calculate, scenarios, sensitivity, research_record
from finance_tools.valuation import multistage_dcf, residual_income, reverse_dcf, reit_bridge, nav
from finance_tools.valuation import multiple_valuation
from finance_tools.basic import cashflow, dated_cashflow, financial_ratio, wacc, fixed_dcf, performance


class FinanceTests(unittest.TestCase):
    """金融计算中继层综合单体测试套件 (涵盖基础现金流、多阶段估值、比率与边界防御)."""

    def test_npv_time_zero(self):
        """【UT-FT-01: 现金流净现值 (NPV) 基准手算验证】

        1. 测试功能与测试点:
           - 验证基础两期现金流在标准折现率下的净现值 (NPV) 计算准确性与无偏手算一致性。

        2. 正常函数业务边界与参数契约:
           - cashflow("npv", cash_flows, discount_rate) 强类型契约。
           - discount_rate 必须为有效浮点数 (discount_rate > -1.0)。

        3. 测试数据与模拟场景说明:
           - 初始资本开支 -100，第 1 期收回现金 110，基准折现率 10.0% (0.1)。

        4. 预期断言与结果验证:
           - NPV = -100 + 110 / (1 + 0.1) = 0.0。
           - 断言计算结果与理论手算精确等于 0。
        """
        self.assertAlmostEqual(cashflow("npv", [-100, 110], 0.1)["value"], 0)

    def test_irr(self):
        """【UT-FT-02: 内部收益率 (IRR) 单解收敛验证】

        1. 测试功能与测试点:
           - 验证标准投资项目的内部收益率 (IRR) 单解数值迭代收敛精度。

        2. 正常函数业务边界与参数契约:
           - 现金流符号发生至少一次正负交替。
           - 返回令 NPV 为 0 的折现率。

        3. 测试数据与模拟场景说明:
           - 初始投入 -100，第 1 期回款 +110。

        4. 预期断言与结果验证:
           - NPV = -100 + 110 / (1 + r) = 0 -> r = 10% (0.1)。
           - 断言 IRR 精确收敛于 0.1。
        """
        self.assertAlmostEqual(cashflow("irr", [-100, 110])["value"], 0.1)

    def test_mirr(self):
        """【UT-FT-03: 修正内部收益率 (MIRR) 融资率与再投资率核算】

        1. 测试功能与测试点:
           - 验证考虑外部融资成本率与项目再投资收益率时的修正内部收益率 (MIRR)。

        2. 正常函数业务边界与参数契约:
           - finance_rate 与 reinvest_rate 均为有效正数。

        3. 测试数据与模拟场景说明:
           - 现金流序列 [-100, 110]，融资成本 finance_rate=5%，再投资收益率 reinvest_rate=3%。

        4. 预期断言与结果验证:
           - 单期正现金流终值不产生复利再投资，MIRR 精确等于 10% (0.1)。
        """
        self.assertAlmostEqual(cashflow("mirr", [-100, 110], finance_rate=0.05, reinvest_rate=0.03)["value"], 0.1)

    def test_annuity(self):
        """【UT-FT-04: 年金公式族 PMT/PV/FV 零利率手算核算】

        1. 测试功能与测试点:
           - 验证等额年金每期支付 (PMT)、现值 (PV) 与终值 (FV) 在零利率极限退化状态下的数值恒等。

        2. 正常函数业务边界与参数契约:
           - interest_rate == 0，退化为算术简单求和除法，包含除零保护。

        3. 测试数据与模拟场景说明:
           - 利率 0%，期数 10 期，现值 100 或每期分摊 -10。

        4. 预期断言与结果验证:
           - PMT(r=0, n=10, pv=100) = -10.0。
           - PV(r=0, n=10, pmt=-10) = 100.0。
           - FV(r=0, n=10, pmt=-10, pv=0) = 100.0。
        """
        self.assertAlmostEqual(cashflow("pmt", interest_rate=0, periods=10, present_value=100)["value"], -10)
        self.assertAlmostEqual(cashflow("pv", interest_rate=0, periods=10, payment=-10)["value"], 100)
        self.assertAlmostEqual(cashflow("fv", interest_rate=0, periods=10, payment=-10, present_value=0)["value"], 100)

    def test_xirr_xnpv_daycount(self):
        """【UT-FT-05: 不定期现金流 XIRR/XNPV 跨年实际天数折现】

        1. 测试功能与测试点:
           - 验证基于真实日历日期序列 (ACT/365) 的不定期现金流内部收益率与净现值。

        2. 正常函数业务边界与参数契约:
           - 日期序列严格单调递增，且长度与现金流序列完全一致。

        3. 测试数据与模拟场景说明:
           - 日期 ['2025-01-01', '2026-01-01']，跨度恰好 365 天，现金流 [-100, 110]。

        4. 预期断言与结果验证:
           - XIRR 精确等于 0.1 (10%)。
           - 在 10% 折现率下 XNPV 精确等于 0.0。
        """
        dates = ["2025-01-01", "2026-01-01"]
        self.assertAlmostEqual(dated_cashflow("xirr", dates, [-100, 110])["value"], 0.1)
        self.assertAlmostEqual(dated_cashflow("xnpv", dates, [-100, 110], 0.1)["value"], 0)

    def test_ratios(self):
        """【UT-FT-06: 8大基础财务与估值比率(ROE/ROA/毛利/PE/PB/EV)参数化核算】

        1. 测试功能与测试点:
           - 验证 8 种高频财务指标公式库运算精度: ROE、ROA、毛利率、净利率、PE、PB、EV/EBITDA、流动比率。

        2. 正常函数业务边界与参数契约:
           - 分母必须为正实数，除零拦截保护。

        3. 测试数据与模拟场景说明:
           - 参数化矩阵测试 8 个标准用例。

        4. 预期断言与结果验证:
           - ROE=10/100=0.1, ROA=10/200=0.05, 毛利率=40/100=0.4, 净利率=10/100=0.1。
           - PE=100/5=20x, PB=100/50=2x, EV/EBITDA=100/10=10x, 流动比率=100/50=2x。
        """
        for method, a, b, expected in [
            ("roe", 10, 100, .1),
            ("roa", 10, 200, .05),
            ("gross_margin", 40, 100, .4),
            ("net_margin", 10, 100, .1),
            ("pe", 100, 5, 20),
            ("pb", 100, 50, 2),
            ("ev_ebitda", 100, 10, 10),
            ("current_ratio", 100, 50, 2),
        ]:
            with self.subTest(method=method):
                self.assertAlmostEqual(financial_ratio(method, a, b)["value"], expected)

    def test_wacc(self):
        """【UT-FT-07: 加权平均资本成本 (WACC) 与 CAPM 股权成本计算】

        1. 测试功能与测试点:
           - 验证基于 CAPM 模型的股权资本成本与考虑税盾效应的债务资本成本加权计算。

        2. 正常函数业务边界与参数契约:
           - 股权价值与债务价值和大于 0，所得税率 0 <= t < 1。

        3. 测试数据与模拟场景说明:
           - E=800, D=200 (总资本 1000，权重 80%/20%)。
           - 无风险利率 Rf=3%, Beta=1.2, 市场组合期望回报 8% (风险溢价 5%)。
           - 税前债务成本 Kd=5%, 所得税率 t=25%。

        4. 预期断言与结果验证:
           - 股权成本 Ke = 0.03 + 1.2 * 0.05 = 0.09 (9.0%)。
           - 税后债务成本 = 0.05 * (1 - 0.25) = 0.0375。
           - WACC = 0.8 * 0.09 + 0.2 * 0.0375 = 0.0795 (7.95%)。
        """
        self.assertAlmostEqual(wacc(800, 200, .03, 1.2, .08, .05, .25)["value"], .0795)

    def test_dcf_hand_calculated(self):
        """【UT-FT-08: 多阶段自由现金流 (FCFF) 折现模型独立手算验证】

        1. 测试功能与测试点:
           - 验证多阶段现金流预测、戈登终值折现与从企业价值穿透至每股公允价值的全流程。

        2. 正常函数业务边界与参数契约:
           - discount_rate > terminal_growth (戈登收敛条件)。
           - shares > 0。

        3. 测试数据与模拟场景说明:
           - 基期 FCFF 100，预测期增长率 [10%, 5%]，WACC 10%，永续增长率 3%，总股数 10，净负债 50。

        4. 预期断言与结果验证:
           - 企业价值 EV = 1600.0。
           - 股权价值 = 1600 - 50 = 1550.0。
           - 每股公允价值 = 155.0。
        """
        result = multistage_dcf(100, [.1, .05], .1, .03, 10, "FCFF", 50)
        self.assertAlmostEqual(result["enterprise_value"], 1600)
        self.assertAlmostEqual(result["value_per_share"], 155)

    def test_dcf_library_crosscheck(self):
        """【UT-FT-09: 多阶段 DCF 与定值 DCF 开源库与自定义实现交叉双向核对】

        1. 测试功能与测试点:
           - 验证自研 multistage_dcf 算法与基准开源 fixed_dcf 实现的双向一致性。

        2. 正常函数业务边界与参数契约:
           - 覆盖负增长 (-10%)、零增长 (0%)、正增长 (+10%) 场景。

        3. 测试数据与模拟场景说明:
           - 基期现金流 100，折现率 12%，永续增长率 2%，净负债 30/50，总股数 10/20。

        4. 预期断言与结果验证:
           - 各种增长情景下两者输出的每股公允价值完全一致。
        """
        for growth in (-.1, 0, .1):
            own = multistage_dcf(100, [growth] * 5, .12, .02, 10, "FCFF", 30)
            library = fixed_dcf(100, growth, .12, .02, 20, 50, 10, 5)
            self.assertAlmostEqual(own["value_per_share"], library["value_per_share"])

    def test_fcfe_no_debt_bridge(self):
        """【UT-FT-10: 股权自由现金流 (FCFE) 零净负债桥接验证】

        1. 测试功能与测试点:
           - 验证 FCFE 模式直接折现为股东权益价值，严禁扣除净负债桥梁。

        2. 正常函数业务边界与参数契约:
           - scope == 'FCFE' 时 enterprise_value 字段必须为 None。

        3. 测试数据与模拟场景说明:
           - 基期 FCFE 100，零增长，折现率 10%，总股数 10。

        4. 预期断言与结果验证:
           - enterprise_value 为 None。
           - 每股公允价值精确等于 100.0。
        """
        result = multistage_dcf(100, [0], .1, 0, 10, "FCFE")
        self.assertIsNone(result["enterprise_value"])
        self.assertAlmostEqual(result["value_per_share"], 100)

    def test_residual_income_zero_excess(self):
        """【UT-FT-11: 剩余收益模型 (Residual Income) 零超额收益基准验证】

        1. 测试功能与测试点:
           - 验证当 ROE == r 时企业超额收益为 0，理论每股价值恒等于基期账面价值。

        2. 正常函数业务边界与参数契约:
           - 基期 BVPS > 0。

        3. 测试数据与模拟场景说明:
           - 基期 BVPS=100，预测期 ROE=10%，股权成本 r=10%。

        4. 预期断言与结果验证:
           - value_per_share 稳定精确等于 100.0。
        """
        self.assertAlmostEqual(residual_income(100, [.1, .1], [.5, .5], .1, .1, .02)["value_per_share"], 100)

    def test_residual_income_hand_calculated(self):
        """【UT-FT-12: 剩余收益模型 (RI) 1年期独立手算与终值验证】

        1. 测试功能与测试点:
           - 验证 1 年期高 ROE 剩余收益与零分红留存下的理论估值。

        2. 正常函数业务边界与参数契约:
           - 输入合法留存率与贴现率。

        3. 测试数据与模拟场景说明:
           - 基期净资产 100，第 1 年 ROE=20%，分红留存率 0 (全部派息)，股权成本 10%，永续超额收益为 0。

        4. 预期断言与结果验证:
           - 每股公允价值精准等于 200.0。
        """
        self.assertAlmostEqual(residual_income(100, [.2], [0], .1, .2, 0)["value_per_share"], 200)

    def test_reverse_recovery(self):
        """【UT-FT-13: 逆向 DCF 模型 (Reverse DCF) 市场隐含增长率收敛求解】

        1. 测试功能与测试点:
           - 验证 reverse_dcf 引擎根据市场交易现价反推隐含年化复合增长率。

        2. 正常函数业务边界与参数契约:
           - 算法在合理增长区间内单调求解。

        3. 测试数据与模拟场景说明:
           - 传入 5% 增长率对应的正向计算股价。

        4. 预期断言与结果验证:
           - status == 'converged'。
           - implied_growth 精确收敛于 0.05 (5.0%)。
        """
        price = fixed_dcf(100, .05, .1, .02, 0, 50, 10, 5)["value_per_share"]
        result = reverse_dcf(price, 100, 5, .1, .02, 10, "FCFF", 50)
        self.assertEqual(result["status"], "converged")
        self.assertAlmostEqual(result["implied_growth"], .05)

    def test_reverse_outside_bounds(self):
        """【UT-FT-14: 逆向 DCF 模型极值越界防御 (Outside Bounds 状态拦截)】

        1. 测试功能与测试点:
           - 验证当市场现价被炒作至荒谬极端价格 ($10,000) 时，算法主动拒绝非理性解。

        2. 正常函数业务边界与参数契约:
           - 越界返回强类型状态码。

        3. 测试数据与模拟场景说明:
           - 现价 10,000，基期现金流 100。

        4. 预期断言与结果验证:
           - status == 'outside_bounds'。
        """
        self.assertEqual(reverse_dcf(10000, 100, 5, .1, .02, 10, "FCFF")["status"], "outside_bounds")

    def test_reit_explicit_bridge(self):
        """【UT-FT-15: REITs 商业不动产现金流桥接 (FFO 与 AFFO 精准扣减)】

        1. 测试功能与测试点:
           - 验证房地产投资信托 (REITs) 从 GAAP 净利润向 FFO 与 AFFO 的桥接转换。

        2. 正常函数业务边界与参数契约:
           - 加回折旧摊销，扣减资产销售利得与维保资本支出。

        3. 测试数据与模拟场景说明:
           - 净利润 100，折旧摊销 20，销售利得 10，非经营项 5/2/-3，维保支出 15，直线租金平滑 -4。

        4. 预期断言与结果验证:
           - FFO == 114.0，AFFO == 95.0。
        """
        result = reit_bridge(100, 20, 10, 5, 2, -3, 15, [{"name": "扣直线租金", "amount": -4}], 10)
        self.assertEqual(result["ffo"], 114)
        self.assertEqual(result["affo"], 95)

    def test_nav(self):
        """【UT-FT-16: 资产净值法 (NAV) 逐项加总与优先股扣减折算】

        1. 测试功能与测试点:
           - 验证重资产企业各项资产重估价值加总、扣除总负债及优先股后的每股 NAV。

        2. 正常函数业务边界与参数契约:
           - shares > 0。

        3. 测试数据与模拟场景说明:
           - 资产估值 [100, 200]，总负债 50，优先股 20，调整项 -10，总股数 10。

        4. 预期断言与结果验证:
           - 净资产 = 300 - 50 - 20 - 10 = 220。
           - value_per_share 精准等于 22.0。
        """
        self.assertEqual(nav([100, 200], 50, 20, -10, 10)["value_per_share"], 22)

    def test_multiple_bridge(self):
        """【UT-FT-17: 可比公司乘数估值 (企业价值 EV 与股权价值 Equity 桥接)】

        1. 测试功能与测试点:
           - 验证可比乘数在企业价值模式 (扣除净负债) 与股权价值模式 (直接折算) 的双向计算。

        2. 正常函数业务边界与参数契约:
           - scope in ('enterprise', 'equity')。

        3. 测试数据与模拟场景说明:
           - 财务基准 100，目标乘数 10，企业价值下净负债 -20 (净现金)，总股数 10。

        4. 预期断言与结果验证:
           - 企业价值模式每股价值为 102.0。
           - 股权价值模式每股价值为 100.0。
        """
        self.assertEqual(multiple_valuation(100, 10, "enterprise", -20, 10)["value_per_share"], 102)
        self.assertEqual(multiple_valuation(100, 10, "equity", 0, 10)["value_per_share"], 100)

    def test_scenarios_and_sensitivity(self):
        """【UT-FT-18: 概率情景加权与二维敏感度矩阵切片】

        1. 测试功能与测试点:
           - 验证多情景概率加权期望值，以及折现率与永续增长率双变量敏感度矩阵单调性。

        2. 正常函数业务边界与参数契约:
           - 各情景概率和必须为 1.0。

        3. 测试数据与模拟场景说明:
           - 单基准情景概率 1.0；折现率 [10%, 20%]，永续增长率 [0%, 1%]。

        4. 预期断言与结果验证:
           - 期望每股价值为 100.0。
           - 敏感度矩阵行数为 4，折现率越低公允估值单调更高。
        """
        params = dict(cash_flow=100, growth_rates=[0], discount_rate=.1, terminal_growth=0,
                      shares=10, scope="FCFF", net_debt=0)
        result = scenarios("multistage_dcf", [{"name": "基准", "probability": 1, "parameters": params}])
        self.assertAlmostEqual(result["expected_value_per_share"], 100)
        rows = sensitivity(params, [.1, .2], [0, .01])
        self.assertEqual(len(rows), 4)
        self.assertGreater(rows[0]["calculation"]["result"]["value_per_share"], rows[2]["calculation"]["result"]["value_per_share"])

    def test_performance_drawdown_includes_initial_wealth(self):
        """【UT-FT-19: 投资组合业绩回撤 (Max Drawdown) 与复合年化收益率 (CAGR)】

        1. 测试功能与测试点:
           - 验证投资组合历史净值序列最大动态回撤 (包含初始本金边界) 与 CAGR。

        2. 正常函数业务边界与参数契约:
           - 收益率序列与日期列表一一对应。

        3. 测试数据与模拟场景说明:
           - 3 日收益率序列 [-10%, +20%, -10%]。

        4. 预期断言与结果验证:
           - max_drawdown 精确等于 -10.0% (-0.1)。
           - cagr 与理论公式一致。
        """
        returns = [-.1, .2, -.1]
        dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
        result = performance(returns, dates, 252, 0)
        self.assertAlmostEqual(result["max_drawdown"], -.1)
        self.assertAlmostEqual(result["cagr"], .972 ** 84 - 1)

    def test_record_is_unchecked(self):
        """【UT-FT-20: 投研证据生成与研究契约 Schema 结构性严格校验】

        1. 测试功能与测试点:
           - 验证金融计算中继层输出的标准记录能够通过 schemas/research.schema.json 契约验证。

        2. 正常函数业务边界与参数契约:
           - 初始化验证状态必须为 unchecked。

        3. 测试数据与模拟场景说明:
           - ROE 比率计算记录。

        4. 预期断言与结果验证:
           - verification_status == 'unchecked'。
           - library_version == '2.2.1'。
           - 契约结构校验 structural 成功通过。
        """
        calc = calculate("financial_ratio", {"operation": "roe", "numerator": 10, "denominator": 100})
        record = research_record(calc, "test", [{"field": "value", "unit": "ratio", "currency": None}], ["obs-1"], [])
        self.assertEqual(record["verification_status"], "unchecked")
        self.assertEqual(calc["library_version"], "2.2.1")
        # 将真实输出送入现有 Schema 子对象校验，避免接口自说自话。
        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_research import structural
        schema = json.loads((ROOT / "schemas/research.schema.json").read_text(encoding="utf-8"))
        structural(record, schema["$defs"]["calculation"], schema)

    def test_local_file_boundary(self):
        """【UT-FT-21: 本地相对路径安全防御 (越界/绝对路径/UNC 严格阻断)】

        1. 测试功能与测试点:
           - 验证本地路径安全防御边界，严禁上级目录跳出、跨盘符绝对路径及 UNC 路径。

        2. 正常函数业务边界与参数契约:
           - 违规路径抛出强类型 ValueError。

        3. 测试数据与模拟场景说明:
           - 非法路径: '../outside.json', 'C:/outside.json', '//host/file.json'。

        4. 预期断言与结果验证:
           - 非法路径均抛出 ValueError。
           - 合法路径解析后严格位于项目根目录内。
        """
        from scripts.calculate_finance import local_path
        for path in ("../outside.json", "C:/outside.json", "//host/file.json", "a\\b.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                local_path(path)
        self.assertEqual(local_path("examples/finance-dcf.request.json"), ROOT / "examples/finance-dcf.request.json")

    def test_dependency_license_hashes(self):
        """【UT-FT-22: 第三方开源计算库依赖清册与 SHA-256 许可证哈希验签】

        1. 测试功能与测试点:
           - 验证第三方金融依赖清册中的各开源库许可证文件未受非法篡改。

        2. 正常函数业务边界与参数契约:
           - 许可证物理文件存在且位于项目内。

        3. 测试数据与模拟场景说明:
           - 读取 third_party/finance/dependency-manifest.json。

        4. 预期断言与结果验证:
           - 每一个许可证文件的 SHA-256 哈希值与清单严格吻合。
        """
        manifest = json.loads((ROOT / "third_party/finance/dependency-manifest.json").read_text(encoding="utf-8"))
        for dist in manifest:
            for license_file in dist["license_files"]:
                file = (ROOT / license_file["path"]).resolve()
                self.assertTrue(file.is_relative_to(ROOT))
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), license_file["sha256"])

    def test_invalid_scenario_probability(self):
        """【UT-FT-23: 情景分析概率和不等于 1.0 刚性校验防御】

        1. 测试功能与测试点:
           - 验证情景分析输入概率归一化校验，严禁概率和不等于 1.0 的数据通过。

        2. 正常函数业务边界与参数契约:
           - 概率和 != 1.0 必须抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 仅传入一个概率为 0.5 的情景。

        4. 预期断言与结果验证:
           - 刚性抛出 ValueError 阻断。
        """
        params = dict(asset_values=[100], liabilities=0, preferred_equity=0, other_adjustments=0, shares=10)
        with self.assertRaises(ValueError):
            scenarios("nav", [{"name": "基准", "probability": .5, "parameters": params}])

    def test_annual_risk_free_rate(self):
        """【UT-FT-24: 夏普比率 (Sharpe Ratio) 年化无风险利率转换核算】

        1. 测试功能与测试点:
           - 验证将年化无风险利率 (5.0%) 转换至单日无风险利率并计算年化夏普比率。

        2. 正常函数业务边界与参数契约:
           - 输入日收益率序列与年化利率。

        3. 测试数据与模拟场景说明:
           - 收益率序列 [-.1, .2, -.1]，年交易日 252 天。

        4. 预期断言与结果验证:
           - 夏普比率与统计学标准理论手算完全一致。
        """
        from statistics import mean, stdev
        values = [-.1, .2, -.1]
        risk_free_per_period = 1.05 ** (1/252) - 1
        expected = mean([x - risk_free_per_period for x in values]) / stdev(values) * math.sqrt(252)
        self.assertAlmostEqual(performance(values, ["2026-01-01", "2026-01-02", "2026-01-03"], 252, .05)["sharpe"], expected)

    def test_undefined_performance_is_blocked(self):
        """【UT-FT-25: 零波动率退化序列夏普比率除零防御阻断】

        1. 测试功能与测试点:
           - 验证收益率序列全为 0 (标准差为 0) 时夏普比率除零防御。

        2. 正常函数业务边界与参数契约:
           - 零波动率禁止输出 NaN。

        3. 测试数据与模拟场景说明:
           - 收益率序列 [0, 0, 0]。

        4. 预期断言与结果验证:
           - 刚性抛出 ValueError。
        """
        with self.assertRaises(ValueError):
            performance([0, 0, 0], ["2026-01-01", "2026-01-02", "2026-01-03"], 252, 0)

    def test_invalid_inputs(self):
        """【UT-FT-26: 非法输入异常抛出穷举回归 (类型、NaN、非收敛、除零)】

        1. 测试功能与测试点:
           - 验证 14 种非法输入边界场景（非数值类型、NaN 污染、IRR 多重根无解、负贴现率、除零）。

        2. 正常函数业务边界与参数契约:
           - 任意非法参数坚决抛出 (ValueError, TypeError)。

        3. 测试数据与模拟场景说明:
           - 遍历 14 组违规匿名调用闭包。

        4. 预期断言与结果验证:
           - 14 个测试分支全部抛出 ValueError 或 TypeError。
        """
        bad = [
            lambda: cashflow("npv", [-100, 110], "10%"),
            lambda: cashflow("npv", [-100, float("nan")], .1),
            lambda: cashflow("irr", [-100, 230, -132]),
            lambda: financial_ratio("roe", 10, 0),
            lambda: financial_ratio("roe", True, 100),
            lambda: multistage_dcf(100, [], .1, .02, 10, "FCFF"),
            lambda: multistage_dcf(100, [0], .1, .1, 10, "FCFF"),
            lambda: multistage_dcf(100, [0], .1, .02, 0, "FCFF"),
            lambda: multistage_dcf(100, [0], .1, .02, 10, "FCFE", 50),
            lambda: residual_income(100, [.1], [2], .1, .1, .02),
            lambda: dated_cashflow("xirr", ["2025-01-01", "2025-01-01"], [-100, 110]),
            lambda: dated_cashflow("xirr", ["2025-01-01", "2026-01-01", "2027-01-01"], [-100, 230, -132]),
            lambda: calculate("financial_ratio", {"operation": "roe", "numerator": 1, "denominator": 2, "unknown": 1}),
            lambda: wacc(800, 200, .03, 1, .08, .05, 2),
        ]
        for i, action in enumerate(bad):
            with self.subTest(case=i), self.assertRaises((ValueError, TypeError)):
                action()


if __name__ == "__main__":
    unittest.main(verbosity=2)
