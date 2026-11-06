"""市场自适应参数与量化因果推导网络全景单元测试.

测试范围:
1. 自适应参数注册中心 (MarketAdaptiveParamsRegistry) 默认回退与 JSON 底账加载;
2. 黄金央行去美元化储备溢价参数解耦与无缝兼容;
3. 危机流动性踩踏相关性幂律加压参数解耦与单调性;
4. 微观增加值动态经营杠杆 (DOL) 与分配法恒等式刚性闭环平账 (SNA Identity Closure);
5. 量化因果推导网络五大商业维度事实生成与自然语言汇报规范验证;
6. 系统全流程管道端到端决策卡片生成集成回归.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.market_adaptive_params import (
    MarketAdaptiveParamsRegistry,
    GoldValuationAdaptiveParams,
    MacroShockAdaptiveParams,
    FirmValueAddedAdaptiveParams,
)
from financial_core.engines.cross_asset_engine import CrossAssetValuationEngine
from financial_core.engines.macro_shock_transmission_engine import (
    MacroShockTransmissionEngine,
    MacroShockInput,
)
from financial_core.engines.firm_value_added_bridge_engine import (
    FirmValueAddedBridgeEngine,
    FirmFinancialFact,
)
from financial_core.engines.causal_inference_engine import (
    QuantitativeCausalInferenceEngine,
    CausalInferenceResult,
)
from financial_core.pipeline.systemic_analysis_pipeline import (
    SystemicAnalysisPipeline,
    SystemicCompanyInput,
)


class TestMarketAdaptiveAndCausalNetwork(unittest.TestCase):
    """测试自适应参数体系与因果推导引擎."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.config_path = self.root / "config" / "market_adaptive_params.json"

    def test_01_adaptive_registry_load_and_fallback(self):
        """【UT-ADAPT-01: 市场自适应参数注册中心(MarketAdaptiveParamsRegistry)默认回退与JSON底账加载】

        1. 测试功能与测试点:
           - 验证 MarketAdaptiveParamsRegistry 内存默认基准配置（央行黄金基准 500 吨，踩踏幂律 1.2，默认经营杠杆 1.05）。
           - 验证从 config/market_adaptive_params.json 配置文件装配参数。
           - 验证非存在路径时的优雅降级与防御性回退。

        2. 正常函数业务边界与参数契约:
           - get_default() 返回 MarketAdaptiveParamsRegistry 强类型单例。
           - load_from_json(path) 返回合法注册对象，即使路径不存在也不抛出破坏性未捕获异常。

        3. 测试数据与模拟场景说明:
           - 真实配置文件 config/market_adaptive_params.json 与故意传入的伪造非存在路径 non_existent.json。

        4. 预期断言与结果验证:
           - default_reg 参数与配置文件参数精准对齐。
           - fallback_reg 成功回退至默认参数。
        """
        default_reg = MarketAdaptiveParamsRegistry.get_default()
        self.assertEqual(default_reg.gold_params.baseline_cb_tonnes, 500.0)
        self.assertEqual(default_reg.macro_shock_params.stampede_power_exponent, 1.2)
        self.assertEqual(default_reg.firm_bridge_params.default_operating_leverage_dol, 1.05)

        # 从 JSON 文件加载
        self.assertTrue(self.config_path.is_file(), "config/market_adaptive_params.json 必须存在")
        loaded_reg = MarketAdaptiveParamsRegistry.load_from_json(self.config_path)
        self.assertAlmostEqual(loaded_reg.gold_params.baseline_cb_tonnes, 500.0)
        self.assertAlmostEqual(loaded_reg.macro_shock_params.stampede_power_exponent, 1.2)
        self.assertTrue(loaded_reg.firm_bridge_params.enforce_accounting_identity_closure)

        # 测试不存在路径时的优雅回退
        fallback_reg = MarketAdaptiveParamsRegistry.load_from_json(self.root / "config" / "non_existent.json")
        self.assertIsNotNone(fallback_reg)
        self.assertEqual(fallback_reg.gold_params.baseline_cb_tonnes, 500.0)

    def test_02_gold_valuation_parameter_decoupling(self):
        """【FT-ADAPT-02: 黄金宏观公允估值中央行购金储备溢价参数解耦与灵敏度对账】

        1. 测试功能与测试点:
           - 验证 CrossAssetValuationEngine.compute_gold_macro_valuation 宏观实物黄金公允估值。
           - 验证去美元化央行储备购金溢价 (central_bank_premium) 计算逻辑。
           - 验证参数解耦与参数敏感性：当将常态基准从 500 吨上调至 1000 吨时，超额购金溢价与公允价单调下降。

        2. 正常函数业务边界与参数契约:
           - 现货金价为正，购金吨数为正，自适应参数支持无缝传入。

        3. 测试数据与模拟场景说明:
           - 黄金现货 2650 美元/盎司，全球央行年度购金 1050 吨。

        4. 预期断言与结果验证:
           - res_default 公允价值 > 2000 美元，央行溢价百分比 > 0。
           - res_custom 的溢价美元数与公允估值均严格小于 res_default。
        """
        # 默认参数评估
        res_default = CrossAssetValuationEngine.compute_gold_macro_valuation(
            spot_gold_usd=2650.0,
            annual_cb_tonnes=1050.0,
        )
        self.assertGreater(res_default.macro_fair_value_usd, 2000.0)
        self.assertGreater(res_default.central_bank_premium_pct, 0.0)

        # 自定义参数：如果上调常态购金基准至 1000 吨，超额购金仅剩 50 吨，溢价应当显著下降
        custom_params = GoldValuationAdaptiveParams(baseline_cb_tonnes=1000.0)
        res_custom = CrossAssetValuationEngine.compute_gold_macro_valuation(
            spot_gold_usd=2650.0,
            annual_cb_tonnes=1050.0,
            adaptive_params=custom_params,
        )
        self.assertLess(res_custom.central_bank_premium_usd, res_default.central_bank_premium_usd)
        self.assertLess(res_custom.macro_fair_value_usd, res_default.macro_fair_value_usd)

    def test_03_macro_shock_transmission_decoupling(self):
        """【IT-ADAPT-03: 跨市场宏观冲击传导中踩踏幂律与信用利差参数解耦与单调性验证】

        1. 测试功能与测试点:
           - 验证 MacroShockTransmissionEngine 计算跨资产恐慌流动性挤兑与折现率 (WACC) 走阔。
           - 验证踩踏幂律指数 (stampede_power_exponent) 对资产相关性收敛速度的非线性调节。
           - 验证宏观 WACC 走阔基点 (bps) 大于 0，冲击后 WACC 高于基准 WACC。

        2. 正常函数业务边界与参数契约:
           - 利率在 (0, 1) 之间，VIX 波动率为正，公司 Beta 与杠杆为正。

        3. 测试数据与模拟场景说明:
           - 美债 10 年期 4.6%，美日汇率 150，VIX 28.0，流动性抽水 600 亿美元。

        4. 预期断言与结果验证:
           - 凸性参数下相关性收敛程度受限。
           - macro_wacc_spread_bps > 0。
           - shocked_wacc_pct > base_wacc_pct。
        """
        base_input = MacroShockInput(
            us_10y_yield=0.046,
            usdjpy_rate=150.0,
            vix_index=28.0,
            usdjpy_daily_change_pct=-0.02,
            fed_liquidity_drain_billion=60.0,
            company_beta=1.3,
            company_debt_to_equity=1.5,
            base_wacc=0.085,
        )

        engine = MacroShockTransmissionEngine()
        res_default = engine.evaluate_macro_shock(base_input)

        # 提高踩踏幂律指数至 2.0 (凸性加剧，在同样中等恐慌下相关性收敛较慢)
        convex_params = MacroShockAdaptiveParams(stampede_power_exponent=2.0)
        res_convex = engine.evaluate_macro_shock(base_input, adaptive_params=convex_params)

        self.assertLessEqual(
            res_convex["converged_market_correlation"],
            res_default["converged_market_correlation"],
        )
        self.assertGreater(res_default["macro_wacc_spread_bps"], 0.0)
        self.assertGreater(res_default["shocked_wacc_pct"], res_default["base_wacc_pct"])

    def test_04_firm_value_added_dynamic_dol_and_accounting_closure(self):
        """【UT-ADAPT-04: 微观企业增加值动态经营杠杆(DOL)与国民核算(SNA)分配法恒等式闭环平账】

        1. 测试功能与测试点:
           - 验证 FirmValueAddedBridgeEngine 估算重资产制造企业动态经营杠杆 (DOL)。
           - 验证宏观行业增加值冲击映射到微观财务报表时的传导闭环。
           - 验证国民账户分配法恒等式平账检验 (SNA Distribution Identity Closure: $Value Added = Wages + Taxes + Gross Operating Surplus$)。
           - 验证经营杠杆放大效应（行业下挫 10%，EBITDA 下跌幅度严格大于 15%）。

        2. 正常函数业务边界与参数契约:
           - FirmFinancialFact 包含企业三表底稿关键要素。
           - map_sector_shock_to_firm 强制保障平账误差 <= 0.01 百万美元。

        3. 测试数据与模拟场景说明:
           - 营收 10 亿、销货成本 6 亿、折旧固定成本高企的制造企业。

        4. 预期断言与结果验证:
           - dol > 1.5。
           - is_distribution_identity_held 为 True。
           - identity_discrepancy_million <= 0.01。
           - simulated_ebitda_million < firm.ebitda_million * 0.85。
        """
        bridge = FirmValueAddedBridgeEngine()

        # 1. 动态经营杠杆测试
        firm_heavy_fixed = FirmFinancialFact(
            ticker="MFR",
            company_name="Heavy Manufacturing Inc.",
            market="US",
            sector_id="SEMI_HARDWARE",
            revenue_million=1000.0,
            cogs_million=600.0,
            operating_expenses_million=250.0,
            ebitda_million=150.0,
            wages_and_salaries_million=180.0,
            taxes_paid_million=70.0,
            capex_million=50.0,
            annual_fcf_million=90.0,
            market_cap_billion=2.5,
        )
        dol = bridge.estimate_dynamic_dol(firm_heavy_fixed)
        self.assertGreater(dol, 1.5)

        # 2. 映射行业冲击与分配法闭环平账
        shock_res = bridge.map_sector_shock_to_firm(
            firm=firm_heavy_fixed,
            sector_va_growth_pct=-10.0,  # 行业增加值下挫 10.0%
        )

        self.assertTrue(shock_res["is_distribution_identity_held"])
        self.assertLessEqual(shock_res["identity_discrepancy_million"], 0.01)
        self.assertAlmostEqual(shock_res["operating_leverage_dol"], dol, places=2)
        # 经营杠杆 > 1 导致 EBITDA 下挫幅度大于总收入下挫幅度 (-10%)
        self.assertLess(shock_res["simulated_ebitda_million"], firm_heavy_fixed.ebitda_million * 0.85)

    def test_05_quantitative_causal_inference_liquor_scenario(self):
        """【FT-ADAPT-05: 白酒/大消费行业特异性量化因果推导(批零倒挂/合同负债干涸/库存滞销)】

        1. 测试功能与测试点:
           - 验证白酒/消费品行业特异性量化因果事实生成。
           - 批零价格严重倒挂（出厂价 1169 vs 批发价 950）。
           - 经销商蓄水池干涸（合同负债环比流出 -22.5%）。
           - 法证库存滞销周转天数异常。
           - 强制断言输出必须为通俗买方自然语言，严禁暴露 LaTeX/Markdown 数学公式符号 (如 \\frac, $$)。

        2. 正常函数业务边界与参数契约:
           - infer_catalysts_and_risks 接收多源金融法证输入。
           - key_risks 列表为自然中文说明。

        3. 测试数据与模拟场景说明:
           - 模拟典型白酒标的 600519 渠道价格恶化场景。

        4. 预期断言与结果验证:
           - risk_text 包含“批零倒挂”、“合同负债”、“库存滞销”。
           - risk_text 绝对不包含 "\\frac" 和 "$$"。
        """
        engine = QuantitativeCausalInferenceEngine()

        res = engine.infer_catalysts_and_risks(
            company_info={
                "ticker": "600519",
                "sector": "LiquorConsumer",
                "factory_quote": 1169.0,
                "real_wholesale_quote": 950.0,  # 倒挂 18.7%
                "contract_liabilities_drain_pct": -22.5,  # 蓄水池流出
                "current_dio_days": 180.0,
            },
            forensic_result={"inventory_verdict": "异常积压滞销", "red_flags": []},
            macro_shock_result={"shocked_wacc_pct": 8.5, "valuation_haircut_pct": 12.0},
            valuation_result={"hard_runway_months": 999.0, "hard_runway_desc": "持续净流入"},
            microstructure_result={"squeeze_score": 15.0},
        )

        # 验证是否精准捕获倒挂与蓄水池干涸事实
        risk_text = " ".join(res.key_risks)
        self.assertIn("批零倒挂", risk_text)
        self.assertIn("合同负债", risk_text)
        self.assertIn("库存滞销", risk_text)

        # 验证是否为通俗商业语言，严禁生硬数学符号
        self.assertNotIn("\\frac", risk_text)
        self.assertNotIn("$$", risk_text)

    def test_06_quantitative_causal_inference_tech_growth_scenario(self):
        """【FT-ADAPT-06: 高科技/生物医药成长股量化因果推导(前沿领跑/空头逼仓/现金跑道告急)】

        1. 测试功能与测试点:
           - 验证高科技/生物医药未盈利成长股量化因果推导。
           - 催化剂捕获：做空筹码极端拥挤逼仓 (Squeeze)、贴近全球技术创新前沿、强定价权抵御成本通胀。
           - 核心风险捕获：非受限现金跌破债务契约最低保留线、硬现金跑道仅剩 8.5 个月告急。

        2. 正常函数业务边界与参数契约:
           - 综合微观结构、宏观微观微基结构、法证与估值输入。

        3. 测试数据与模拟场景说明:
           - RXRX 借券成本 12%，现金跑道 8.5 个月，微观加价率 1.25。

        4. 预期断言与结果验证:
           - 催化剂文本包含“空头筹码高度拥挤逼仓”、“紧贴全球创新技术前沿”、“定价权护城河抗成本通胀”。
           - 风险文本包含“现金跑道告急与股权稀释红线”。
        """
        engine = QuantitativeCausalInferenceEngine()

        res = engine.infer_catalysts_and_risks(
            company_info={
                "ticker": "RXRX",
                "sector": "Biotech",
                "cost_to_borrow_pct": 12.0,
                "debt_covenant_min_cash": 80.0,
            },
            forensic_result={
                "unrestricted_cash": 70.0,  # 破最低保留线
                "inventory_verdict": "良性周转",
                "red_flags": ["研发全部费用化"],
            },
            macro_shock_result={"shocked_wacc_pct": 11.2, "valuation_haircut_pct": 24.0},
            valuation_result={"hard_runway_months": 8.5, "hard_runway_desc": "8.5 个月"},
            microstructure_result={"squeeze_score": 68.0},
            micro_founded_macro_result={
                "pricing_power_tier": "强定价权",
                "micro_markup_ratio": 1.25,
                "distance_to_technology_frontier": 0.09,
            },
        )

        cat_text = " ".join(res.primary_catalysts)
        risk_text = " ".join(res.key_risks)

        # 验证催化事实
        self.assertIn("空头筹码高度拥挤逼仓", cat_text)
        self.assertIn("紧贴全球创新技术前沿", cat_text)
        self.assertIn("定价权护城河抗成本通胀", cat_text)

        # 验证风险事实
        self.assertIn("现金跑道告急与股权稀释红线", risk_text)

    def test_07_pipeline_decision_card_integration(self):
        """【IT-ADAPT-07: 系统全流程管道端到端决策卡片生成集成回归与因果事实清单挂载】

        1. 测试功能与测试点:
           - 验证 SystemicAnalysisPipeline 端到端完整管线执行。
           - 输入企业真实财报三表、行情时效、折旧资本开支与股权激励底账。
           - 验证管线状态返回 'SUCCESS'。
           - 验证最终产物挂载 final_institutional_decision_card，内含催化剂清单与主要风险清单。

        2. 正常函数业务边界与参数契约:
           - SystemicCompanyInput 必须通过 Assets = Liabilities + Equity 刚性平账自检。
           - run_systemic_analysis 输出包含完整研报与决策卡片字典。

        3. 测试数据与模拟场景说明:
           - 资产 800M = 负债 300M + 权益 500M 刚性平账样本。

        4. 预期断言与结果验证:
           - pipeline_status == "SUCCESS"。
           - primary_catalysts 与 key_risks 均为列表且长度 > 0。
        """
        pipeline = SystemicAnalysisPipeline()
        sample_input = SystemicCompanyInput(
            ticker="TEST_TICKER",
            company_name="Test Enterprise Corp.",
            sector="General",
            quote_timestamp="2026-10-17 10:00:00 EDT",
            market_session="regular_trading",
            current_price=50.0,
            baseline_reference_price=55.0,
            reported_cash=200.0,
            restricted_cash=20.0,
            debt_covenant_min_cash=50.0,
            total_debt=100.0,
            total_assets=800.0,
            total_liabilities=300.0,
            stockholders_equity=500.0,
            reported_operating_cash_flow=80.0,
            reported_capex=30.0,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=10.0,
            reported_revenue=600.0,
            reported_operating_income=90.0,
            reported_net_income=70.0,
            shares_outstanding=20.0,
        )

        output = pipeline.run_systemic_analysis(sample_input)
        self.assertEqual(output["pipeline_status"], "SUCCESS")

        card = output["final_institutional_decision_card"]
        self.assertIn("primary_catalysts", card)
        self.assertIn("key_risks", card)
        self.assertIsInstance(card["primary_catalysts"], list)
        self.assertIsInstance(card["key_risks"], list)
        self.assertGreater(len(card["primary_catalysts"]), 0)
        self.assertGreater(len(card["key_risks"]), 0)

    def test_08_causal_inference_narrative_and_to_dict_contract(self):
        """【UT-CAUSAL-08: 量化因果推导买方全息研报卡片与去工程符号化字典契约断言】

        1. 测试功能与测试点:
           - 验证 CausalInferenceResult 完整输出通俗买方自然语言 narrative_zh 全息卡片；
           - 验证 CausalInferenceResult.to_dict() 字典序列化契约的完整性；
           - 验证当借券成本为 0 或未提供时，不出现机械的'借券成本 0.0%'描述；
           - 验证当单一客户集中度比例为 0 但标记集中度风险时，不出现'超 0.0% 营收'的语病；
           - 验证研报卡片彻底消除工程代号、代码符号及 LaTeX/Markdown 公式。

        2. 正常函数业务边界与参数契约:
           - infer_catalysts_and_risks 接收标的基本面与微观法证数据，输出强类型 CausalInferenceResult 实体。

        3. 测试数据与模拟场景说明:
           - 标的: NVDA (半导体巨头)，做空评分 60.0，借券成本未提供 (0.0)，客户集中度风险置位但 share 为 0。

        4. 预期断言与结果验证:
           - narrative_zh 包含'量化因果推导与情景触发全息研报'；
           - narrative_zh 包含'因果推断置信度'、'主导催化与乐观靶心路径'、'核心催化清单'；
           - 研报中绝对不包含'借券成本 0.0%'与'超 0.0% 营收'；
           - to_dict() 导出的字典包含 narrative_zh 与全部清单，且与实体属性完全自洽。
        """
        engine = QuantitativeCausalInferenceEngine()

        res = engine.infer_catalysts_and_risks(
            company_info={
                "ticker": "NVDA",
                "sector": "Semiconductor",
                "current_price": 140.0,
                "cost_to_borrow_pct": 0.0, # 未提供或为0
                "top_customer_risk_flag": True,
                "top_customer_share": 0.0, # 未提供具体份额
            },
            forensic_result={"inventory_verdict": "良性周转", "red_flags": []},
            macro_shock_result={"shocked_wacc_pct": 8.8, "valuation_haircut_pct": 10.0},
            valuation_result={"hard_runway_months": 999.0, "hard_runway_desc": "持续净流入"},
            microstructure_result={"squeeze_score": 62.0},
        )

        self.assertIsInstance(res, CausalInferenceResult)
        # 1. 验证研报卡片格式
        self.assertIn("NVDA 量化因果推导与情景触发全息研报", res.narrative_zh)
        self.assertIn("因果推断置信度", res.narrative_zh)
        self.assertIn("主导催化与乐观靶心路径", res.narrative_zh)
        self.assertIn("底线防御与悲观底价破位风险", res.narrative_zh)

        # 2. 验证语病消除: 不出现 '借券成本 0.0%' 与 '超 0.0% 营收'
        all_text = res.narrative_zh + " " + " ".join(res.primary_catalysts) + " " + " ".join(res.key_risks)
        self.assertNotIn("借券成本 0.0%", all_text)
        self.assertNotIn("超 0.0% 营收", all_text)

        # 3. 验证 to_dict() 契约
        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)
        self.assertIn("primary_catalysts", d)
        self.assertIn("key_risks", d)
        self.assertIn("top_optimistic_trigger", d)
        self.assertIn("top_pessimistic_trigger", d)
        self.assertIn("causal_confidence_score", d)


if __name__ == "__main__":
    unittest.main()
