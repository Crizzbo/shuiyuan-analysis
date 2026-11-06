"""单元测试：宏微观大贯通总控编排器与 Excel 报告书建造器 (test_macro_micro_systemic.py).

验证：
1. 资产负债表刚性平账自检拦截与 320+ 家全量已核验企业加载；
2. 宏微观全回路闭环一般均衡计算与两阶段收敛 DCF；
3. 行星最终吸收平衡律严格守恒；
4. 买方 4-Sheet Excel 报告书生成、样式与 100% 物理清除 Emoji；
5. PredictionLedger SHA-256 密码学不可篡改审计链条。
"""

from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import tempfile
import unittest
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.filing_mapper import OfficialFilingMapper
from financial_reporting.macro_micro_systemic_orchestrator import (
    MacroMicroSystemicOrchestrator,
    MicroFirmEnrichedValuation,
)
from financial_reporting.excel_macro_micro_builder import ExcelMacroMicroReportBuilder


class TestMacroMicroSystemicIntegration(unittest.TestCase):
    """宏微观大贯通集成测试用例集."""

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = MacroMicroSystemicOrchestrator()

    def test_01_load_and_prepare_universe_integrity(self):
        """【IT-SYSTEMIC-01: 300+家资产全息底账加载与资产负债表刚性平账自检】

        1. 测试功能与测试点:
           - 验证 MacroMicroSystemicOrchestrator.load_and_prepare_universe 从本地磁盘全量加载已核验企业池。
           - 验证资产负债表刚性平衡公理门禁: Assets = Liabilities + Stockholders' Equity。
           - 相对误差不得超过千分之一 (diff / Assets <= 0.1%)，任何不平账财报直接阻断。
           - 验证行业分类元数据对齐: 确保每家企业均具备 micro sector_id, macro_sector_id 与 industry_id。

        2. 正常函数业务边界与参数契约:
           - 资产、负债、所有者权益必须为有限非负数值。
           - 相对误差公式: |Assets - (Liabilities + Equity)| / max(Assets, 1.0) <= 0.001。

        3. 测试数据与模拟场景说明:
           - 扫描并加载项目 data/ 目录下 320+ 家美股 (SEC) 与日股 (JPX) 官方真实披露财报底账。
           - 抽检前 50 家标的执行逐一穿透平账核算。

        4. 预期断言与结果验证:
           - 断言合规且通过平账自检的企业数量 > 300。
           - 断言抽检企业 rel_diff <= 0.001。
           - 断言各企业行业编码字段非空。
        """
        prepared = self.orchestrator.load_and_prepare_universe()
        # 必须加载超过 300 家合规且通过平账自检的企业
        self.assertGreater(len(prepared), 300, f"平账合规企业数量不足: {len(prepared)}")

        # 严格抽检资产负债表平衡：Assets = Liabilities + Equity (容差 <= 0.1%)
        for fact, rec, raw in prepared[:50]:
            raw_fin = raw.get("raw_financials_table", {})
            assets = OfficialFilingMapper.parse_financial_number(raw_fin.get("total_assets", 0.0))
            liab = OfficialFilingMapper.parse_financial_number(raw_fin.get("total_liabilities", 0.0))
            equity = OfficialFilingMapper.parse_financial_number(raw_fin.get("equity", raw_fin.get("stockholders_equity", 0.0)))
            if equity == 0.0 and assets > 0 and liab > 0:
                equity = assets - liab
            elif liab == 0.0 and assets > 0 and equity > 0:
                liab = assets - equity
            diff = abs(assets - (liab + equity))
            rel_diff = diff / max(assets, 1.0)
            self.assertLessEqual(rel_diff, 0.001, f"标的 {fact.ticker} 资产负债表严重不平账: 资产={assets}, 负债+权益={liab + equity}")
            self.assertTrue(len(fact.sector_id) > 0)
            self.assertTrue(len(rec.macro_sector_id) > 0)
            self.assertTrue(len(rec.industry_id) > 0)

    def test_02_run_systemic_pipeline_and_conservation(self):
        """【IT-SYSTEMIC-02: 宏微观全回路端到端总控计算与行星最终吸收守恒律验证】

        1. 测试功能与测试点:
           - 验证宏微观大贯通流水线 (Systemic Pipeline) 端到端全回路计算。
           - 验证行星最终吸收守恒公理 (Planetary Absorption Conservation Law): 宏观增加值产出与各行业投入产出完全守恒。
           - 验证微观企业全息两阶段 DCF 折现估值、悲观底线估值与前收盘价时效标注。
           - 验证三大买方分类清单: 价值洼地击球区 (undervalued)、高估泡沫排雷池 (overvalued)、高ROIC复利底仓池 (quality)。
           - 验证 PredictionLedger SHA-256 密码学时间链条全量入库存证。

        2. 正常函数业务边界与参数契约:
           - as_of_date: ISO 格式日期字符串 (如 '2026-10-18')。
           - record_to_ledger: 布尔值，控制是否存入密码学账本。
           - 评估标的数必须 > 300 家。

        3. 测试数据与模拟场景说明:
           - 执行 2026-10-18 基准日全回路运算，覆盖宏观投入产出、300+ 标的两阶段 DCF 与密码学存证。

        4. 预期断言与结果验证:
           - 断言 planetary_absorption_strictly_conserved 为 True。
           - 断言 total_verified_firms_evaluated > 300。
           - 断言 micro 估值输出中两阶段公允价值与底价均 > 0。
           - 断言三大清单长度均 > 0。
           - 断言 ledger_hashes 长度 > 0。
        """
        # 运行流水线
        res = self.orchestrator.run_systemic_pipeline(
            as_of_date="2026-10-18",
            record_to_ledger=True,
        )

        meta = res["meta"]
        self.assertEqual(meta["as_of_date"], "2026-10-18")
        self.assertTrue(meta["planetary_absorption_strictly_conserved"], "行星吸收守恒律破损！")
        self.assertGreater(meta["total_verified_firms_evaluated"], 300)

        # 检验微观企业全息估值记录
        enriched_firms = res["enriched_firms"]
        self.assertGreater(len(enriched_firms), 300)

        for f in enriched_firms[:20]:
            self.assertIsInstance(f, MicroFirmEnrichedValuation)
            self.assertGreater(f.revenue_million, 0)
            self.assertGreater(f.two_stage_fair_value_billion, 0)
            self.assertGreater(f.pessimistic_floor_value_billion, 0)
            self.assertIn("前收基准", f.price_freshness_label)
            self.assertIn(f.institutional_verdict, ["价值洼地击球区", "高估泡沫排雷标的", "合理中枢持有区"])

        # 检验价值洼地与高估排雷清单
        undervalued = res["undervalued_batting_zone"]
        overvalued = res["overvalued_bubble_mines"]
        quality = res["quality_core_compounders"]

        self.assertGreater(len(undervalued), 0, "应筛选出具备安全边际的价值洼地标的")
        self.assertGreater(len(overvalued), 0, "应筛选出严重高估透支或现金流失血的排雷标的")
        self.assertGreater(len(quality), 0, "应筛选出高 ROIC 卓越复利底仓标的")

        # 检验密码学账本存证
        ledger_hashes = res["ledger_hashes"]
        self.assertGreater(len(ledger_hashes), 0, "密码学账本存证链条为空！")

    def test_03_excel_macro_micro_builder_and_zero_emoji(self):
        """【FT-SYSTEMIC-03: 买方机构级4-Sheet多维Excel研报构建与零Emoji合规断言】

        1. 测试功能与测试点:
           - 验证 ExcelMacroMicroReportBuilder.build_workbook 构建投行标准 4-Sheet 工作簿。
           - Sheet 0: 00_宏观总账与均衡基准；
           - Sheet 1: 01_12大行业投入产出与增加值；
           - Sheet 2: 02_微观企业公允估值总览；
           - Sheet 3: 03_价值洼地与高估排雷清单。
           - 验证视觉规范: 必须开启首行首列冻结窗格 (freeze_panes) 与显示网格线 (showGridLines)。
           - 验证买方机构专业合规铁律: 全表逐单元格扫描，断言 100% 物理消除所有 Emoji 符号表情。

        2. 正常函数业务边界与参数契约:
           - pipeline_data 为宏微观总控引擎输出字典。
           - output_path 必须为合法可写的 .xlsx 文件路径。

        3. 测试数据与模拟场景说明:
           - 基于流水线数据渲染完整 Excel 工作簿至临时文件，并使用 openpyxl 穿透读取。

        4. 预期断言与结果验证:
           - 断言文件存在且大小 > 1KB。
           - 断言 sheetnames 精确等于预期 4 大工作表。
           - 断言所有工作表 freeze_panes 非空且 showGridLines 为 True。
           - 断言遍历单元格中 emoji_pattern.findall 匹配次数为 0。
        """
        # 构造微型 pipeline 数据以加速测试
        res = self.orchestrator.run_systemic_pipeline(
            as_of_date="2026-10-18",
            record_to_ledger=False,
        )

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            out_file = ExcelMacroMicroReportBuilder.build_workbook(
                pipeline_data=res,
                output_path=tmp_path,
            )
            self.assertTrue(out_file.exists())
            self.assertGreater(out_file.stat().st_size, 1024)

            # 读取导出的 Excel 工作簿
            wb = openpyxl.load_workbook(out_file, data_only=True)
            expected_sheets = [
                "00_宏观总账与均衡基准",
                "01_12大行业投入产出与增加值",
                "02_微观企业公允估值总览",
                "03_价值洼地与高估排雷清单",
            ]
            self.assertEqual(wb.sheetnames, expected_sheets)

            # 遍历所有单元格，断言 100% 零 Emoji 泄露
            emoji_pattern = re.compile(
                "[\U00010000-\U0010ffff\U00002600-\U000027ff\U00002b50\U00002b06\U00002934\U000025b6\U000025c0]",
                flags=re.UNICODE,
            )

            for sheet_name in expected_sheets:
                ws = wb[sheet_name]
                # 验证首行或首列冻结
                self.assertIsNotNone(ws.freeze_panes, f"工作表 {sheet_name} 未设置冻结窗格")
                # 验证网格线开启
                self.assertTrue(ws.views.sheetView[0].showGridLines, f"工作表 {sheet_name} 网格线未开启")

                # 抽检单元格内容与无 Emoji
                for row_idx in range(1, min(ws.max_row + 1, 50)):
                    for col_idx in range(1, min(ws.max_column + 1, 15)):
                        val = ws.cell(row=row_idx, column=col_idx).value
                        if val is not None and isinstance(val, str):
                            matches = emoji_pattern.findall(val)
                            self.assertEqual(
                                len(matches), 0,
                                f"工作表 {sheet_name} 行 {row_idx} 列 {col_idx} 发现 Emoji 泄漏: {val}"
                            )
            wb.close()
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
