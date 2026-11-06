"""单元测试: 金融计算年金数值稳定性与 80 位高精度独立交叉对账测试套件.

测试覆盖范围:
1. 【UT-ANNUITY-01】: 80 位高精度 Decimal 逐期现金流独立参考基准，覆盖 13 种极端近零与分界利率
2. 【UT-ANNUITY-02】: 极端超大期数与不可表示超限浮点输入拦截防御
3. 【UT-ANNUITY-03】: 严格输入契约校验，拦截布尔型、NaN 与 Inf 等非有限非法浮点输入
"""
from decimal import Decimal, localcontext
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finance_tools.basic import cashflow


class AnnuityStabilityTests(unittest.TestCase):
    """【单元测试】金融计算现金流折现与年金因子高精度数值稳定性测试."""

    def test_decimal_cashflow_oracle(self):
        """【UT-ANNUITY-01: 80位高精度逐期现金流独立对账】

        1. 测试功能与测试点:
           - 验证现金流求解器在极端近零利率（如 1e-16, 1e-12, 1e-8）及分界点利率（1e-4, 5%）下的数值稳定性。
           - 杜绝使用被测代码本身的 expm1 展开方程做循环论证，强制以 Python 标准库 80 位精度 Decimal 逐期贴现累加求和作为绝对预言机。

        2. 正常函数业务边界与参数契约:
           - 贴现利率 r: 有限实数，支持负利率、绝对零利率与常规利率，本用例覆盖 [-0.05, 0.05] 及近零正负区间。
           - 期数 periods: 正整数，本用例覆盖短中长周期 (n=1, n=10, n=360)。
           - 支付时点 when: 'begin' (期初支付/预付年金) 或 'end' (期末支付/普通年金)。
           - 求解模式: 支持 'pv' (现值), 'pmt' (每期年金), 'fv' (终值)。

        3. 测试数据与模拟场景说明:
           - 模拟场景 A: 日本央行零利率及极小浮动环境 (r = 0.0, ±1e-16, ±1e-12, ±1e-8)。
           - 模拟场景 B: expm1 与传统公式切换边界测试 (r = ±0.00009999 与 ±0.00010000)。
           - 模拟场景 C: 机构常规贷款与债券贴现环境 (r = ±0.05，涵盖 360 期超长按揭久期)。
           - 现金流构造: 固定每期支付 -10.0，期末资产终值 25.0，期初投资现值 100.0。

        4. 预期断言与结果验证:
           - 被测 cashflow 求解出的 pv/pmt/fv 与 80 位 Decimal 独立参考值的归一化相对误差不超过 2e-10。
        """
        # 直接逐期累加，不复制被测实现中的 expm1 因子。
        rates = (0., 1e-16, -1e-16, 1e-12, -1e-12, 1e-8, -1e-8,
                 .00009999, -.00009999, .0001, -.0001, .05, -.05)
        with localcontext() as ctx:
            ctx.prec = 80
            for r in rates:
                for n in (1, 10, 360):
                    for when in ('begin', 'end'):
                        with self.subTest(rate=r, periods=n, when=when):
                            g = 1 + Decimal(str(r))
                            start = 0 if when == 'begin' else 1
                            pv_payments = sum(g**(-t) for t in range(start, n+start))
                            expected_pv = float(Decimal(10)*pv_payments - Decimal(25)*g**(-n))
                            expected_pmt = float(-(Decimal(100)+Decimal(25)*g**(-n))/pv_payments)
                            expected_fv = float(-Decimal(100)*g**n+Decimal(10)*pv_payments*g**n)
                            kwargs = dict(interest_rate=r,periods=n,when=when)
                            actuals = (
                                (cashflow('pv',payment=-10,future_value=25,**kwargs)['value'],expected_pv),
                                (cashflow('pmt',present_value=100,future_value=25,**kwargs)['value'],expected_pmt),
                                (cashflow('fv',payment=-10,present_value=100,**kwargs)['value'],expected_fv),
                            )
                            for actual, expected in actuals:
                                self.assertAlmostEqual(actual,expected,delta=2e-10*max(1,abs(expected)))

    def test_extreme_unrepresentable_input_rejected(self):
        """【UT-ANNUITY-02: 极端超大期数与浮点溢出边界拦截】

        1. 测试功能与测试点:
           - 验证当输入超出 IEEE 754 双精度浮点可表示范围的物理极值期数时，系统是否能主动拦截并抛出 ValueError，杜绝底层抛出无控制的 OverflowError 或返回 inf。

        2. 正常函数业务边界与参数契约:
           - periods: 必须为合理金融周期（通常 n <= 1200 即 100 年月度）。当 n 达到 1e308 时已超出物理金融意义。

        3. 测试数据与模拟场景说明:
           - 模拟恶意或计算溢出导致的超大期数注入: periods = 1e308，贴现利率 r = 1e-5 与 -1e-5。

        4. 预期断言与结果验证:
           - 断言系统刚性抛出 ValueError 阻断非法运算。
        """
        for r in (1e-5,-1e-5):
            with self.subTest(rate=r), self.assertRaises(ValueError):
                cashflow('pv',interest_rate=r,periods=1e308,payment=-10)

    def test_finite_input_contract_preserved(self):
        """【UT-ANNUITY-03: 非有限浮点数与布尔类型刚性拦截门禁】

        1. 测试功能与测试点:
           - 验证金融计算核心输入门禁对非有限数（NaN, Inf）以及 Python 常见隐式类型混淆（True/False）的物理拦截机制。

        2. 正常函数业务边界与参数契约:
           - interest_rate: 必须为有限非布尔浮点数 (math.isfinite() == True 且 not isinstance(r, bool))。

        3. 测试数据与模拟场景说明:
           - 模拟场景 A: 传入布尔值 True (在 Python 中可被视作 1.0，但无金融语义)。
           - 模拟场景 B: 传入非数 float('nan') (如除零或清洗失败的未定义中间量)。
           - 模拟场景 C: 传入无穷大 float('inf') (如发散的极端风险系数)。

        4. 预期断言与结果验证:
           - 断言系统在遇到上述任一非法输入时，立即抛出 ValueError 刚性中断，杜绝 NaN 污染全管道。
        """
        for r in (True, float('nan'),float('inf')):
            with self.subTest(rate=r), self.assertRaises(ValueError):
                cashflow('pv',interest_rate=r,periods=10,payment=-10)


if __name__ == '__main__':
    unittest.main()
