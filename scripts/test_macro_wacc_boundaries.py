"""单元测试: 宏观 WACC 边界防御、零债务自然收敛与显式零成本测试套件.

测试覆盖范围:
1. 【UT-WACC-01】: 宏观 WACC 非法入参物理拦截与异常类型防御 (NaN, Inf, 布尔值, 负债务, 越界税率)
2. 【UT-WACC-02】: 显式零债务成本与缺失值的物理隔离 (合法 0% 利率不被回退)
3. 【UT-WACC-03】: 零债务企业 WACC 自然极限收敛与来源标识 (WACC == Cost of Equity)
"""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from financial_reporting.macro_valuation import MacroValuationEngine as Engine


class MacroWaccBoundaryTests(unittest.TestCase):
    """【单元测试】宏观加权平均资本成本 (WACC) 边界与数值防御测试."""

    def test_reject_invalid_inputs(self):
        """【UT-WACC-01: 宏观WACC非法入参物理拦截与异常类型防御】

        1. 测试功能与测试点:
           - 验证加权平均资本成本求解器前置输入门禁。
           - 拦截非法数值: NaN、Inf、Python 隐式布尔值 (True/False)。
           - 拦截违反金融物理定义的输入: 市值 <= 0、总负债 < 0、税率不在 [0, 1] 区间、债务成本 < 0。

        2. 正常函数业务边界与参数契约:
           - market_cap: 有限浮点数且 > 0.0。
           - total_debt: 有限浮点数且 >= 0.0。
           - tax_rate: 有限浮点数且 0.0 <= tax_rate <= 1.0。
           - debt_cost: 有限浮点数且 >= 0.0。
           - beta: 有限非布尔浮点数。
           - rf: 有限非布尔浮点数。

        3. 测试数据与模拟场景说明:
           - 遍历 market_cap, total_debt, tax_rate, debt_cost, beta, rf 六大核心字段的各类非法注入值。

        4. 预期断言与结果验证:
           - 断言每项非法输入均刚性抛出 ValueError 阻断，杜绝非法浮点数进入折现分母。
        """
        base=dict(market_cap=100,total_debt=20,beta=1,rf=.03)
        invalid={'market_cap':[float('nan'),float('inf'),True,0],
                 'total_debt':[-1,float('nan'),True],
                 'tax_rate':[-.01,1.01,float('nan'),True],
                 'debt_cost':[-.01,float('nan'),float('inf'),True],
                 'beta':[True,float('nan')],'rf':[True,float('inf')]}
        for field,values in invalid.items():
            for value in values:
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    Engine.calculate_wacc(**dict(base,**{field:value}))

    def test_zero_cost_is_not_missing(self):
        """【UT-WACC-02: 显式零债务成本与缺失值的物理隔离】

        1. 测试功能与测试点:
           - 验证当用户或模型显式传入 debt_cost=0.0 时（例如无息股东借款、政府贴息或日本极低息特种贷款），系统严禁使用 `debt_cost or default` 语法将合法的 0 覆盖为默认假设。
           - 验证债务成本来源被明确标记为 'explicit_input'。

        2. 正常函数业务边界与参数契约:
           - 当 debt_cost is not None 且 debt_cost == 0 时，税前债务成本精确为 0.0。
           - WACC = (E/(E+D)) * Re + (D/(E+D)) * 0 = (100/200) * (0.03 + 1*0.05) + 0 = 0.5 * 0.08 = 0.04 (4.0%)。

        3. 测试数据与模拟场景说明:
           - 市值 100，负债 100，Beta 1.0，无风险利率 3%，ERP 默认 5% (Re = 8%)，债务成本显式传入 0。

        4. 预期断言与结果验证:
           - 断言 wacc 精确等于 0.04。
           - 断言 cost_of_debt_pre_tax 精确等于 0。
           - 断言 debt_cost_source 为 'explicit_input'。
        """
        result=Engine.calculate_wacc(100,100,1,.03,debt_cost=0)
        self.assertEqual(result['wacc'],.04)
        self.assertEqual(result['cost_of_debt_pre_tax'],0)
        self.assertEqual(result['debt_cost_source'],'explicit_input')

    def test_zero_debt_limit_and_assumption_label(self):
        """【UT-WACC-03: 零债务企业WACC自然极限收敛与来源标识】

        1. 测试功能与测试点:
           - 验证当企业为纯股权、零有息负债结构 (total_debt=0) 时，WACC 自然平滑收敛至权益资本成本 Re:
             lim_{D->0} WACC = Re = rf + beta * ERP。
           - 验证系统严禁抛出除零错误，债务权重恒为 0。

        2. 正常函数业务边界与参数契约:
           - total_debt == 0.0。
           - Re = 0.03 + 1.0 * 0.05 = 0.08 (8.0%)。
           - WACC 恒等于 Re = 8.0%。

        3. 测试数据与模拟场景说明:
           - 标的为完全无负债企业: 市值 100，负债 0，Beta 1.0，无风险利率 3%。

        4. 预期断言与结果验证:
           - 断言 wacc 精确等于 0.08。
           - 断言债务成本标记保留合法假设说明。
        """
        result=Engine.calculate_wacc(100,0,1,.03)
        self.assertEqual(result['wacc'],.08)
        self.assertEqual(result['debt_cost_source'],'assumption_rf_plus_125bps')


if __name__=='__main__':unittest.main()
