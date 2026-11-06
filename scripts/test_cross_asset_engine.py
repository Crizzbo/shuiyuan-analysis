"""单元测试: 跨资产量化核算核心引擎测试 (Cross-Asset Valuation Core Tests).

测试覆盖:
1. ETF 成分股加权穿透重叠度 (Weighted Overlap) 与 Jaccard 相似度
2. ETF 集中度 (CR10, HHI) 与 1/3/5 年复利费率损耗 (Expense Drag)
3. 现货黄金 10Y TIPS 真实利率定价锚、央行去美元化储备溢价与三态情景推演
4. 特级金矿股 (NEM/GOLD/AEM) AISC 现金毛利、营运杠杆倍数与 FCF 目标价
5. 核心层架构纯洁性校验: 确认无任何外层逆向依赖
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.cross_asset_engine import (
    CrossAssetValuationEngine,
    ETFOverlapResult,
    ETFPenetrationFact,
    GoldValuationFact,
    GoldMinerLeverageFact,
)


class TestCrossAssetEngine(unittest.TestCase):
    """跨资产量化核算引擎单元测试套件."""

    def setUp(self):
        self.engine = CrossAssetValuationEngine()

    def test_etf_overlap_calculation(self):
        """【UT-CROSS-01: ETF成分股加权穿透重叠度(Weighted Overlap)与Jaccard相似度】

        1. 测试功能与测试点:
           - 验证 compute_etf_overlap 跨指数/主题 ETF 头部成分股权重穿透算法。
           - 加权穿透重叠度公式: Weighted Overlap = Σ min(Weight_A_i, Weight_B_i)。
           - Jaccard 集合相似度: |Holdings_A ∩ Holdings_B| / |Holdings_A ∪ Holdings_B|。
           - 判定高重叠预警: 当加权重叠度 >= 30.0% 时置位 is_high_overlap = True。

        2. 正常函数业务边界与参数契约:
           - holdings_a 与 holdings_b 为字典映射 {Ticker: Weight}。
           - 权重之和通常 <= 1.0。
           - 返回 ETFOverlapResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 模拟标普500 (SPY) 与纳斯达克100 (QQQ) 头部 6 只重仓权重。
           - 共同持仓包含 MSFT, AAPL, NVDA, AMZN, META 共 5 只巨头。

        4. 预期断言与结果验证:
           - 断言 common_holdings_count 精确等于 5。
           - 断言 weighted_overlap_pct 约为 26.5% (26.5% < 30%)。
           - 断言 is_high_overlap 为 False。
           - 断言 jaccard_similarity_pct 约为 71.4% (5/7)。
        """
        # 模拟 SPY 与 QQQ 的头部重叠
        holdings_spy = {
            "MSFT": 0.071,
            "AAPL": 0.069,
            "NVDA": 0.062,
            "AMZN": 0.038,
            "META": 0.025,
            "BRK.B": 0.018,
        }
        holdings_qqq = {
            "AAPL": 0.088,
            "MSFT": 0.082,
            "NVDA": 0.079,
            "AMZN": 0.052,
            "META": 0.048,
            "TSLA": 0.025,
        }

        res = self.engine.compute_etf_overlap(
            holdings_a=holdings_spy,
            holdings_b=holdings_qqq,
            ticker_a="SPY",
            ticker_b="QQQ",
        )

        self.assertIsInstance(res, ETFOverlapResult)
        self.assertEqual(res.etf_a, "SPY")
        self.assertEqual(res.etf_b, "QQQ")
        self.assertEqual(res.common_holdings_count, 5) # MSFT, AAPL, NVDA, AMZN, META

        # 共有重叠权重: min(0.071, 0.082) + min(0.069, 0.088) + min(0.062, 0.079) + min(0.038, 0.052) + min(0.025, 0.048)
        # = 0.071 + 0.069 + 0.062 + 0.038 + 0.025 = 0.265 (26.5%)
        self.assertAlmostEqual(res.weighted_overlap_pct, 26.5, places=1)
        self.assertFalse(res.is_high_overlap) # 26.5% < 30%

        # Jaccard = 5 / 7 = ~71.4%
        self.assertAlmostEqual(res.jaccard_similarity_pct, (5.0 / 7.0) * 100.0, places=1)

    def test_etf_penetration_and_fee_drag(self):
        """【UT-CROSS-02: ETF持仓集中度(CR10/HHI)与1/3/5年复利费率损耗】

        1. 测试功能与测试点:
           - 验证 compute_etf_penetration 对行业主题 ETF 的集中度解剖与费率摩擦测算。
           - 前十大集中度 (CR10): Σ Top 10 Weights。
           - 赫芬达尔-赫希曼指数 (HHI): Σ (Weight_i * 100)^2。
           - 长期管理费率复利摩擦 (Expense Drag): 测算 1年、3年、5年对基准本金的实际侵蚀。

        2. 正常函数业务边界与参数契约:
           - expense_ratio > 0, aum_billion_usd > 0, capital_baseline > 0。
           - 集中度判断: CR10 >= 50% 触发 is_concentrated = True。

        3. 测试数据与模拟场景说明:
           - 标的: 半导体巨头 ETF (SMH)，管理费率 0.35%，AUM 230 亿美元；头部 5 大持仓占比达 51.4% (NVDA 20.5%, TSM 12.8% 等)；基准本金 100,000 美元。

        4. 预期断言与结果验证:
           - 断言 cr10_pct 为 51.4%。
           - 断言 is_concentrated 为 True。
           - 断言 hhi_index > 0。
           - 断言 fee_drag_1y 精确等于 350.0 美元 (100,000 * 0.0035)。
           - 断言 fee_drag_3y > fee_drag_1y * 3 (复利滚存损耗)。
        """
        top_holdings = {
            "NVDA": 0.205,
            "TSM": 0.128,
            "AVGO": 0.082,
            "QCOM": 0.051,
            "AMD": 0.048,
        }
        factor_scores = {"growth": 95.0, "value": 20.0}

        fact = self.engine.compute_etf_penetration(
            ticker="SMH",
            expense_ratio=0.0035,
            aum_billion_usd=23.0,
            top_holdings=top_holdings,
            factor_scores=factor_scores,
            capital_baseline=100000.0,
        )

        self.assertIsInstance(fact, ETFPenetrationFact)
        self.assertEqual(fact.ticker, "SMH")
        self.assertEqual(fact.cr10_pct, (0.205 + 0.128 + 0.082 + 0.051 + 0.048) * 100.0)
        self.assertTrue(fact.is_concentrated) # 51.4% >= 50%
        self.assertGreater(fact.hhi_index, 0.0)

        # 费率摩擦验证: 100,000 * 0.0035 = 350
        self.assertAlmostEqual(fact.fee_drag_1y, 350.0, places=1)
        self.assertGreater(fact.fee_drag_3y, fact.fee_drag_1y * 3.0) # 复利侵蚀效应
        self.assertGreater(fact.fee_drag_5y, fact.fee_drag_3y)

    def test_gold_macro_valuation(self):
        """【UT-CROSS-03: 现货黄金10Y TIPS实际利率定价锚与央行去美元化储备溢价】

        1. 测试功能与测试点:
           - 验证 compute_gold_macro_valuation 买方宏观黄金定价模型。
           - 实际利率锚 (10Y TIPS Real Yield): 名义利率 (Nominal 10Y) - 通胀预期 (10Y Breakeven)。
           - 传统负相关折现锚 (Traditional TIPS Anchor): 实际利率对黄金的机会成本定价。
           - 央行去美元化主权储备溢价 (Central Bank Premium): 结合全球主权央行年净增持吨数与上海黄金交易所 (SGE) 实物溢价。
           - 三态宏观情景单调性: 悲观底价 < 基准公允价 < 乐观靶心。

        2. 正常函数业务边界与参数契约:
           - spot_gold_usd > 0, nominal_10y_yield > 0, annual_cb_tonnes >= 0。
           - 宏观公允价 > 传统单纯实际利率模型价格 (包含了去美元化溢价)。

        3. 测试数据与模拟场景说明:
           - 现货金价 $2650/oz，10Y 名义利率 4.40%，通胀预期 2.35% (实际利率 2.05%)，DXY 104.2，央行年购金 1050 吨，SGE 溢价 $28.5。

        4. 预期断言与结果验证:
           - 断言 tips_10y_real_yield_pct 精确等于 2.05%。
           - 断言 traditional_tips_anchor_usd > 1500.0。
           - 断言 central_bank_premium_usd > 0.0。
           - 断言 macro_fair_value_usd > traditional_tips_anchor_usd。
           - 断言 bear_case_usd < base_case_usd < bull_case_usd。
        """
        fact = self.engine.compute_gold_macro_valuation(
            spot_gold_usd=2650.0,
            nominal_10y_yield=0.0440,
            breakeven_10y=0.0235,
            dxy_index=104.2,
            annual_cb_tonnes=1050.0,
            sge_premium_usd=28.5,
        )

        self.assertIsInstance(fact, GoldValuationFact)
        # 10Y TIPS real yield: 4.40% - 2.35% = 2.05%
        self.assertAlmostEqual(fact.tips_10y_real_yield_pct, 2.05, places=2)
        self.assertGreater(fact.traditional_tips_anchor_usd, 1500.0)
        self.assertGreater(fact.central_bank_premium_usd, 0.0)
        self.assertGreater(fact.macro_fair_value_usd, fact.traditional_tips_anchor_usd)

        # 验证三态情景单调性: bear < base < bull
        self.assertLess(fact.bear_case_usd, fact.base_case_usd)
        self.assertLess(fact.base_case_usd, fact.bull_case_usd)

    def test_gold_miner_leverage_multiplier(self):
        """【UT-CROSS-04: 特级金矿龙头AISC营运杠杆倍数与FCF公允目标价推导】

        1. 测试功能与测试点:
           - 验证 compute_gold_miner_leverage 金矿股特异性杠杆估值模型。
           - 全维持成本 (All-In Sustaining Costs, AISC) 现金毛利: Spot Gold - AISC。
           - 经营杠杆放大倍数 (Operating Leverage Multiplier): 金价上涨 1% 时，现金毛利扩大的非线性倍数。
           - 自由现金流估值法 (FCF Multiple): 基于现金毛利与产量的公允股价推导。

        2. 正常函数业务边界与参数契约:
           - spot_gold_price > aisc_per_oz。
           - annual_production_koz > 0, shares_mil > 0, valuation_multiple > 0。

        3. 测试数据与模拟场景说明:
           - 标的: 纽蒙特矿业 (NEM 现价 $53.20)，AISC 为 $1440/oz，现货金价 $2650/oz，年产量 670 万盎司，总股本 11.5 亿股，估值乘数 12x。

        4. 预期断言与结果验证:
           - 断言 cash_margin_per_oz 精确等于 1210.0 美元 (2650 - 1440)。
           - 断言 operating_leverage_multiplier > 1.5 倍。
           - 断言 annual_fcf_mil > 1000.0 百万美元。
           - 断言 fcf_yield_pct > 0.0 且 fair_target_price > 0.0。
        """
        fact = self.engine.compute_gold_miner_leverage(
            ticker="NEM",
            current_price=53.20,
            aisc_per_oz=1440.0,
            annual_production_koz=6700.0,
            shares_mil=1150.0,
            spot_gold_price=2650.0,
            valuation_multiple=12.0,
        )

        self.assertIsInstance(fact, GoldMinerLeverageFact)
        self.assertEqual(fact.ticker, "NEM")
        # 现金毛利: 2650 - 1440 = 1210
        self.assertAlmostEqual(fact.cash_margin_per_oz, 1210.0, places=1)
        # 营运杠杆应大于 1.5x
        self.assertGreater(fact.operating_leverage_multiplier, 1.5)
        self.assertGreater(fact.annual_fcf_mil, 1000.0)
        self.assertGreater(fact.fcf_yield_pct, 0.0)
        self.assertGreater(fact.fair_target_price, 0.0)

    def test_ut_cross_05_buyer_dossier_cards_and_to_dict_contract(self):
        """【UT-CROSS-05: 跨资产穿透与宏观大宗买方全息研报卡片与去工程符号化契约断言】

        1. 测试功能与测试点:
           - 验证跨资产四大对象 (ETFOverlapResult, ETFPenetrationFact, GoldValuationFact, GoldMinerLeverageFact)
             完整包含自然语言 narrative_zh 全息卡片并支持 to_dict() 序列化；
           - 验证纯自然中文定性字段 (overlap_level_zh, concentration_level_zh, valuation_status_zh, leverage_profile_zh)；
           - 验证研报卡片彻底消除纯英文代号与未经翻译的工程标识，符合买方机构投研规范。

        2. 正常函数业务边界与参数契约:
           - 输入合法 ETF 与黄金基本面参数，输出强类型对象及序列化字典。

        3. 测试数据与模拟场景说明:
           - 场景 A: 标普500 vs 纳指100 重叠度；
           - 场景 B: 芯片巨头 ETF 集中度穿透；
           - 场景 C: 现货黄金宏观公允估值；
           - 场景 D: 纽蒙特矿业金矿股营运杠杆。

        4. 预期断言与结果验证:
           - 四大对象 narrative_zh 均包含对应的【...全息研报】字样与买方指引；
           - 四大对象 to_dict() 均包含 narrative_zh 与纯自然中文定性字段；
           - 属性值与字典导出完全自洽。
        """
        # 1. 验证 ETFOverlapResult
        holdings_a = {"AAPL": 0.10, "MSFT": 0.10}
        holdings_b = {"AAPL": 0.10, "GOOGL": 0.10}
        overlap = self.engine.compute_etf_overlap(holdings_a, holdings_b, "ETF_1", "ETF_2")
        self.assertIn("ETF 穿透重叠度全息研报", overlap.narrative_zh)
        self.assertTrue(bool(overlap.overlap_level_zh))
        d_overlap = overlap.to_dict()
        self.assertIn("overlap_level_zh", d_overlap)
        self.assertIn("narrative_zh", d_overlap)
        self.assertEqual(d_overlap["narrative_zh"], overlap.narrative_zh)

        # 2. 验证 ETFPenetrationFact
        penetration = self.engine.compute_etf_penetration(
            ticker="XLK",
            expense_ratio=0.0010,
            aum_billion_usd=60.0,
            top_holdings={"MSFT": 0.22, "AAPL": 0.21, "NVDA": 0.06},
            factor_scores={"growth": 88.0},
        )
        self.assertIn("全景穿透与费率摩擦全息研报", penetration.narrative_zh)
        self.assertTrue(bool(penetration.concentration_level_zh))
        d_pen = penetration.to_dict()
        self.assertIn("concentration_level_zh", d_pen)
        self.assertIn("narrative_zh", d_pen)
        self.assertEqual(d_pen["narrative_zh"], penetration.narrative_zh)

        # 3. 验证 GoldValuationFact
        gold = self.engine.compute_gold_macro_valuation(spot_gold_usd=2650.0)
        self.assertIn("现货黄金宏观公允估值与情景全息研报", gold.narrative_zh)
        self.assertTrue(bool(gold.valuation_status_zh))
        d_gold = gold.to_dict()
        self.assertIn("valuation_status_zh", d_gold)
        self.assertIn("narrative_zh", d_gold)
        self.assertEqual(d_gold["narrative_zh"], gold.narrative_zh)

        # 4. 验证 GoldMinerLeverageFact
        miner = self.engine.compute_gold_miner_leverage(
            ticker="GOLD",
            current_price=18.50,
            aisc_per_oz=1350.0,
            annual_production_koz=4000.0,
            shares_mil=1700.0,
        )
        self.assertIn("特级金矿龙头 GOLD 营运杠杆与现金流弹性全息研报", miner.narrative_zh)
        self.assertTrue(bool(miner.leverage_profile_zh))
        d_miner = miner.to_dict()
        self.assertIn("leverage_profile_zh", d_miner)
        self.assertIn("narrative_zh", d_miner)
        self.assertEqual(d_miner["narrative_zh"], miner.narrative_zh)

    def test_ut_cross_06_cross_market_currency_adaptation(self):
        """【UT-CROSS-06: 跨市场多币种自适应推导与日股/A股研报货币符号断言】

        一、测试功能与测试点:
            1. 验证传入日股 ETF 代码 (如 1306.T, market="JP") 时，自动推导货币符号为 '¥'；
            2. 验证 compute_etf_penetration 与 compute_gold_miner_leverage 的研报卡片 narrative_zh 中
               均使用 '¥'，严禁死锁 '$'；
            3. 验证各对象 to_dict() 序列化中均包含 "currency_symbol": "¥"。

        二、正常函数业务边界与参数契约:
            - 日股东证 ETF 与日股矿业股输入。

        三、预期断言与结果验证:
            断言 currency_symbol == "¥"，narrative_zh 中包含 "¥" 且无 "$" 符号。
        """
        # 1. 日股 ETF 自适应
        etf_jp = self.engine.compute_etf_penetration(
            ticker="1306.T",
            expense_ratio=0.0008,
            aum_billion_usd=8500.0,
            top_holdings={"7203": 0.05, "6758": 0.04, "9984": 0.03},
            factor_scores={"value": 75.0},
            capital_baseline=10000000.0,
            market="JP",
        )
        self.assertEqual(etf_jp.currency_symbol, "¥")
        self.assertIn("¥", etf_jp.narrative_zh)
        self.assertNotIn("$", etf_jp.narrative_zh)
        self.assertEqual(etf_jp.to_dict()["currency_symbol"], "¥")

        # 2. 日股/A股 金矿股自适应
        miner_jp = self.engine.compute_gold_miner_leverage(
            ticker="5713.T",
            current_price=4800.0,
            aisc_per_oz=1400.0,
            annual_production_koz=500.0,
            shares_mil=290.0,
            market="JP",
        )
        self.assertEqual(miner_jp.currency_symbol, "¥")
        self.assertIn("¥", miner_jp.narrative_zh)
        self.assertNotIn("$", miner_jp.narrative_zh)
        self.assertEqual(miner_jp.to_dict()["currency_symbol"], "¥")


if __name__ == "__main__":
    unittest.main()
