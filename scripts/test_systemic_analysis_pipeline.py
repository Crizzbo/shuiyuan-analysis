"""系统性投研分析主管道集成测试套件 (Systemic Pipeline Integration Tests).

验证端到端六道工序系统级串联:
时效门禁 -> 法证手术刀 -> 宏观加压 -> 估值跑道 -> 筹码期权 -> 买方决策卡片合成
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finance_tools.systemic_analysis_pipeline import (
    SystemicCompanyInput,
    SystemicAnalysisPipeline,
)


class TestSystemicAnalysisPipeline(unittest.TestCase):
    """测试系统性投研主管道端到端闭环."""

    def setUp(self):
        self.pipeline = SystemicAnalysisPipeline()

    def test_full_systemic_pipeline_run_rxrx_case(self):
        """【IT-SYSTEMIC-01: 高研发Biotech全景系统性投研六道工序端到端集成解剖】

        1. 测试功能与测试点:
           - 验证 SystemicAnalysisPipeline 针对高研发 Biotech 标的 (如 RXRX) 的端到端系统性六道工序串联解剖:
             1. Stage 1 时效门禁: 校验时区感知与盘中交易状态；
             2. Stage 2 法证手术刀: 剔除受限资金，扣减借款协议刚性最低现金，刺破股权激励失真；
             3. Stage 3 宏观加压: 联立 10Y 美债收益率、日元套息与流动性收缩实施 WACC 动态加压；
             4. Stage 4 动态硬现金跑道测算: 结合净流出速度精准推演硬跑道月数与定增稀释风险；
             5. Stage 5 筹码挤压与美式期权: 测算做空比率、借券成本、逼空阻力与期权时间损耗；
             6. Stage 6 买方决策卡合成: 生成三态估值走廊与价格落差归因。

        2. 正常函数业务边界与参数契约:
           - SystemicCompanyInput 强类型契约，平账约束（Assets == Liabilities + Equity）。
           - 受限资金与银行底线现金必须 <= 账面现金。
           - 跑道月数 > 0，挤压得分在 [0, 100] 之间。

        3. 测试数据与模拟场景说明:
           - 标的: Recursion Pharmaceuticals (RXRX)。
           - 现价 $3.82，前期基准价 $5.20 (落差 -$1.38)。
           - 账面现金 3.85 亿，附注揭示 3500 万受限不可用，银行协议要求保留 5000 万，总负债 4500 万。
           - 资产 7.2 亿 = 负债 2.1 亿 + 权益 5.1 亿 (严格平账)。
           - 年化经营现金流 -2.8 亿，资本开支 3500 万，月均烧钱 2625 万。
           - 空头持仓 5200 万股 (占比 24.8%)，借券成本高达 28.5%，行权价 $4.00 美式看涨期权。

        4. 预期断言与结果验证:
           - Stage 1 断言 is_fresh_quote 为 True，market_session 为 'regular_trading'。
           - Stage 2 断言 unrestricted_cash == 350M，covenant_buffer == 300M。
           - Stage 3 断言 shocked_wacc_pct > 9.0%。
           - Stage 4 断言 hard_runway_months < 14.0 (跌破 12~14 个月临界线，提示定增预警)。
           - Stage 5 断言 squeeze_score > 60.0，包含 '行权价 4.0' 与 '每日时间损耗'。
           - Stage 6 断言 card['ticker'] == 'RXRX'，悲观触发包含 '跑道'，乐观靶心大于现价，包含落差归因。
        """
        inp = SystemicCompanyInput(
            ticker="RXRX",
            company_name="Recursion Pharmaceuticals, Inc.",
            sector="Biotech",
            quote_timestamp="2026-10-14 15:50:00 EDT",
            market_session="regular_trading",
            current_price=3.82,
            baseline_reference_price=5.20, # 前期基准价 5.20，现价 3.82，落差 -$1.38
            reported_cash=385_000_000,
            restricted_cash=35_000_000,   # 附注中 3500 万受限不可用
            debt_covenant_min_cash=50_000_000, # 银行借款协议要求至少保留 5000 万
            total_debt=45_000_000,
            total_assets=720_000_000,
            total_liabilities=210_000_000,
            stockholders_equity=510_000_000, # 平账: 720M = 210M + 510M
            reported_operating_cash_flow=-280_000_000,
            reported_capex=35_000_000,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=65_000_000, # 高达 6500 万发股票发工资
            reported_revenue=55_000_000,
            reported_operating_income=-310_000_000,
            reported_net_income=-295_000_000,
            shares_outstanding=245_000_000,
            raw_materials=0.0,
            work_in_process=0.0,
            finished_goods=0.0,
            prior_finished_goods=0.0,
            revenue_growth_pct=0.10,
            total_rd_spent=240_000_000,
            capitalized_rd_amount=0.0,
            top_customer_share=0.25,
            top_customer_risk_flag=False,
            pipeline_rnpv_value=586_000_000, # 3条临床二期管线 rNPV 估值
            us_10y_yield=0.045,
            usdjpy_rate=150.0,
            vix_index=22.0,
            usdjpy_daily_change_pct=-0.015, # 日元轻微升值
            fed_liquidity_drain_billion=60.0,
            company_beta=1.5,
            factory_quote=0.0,
            real_wholesale_quote=0.0,
            contract_liabilities_drain_pct=0.0,
            short_interest_shares=52_000_000,
            free_float_shares=210_000_000,
            cost_to_borrow_pct=28.5,
            average_volume_30d=5_500_000,
            option_target_strike=4.0, # 用户关注的行权价 4 美元 Call
            option_expiry_days=30,
            option_implied_vol=1.15,
            is_call_option=True,
        )

        report = self.pipeline.run_systemic_analysis(inp)

        # 1. 验证 Stage 1: 时效门禁通过
        self.assertTrue(report["stage_1_gatekeepers"]["is_fresh_quote"])
        self.assertEqual(report["stage_1_gatekeepers"]["market_session"], "regular_trading")

        # 2. 验证 Stage 2: 手术刀剥离受限资金
        # 可动用现金 = 385M - 35M = 350M
        self.assertEqual(report["stage_2_forensic_scalpel"]["unrestricted_cash"], 350_000_000.0)
        # 契约安全垫 = 350M - 50M = 300M
        self.assertEqual(report["stage_2_forensic_scalpel"]["covenant_buffer"], 300_000_000.0)

        # 3. 验证 Stage 3: 宏观 WACC 动态加压
        self.assertGreater(report["stage_3_macro_stress"]["shocked_wacc_pct"], 9.0)

        # 4. 验证 Stage 4: 动态硬现金跑道测算
        # 真实净现金 = 350M - 45M = 305M, 月均烧钱 = (280M + 35M)/12 = 26.25M
        # 跑道 = 305 / 26.25 = 11.6 个月 (跌破 12 个月大关，触发定增稀释预警!)
        self.assertLess(report["stage_4_valuation"]["hard_runway_months"], 14.0)

        # 5. 验证 Stage 5: 筹码挤压与美式期权
        self.assertGreater(report["stage_5_microstructure_and_options"]["squeeze_score"], 60.0)
        self.assertIn("行权价 4.0", report["stage_5_microstructure_and_options"]["options_verdict"])
        self.assertIn("每日时间损耗", report["stage_5_microstructure_and_options"]["options_verdict"])

        # 6. 验证 Stage 6: 顶层买方决策卡片生成
        card = report["final_institutional_decision_card"]
        self.assertEqual(card["ticker"], "RXRX")
        self.assertIn("跑道", card["pessimistic_trigger"])
        self.assertGreater(card["optimistic_target_price"], card["current_price"])
        self.assertIn("落差", card["price_gap_attribution_summary"])


if __name__ == "__main__":
    unittest.main()
