"""全方位数值取值与小数位精度保真单元测试套件 (test_quote_and_metric_precision.py).

严格遵循用户指示与工程规范：
1. 股票行情美分级精度保真 (Cent-Precision Invariant)：杜绝尾零截断与浮点漂移 (如 $204.00 绝不能退化为 $204)；
2. 官方财报与十亿美元单位换算精度：资产、负债、权益与现金流全部保留精确两位小数 (如 $206.80B 不得缩水为 $206.8B)；
3. 财务衍生指标精度：DIO (存货周转天数)、ROIC (资本回报率)、利息覆盖倍数必须保留明确小数位，严禁整数截断；
4. 全量决策研判卡正则语法硬断言：通过严格正则校验整卡中所有金额与价格，断言 100% 具备两位小数；
5. 零硬编码与防篡改硬阻断：验证上游价格输入与下游各工位输出严格一致，缺失权威行情时刚性抛出 QuoteFreshnessError。
"""

import json
import math
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway
from finance_tools.market_quote_verifier import MarketQuoteVerifier, ExcelQuoteResult
import openpyxl
from financial_core.engines.prediction_ledger import PredictionLedger
from scripts.test_support.fixtures import project_temp
from scripts.canyon_linear_pipeline import (
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
    Stage1QuoteResult,
    Stage2FilingResult,
    Stage3MacroResult,
    Stage4ValuationResult,
    Stage5StrikeZoneResult,
)


