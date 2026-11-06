"""强约束估值模型单元测试与断言验证."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.strong_constrained_valuation import (
    CompanyFinancialFacts,
    MacroParameters,
    StronglyConstrainedValuationEngine,
)


class TestStronglyConstrainedValuation(unittest.TestCase):
    def setUp(self):
        # 1. 样板企业 A: 现金充沛但尚未盈利的研发型导入期生物药企 (类似真实 RXRX)
        self.rxrx_facts = CompanyFinancialFacts(
            ticker="RXRX",
            currency="USD",
            current_price=4.36,
            shares=533.0,
            cash_and_equivalents=550.0,
            total_debt=45.0,
            total_assets=820.0,
            current_assets=600.0,
            total_liabilities=120.0,
            equity=700.0,
            goodwill_and_intangibles=120.0,
            revenue=48.0,
            operating_income=-180.0,
            net_income=-160.0,
            free_cash_flow=-140.0,
            operating_cash_flow=-110.0,
            beta=1.35,
        )

        # 2. 样板企业 B: 高现金流垄断型 AI 算力龙头 (类似真实 NVDA)
        self.nvda_facts = CompanyFinancialFacts(
            ticker="NVDA",
            currency="USD",
            current_price=132.40,
            shares=24600.0,
            cash_and_equivalents=34800.0,
            total_debt=11000.0,
            total_assets=85000.0,
            current_assets=58000.0,
            total_liabilities=24000.0,
            equity=61000.0,
            goodwill_and_intangibles=5200.0,
            revenue=96000.0,
            operating_income=60000.0,
            net_income=53000.0,
            free_cash_flow=45000.0,
            operating_cash_flow=51000.0,
            beta=1.65,
        )

    def test_hard_asset_floors_rxrx(self):
        """【UT-CONSTRAINED-01: 研发导入期生物药企资产硬底线三测算 (NCPS/NCAV/TBV)】

        1. 测试功能与测试点:
           - 验证 StronglyConstrainedValuationEngine.calculate_hard_asset_floors 资产清算防御底线。
           - 净现金每股底 (Net Cash Per Share, NCPS): (Cash & Equivalents - Total Debt) / Shares。
           - 格雷厄姆净流动资产价值 (Net Current Asset Value, NCAV): (Current Assets - Total Liabilities) / Shares。
           - 有形账面净值 (Tangible Book Value, TBV): (Equity - Goodwill & Intangibles) / Shares。
           - 最终硬底线 (Hard Asset Floor): max(NCPS, NCAV, TBV) 确保企业在任何悲观情景下具有清算价值支撑。

        2. 正常函数业务边界与参数契约:
           - shares > 0。
           - 资产、负债、商誉无形资产均为有限实数。
           - 资产底线恒为正数 (Hard Floor > 0.0)。

        3. 测试数据与模拟场景说明:
           - 标的: RXRX (AI 药物研发新星)，现金 550M，债务 45M (净现金 505M)；流动资产 600M，总负债 120M；净资产 700M，无形资产 120M；股本 533M 股。
           - 理论测算: NCPS = 505/533 = $0.95, NCAV = 480/533 = $0.90, TBV = 580/533 = $1.09。

        4. 预期断言与结果验证:
           - 断言 ncps 约等于 0.95。
           - 断言 ncav 约等于 0.90。
           - 断言 tbv 约等于 1.09。
           - 断言 floor > 0.50 且严格为正数。
        """
        ncps, ncav, tbv, floor = StronglyConstrainedValuationEngine.calculate_hard_asset_floors(self.rxrx_facts)
        # 净现金 = (550 - 45) / 533 = 505 / 533 = 0.95
        self.assertAlmostEqual(ncps, 0.95, places=1)
        # NCAV = (600 - 120) / 533 = 480 / 533 = 0.90
        self.assertAlmostEqual(ncav, 0.90, places=1)
        # TBV = (700 - 120) / 533 = 580 / 533 = 1.09
        self.assertAlmostEqual(tbv, 1.09, places=1)
        # Hard floor must be positive and non-zero
        self.assertGreater(floor, 0.50)

    def test_reverse_dcf_convergence(self):
        """【UT-CONSTRAINED-02: 反向DCF市场预期反解单调收敛性与二分数值稳定性】

        1. 测试功能与测试点:
           - 验证 solve_reverse_dcf 反向现金流折现求解器。
           - 核心思想: 给定当前二级市场价格与资本成本，反解出“市场现价隐含的企业前5年预期复合增长率 g”。
           - 验证数值求解二分法/牛顿法的单调收敛性，杜绝死循环、除零或发散崩溃。

        2. 正常函数业务边界与参数契约:
           - current_price > 0, cash_flow > 0, shares > 0, wacc > terminal_growth。
           - 隐含增速 g 属于合理经济区间 [-50%, +100%]。

        3. 测试数据与模拟场景说明:
           - 模拟基准企业: 基期现金流 1000 万，市价 $50，股本 100 万股 (市值 5000 万)，无净负债，WACC=10.0%, 永续增长率 2.5%。

        4. 预期断言与结果验证:
           - 断言反解得到的 g 不为 None。
           - 断言 g 落在 [-0.50, 1.00] 的稳定经济收敛区间内。
        """
        macro = MacroParameters()
        wacc = 0.10
        tg = 0.025
        # 已知基期现金流 1000，市价 $50，股本 100，净债务 0
        g = StronglyConstrainedValuationEngine.solve_reverse_dcf(
            current_price=50.0,
            cash_flow=1000.0,
            shares=100.0,
            net_debt=0.0,
            wacc=wacc,
            terminal_growth=tg,
            years=5,
        )
        self.assertIsNotNone(g)
        self.assertTrue(-0.5 <= g <= 1.0)

    def test_nvda_evaluation_and_corridor(self):
        """【UT-CONSTRAINED-03: 垄断成长巨头强约束估值走廊截断与四分之一凯利风控】

        1. 测试功能与测试点:
           - 验证 StronglyConstrainedValuationEngine.evaluate_valuation 对高成长垄断龙头的完整多情景评估。
           - 走廊截断机制: 行业 PE 走廊 (20x, 35x, 50x) 限制极端乐观估值溢价。
           - 单调性约束: 悲观公允价 <= 基准公允价 <= 乐观公允价。
           - 买方风控硬约束: 单标的四分之一凯利仓位配置比例上限严格受控在 <= 15.0%。

        2. 正常函数业务边界与参数契约:
           - 输入强类型 CompanyFinancialFacts，行业 PE 走廊三元组 (min_pe, mid_pe, max_pe)。
           - 输出 ValuationResult 包含三情景价格、隐含 PE 与风控仓位。

        3. 测试数据与模拟场景说明:
           - 标的: NVDA 真实财务底账 (现价 $132.40, 营收 960 亿, 自由现金流 450 亿, 现金 348 亿, 负债 110 亿)。

        4. 预期断言与结果验证:
           - 断言 hard_asset_floor > 0。
           - 断言 bear_fair_value <= base_fair_value <= bull_fair_value。
           - 断言 implied_base_pe <= 50.0。
           - 断言 quarter_kelly_allocation_pct <= 15.0%。
        """
        res = StronglyConstrainedValuationEngine.evaluate_valuation(
            self.nvda_facts,
            industry_pe_corridor=(20.0, 35.0, 50.0),
            lifecycle_stage="growth",
        )
        # 1. 资产底线必须计算成功
        self.assertGreater(res.hard_asset_floor, 0)
        # 2. 悲观价 <= 基准价 <= 乐观价
        self.assertLessEqual(res.bear_fair_value, res.base_fair_value)
        self.assertLessEqual(res.base_fair_value, res.bull_fair_value)
        # 3. 隐含 PE 必须落在合理区间
        if res.implied_base_pe:
            self.assertLessEqual(res.implied_base_pe, 50.0)
        # 4. 仓位必须受到 15% 绝对风控上限保护
        self.assertLessEqual(res.quarter_kelly_allocation_pct, 15.0)

    def test_rxrx_evaluation_with_negative_cf(self):
        """【UT-CONSTRAINED-04: 自由现金流持续失血企业估值降级与资产硬底线防御】

        1. 测试功能与测试点:
           - 验证当高科技企业处于研发导入期、自由现金流为负 (FCF < 0) 时，强约束引擎的降级与防御能力。
           - 严禁引擎因现金流为负抛出除零或产生荒谬负股价；
           - 悲观情景价格刚性锚定在资产清算底线之上 (Bear Fair Value >= Hard Asset Floor)；
           - 给出有效的安全边际买入击球区 (Margin of Safety Buy Zone > 0)。

        2. 正常函数业务边界与参数契约:
           - lifecycle_stage="intro"。
           - free_cash_flow < 0。

        3. 测试数据与模拟场景说明:
           - 标的: RXRX 自由现金流 -1.4 亿美元，营业利润 -1.8 亿美元。

        4. 预期断言与结果验证:
           - 断言 base_fair_value 非空且合理。
           - 断言 bear_fair_value >= hard_asset_floor。
           - 断言 margin_of_safety_buy_zone > 0。
           - 断言 quarter_kelly_allocation_pct <= 15.0%。
        """
        res = StronglyConstrainedValuationEngine.evaluate_valuation(
            self.rxrx_facts,
            lifecycle_stage="intro",
        )
        # 即使自由现金流为负，引擎绝不崩溃
        self.assertIsNotNone(res.base_fair_value)
        # 悲观价格绝不能低于资产底线 Hard Floor
        self.assertGreaterEqual(res.bear_fair_value, res.hard_asset_floor)
        # 安全边际买点必须合理有效
        self.assertGreater(res.margin_of_safety_buy_zone, 0)
        self.assertLessEqual(res.quarter_kelly_allocation_pct, 15.0)

    def test_overvalued_company_gives_zero_allocation(self):
        """【UT-CONSTRAINED-05: 泡沫与高危标的强制零仓位风控阻断与回避评级】

        1. 测试功能与测试点:
           - 验证对于资不抵债、估值极度透支的泡沫标的，风控引擎的强制归零阻断能力。
           - 凯利公式配置仓位强制置为 0.0% (quarter_kelly_allocation_pct == 0.0)。
           - 投资结论 (investment_verdict) 明确发出“回避”预警。

        2. 正常函数业务边界与参数契约:
           - 现价远高于公允价值 (现价 $500，微薄净利 100 万)。

        3. 测试数据与模拟场景说明:
           - 模拟严重泡沫标的 BUBBLE: 市值 500 亿，总负债 550 亿，净利润仅 100 万，自由现金流仅 50 万。

        4. 预期断言与结果验证:
           - 断言 quarter_kelly_allocation_pct 精确等于 0.0。
           - 断言 investment_verdict 包含“回避”。
        """
        bubble_company = CompanyFinancialFacts(
            ticker="BUBBLE",
            currency="USD",
            current_price=500.0, # 极高价格
            shares=100.0,
            cash_and_equivalents=10.0,
            total_debt=500.0,
            total_assets=600.0,
            current_assets=100.0,
            total_liabilities=550.0,
            equity=50.0,
            goodwill_and_intangibles=40.0,
            revenue=50.0,
            operating_income=2.0,
            net_income=1.0,
            free_cash_flow=0.5,
            operating_cash_flow=1.0,
        )
        res = StronglyConstrainedValuationEngine.evaluate_valuation(bubble_company)
        self.assertEqual(res.quarter_kelly_allocation_pct, 0.0)
        self.assertIn("回避", res.investment_verdict)

    def test_quote_freshness_verification(self):
        """【UT-CONSTRAINED-06: 估值引擎行情新鲜度硬门禁核验与超期失真物理阻断】

        1. 测试功能与测试点:
           - 验证 verify_quote_freshness 行情新鲜度门禁。
           - 当行情处于 24 小时以内时判定为“当日最新行情”；
           - 当行情时间戳严重超期 (>24小时) 时判定为“严重超期阻断”并返回 False；
           - 在主估值流程 evaluate_valuation 中，若传入超期历史行情，必须抛出 ValueError 阻断。

        2. 正常函数业务边界与参数契约:
           - quote_timestamp 与 current_time_iso 为 ISO 8601 格式时间戳。
           - max_staleness_hours 默认 24.0。

        3. 测试数据与模拟场景说明:
           - 场景 A: 1 小时前新鲜行情 (合法通过)。
           - 场景 B: 48 小时前陈旧行情 (门禁拦截)。
           - 场景 C: 4 天前陈旧行情传入 evaluate_valuation (物理抛出 ValueError)。

        4. 预期断言与结果验证:
           - 场景 A 断言 ok 为 True，msg 包含“当日最新行情”。
           - 场景 B 断言 ok_stale 为 False，msg 包含“严重超期阻断”。
           - 场景 C 断言抛出 ValueError 且信息包含“行情时效硬约束阻断”。
        """
        # 当日新鲜行情 (1小时前)
        ok, msg = StronglyConstrainedValuationEngine.verify_quote_freshness(
            quote_timestamp="2026-10-14T06:00:00Z",
            current_time_iso="2026-10-14T07:00:00Z",
            max_staleness_hours=24.0,
        )
        self.assertTrue(ok)
        self.assertIn("当日最新行情", msg)

        # 严重超期历史行情 (48小时前，必须阻断并报警)
        ok_stale, msg_stale = StronglyConstrainedValuationEngine.verify_quote_freshness(
            quote_timestamp="2026-10-12T06:00:00Z",
            current_time_iso="2026-10-14T07:00:00Z",
            max_staleness_hours=24.0,
        )
        self.assertFalse(ok_stale)
        self.assertIn("严重超期阻断", msg_stale)

        # 在 evaluate_valuation 运行时传入超期行情必须强制抛出 ValueError 阻断
        from dataclasses import replace
        stale_facts = replace(self.rxrx_facts, quote_timestamp="2026-10-10T00:00:00Z")
        with self.assertRaises(ValueError) as ctx:
            StronglyConstrainedValuationEngine.evaluate_valuation(stale_facts)
        self.assertIn("行情时效硬约束阻断", str(ctx.exception))



if __name__ == "__main__":
    unittest.main()

