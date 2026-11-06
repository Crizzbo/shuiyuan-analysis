# -*- coding: utf-8 -*-
"""全量买方机构级核心引擎测试套件 (Test Institutional Engines Suite)

测试对象：
1. ConsensusSurpriseEngine (一致预期差与透支惩罚)
2. MicrostructureFlowEngine (微观筹码与空头挤压)
3. CatalystCalendarEngine (催化剂日历与二元定价)
4. PeerBenchmarkEngine (同业横向对标与相对估值)
5. UnitEconomicsEngine (rNPV 管线折现与 P×Q 量价拆解)
6. IntegratedThreeStatementEngine (动态三表闭环与跑道模拟)
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools import (
    ConsensusDataInput,
    ConsensusSurpriseEngine,
    MicrostructureInput,
    MicrostructureFlowEngine,
    CorporateEvent,
    CatalystCalendarEngine,
    CompanyPeerMetrics,
    PeerBenchmarkEngine,
    PipelineAsset,
    UnitEconomicsEngine,
    BaselineFinancials,
    IntegratedThreeStatementEngine,
)


class TestInstitutionalEngines(unittest.TestCase):
    """买方机构级核心六大引擎测试类。"""

    def test_consensus_surprise_double_beat(self):
        """【UT-INST-01: 一致预期差双超(Double Beat)与分析师净上修动量(Revision Momentum)断言】

        1. 测试功能与测试点:
           - 验证 ConsensusSurpriseEngine 评估财报预期差。
           - 实际 EPS 与营收同时超越市场一致预期（英伟达 NVDA 典型案例：EPS +8.0%，营收 +7.94%）。
           - 验证归类为 "Double Beat"。
           - 验证 30 天内分析师净上修动量计算 (8 上调 vs 1 下调 -> 0.70)。
           - 验证无透支惩罚，折价乘数等于 1.0。

        2. 正常函数业务边界与参数契约:
           - ConsensusDataInput 包含基准一致预期与实际披露值。
           - evaluate(inp) 输出 ConsensusSurpriseResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - NVDA Q3 财报公布场景。

        4. 预期断言与结果验证:
           - beat_category 包含 "Double Beat"。
           - eps_surprise_pct == 8.0，revenue_surprise_pct == 7.94。
           - revision_momentum == 0.70，overhang_penalty_factor == 1.0。
        """
        inp = ConsensusDataInput(
            ticker="NVDA",
            fiscal_period="Q3 2024",
            consensus_eps=0.75,
            consensus_revenue=32500.0,
            reported_eps=0.81,  # +8.0%
            reported_revenue=35082.0,  # +7.9%
            analysts_upgrades_30d=8,
            analysts_downgrades_30d=1,
            total_covering_analysts=10,
        )
        res = ConsensusSurpriseEngine.evaluate(inp)
        self.assertIn("Double Beat", res.beat_category)
        self.assertAlmostEqual(res.eps_surprise_pct, 8.0, places=1)
        self.assertAlmostEqual(res.revenue_surprise_pct, 7.94, places=1)
        self.assertEqual(res.revision_momentum, 0.70)
        self.assertEqual(res.overhang_penalty_factor, 1.0)

    def test_consensus_overhang_penalty(self):
        """【UT-INST-02: 业绩暴雷(Double Miss)叠加过高隐含增速透支的阻尼折价惩罚断言】

        1. 测试功能与测试点:
           - 验证预期差引擎在极端高预期落空时的风控惩罚机制。
           - 股价过度计入 45% 高增速，但实际业绩双不及预期 (Double Miss)。
           - 多数分析师集中下调评级。
           - 严格断言估值阻尼折价因子 (overhang_penalty_factor) 受到压制 (<= 0.75)。

        2. 正常函数业务边界与参数契约:
           - 任何业绩暴雷与预期严重透支场景下，乘数严禁为 1.0。

        3. 测试数据与模拟场景说明:
           - 模拟伪造高估值暴雷标的 OVERVALUED。

        4. 预期断言与结果验证:
           - beat_category 包含 "Double Miss"。
           - overhang_penalty_factor <= 0.75。
        """
        inp = ConsensusDataInput(
            ticker="OVERVALUED",
            fiscal_period="Q3 2024",
            consensus_eps=1.00,
            consensus_revenue=1000.0,
            reported_eps=0.90,  # 暴雷
            reported_revenue=950.0,  # 暴雷
            analysts_upgrades_30d=1,
            analysts_downgrades_30d=5,
            total_covering_analysts=10,
            market_implied_growth=0.45,  # 隐含 45% 增速，过度透支
        )
        res = ConsensusSurpriseEngine.evaluate(inp)
        self.assertIn("Double Miss", res.beat_category)
        self.assertLessEqual(res.overhang_penalty_factor, 0.75)

    def test_microstructure_short_squeeze_scoring(self):
        """【UT-INST-03: 微观筹码分布/空头借券成本(CTB)/利用率与极端轧空(Short Squeeze)评分核验】

        1. 测试功能与测试点:
           - 验证 MicrostructureFlowEngine 识别微观结构极端拥挤与轧空潜力。
           - 模拟 Recursion (RXRX) 极端筹码结构：流通空头比例 > 30%、回补天数 (DTC) 达 10 天、融券年化成本 35%、利用率 92%。
           - 内部人高管 90 天净自购无减持。
           - 严格断言轧空评级进入 "Extreme" 极危区间，评分 > 75 分。

        2. 正常函数业务边界与参数契约:
           - MicrostructureInput 接收微观借券与筹码数据。
           - 返回 MicrostructureResult 结果。

        3. 测试数据与模拟场景说明:
           - RXRX 典型买方微观盘口参数。

        4. 预期断言与结果验证:
           - short_percent_of_float > 30.0。
           - days_to_cover == 10.0。
           - squeeze_score > 75.0。
           - squeeze_risk_level 包含 "Extreme"。
        """
        inp = MicrostructureInput(
            ticker="RXRX",
            current_price=3.835,
            float_shares=260.0,
            short_interest_shares=80.0,  # 80 / 260 = 30.77%
            average_daily_volume_30d=8.0,  # DTC = 10 天
            cost_to_borrow_pct=35.0,  # 35% 借券年化利率
            borrow_utilization_pct=92.0,  # 92% 利用率
            insider_buy_shares_90d=0.20,
            insider_sell_shares_90d=0.0,
            top10_inst_net_flow_shares=4.5,
        )
        res = MicrostructureFlowEngine.evaluate(inp)
        self.assertGreater(res.short_percent_of_float, 30.0)
        self.assertAlmostEqual(res.days_to_cover, 10.0, places=1)
        self.assertGreater(res.squeeze_score, 75.0)
        self.assertIn("Extreme", res.squeeze_risk_level)
        self.assertIn("自购增持", res.insider_flow_status)

    def test_catalyst_calendar_binary_pricing(self):
        """【FT-INST-04: 二元临床读出/催化剂日历数学期望与期权隐含波动率波动套利断言】

        1. 测试功能与测试点:
           - 验证 CatalystCalendarEngine 对二元催化剂事件的数学期望测算。
           - 模拟关键临床 Phase 2 数据读出：成功概率 60%，上行空间 +75%，下行风险 -45%。
           - 预期涨跌幅 = 0.60 * 75% + 0.40 * (-45%) = +27.0%。
           - 期权市场仅定价 22% 隐含波动，识别出明显的“波动率低估”买方套利机会。

        2. 正常函数业务边界与参数契约:
           - CorporateEvent 定义二元胜率与赔率空间。
           - evaluate_event 严格按概率期望与赔率比对。

        3. 测试数据与模拟场景说明:
           - REC-994 二期海绵状血管瘤读出事件。

        4. 预期断言与结果验证:
           - days_until_event == 32。
           - binary_expected_move_pct == 27.0。
           - odds_ratio == 75.0 / 45.0。
           - verdict 包含 "低估"。
        """
        evt = CorporateEvent(
            event_id="REC994_PHASE2",
            target_date="2026-11-15",
            category="clinical_readout",
            title_zh="REC-994 CCM Phase 2 关键疗效数据读出",
            description_zh="海绵状血管瘤病灶体积缩小显著性检验",
            upside_potential_pct=75.0,
            downside_risk_pct=-45.0,
            probability_of_success=0.60,
            options_implied_move_pct=22.0,  # 期权仅定价 22% 波动
        )
        res = CatalystCalendarEngine.evaluate_event(evt, as_of_date="2026-10-14")
        self.assertEqual(res.days_until_event, 32)
        # 期望 = 0.60 * 75 + 0.40 * (-45) = 45 - 18 = +27.0%
        self.assertAlmostEqual(res.binary_expected_move_pct, 27.0, places=1)
        self.assertAlmostEqual(res.odds_ratio, 75.0 / 45.0, places=2)
        self.assertIn("低估", res.volatility_arbitrage_verdict)

    def test_peer_benchmark_matrix(self):
        """【IT-INST-05: 同业横向对标矩阵(Peer Matrix)/增长与估值倍数折价错杀识别验证】

        1. 测试功能与测试点:
           - 验证 PeerBenchmarkEngine 在同赛道可比标的池中计算中位数与相对折溢价。
           - 目标公司 RXRX（EV/Sales 12.5x，营收同比增速 38%）。
           - 行业可比同业 SDGR (18.0x), RLAY (15.0x), TEM (22.0x)，中位数 18.0x。
           - 相对同业中位数折价 > 20%，但增速领先 > 10%，触发“错杀”相对价值研判。

        2. 正常函数业务边界与参数契约:
           - evaluate(target, peers) 接收标的及同业列表。
           - 返回 PeerBenchmarkResult 包含中位数与相对优势。

        3. 测试数据与模拟场景说明:
           - AI 药物研发 4 家上市公司同业对标。

        4. 预期断言与结果验证:
           - peer_count == 3。
           - median_ev_sales == 18.0。
           - ev_sales_premium_to_median_pct < -20.0。
           - verdict 包含 "错杀"。
        """
        target = CompanyPeerMetrics(
            ticker="RXRX",
            company_name="Recursion",
            ev_to_sales=12.5,
            pe_ratio=None,
            pb_ratio=1.65,
            fcf_yield_pct=-15.0,
            revenue_growth_yoy=38.0,  # 增长强劲
            gross_margin_pct=65.0,
        )
        peers = [
            CompanyPeerMetrics(
                ticker="SDGR",
                company_name="Schrodinger",
                ev_to_sales=18.0,
                pe_ratio=None,
                pb_ratio=2.8,
                fcf_yield_pct=-8.0,
                revenue_growth_yoy=15.0,
                gross_margin_pct=72.0,
            ),
            CompanyPeerMetrics(
                ticker="RLAY",
                company_name="Relay",
                ev_to_sales=15.0,
                pe_ratio=None,
                pb_ratio=1.9,
                fcf_yield_pct=-22.0,
                revenue_growth_yoy=12.0,
                gross_margin_pct=55.0,
            ),
            CompanyPeerMetrics(
                ticker="TEM",
                company_name="Tempus AI",
                ev_to_sales=22.0,
                pe_ratio=None,
                pb_ratio=4.5,
                fcf_yield_pct=-5.0,
                revenue_growth_yoy=25.0,
                gross_margin_pct=60.0,
            ),
        ]
        res = PeerBenchmarkEngine.evaluate(target, peers)
        self.assertEqual(res.peer_count, 3)
        self.assertEqual(res.median_ev_sales, 18.0)
        # RXRX 12.5 vs 18.0 中位数折价
        self.assertLess(res.ev_sales_premium_to_median_pct, -20.0)
        self.assertGreater(res.relative_growth_advantage_pct, 10.0)
        self.assertIn("错杀", res.relative_value_verdict)

    def test_unit_economics_biotech_rnpv(self):
        """【FT-INST-06: 创新药多管线逐条概率折现(rNPV)与单股公允价值估值模型核验】

        1. 测试功能与测试点:
           - 验证 UnitEconomicsEngine 计算创新药企多资产管线 rNPV 概率加权公允价值。
           - 穿透两项核心资产（REC-994 与 REC-2282）各自的 POS 临床成功率、峰值销售、分成比例与折现期。
           - 叠加净现金 (Net Cash) 与平台基础底座价值，推导单股公允价值。

        2. 正常函数业务边界与参数契约:
           - calculate_biotech_rnpv(ticker, shares, net_cash, wacc, pipelines, platform_base_value)。
           - 返回 rNPV 汇总结果及资产细分项。

        3. 测试数据与模拟场景说明:
           - 股数 535M，净现金 515M，WACC 9.5%，管线资产 2 项。

        4. 预期断言与结果验证:
           - total_pipeline_rnpv > 0。
           - rnpv_fair_value_per_share > 2.0。
           - len(asset_breakdowns) == 2。
        """
        pipes = [
            PipelineAsset(
                asset_name="REC-994",
                phase="Phase 2",
                pos=0.30,
                peak_annual_sales=800.0,
                royalty_take_rate=0.20,
                years_to_peak=5,
            ),
            PipelineAsset(
                asset_name="REC-2282",
                phase="Phase 2",
                pos=0.25,
                peak_annual_sales=600.0,
                royalty_take_rate=0.18,
                years_to_peak=6,
            ),
        ]
        res = UnitEconomicsEngine.calculate_biotech_rnpv(
            ticker="RXRX",
            shares=535.0,
            net_cash=515.0,
            wacc=0.095,
            pipelines=pipes,
            platform_base_value=300.0,
        )
        self.assertGreater(res.total_pipeline_rnpv, 0.0)
        self.assertGreater(res.rnpv_fair_value_per_share, 2.0)
        self.assertEqual(len(res.asset_breakdowns), 2)

    def test_integrated_three_statement_simulation(self):
        """【IT-INST-07: 动态三表勾稽联动与生物医药硬现金跑道(Hard Runway)情景模拟断言】

        1. 测试功能与测试点:
           - 验证 IntegratedThreeStatementEngine 模拟三表联动演化与营运资本占用 (DSO/DIO/DPO)。
           - 模拟创新药企在持续研发投入 (R&D) 与有限营收下的现金衰减速度。
           - 精确测算安全现金跑道月数 (runway_months)。
           - 评估潜在次级增发稀释风险等级 (dilution_risk_level)。

        2. 正常函数业务边界与参数契约:
           - simulate(base, revenue_growths, opex_escalation_pct) 输出多期财务预测与跑道研判。

        3. 测试数据与模拟场景说明:
           - 初始现金 550M，研发 220M，销售管理 80M，模拟 3 年。

        4. 预期断言与结果验证:
           - projections 预测期数为 3。
           - runway_months > 18.0（位于合理区间 20-28 个月）。
           - dilution_risk_level 包含 "跑道"。
        """
        base = BaselineFinancials(
            ticker="RXRX",
            cash_and_equivalents=550.0,
            total_debt=35.0,
            revenue=50.0,
            gross_margin_pct=70.0,
            opex_rnd=220.0,
            opex_sga=80.0,
            depr_amort=25.0,
            capex=20.0,
            dso_days=40.0,
            dio_days=25.0,
            dpo_days=35.0,
        )
        res = IntegratedThreeStatementEngine.simulate(
            base,
            revenue_growths=[0.30, 0.25, 0.20],
            opex_escalation_pct=3.0,
        )
        self.assertEqual(len(res.projections), 3)
        # 初始现金 550M，年烧钱约 250M，跑道应约为 20-28 个月
        self.assertGreater(res.runway_months, 18.0)
        self.assertIn("跑道", res.dilution_risk_level)

    def test_ut_inst_08_whisper_number_qualitative_gap_and_dual_negative_fix(self):
        """【UT-INST-08: 买方暗盘耳语预期差(Whisper Number)定性与双重负号语病根除断言】

        一、测试功能与测试点:
            1. 验证 ConsensusSurpriseEngine 补齐买方暗盘预期差 (Whisper Number Gap) 的商业定性:
               当披露实际业绩超越卖方公开一致预期、但击穿买方暗盘心理预期时，
               明确触发“买方暗盘耳语预期跑输/见光死抛压警报”。
            2. 验证业绩暴雷场景下彻底消除“跑输一致预期 15.0% (-15.0%)”等双重负号机械重复语病，
               采用自然通畅的“跑输一致预期 15.0 个百分点”。

        二、正常函数业务边界与参数契约:
            - whisper_eps > consensus_eps > reported_eps
            - 正常输出 assessment_zh 包含暗盘定性研判。

        三、测试数据与模拟场景说明:
            - 卖方公开预期 $1.00，买方暗盘预期 $1.20；实际披露 $1.05。
            - 表面 Beat 卖方 +5.0%，但击穿暗盘 Whisper 预期 -12.5%。

        四、预期断言与结果验证:
            - 断言 assessment_zh 包含 "买方暗盘耳语预期跑输"。
            - 断言 assessment_zh 杜绝 "(-" 或 "% (+" 等符号拼贴机械重复。
        """
        inp_whisper = ConsensusDataInput(
            ticker="WHISPER_MISS",
            fiscal_period="Q3 2024",
            consensus_eps=1.00,
            consensus_revenue=1000.0,
            reported_eps=1.05,  # 胜过卖方 1.00
            reported_revenue=1050.0,
            whisper_eps=1.20,   # 但低于暗盘 1.20 (跑输 12.5%)
        )
        res_w = ConsensusSurpriseEngine.evaluate(inp_whisper)
        self.assertIn("买方暗盘耳语预期跑输", res_w.assessment_zh)
        self.assertNotIn("(-", res_w.assessment_zh)

        # 验证双暴雷场景文字消除机械双重负号
        inp_miss = ConsensusDataInput(
            ticker="MISS_CLEAN",
            fiscal_period="Q3 2024",
            consensus_eps=1.00,
            consensus_revenue=1000.0,
            reported_eps=0.85,  # 跑输 15%
            reported_revenue=920.0,  # 跑输 8%
        )
        res_m = ConsensusSurpriseEngine.evaluate(inp_miss)
        self.assertIn("跑输一致预期 15.0 个百分点", res_m.assessment_zh)
        self.assertNotIn("(-15.0%)", res_m.assessment_zh)

    def test_ut_inst_09_consensus_extreme_small_eps_bounded_and_narrative_zh(self):
        """【UT-INST-09: 微小基数EPS离群值夹逼保护与买方全息研报卡片断言】

        一、测试功能与测试点:
            1. 验证微小 EPS 基数下的超预期百分比离群值防御:
               当卖方预期 EPS 极小 (如 $0.005) 时，实际微差 $0.03 不会导致超预期百分比无边界暴增，
               刚性夹逼在 [-500.0%, +500.0%] 物理合理区间内。
            2. 验证 ConsensusSurpriseResult 输出去工程符号化的全息研报卡片 narrative_zh。

        二、正常函数业务边界与参数契约:
            - consensus_eps 近似为零 (0.005)
            - 结果 narrative_zh 字段非空。

        三、测试数据与模拟场景说明:
            微利转型企业场景。

        四、预期断言与结果验证:
            - 断言 eps_surprise_pct 绝对值不超过 500.0%。
            - 断言 narrative_zh 包含 "财报预期差全息研报" 与自然中文定性。
        """
        inp_small = ConsensusDataInput(
            ticker="TINY_EPS",
            fiscal_period="Q2 2024",
            consensus_eps=0.005,
            consensus_revenue=100.0,
            reported_eps=0.05,  # 差 0.045
            reported_revenue=110.0,
        )
        res = ConsensusSurpriseEngine.evaluate(inp_small)
        self.assertLessEqual(res.eps_surprise_pct, 500.0)
        self.assertGreaterEqual(res.eps_surprise_pct, -500.0)
        self.assertIn("财报预期差全息研报", res.narrative_zh)
        self.assertIn("华尔街情绪动向", res.narrative_zh)

    def test_ut_inst_10_microstructure_dtc_bounded_and_negative_inputs_defense(self):
        """【UT-INST-10: 做空持仓非负清洗与回补天数(DTC)离群值封顶防御断言】

        一、测试功能与测试点:
            验证 MicrostructureFlowEngine 金融数学边界防御:
            1. 传入异常负数做空持仓 (short_interest_shares < 0) 时自动清洗为 0.0，杜绝负做空比例;
            2. 极端微小日均成交量下，回补天数 (DTC) 刚性封顶至 100 天，防止除以接近 0 算出数万天溢出离群值。

        二、正常函数业务边界与参数契约:
            - short_interest_shares: -5.0
            - average_daily_volume_30d: 0.0001
            - float_shares: 50.0

        三、测试数据与模拟场景说明:
            极度缺乏流动性的僵尸标的与脏数据输入。

        四、预期断言与结果验证:
            - short_percent_of_float >= 0.0。
            - days_to_cover <= 100.0。
            - squeeze_score 稳定计算于 [0, 100] 区间内。
        """
        inp_neg = MicrostructureInput(
            ticker="NEG_TEST",
            current_price=10.0,
            float_shares=50.0,
            short_interest_shares=-5.0,  # 异常负数
            average_daily_volume_30d=0.00001,  # 极小成交量
            cost_to_borrow_pct=5.0,
        )
        res = MicrostructureFlowEngine.evaluate(inp_neg)
        self.assertEqual(res.short_percent_of_float, 0.0)
        self.assertLessEqual(res.days_to_cover, 100.0)
        self.assertGreaterEqual(res.squeeze_score, 0.0)

    def test_ut_inst_11_microstructure_narrative_zh_deengineered_and_ssot(self):
        """【UT-INST-11: 微观筹码全息研报卡片去工程符号化与门面SSOT断言】

        一、测试功能与测试点:
            1. 验证 MicrostructureFlowEngine.evaluate 输出自然流畅的买方通俗全息研报卡片 (narrative_zh);
            2. 杜绝暴露 "short_percent_of_float"、"days_to_cover" 等纯代码变量名;
            3. 验证 finance_tools 门面与 financial_core 核心层 SSOT 完全等价。

        二、正常函数业务边界与参数契约:
            - 正常筹码输入参数。

        三、测试数据与模拟场景说明:
            测试标准高做空博弈标的。

        四、预期断言与结果验证:
            - narrative_zh 包含 "微观筹码与博弈流动性全息研报"。
            - narrative_zh 包含 "轧空得分"。
            - narrative_zh 严禁包含英文代码代号。
        """
        inp = MicrostructureInput(
            ticker="MEME_STOCK",
            current_price=25.0,
            float_shares=100.0,
            short_interest_shares=35.0,
            average_daily_volume_30d=4.0,  # DTC = 8.75 天
            cost_to_borrow_pct=40.0,
            borrow_utilization_pct=88.0,
        )
        res_facade = MicrostructureFlowEngine.evaluate(inp)
        narrative = res_facade.narrative_zh
        self.assertIn("微观筹码与博弈流动性全息研报", narrative)
        self.assertIn("轧空得分", narrative)
        self.assertNotIn("short_percent_of_float", narrative)
        self.assertNotIn("days_to_cover", narrative)

        from financial_core.engines.microstructure_flow_engine import MicrostructureFlowEngine as CoreFlowEngine
        res_core = CoreFlowEngine.evaluate(inp)
        self.assertEqual(res_core.squeeze_score, res_facade.squeeze_score)
        self.assertEqual(res_core.narrative_zh, res_facade.narrative_zh)

    def test_ut_inst_12_catalyst_negative_expectation_midterm_risk_warning(self):
        """【UT-INST-12: 催化剂中期负期望高危利空风险预警与正负号自动清洗断言】

        一、测试功能与测试点:
            1. 根治二元事件在中期发酵窗口 (14~60天) 不加判断一律建议“分批建仓埋伏”的重大逻辑倒错:
               当二元催化剂数学期望为负 (exp_move < 0) 或赔率倒挂 (odds < 0.8) 时，
               系统坚决输出【中期利空/风险提示窗口】，告诫“切忌盲目抄底或逢低埋伏”，
               以逢高减持控仓或对冲下行尾部风险为主。
            2. 验证下行跌幅 (downside_risk_pct) 误传正数时自动纠偏为负数损失，
               杜绝因正负号混淆导致期望颠倒的金融计算错误。

        二、正常函数业务边界与参数契约:
            - days_until_event 处于 (14, 60] 区间
            - 负期望: 成功率低 (30%)，涨幅小 (+20%)，跌幅大 (-50%) -> exp_move = -29.0%

        三、测试数据与模拟场景说明:
            面临专利悬崖诉讼判决高危利空事件。

        四、预期断言与结果验证:
            - 断言 binary_expected_move_pct 精确等于 -29.0%。
            - 断言 actionable_tactics_zh 明确包含 "中期利空/风险提示窗口"。
            - 断言 actionable_tactics_zh 严禁出现 "分批建仓埋伏"。
        """
        # 测试故意传入正数 50.0 作为跌幅，验证自动纠偏为 -50.0
        evt_negative = CorporateEvent(
            event_id="PATENT_CLIFF_RISK",
            target_date="2026-11-20",
            category="litigation",
            title_zh="重磅抗癌药专利保护期无效判决",
            description_zh="仿制药企专利无效二审终局判决",
            upside_potential_pct=20.0,
            downside_risk_pct=50.0,  # 传入正数跌幅，引擎必须自动清洗为 -50.0
            probability_of_success=0.30,  # 胜率仅 30%
        )
        res = CatalystCalendarEngine.evaluate_event(evt_negative, as_of_date="2026-10-15")
        # 距事件 36 天，处于中期发酵窗口
        self.assertEqual(res.days_until_event, 36)
        # 期望 = 0.30 * 20.0 + 0.70 * (-50.0) = 6.0 - 35.0 = -29.0%
        self.assertEqual(res.binary_expected_move_pct, -29.0)
        self.assertIn("中期利空/风险提示窗口", res.actionable_tactics_zh)
        self.assertIn("切忌盲目抄底或逢低埋伏", res.actionable_tactics_zh)
        self.assertNotIn("分批建仓埋伏", res.actionable_tactics_zh)

    def test_ut_inst_13_catalyst_narrative_zh_deengineered_and_options_arbitrage(self):
        """【UT-INST-13: 催化剂全息研报卡片去工程符号化与波动率套利断言】

        一、测试功能与测试点:
            1. 验证 CatalystCalendarEngine.evaluate_event 输出去工程符号化的
               买方通俗全息研报卡片 (narrative_zh);
            2. 验证期权隐含波动率过低时输出波动率被低估买方套利建议。

        二、正常函数业务边界与参数契约:
            - 正常二元事件输入与期权隐含波动率。

        三、测试数据与模拟场景说明:
            测试积极催化剂且期权波动率低估场景。

        四、预期断言与结果验证:
            - narrative_zh 包含 "二元催化剂事件全息研判"。
            - narrative_zh 包含 "买方操作战术建议"。
            - narrative_zh 严禁包含 "binary_expected_move_pct" 等纯技术字段名。
        """
        evt_bullish = CorporateEvent(
            event_id="FDA_APPROVAL",
            target_date="2026-11-10",
            category="fda_pdufa",
            title_zh="新药 BLA 获批 PDUFA 决战",
            description_zh="首创药物正式上市审批",
            upside_potential_pct=80.0,
            downside_risk_pct=-30.0,
            probability_of_success=0.75,
            options_implied_move_pct=25.0,  # 期权低估
        )
        res = CatalystCalendarEngine.evaluate_event(evt_bullish, as_of_date="2026-10-15")
        narrative = res.narrative_zh
        self.assertIn("二元催化剂事件全息研判", narrative)
        self.assertIn("买方操作战术建议", narrative)
        self.assertNotIn("binary_expected_move_pct", narrative)
        self.assertNotIn("upside_potential_pct", narrative)
        self.assertIn("期权波动率被低估", res.volatility_arbitrage_verdict)

    def test_ut_inst_14_credit_risk_narrative_zh_and_facade_ssot(self):
        """【UT-INST-14: 信用风险全息研报卡片去工程符号化与门面SSOT断言】

        一、测试功能与测试点:
            1. 验证 CreditRiskAndSolvencyEngine 端到端综合评估输出 narrative_zh 全息卡片;
            2. 验证财务稳健标的与高危标的信用画像去工程符号化;
            3. 验证 finance_tools 门面与 financial_core 核心层 SSOT 完全等价。

        二、正常函数业务边界与参数契约:
            - 正常财报与市值负债输入。

        三、测试数据与模拟场景说明:
            测试优质蓝筹企业信用评估场景。

        四、预期断言与结果验证:
            - 结果包含 narrative_zh 且非空。
            - 包含标的和偿债、违约风险信息。
            - 核心层与门面层计算输出 100% 一致。
        """
        from financial_core.engines.credit_risk_engine import CreditRiskAndSolvencyEngine as CoreCreditEngine
        from finance_tools.credit_risk_engine import CreditRiskAndSolvencyEngine as FacadeCreditEngine
        self.assertIs(FacadeCreditEngine, CoreCreditEngine)
        core_engine = CoreCreditEngine()

        res_core = core_engine.evaluate_comprehensive_credit(
            ticker="SAFE_CORP",
            equity_market_cap=50000.0,
            total_debt=5000.0,
            current_assets=12000.0,
            current_liabilities=4000.0,
            retained_earnings=18000.0,
            ebit=6000.0,
            revenue=30000.0,
            total_assets=45000.0,
            total_liabilities=10000.0,
        )
        self.assertIn("SAFE_CORP", res_core.narrative_zh)
        self.assertIn("偿债能力", res_core.narrative_zh)
        self.assertIn("违约风险", res_core.narrative_zh)
        self.assertIn("财务安全稳健", res_core.narrative_zh)
        self.assertEqual(res_core.altman_zone, "Safe")
        self.assertFalse(res_core.credit_alert_flag)

        # 验证 to_dict 暴露 narrative_zh
        d = res_core.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res_core.narrative_zh)


if __name__ == "__main__":
    unittest.main()
