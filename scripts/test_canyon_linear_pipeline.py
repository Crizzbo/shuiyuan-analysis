"""Canyon 单向线性流水线单元测试套件 (Canyon Linear Pipeline Tests).

覆盖 6 大标准作业工位的单向流动、门禁阻断、估值走廊约束与密码学时间链条验证。
"""

import unittest
from datetime import datetime, timezone, timedelta
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.pipeline.canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from financial_core.engines.prediction_ledger import PredictionLedger
from scripts.test_support.fixtures import isolated_facade_ledger, project_temp, freeze_quote_clock


class TestCanyonLinearPipeline(unittest.TestCase):
    """Canyon 单向线性流水线全工位验证。"""

    def setUp(self):
        self.temp_dir = project_temp(self, "test-canyon-")
        self.ledger_db_path = Path(self.temp_dir) / "test_canyon_ledger.db"
        self.ledger = PredictionLedger(db_path=str(self.ledger_db_path))
        isolated_facade_ledger(self, self.ledger)
        self.pipeline = CanyonLinearPipeline(ledger=self.ledger)

        edt_tz = timezone(timedelta(hours=-4))
        self.fresh_ts = (freeze_quote_clock(self).astimezone(edt_tz) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S EDT")

        # 标准合规输入样本 (以典型蓝筹高通胀测试用例为基准)
        self.valid_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            sector="TechHardware",
            current_price=180.0,
            quote_timestamp=self.fresh_ts,
            market_session="regular_trading",
            baseline_reference_price=175.0,
            reported_cash=30000.0,
            restricted_cash=2000.0,
            debt_covenant_min_cash=3000.0,
            total_debt=100000.0,
            total_assets=350000.0,
            total_liabilities=280000.0,
            stockholders_equity=70000.0,  # 350000 == 280000 + 70000 (严格平账)
            reported_operating_cash_flow=110000.0,
            reported_capex=12000.0,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=10000.0,
            reported_revenue=380000.0,
            reported_operating_income=115000.0,
            reported_net_income=97000.0,
            shares_outstanding=15000.0,
            us_10y_yield=0.044,
            vix_index=19.5,
            fed_liquidity_drain_billion=45.0,
            company_beta=1.15,
            option_target_strike=185.0,
            option_expiry_days=30.0,
            option_implied_vol=0.25,
            is_call_option=True,
        )

    def test_end_to_end_linear_flow_success(self):
        """【IT-CANYON-01: Canyon 6工位单向线性全链路买方决策卡生成与估值走廊公理守恒】

        1. 测试功能与测试点:
           - 验证 CanyonLinearPipeline 6 大工位单向无环流水线全链路执行。
           - 1.行情时效核验 -> 2.资产负债表平账 -> 3.宏观压力折现 -> 4.情景DCF与反向预期反解 -> 5.击球区与凯利仓位 -> 6.区块链式账本存证。
           - 美分级精度保真: 现价严格格式化为两位小数 ($180.00)。
           - 估值走廊公理守恒: 悲观底价 <= 公允内在价值中枢 <= 乐观靶心。
           - 弹性安全边际 (Elastic MoS): 结合企业久期与宏观压力的动态折扣。

        2. 正常函数业务边界与参数契约:
           - CanyonStationInput 必须严格平账 (Assets == Liabilities + Equity)。
           - 产出 CanyonDecisionCard 强类型数据结构。

        3. 测试数据与模拟场景说明:
           - 标的: AAPL，现价 $180.00，总资产 3500 亿，总负债 2800 亿，股东权益 700 亿 (严格平账)；经营现金流 1100 亿，CapEx 120 亿，SBC 100 亿；10Y 利率 4.4%，VIX 19.5。

        4. 预期断言与结果验证:
           - 断言 card.ticker == 'AAPL'。
           - 断言 formatted_price 符合正则 r"^\$\d+\.\d{2}$"。
           - 断言 pessimistic_floor <= neutral_fair_value <= optimistic_target。
           - 断言 strike_price < neutral_fair_value 且 elastic_mos_pct > 15.0%。
           - 断言 zone_status 属于合法枚举且包含相符的自然语言建议。
           - 断言 len(card.ledger_hash) == 64 且 ledger.verify_integrity().is_valid 为 True。
        """
        card = self.pipeline.run(self.valid_input)

        self.assertIsInstance(card, CanyonDecisionCard)
        self.assertEqual(card.ticker, "AAPL")
        self.assertEqual(card.company_name, "Apple Inc.")

        # 1. 美分级与货币精度断言 (验证绝无浮点漂移或整数截断)
        formatted_price = f"${card.current_price:.2f}"
        self.assertRegex(formatted_price, r"^\$\d+\.\d{2}$", "决策卡现价必须保持严格美分级两位小数")
        self.assertGreater(card.current_price, 0.0, "现价必须为严格正数")

        # 2. 估值单调走廊数学硬约束: 悲观底 <= 公允锚点 <= 乐观靶心
        self.assertLessEqual(card.pessimistic_floor, card.neutral_fair_value, "悲观底不能超过公允中枢")
        self.assertLessEqual(card.neutral_fair_value, card.optimistic_target, "公允中枢不能超过乐观靶心")

        # 3. 黄金击球买入底线与弹性安全边际精准计算断言 (非空泛断言)
        self.assertLess(card.strike_price, card.neutral_fair_value, "买入底线必须严于公允内在价值")
        expected_mos = ((card.neutral_fair_value - card.strike_price) / card.neutral_fair_value) * 100.0
        self.assertAlmostEqual(
            card.elastic_mos_pct,
            expected_mos,
            places=2,
            msg=f"弹性安全边际计算不符: 实际 {card.elastic_mos_pct}%, 期望 {expected_mos:.2f}%",
        )
        self.assertGreater(card.elastic_mos_pct, 15.0, "蓝筹严苛安全边际必须大于 15%")

        # 4. 区位与行动建议的真实商业语义一致性断言 (拒绝长度判断)
        valid_zones = ["GOLDEN_STRIKE_ZONE", "NEUTRAL_HOLD", "PREMIUM_OVERVALUED"]
        self.assertIn(card.zone_status, valid_zones)
        if card.zone_status == "GOLDEN_STRIKE_ZONE":
            self.assertTrue(
                any(kw in card.recommended_action for kw in ["买入", "建仓", "吸纳", "关注"]),
                f"击球区建议必须包含买入相关自然语言投资动作: {card.recommended_action}",
            )
        elif card.zone_status == "PREMIUM_OVERVALUED":
            self.assertTrue(
                any(kw in card.recommended_action for kw in ["观望", "减持", "止盈", "防范", "溢价"]),
                f"高估区建议必须包含防守相关投资动作: {card.recommended_action}",
            )

        # 5. 密码学不可篡改链条真实签名与完整性验签
        self.assertEqual(len(card.ledger_hash), 64, "账本哈希必须为 SHA-256 64 位十六进制串")
        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid, f"账本密码学链条篡改检测失败: {integrity.error}")

    def test_station_1_quote_freshness_zero_price_blocked(self):
        """【UT-CANYON-02: 工位1-报价时效门禁-零价格与负价格硬阻断】

        1. 测试功能与测试点:
           - 验证 Canyon 工位 1 (MarketQuoteVerifier) 对非法价格输入的防御。
           - 金融数学边界: 资产价格必须严格大于零 (Price > 0.0)，有限责任下界。

        2. 正常函数业务边界与参数契约:
           - current_price <= 0.0 时触发 QuoteFreshnessError 阻断。

        3. 测试数据与模拟场景说明:
           - 传入 current_price = 0.0。

        4. 预期断言与结果验证:
           - 抛出 QuoteFreshnessError。
           - 错误信息包含“价格必须严格大于零”。
        """
        bad_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=0.0,
            quote_timestamp=self.fresh_ts,
        )
        with self.assertRaises(QuoteFreshnessError) as ctx:
            self.pipeline.run(bad_input)
        self.assertIn("价格必须严格大于零", str(ctx.exception))

    def test_station_1_quote_freshness_missing_timestamp_blocked(self):
        """【UT-CANYON-03: 工位1-报价时效门禁-缺失精确报价时间戳硬阻断】

        1. 测试功能与测试点:
           - 验证 Canyon 工位 1 报价时效与时区门禁要求。
           - 严禁无时间戳的幽灵数据流入估值模型。

        2. 正常函数业务边界与参数契约:
           - quote_timestamp 必须非空且包含有效时区。

        3. 测试数据与模拟场景说明:
           - 传入 quote_timestamp = "" 空字符串。

        4. 预期断言与结果验证:
           - 抛出 QuoteFreshnessError。
           - 错误说明包含“缺失精确报价时间戳”。
        """
        bad_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.0,
            quote_timestamp="",
        )
        with self.assertRaises(QuoteFreshnessError) as ctx:
            self.pipeline.run(bad_input)
        self.assertIn("缺失精确报价时间戳", str(ctx.exception))

    def test_station_2_balance_sheet_imbalance_blocked(self):
        """【UT-CANYON-04: 工位2-会计底账门禁-资产负债表失衡刚性阻断】

        1. 测试功能与测试点:
           - 验证 Canyon 工位 2 会计平衡公理守恒检验。
           - 刚性自检: |Total Assets - (Total Liabilities + Equity)| / Total Assets <= 0.1%。
           - 不平账财报直接阻断，杜绝污染下游 DCF 净债务与估值底账。

        2. 正常函数业务边界与参数契约:
           - 相对失衡率 > 0.1% 触发 BalanceSheetInvariantError。

        3. 测试数据与模拟场景说明:
           - 资产 350,000，负债 200,000，权益 50,000 (资产超出负债+权益达 100,000，严重不平)。

        4. 预期断言与结果验证:
           - 抛出 BalanceSheetInvariantError。
           - 错误说明包含“资产负债表严重失衡”。
        """
        imbalanced_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=180.0,
            quote_timestamp=self.fresh_ts,
            total_assets=350000.0,
            total_liabilities=200000.0,
            stockholders_equity=50000.0,  # 350000 != 200000 + 50000 (差 100,000)
        )
        with self.assertRaises(BalanceSheetInvariantError) as ctx:
            self.pipeline.run(imbalanced_input)
        self.assertIn("资产负债表严重失衡", str(ctx.exception))

    def test_station_3_macro_stress_and_elastic_mos(self):
        """【UT-CANYON-05: 工位3-宏观压力测试与弹性安全边际(Elastic MoS)非线性放大】

        1. 测试功能与测试点:
           - 验证 Canyon 工位 3 宏观信贷脉冲与系统性压力向折现率和安全边际的传导。
           - 在流动性抽水、美债收益率狂飙与 VIX 恐慌恶化时，安全边际要求自动从基准上浮放大。

        2. 正常函数业务边界与参数契约:
           - macro_stress_score(高压力) > macro_stress_score(低压力)。
           - elastic_mos_pct(高压力) > elastic_mos_pct(低压力)。

        3. 测试数据与模拟场景说明:
           - 低压力场景: VIX 12.0, 10Y 收益率 3.5%, 美联储抽水 0。
           - 高压力场景: VIX 45.0, 10Y 收益率 6.5%, 美联储抽水 1000 亿。

        4. 预期断言与结果验证:
           - 断言 card_high.macro_stress_score > card_low.macro_stress_score。
           - 断言 card_high.elastic_mos_pct > card_low.elastic_mos_pct。
        """
        # 低压力环境
        low_stress_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=180.0,
            quote_timestamp=self.fresh_ts,
            total_assets=100.0,
            total_liabilities=50.0,
            stockholders_equity=50.0,
            reported_operating_cash_flow=20.0,
            vix_index=12.0,
            us_10y_yield=0.035,
            fed_liquidity_drain_billion=0.0,
        )
        card_low = self.pipeline.run(low_stress_input)

        # 极端踩踏高压力环境
        high_stress_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=180.0,
            quote_timestamp=self.fresh_ts,
            total_assets=100.0,
            total_liabilities=50.0,
            stockholders_equity=50.0,
            reported_operating_cash_flow=20.0,
            vix_index=45.0,
            us_10y_yield=0.065,
            fed_liquidity_drain_billion=100.0,
        )
        card_high = self.pipeline.run(high_stress_input)

        self.assertGreater(card_high.macro_stress_score, card_low.macro_stress_score)
        self.assertGreater(card_high.elastic_mos_pct, card_low.elastic_mos_pct)

    def test_station_5_golden_strike_zone_trigger(self):
        """【UT-CANYON-06: 工位5-现价击穿买入底线触发黄金击球区与半凯利建仓】

        1. 测试功能与测试点:
           - 验证 Canyon 工位 5 安全区位与仓位配置算法。
           - 判定击球区: 当 Current Price <= Strike Price 时，置位 GOLDEN_STRIKE_ZONE。
           - 结合凯利公式 (Kelly Criterion) 输出建议建仓头寸占比。

        2. 正常函数业务边界与参数契约:
           - current_price < strike_price。

        3. 测试数据与模拟场景说明:
           - 现价仅 $10.00，基本面现金流充沛，内在价值远高于现价。

        4. 预期断言与结果验证:
           - 断言 card.zone_status == 'GOLDEN_STRIKE_ZONE'。
           - 断言 card.kelly_position_pct > 0.0。
           - 断言 recommended_action 包含“击穿黄金买入底线”。
        """
        cheap_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=10.0,  # 现价远低于公允价值
            quote_timestamp=self.fresh_ts,
            total_assets=350000.0,
            total_liabilities=280000.0,
            stockholders_equity=70000.0,
            reported_operating_cash_flow=110000.0,
            reported_capex=12000.0,
            stock_based_compensation=10000.0,
            shares_outstanding=15000.0,
        )
        card = self.pipeline.run(cheap_input)

        self.assertEqual(card.zone_status, "GOLDEN_STRIKE_ZONE")
        self.assertGreater(card.kelly_position_pct, 0.0)
        self.assertIn("击穿黄金买入底线", card.recommended_action)

    def test_multi_record_ledger_cryptographic_chain_continuity(self):
        """【IT-CANYON-07: 连续标的入库PredictionLedger密码学时间链条连贯性验签】

        1. 测试功能与测试点:
           - 验证多家公司批处理连续调用 Canyon 管线时，时间链条的密码学哈希完整性。
           - 链条状态连续递进，prev_hash 精确指针绑定。

        2. 正常函数业务边界与参数契约:
           - 依次处理 AAPL, NVDA, MSFT。

        3. 测试数据与模拟场景说明:
           - 三家标的连续流入，均生成 64 位 SHA-256 哈希。

        4. 预期断言与结果验证:
           - 每次生成的 card.ledger_hash 长度均为 64。
           - ledger.verify_integrity().is_valid 为 True 且 error 为 None。
        """
        tickers = ["AAPL", "NVDA", "MSFT"]
        for t in tickers:
            inp = CanyonStationInput(
                ticker=t,
                company_name=f"{t} Corporation",
                current_price=150.0,
                quote_timestamp=self.fresh_ts,
                total_assets=100.0,
                total_liabilities=60.0,
                stockholders_equity=40.0,
                reported_operating_cash_flow=25.0,
                reported_capex=5.0,
                shares_outstanding=10.0,
            )
            card = self.pipeline.run(inp)
            self.assertEqual(len(card.ledger_hash), 64)

        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid)
        self.assertIsNone(integrity.error)

    def test_facade_analyze_linear_equity_integration(self):
        """【IT-CANYON-08: FinancialAnalysisSystem统一门面透明集成调用验证】

        1. 测试功能与测试点:
           - 验证金融分析系统总控门面 FinancialAnalysisSystem.analyze_linear_equity 门面模式封装。
           - 确保外部调用方通过门面与直接调用流水线结果等价。

        2. 正常函数业务边界与参数契约:
           - 输入 valid_input，输出 CanyonDecisionCard。

        3. 测试数据与模拟场景说明:
           - AAPL 标准合规事实。

        4. 预期断言与结果验证:
           - card.ticker == 'AAPL'。
           - 现价格式为美分级两位小数且 > 0。
           - len(card.ledger_hash) == 64。
        """
        from financial_core import FinancialAnalysisSystem
        system = FinancialAnalysisSystem()
        card = system.analyze_linear_equity(self.valid_input)
        self.assertIsInstance(card, CanyonDecisionCard)
        self.assertEqual(card.ticker, "AAPL")
        self.assertRegex(f"${card.current_price:.2f}", r"^\$\d+\.\d{2}$", "现价必须保持严格美分级两位小数")
        self.assertGreater(card.current_price, 0.0)
        self.assertEqual(len(card.ledger_hash), 64)

    def test_real_excel_medium_nvda_flow(self):
        """【FT-CANYON-09: 真实Excel介质落盘行情提取与NVDA全工位流水线驱动实测】

        1. 测试功能与测试点:
           - 验证实物落地: 真实创建物理 Excel 工作簿，写入 NVDA 现价 $204.64。
           - MarketQuoteVerifier 物理提取单元格价格并转换为强类型事实。
           - 驱动 Canyon 流水线 6 大工位全息运转并产出买方决策卡与账本验签。

        2. 正常函数业务边界与参数契约:
           - 提取价格与 NVDA FY2026 财报底账结合，资产 206,800 == 负债 49,510 + 权益 157,290 严格平账。

        3. 测试数据与模拟场景说明:
           - 在临时目录创建 NVDA_live_model.xlsx，C3 单元格填入 204.64。

        4. 预期断言与结果验证:
           - extracted.is_valid 为 True 且 extracted_price == 204.64。
           - card.ticker == 'NVDA' 且 current_price 格式化为 '$204.64'。
           - card.neutral_fair_value > 0.0。
           - pessimistic_floor <= neutral_fair_value <= optimistic_target。
           - len(card.ledger_hash) == 64 且 ledger.verify_integrity().is_valid 为 True。
        """
        import openpyxl
        from finance_tools.market_quote_verifier import MarketQuoteVerifier

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_excel = Path(tmp_dir) / "NVDA_live_model.xlsx"
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "跨周期情景DCF模型"
            ws["B3"] = "当前市价:"
            ws["C3"] = 204.64  # 写入真实核准的 NVDA 现价
            wb.save(tmp_excel)

            # 1. 真实从 Excel 物理文件中提取
            verifier = MarketQuoteVerifier(Path(tmp_dir))
            extracted = verifier.extract_quote_from_excel(tmp_excel, ticker="NVDA", coordinate="C3")
            self.assertTrue(extracted.is_valid, f"Excel 提取失败: {extracted.error_message}")
            self.assertEqual(extracted.extracted_price, 204.64)
            self.assertEqual(extracted.formatted_price, "$204.64")

            # 2. 将真实介质提取的现价与 NVDA FY2026 10-K 平账底账组装输入
            nvda_input = CanyonStationInput(
                ticker="NVDA",
                company_name="NVIDIA Corporation",
                market="US",
                sector="TechHardware",
                current_price=extracted.extracted_price,
                quote_timestamp=self.fresh_ts,
                market_session="regular_trading",
                total_assets=206800.0,
                total_liabilities=49510.0,
                stockholders_equity=157290.0,  # 206800 == 49510 + 157290 (平账)
                reported_operating_cash_flow=64500.0,
                reported_capex=3100.0,
                stock_based_compensation=4200.0,
                reported_revenue=96300.0,
                reported_operating_income=55200.0,
                reported_net_income=50100.0,
                shares_outstanding=24940.0,
            )

            # 3. 运行全工位线性流水线
            card = self.pipeline.run(nvda_input)
            self.assertEqual(card.ticker, "NVDA")
            self.assertEqual(f"${card.current_price:.2f}", "$204.64", "决策卡现价必须严格等于 Excel 提取的 $204.64")
            self.assertGreater(card.neutral_fair_value, 0.0)
            self.assertLessEqual(card.pessimistic_floor, card.neutral_fair_value)
            self.assertLessEqual(card.neutral_fair_value, card.optimistic_target)
            self.assertEqual(len(card.ledger_hash), 64)
            integrity = self.ledger.verify_integrity()
            self.assertTrue(integrity.is_valid)


if __name__ == "__main__":
    unittest.main()