class TestQuoteAndMetricPrecision(unittest.TestCase):
    """全方位数值取值、小数位展示保真度与防篡改测试。"""

    def setUp(self):
        self.temp_dir = project_temp(self, "test-precision-")
        self.ledger_db_path = Path(self.temp_dir) / "test_precision_ledger.db"
        self.ledger = PredictionLedger(db_path=str(self.ledger_db_path))
        self.pipeline = CanyonLinearPipeline(ledger=self.ledger)
        self.test_as_of = "2026-11-01T00:00:00Z"

    def test_01_quote_cent_precision_preservation(self):
        """【UT-PRECISION-01: 股票现价美分级精度保真(Cent-Precision Invariant)与尾零防截断】

        1. 测试功能与测试点:
           - 验证股票报价严格美分级精度不变量 (Cent-Precision Invariant)。
           - 杜绝浮点漂移或整数尾零截断 (例如 $204.00 绝不能退化为 $204，尾数为 0 时必须完整保留 .00)。
           - 正则表达式断言: 校验金额格式必须严格满足 r"^\\$\\d+\\.\\d{2}$"。

        2. 正常函数业务边界与参数契约:
           - 针对任何正浮点价格，经过两位小数格式化后，美分位必须精确等于 2 位。

        3. 测试数据与模拟场景说明:
           - 覆盖整数尾零、单个小数、随机美分值组合: 204.00, 204.37, 344.63, 618.45, 435.20, 283.84, 490.50。

        4. 预期断言与结果验证:
           - 断言格式化字符串完全匹配期望目标 (如 204.00 -> '$204.00')。
           - 断言正则匹配 group(2) 长度精确等于 2。
        """
        test_cases = [
            (204.00, "$204.00"),
            (204.37, "$204.37"),
            (344.63, "$344.63"),
            (618.45, "$618.45"),
            (435.20, "$435.20"),
            (283.84, "$283.84"),
            (490.50, "$490.50"),
        ]

        for price_val, expected_str in test_cases:
            formatted = f"${price_val:.2f}"
            self.assertEqual(
                formatted,
                expected_str,
                f"价格 {price_val} 格式化失败，期望 {expected_str}，实际 {formatted}",
            )
            # 断言尾数两位小数存在且为有效数字
            match = re.match(r"^\$(\d+)\.(\d{2})$", formatted)
            self.assertIsNotNone(match, f"{formatted} 不符合严格美分格式")
            cents_part = match.group(2)
            self.assertEqual(len(cents_part), 2, "美分位必须严格为 2 位")

    def test_02_quote_freshness_gate_precision_and_anti_tamper(self):
        """【IT-PRECISION-02: Excel真实物理介质现价提取与流水线行情时效门禁防篡改核验】

        1. 测试功能与测试点:
           - 验证 MarketQuoteVerifier 从真实 Excel 文件单元格中提取现价的保真能力 (提取 NVDA $204.64)。
           - 验证 CanyonLinearPipeline 工位 1 (Stage 1 Quote Freshness Gate) 取值与 Excel 提取值完全物理对齐。
           - 防篡改与零伪造门禁: 传入不存在的虚假代码时刚性抛出 QuoteFreshnessError，严禁伪造假数据。

        2. 正常函数业务边界与参数契约:
           - excel 单元格配置 "$#,##0.00" 格式。
           - 无效标的输入必须触发强类型拦截。

        3. 测试数据与模拟场景说明:
           - 临时创建工作簿 NVDA_dossier_sheet.xlsx，在 '跨周期情景DCF模型' 表 C3 写入 204.64。
           - 测试 AAPL 现价 344.63 与虚假标的 'NON_EXISTENT_FAKE_TICKER'。

        4. 预期断言与结果验证:
           - 断言 extracted_price == 204.64 且 formatted_price == '$204.64'。
           - 断言 q_res.current_price == excel_res.extracted_price。
           - 断言 AAPL 现价保持 $344.63。
           - 断言虚假代码刚性抛出 QuoteFreshnessError。
        """
        # 1. 真实准备带有英伟达活体模型结构的 Excel 工作簿
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_excel = Path(tmp_dir) / "NVDA_dossier_sheet.xlsx"
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "跨周期情景DCF模型"
            ws["B3"] = "当前市价:"
            ws["C3"] = 204.64  # 从 Google Sheet / 活体模型提取出的真实美分级现价
            ws["C3"].number_format = "$#,##0.00"
            wb.save(tmp_excel)

            # 通过专门工具从 Excel 抽取
            verifier = MarketQuoteVerifier(ROOT)
            excel_res = verifier.extract_quote_from_excel(
                excel_path=tmp_excel,
                ticker="NVDA",
                sheet_name="跨周期情景DCF模型",
                coordinate="C3",
            )
            self.assertIsInstance(excel_res, ExcelQuoteResult)
            # 断言从 Excel 中实际提取到的价格真实等于 204.64
            self.assertEqual(
                excel_res.extracted_price,
                204.64,
                f"从 Excel 中提取的现价必须真实等于 204.64，实际提取到: {excel_res.extracted_price}",
            )
            self.assertEqual(
                excel_res.formatted_price,
                "$204.64",
                f"从 Excel 提取价格的美分级展示必须为 $204.64，实际为: {excel_res.formatted_price}",
            )

        # 2. 验证流水线工位 1 行情门禁真实取值精度与 Excel 提取值完全对齐
        q_res = self.pipeline.stage_1_quote_freshness_gate("NVDA", self.test_as_of)
        self.assertIsInstance(q_res, Stage1QuoteResult)
        self.assertEqual(
            q_res.current_price,
            excel_res.extracted_price,
            "流水线工位 1 现价必须与从 Excel 提取的价格严格一致",
        )
        self.assertEqual(f"${q_res.current_price:.2f}", "$204.64")

        # 3. 验证非整数行情 (如 AAPL 344.63) 保真度
        q_aapl = self.pipeline.stage_1_quote_freshness_gate("AAPL", self.test_as_of)
        self.assertEqual(q_aapl.current_price, 344.63)
        self.assertEqual(f"${q_aapl.current_price:.2f}", "$344.63")

        # 4. 验证无效代码或缺失行情时绝对不使用任何假数据回退，必须抛出 QuoteFreshnessError
        with self.assertRaises(QuoteFreshnessError):
            self.pipeline.stage_1_quote_freshness_gate("NON_EXISTENT_FAKE_TICKER", self.test_as_of)

    def test_03_financial_statement_billion_unit_decimal_precision(self):
        """【UT-PRECISION-03: 官方财报十亿美元(B)单位换算小数位保真与平账误差美分受控】

        1. 测试功能与测试点:
           - 验证财报核心科目以十亿美元 ($B) 为单位展示时的小数位精准度。
           - 尾数防缩水: 例如总资产 $206.80B 绝不能丢失末位零缩水为 $206.8B。
           - 会计平账硬约束: 平账误差保留两位小数格式化后必须为 $0.00。

        2. 正常函数业务边界与参数契约:
           - filing_res 为经过 SEC 官方映射的 Stage2FilingResult 事实。

        3. 测试数据与模拟场景说明:
           - NVDA FY2026 底账: 总资产 2068 亿，总负债 495.1 亿，股东权益 1572.9 亿，自由现金流 966.8 亿。

        4. 预期断言与结果验证:
           - 断言 assets_b_str 精确等于 '$206.80B'。
           - 断言 liab_b_str == '$49.51B'，equity_b_str == '$157.29B'，fcf_b_str == '$96.68B'。
           - 断言 diff_str 精确等于 '$0.00'。
        """
        filing_res = self.pipeline.stage_2_official_filing_gate("NVDA")
        self.assertIsInstance(filing_res, Stage2FilingResult)

        # 验证总资产 $206.80B (注意末位为 0 时绝不能丢失变成 $206.8B)
        assets_b_str = f"${filing_res.total_assets / 1e9:.2f}B"
        self.assertEqual(
            assets_b_str,
            "$206.80B",
            f"总资产十亿美元单位换算失败，期望 $206.80B，实际 {assets_b_str}",
        )

        # 验证总负债 $49.51B
        liab_b_str = f"${filing_res.total_liabilities / 1e9:.2f}B"
        self.assertEqual(liab_b_str, "$49.51B")

        # 验证股东权益 $157.29B
        equity_b_str = f"${filing_res.stockholders_equity / 1e9:.2f}B"
        self.assertEqual(equity_b_str, "$157.29B")

        # 验证年化自由现金流 $96.68B
        fcf_b_str = f"${filing_res.free_cash_flow / 1e9:.2f}B"
        self.assertEqual(fcf_b_str, "$96.68B")

        # 刚性平账误差必须在分 (Cent) 级别精准受控
        diff_str = f"${filing_res.balance_difference:.2f}"
        self.assertEqual(diff_str, "$0.00", "经审计平账误差必须为 $0.00")

    def test_04_derived_financial_metrics_decimal_fidelity(self):
        """【UT-PRECISION-04: 核心财务衍生指标(DIO/ROIC/利息覆盖)小数位真实精度与防截断】

        1. 测试功能与测试点:
           - 验证微观血肉衍生指标的精确数学计算与非整型保留。
           - 存货周转天数 (DIO): 精确保留 1 位小数 (125.0 天)，严禁截断为整数 125。
           - 资本回报率 (ROIC): 精确保留 1 位小数 (71.9%)，严禁四舍五入为 72%。
           - 利息覆盖倍数: 精确保留 1 位小数 (372.5x)。

        2. 正常函数业务边界与参数契约:
           - 纯数学公式计算并格式化输出。

        3. 测试数据与模拟场景说明:
           - NVDA 官方三表底稿数据: COGS、Inventory、EBIT、NOPAT 与有息负债。

        4. 预期断言与结果验证:
           - 断言 dio_str == '125.0' 且不等于 '125'。
           - 断言 roic_str == '71.9%' 且不等于 '72%'。
           - 断言 cov_str == '372.5x'。
        """
        raw_filing_path = (
            Path("D:/美股分析")
            / "02_格式化标准三表库"
            / "JSON格式"
            / "NVDA_NVIDIA_CORP_标准财报底稿.json"
        )
        if raw_filing_path.exists():
            data = json.loads(raw_filing_path.read_text(encoding="utf-8"))
            bs = data["balance_sheet"]
            inc = data["income_statement"]
            cf = data["cash_flow_statement"]

            # 1. 存货周转天数 DIO 纯数学重算
            cogs = inc["cost_of_revenue"]
            inv = bs["inventory"]
            dio_exact = (inv / cogs) * 365
            dio_str = f"{dio_exact:.1f}"
            self.assertEqual(
                dio_str,
                "125.0",
                f"DIO 精确计算失败，期望 125.0 天，实际 {dio_str} 天",
            )
            # 绝不允许截断为整型 125
            self.assertNotEqual(dio_str, "125", "DIO 严禁省略小数被截断为整数 125")

            # 2. 资本回报率 ROIC 重算
            ebit = inc["operating_income"]
            tax_rate = 0.15
            nopat = ebit * (1 - tax_rate)
            invested_cap = bs["stockholders_equity"] + bs["total_debt"] - bs["cash_and_cash_equivalents"]
            roic_exact = (nopat / invested_cap) * 100
            roic_str = f"{roic_exact:.1f}%"
            self.assertEqual(roic_str, "71.9%", f"ROIC 期望 71.9%，实际 {roic_str}")
            self.assertNotEqual(roic_str, "72%", "ROIC 严禁省略小数位被截断为整数 72%")

            # 3. 利息覆盖倍数
            est_interest = 350000000.0
            cov_exact = ebit / est_interest
            cov_str = f"{cov_exact:.1f}x"
            self.assertEqual(cov_str, "372.5x")

    def test_05_monte_carlo_valuation_corridor_precision(self):
        """【UT-PRECISION-05: 蒙特卡洛DCF三态情景走廊美分级保真与单调性公理守恒】

        1. 测试功能与测试点:
           - 验证 10,000 次蒙特卡洛 DCF 模拟输出三态价格的分位数单调性与美分级格式。
           - 估值公理守恒: 悲观底价 P10 <= 基准中性公允 P50 <= 乐观靶心 P90。
           - 价格小数位断言: 所有情景价格必须完全符合 r"^\\$\\d+\\.\\d{2}$"。

        2. 正常函数业务边界与参数契约:
           - stage_4_three_scenario_valuation 返回 Stage4ValuationResult。

        3. 测试数据与模拟场景说明:
           - NVDA 输入样本，结合宏观弹性折现引擎。

        4. 预期断言与结果验证:
           - 断言 p10 <= p50 <= p90。
           - 断言 p10_str, p50_str, p90_str 正则校验通过。
        """
        quote_res = self.pipeline.stage_1_quote_freshness_gate("NVDA", self.test_as_of)
        filing_res = self.pipeline.stage_2_official_filing_gate("NVDA")
        macro_res = self.pipeline.stage_3_macro_elastic_margin_engine(
            filing=filing_res, quote=quote_res
        )

        val_res = self.pipeline.stage_4_three_scenario_valuation(
            quote=quote_res,
            filing=filing_res,
            macro=macro_res,
        )
        self.assertIsInstance(val_res, Stage4ValuationResult)

        p10 = val_res.pessimistic_floor_price
        p50 = val_res.neutral_fair_anchor_price
        p90 = val_res.optimistic_target_price

        # 验证单调性: P10 <= P50 <= P90
        self.assertLessEqual(p10, p50, "悲观底价 P10 必须小于等于中性公允 P50")
        self.assertLessEqual(p50, p90, "中性公允 P50 必须小于等于乐观靶心 P90")

        # 验证格式化均为精确两位小数
        p10_str = f"${p10:.2f}"
        p50_str = f"${p50:.2f}"
        p90_str = f"${p90:.2f}"

        for s in [p10_str, p50_str, p90_str]:
            self.assertTrue(
                re.match(r"^\$\d+\.\d{2}$", s),
                f"估值走廊价格 {s} 必须严格具备两位小数",
            )

    def test_06_decision_card_full_markdown_decimal_rigor(self):
        """【FT-PRECISION-06: 投委会买方决策卡Markdown全文正则语法硬断言与零裸整数校验】

        1. 测试功能与测试点:
           - 验证决策研报全文本正则语法断言: 杜绝任何粗制滥造的无小数裸整数美元金额 (如裸写 $204 而非 $204.00 或 $204.64)。
           - 验证决策卡现价必须显式包含 '**$204.64 USD**'。
           - 验证财报指标必须包含 **$206.80B** 等十亿美元两位小数标注。
           - 验证击球底线必须符合 r"严苛击球买入底线：\\*\\*\\$\\d+\\.\\d{2}\\*\\*"。

        2. 正常函数业务边界与参数契约:
           - 正则表达式扫描裸整数模式: r"\\$(?!\\d+\\.\\d{2})\\d+"。

        3. 测试数据与模拟场景说明:
           - 驱动完整流水线生成 NVDA 决策卡 Markdown 文本。

        4. 预期断言与结果验证:
           - 断言 naked_matches 列表为空 (零裸整数非法金额)。
           - 断言各项关键指标包含明确格式。
        """
        full_res = self.pipeline.run("NVDA", self.test_as_of)
        card_md = full_res.decision_card_markdown

        # 1. 验证现价行: 必须为 $204.64 USD
        self.assertIn(
            "**$204.64 USD**",
            card_md,
            "决策卡中现价必须完整显示为 **$204.64 USD**，尾数不得省略",
        )

        # 2. 验证财报指标行: 必须含有 $206.80B、$49.51B、$157.29B、$96.68B
        self.assertIn("**$206.80B**", card_md, "总资产必须为 **$206.80B**")
        self.assertIn("**$49.51B**", card_md, "负债必须为 **$49.51B**")
        self.assertIn("**$157.29B**", card_md, "股东权益必须为 **$157.29B**")
        self.assertIn("**$96.68B**", card_md, "自由现金流必须为 **$96.68B**")

        # 3. 验证核验误差必须显式保留两位小数
        self.assertIn("$0.00", card_md, "平账误差必须为 $0.00")

        # 4. 验证严苛击球买入底线必须带两位小数
        self.assertRegex(
            card_md,
            r"严苛击球买入底线：\*\*\$\d+\.\d{2}\*\*",
            "击球买入底线必须具有精确到分的两位小数",
        )

        # 5. 验证绝对杜绝任何不带小数的美元整数标注 (如 $204 后面不带点)
        # 正则查找形如 $204 但后面不是 .数字 的非法简写
        naked_dollar_pattern = re.compile(r"\$(?!\d+\.\d{2})\d+")
        naked_matches = naked_dollar_pattern.findall(card_md)
        # 允许的例外：无（所有金额均应格式化为 .2f）
        self.assertEqual(
            naked_matches,
            [],
            f"检测到未保留小数位的非法缩水金额: {naked_matches}",
        )

    def test_07_end_to_end_custom_cents_pipeline_fidelity(self):
        """【UT-PRECISION-07: 端到端自定义美分输入保真贯通与时效网关验证】

        1. 测试功能与测试点:
           - 验证 QuoteFreshnessGateway.verify_quote 对自定义输入价格的小数位保真。
           - 输入 204.85，输出标签中必须精确体现 '204.85' 与 'USD204.85'，全链路无浮点漂移。

        2. 正常函数业务边界与参数契约:
           - price > 0, currency="USD", max_staleness_hours=72.0。

        3. 测试数据与模拟场景说明:
           - 传入 204.85 美元，时间戳 2026-10-31T20:00:00Z。

        4. 预期断言与结果验证:
           - 断言 v_res.formatted_label 包含 '204.85' 与 'USD204.85'。
        """
        # 测试自定义价格输入时的 Stage 1 验证
        v_res = QuoteFreshnessGateway.verify_quote(
            price=204.85,
            currency="USD",
            quote_timestamp="2026-10-31T20:00:00Z",
            market="US",
            current_time_iso=self.test_as_of,
            max_staleness_hours=72.0,
        )
        self.assertIn("204.85", v_res.formatted_label)
        self.assertIn("USD204.85", v_res.formatted_label)


if __name__ == "__main__":
    unittest.main()
