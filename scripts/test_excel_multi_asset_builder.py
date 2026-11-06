"""测试买方机构级多资产 Excel 报告书建造器 (ExcelMultiAssetReportBuilder)."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import openpyxl

from financial_reporting.excel_multi_asset_builder import ExcelMultiAssetReportBuilder
from financial_reporting.ai_research_agent import EMOJI_PATTERN
from financial_core.contracts import DecisionCardData

ROOT = Path(__file__).resolve().parents[1]


class TestExcelMultiAssetReportBuilder(unittest.TestCase):
    """测试多资产 Excel 建造器各项核心功能与规范契约."""

    def setUp(self):
        # 准备 ETF 测试数据
        self.etf_dossiers = [
            {
                "ticker": "SPY",
                "name_zh": "标普500核心ETF",
                "asset_class": "美股宽基",
                "aum_display": "$580B",
                "expense_ratio": 0.0009,
                "concentration": {"cr10_pct": 34.5, "hhi": 185.0},
                "factor_scores": {"growth": 65.0, "value": 55.0, "quality": 85.0, "momentum": 70.0},
                "expense_drag": {"1y_drag_pct": 0.09, "3y_drag_pct": 0.28, "5y_drag_pct": 0.48},
            },
            {
                "ticker": "QQQ",
                "name_zh": "纳斯达克100精选ETF",
                "asset_class": "大型科技成长",
                "aum_display": "$310B",
                "expense_ratio": 0.0020,
                "concentration": {"cr10_pct": 51.2, "hhi": 340.0},
                "factor_scores": {"growth": 90.0, "value": 30.0, "quality": 88.0, "momentum": 85.0},
                "expense_drag": {"1y_drag_pct": 0.20, "3y_drag_pct": 0.62, "5y_drag_pct": 1.05},
            },
        ]
        self.overlap_pairs = [
            {
                "etf_a": "SPY",
                "etf_b": "QQQ",
                "overlap_weight_pct": 46.2,
                "jaccard_similarity_pct": 18.5,
                "overlapping_holdings": ["AAPL", "MSFT", "NVDA", "AMZN"],
            }
        ]

        # 准备黄金测试数据
        self.gold_valuation = {
            "spot_price": 2650.0,
            "valuation_models": {
                "tips_yield_anchor": 2150.0,
                "central_bank_structural_premium": 480.0,
                "macro_fair_value_center": 2630.0,
            },
            "scenarios": {
                "bear_case": 2250.0,
                "base_case": 2630.0,
                "bull_case": 2980.0,
            },
            "strategic_verdict_zh": "维持黄金作为战略去美元化与抗通胀核心底仓配置。",
        }
        self.gold_miners = [
            {
                "ticker": "NEM",
                "name_zh": "纽蒙特矿业",
                "market_cap_display": "$58B",
                "current_price": 48.50,
                "aisc_usd_per_oz": 1350.0,
                "fcf_annual_display": "$2.5B",
                "operating_leverage_ratio": 2.4,
                "fair_upside_pct": 35.0,
            }
        ]

        # 准备成长股测试数据 (同时包含 DecisionCardData 对象与 Dict 卡片)
        card_pltr = DecisionCardData(
            ticker="PLTR",
            company_name="Palantir Technologies",
            market="US",
            currency="USD",
            currency_symbol="$",
            sector="企业级AI与决策操作系统",
            quote_timestamp="2026-10-17T12:00:00Z",
            market_session="regular",
            current_price=42.50,
            baseline_reference_price=42.50,
            objective_signal="VALUE_BUY",
            pessimistic_floor=28.00,
            neutral_fair_value=48.00,
            optimistic_target=65.00,
            margin_of_safety_pct=12.9,
            hard_runway_desc="净现金超40亿美元，零有息负债，跑道充裕",
            forensic_red_flags_count=0,
            forensic_yellow_flags_count=0,
            primary_catalysts=["AIP平台在商业客户加速渗透", "美国政府防务大单续约"],
            key_risks=["估值倍数偏高", "政企采购周期拉长"],
            summary_verdict="估值处于合理偏低价值击球区",
        )
        card_arm_dict = {
            "ticker": "ARM",
            "company_name": "Arm Holdings",
            "sector": "端侧半导体与IP架构",
            "current_price": 140.00,
            "pessimistic_floor": 95.00,
            "neutral_fair_value": 155.00,
            "optimistic_target": 210.00,
            "margin_of_safety_pct": 10.7,
            "objective_signal": "GROWTH_BUY",
            "primary_catalysts": ["Armv9架构高特许权使用费率", "AI端侧芯片出货扩张"],
            "key_risks": ["手机大盘饱和", "RISC-V生态竞争"],
            "hard_runway_desc": "高自由现金流转化，无债务风险",
        }
        self.growth_items = [{"card": card_pltr}, {"card": card_arm_dict}]

    def test_build_multi_asset_workbook_success(self):
        """【IT-EXCEL-MA-01: 买方多资产Excel报告书全息构建、4-Sheet结构与零Emoji合规验签】

        1. 测试功能与测试点:
           - 验证 ExcelMultiAssetReportBuilder.build_multi_asset_workbook 买方机构级多资产 Excel 工作簿构建器。
           - 4 大业务工作表覆盖: '00_ETF穿透与持仓重叠度'、'01_黄金与大宗商品宏观估值'、'02_高价值成长股决策走廊'、'03_全量41细分行业因果图谱'。
           - 机构买方研报严苛质检: 网格线强制开启 (showGridLines=True)、100% 物理消除所有 Emoji 表情符、美分级精度与数值格式保真。
           - 估值三态走廊单调性公理: 悲观底价 <= 公允中枢 <= 乐观靶心。

        2. 正常函数业务边界与参数契约:
           - 接收 etf_dossiers, overlap_pairs, gold_valuation, gold_miners, growth_items。
           - output_path 必须为有效文件写入路径，生成文件字节大小 > 5000 bytes。

        3. 测试数据与模拟场景说明:
           - ETF: SPY (费率 0.09%, AUM $580B) 与 QQQ (费率 0.20%, AUM $310B)，穿透重叠度 46.2%。
           - 黄金: 现货 $2650/oz，10Y TIPS 实际利率锚 $2150，央行溢价 $480；纽蒙特矿业 NEM (现价 $48.50, AISC $1350/oz)。
           - 成长股: PLTR (现价 $42.50，悲观底 $28.00，公允 $48.00，乐观 $65.00) 与 ARM。
           - 41 细分行业: 包含 semiconductors 等全谱系映射。

        4. 预期断言与结果验证:
           - 断言生成工作簿物理存在且大小 > 5000 字节。
           - 断言 sheetnames 长度精确等于 4 且包含 4 张标准命名表。
           - 遍历所有单元格，断言 EMOJI_PATTERN 匹配结果全部为 None (零 Emoji)。
           - 断言 SPY 费率精确为 0.0009，AUM 为 '$580B'。
           - 断言 NEM 现价精确为 48.50。
           - 断言 PLTR 现价 42.50，且 pltr_floor (28.0) <= pltr_fair (48.0) <= pltr_target (65.0)。
           - 断言因果图谱包含 'semiconductors'。
        """
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            out_file = ExcelMultiAssetReportBuilder.build_multi_asset_workbook(
                etf_dossiers=self.etf_dossiers,
                overlap_pairs=self.overlap_pairs,
                gold_valuation=self.gold_valuation,
                gold_miners=self.gold_miners,
                growth_items=self.growth_items,
                report_date="2026-10-17",
                output_path=tmp_path,
            )

            self.assertTrue(out_file.exists())
            self.assertGreater(out_file.stat().st_size, 5000)

            # 读取工作簿并校验结构
            wb = openpyxl.load_workbook(out_file)
            sheet_names = wb.sheetnames
            self.assertEqual(len(sheet_names), 4)
            self.assertIn("00_ETF穿透与持仓重叠度", sheet_names)
            self.assertIn("01_黄金与大宗商品宏观估值", sheet_names)
            self.assertIn("02_高价值成长股决策走廊", sheet_names)
            self.assertIn("03_全量41细分行业因果图谱", sheet_names)

            # 严格遍历所有单元格，确保 100% 物理消除所有 Emoji 表情符
            for sname in sheet_names:
                ws = wb[sname]
                self.assertTrue(ws.views.sheetView[0].showGridLines, f"{sname} 网格线必须开启")
                for row in ws.iter_rows(values_only=True):
                    for val in row:
                        if isinstance(val, str):
                            self.assertIsNone(
                                EMOJI_PATTERN.search(val),
                                f"工作表 {sname} 中发现了非法表情符号: {val}",
                            )

            # 校验 Sheet 0 内容 (精细坐标、格式与数值断言)
            ws0 = wb["00_ETF穿透与持仓重叠度"]
            col_a_vals = [cell.value for cell in ws0["A"]]
            self.assertIn("SPY", col_a_vals, "ETF持仓表必须包含核心标的 SPY")
            self.assertIn("QQQ", col_a_vals, "ETF持仓表必须包含核心标的 QQQ")
            # 找到 SPY 所在行并校验其费率与数值精度
            spy_row = col_a_vals.index("SPY") + 1
            spy_name = ws0.cell(row=spy_row, column=2).value
            self.assertEqual(spy_name, "标普500核心ETF")
            spy_aum = ws0.cell(row=spy_row, column=4).value
            self.assertEqual(spy_aum, "$580B", "SPY 资产规模 AUM 必须展示为 $580B")
            spy_fee = ws0.cell(row=spy_row, column=5).value
            self.assertEqual(spy_fee, 0.0009, "SPY 费率必须精确等于 0.09%")

            # 校验 Sheet 1 黄金大宗商品宏观估值模型
            ws1 = wb["01_黄金与大宗商品宏观估值"]
            col_a_g = [cell.value for cell in ws1["A"]]
            self.assertIn("NEM", col_a_g, "黄金表必须包含纽蒙特矿业 NEM")
            nem_row = col_a_g.index("NEM") + 1
            self.assertEqual(ws1.cell(row=nem_row, column=2).value, "纽蒙特矿业")
            self.assertEqual(ws1.cell(row=nem_row, column=4).value, 48.50, "NEM 现价必须等于 $48.50 美分级精度")

            # 校验 Sheet 2 成长股决策走廊与估值边界
            ws2 = wb["02_高价值成长股决策走廊"]
            col_a_p = [cell.value for cell in ws2["A"]]
            self.assertIn("PLTR", col_a_p, "决策走廊必须包含标的 PLTR")
            pltr_row = col_a_p.index("PLTR") + 1
            pltr_price = ws2.cell(row=pltr_row, column=4).value
            self.assertEqual(pltr_price, 42.50, "PLTR 现价必须为美分级 $42.50")
            pltr_floor = ws2.cell(row=pltr_row, column=5).value
            pltr_fair = ws2.cell(row=pltr_row, column=6).value
            pltr_target = ws2.cell(row=pltr_row, column=7).value
            self.assertEqual(pltr_floor, 28.00, "PLTR 悲观底必须等于 $28.00")
            self.assertEqual(pltr_fair, 48.00, "PLTR 公允中枢必须等于 $48.00")
            self.assertEqual(pltr_target, 65.00, "PLTR 乐观靶心必须等于 $65.00")
            self.assertLessEqual(pltr_floor, pltr_fair)
            self.assertLessEqual(pltr_fair, pltr_target)

            # 校验 Sheet 3 全量 41 细分行业因果图谱
            ws3 = wb["03_全量41细分行业因果图谱"]
            col_b_sec = [cell.value for cell in ws3["B"]]
            self.assertIn("semiconductors", col_b_sec, "因果图谱必须包含半导体与集成电路行业")

        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
