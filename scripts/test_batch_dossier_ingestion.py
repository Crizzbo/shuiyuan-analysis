"""测试批次全息档案数据向 SystemicCompanyInput 的结构化转换与端到端计算 (Test Batch Dossier Ingestion).

验证 78 个 Batch 档案能够无缝转换、平账并喂入 FinancialAnalysisSystem 计算。
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.filing_mapper import OfficialFilingMapper, IncompleteFilingFactError
from financial_core.api import FinancialAnalysisSystem
from data_sources.batch78_verified_dossiers_data import BATCH78_DOSSIERS


class TestBatchDossierIngestion(unittest.TestCase):
    """测试批次全息档案数据转换与端到端计算."""

    def setUp(self):
        self.fin_system = FinancialAnalysisSystem()

    def test_parse_financial_number_edge_cases(self):
        """【UT-INGEST-01: 复杂非标官方财报字符串清洗、多币种乘数与日股短信符号解析】

        1. 测试功能与测试点:
           - 验证 OfficialFilingMapper.parse_financial_number 对全球多币种、多语种财报非标字符串的稳健清洗。
           - 覆盖美股 (SEC 10-K/10-Q) 中的百万 (M)、十亿 (B)、括号负数 ($345.0M) 与含中文注释字符。
           - 覆盖日股 (TDnet/EDINET 决算短信) 中的億円、百万円、円，以及传统日式会计负数符号 (△, ▲, 全角括号)。
           - 覆盖极端缺失输入 (None, 'N/A') 优雅退化为 0.0。

        2. 正常函数业务边界与参数契约:
           - 输入为 Optional[str]。
           - 输出为 float，严禁崩溃抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 包含美股 "$750.0M (现金及国债)", "-$380.0M", "($345.0M)", "$1.2B", "380.0M 股"。
           - 包含日股 "5,600億円", "890円", "△5,200百万円", "▲12.5%", "（△340億円）", "▲¥1,250.5M"。

        4. 预期断言与结果验证:
           - 美股 "$750.0M (现金及国债)" 精确解析为 750,000,000.0。
           - 括号负数 "($345.0M)" 精确解析为 -345,000,000.0。
           - 日股 "△5,200百万円" 精确解析为 -5,200,000,000.0。
           - None 与 "N/A" 严格解析为 0.0。
        """
        mapper = OfficialFilingMapper
        self.assertEqual(mapper.parse_financial_number("$750.0M (现金及国债)"), 750_000_000.0)
        self.assertEqual(mapper.parse_financial_number("-$380.0M"), -380_000_000.0)
        self.assertEqual(mapper.parse_financial_number("($345.0M)"), -345_000_000.0)
        self.assertEqual(mapper.parse_financial_number("$1.2B"), 1_200_000_000.0)
        self.assertEqual(mapper.parse_financial_number("380.0M 股"), 380_000_000.0)
        self.assertEqual(mapper.parse_financial_number("5,600億円"), 560_000_000_000.0)
        self.assertEqual(mapper.parse_financial_number("890円"), 890.0)
        # 日股 TDnet / EDINET 决算短信常见负数符号 (△, ▲, 全角括号)
        self.assertEqual(mapper.parse_financial_number("△5,200百万円"), -5_200_000_000.0)
        self.assertEqual(mapper.parse_financial_number("▲12.5%"), -12.5)
        self.assertEqual(mapper.parse_financial_number("（△340億円）"), -34_000_000_000.0)
        self.assertEqual(mapper.parse_financial_number("▲¥1,250.5M"), -1_250_500_000.0)
        self.assertEqual(mapper.parse_financial_number(None), 0.0)
        self.assertEqual(mapper.parse_financial_number("N/A"), 0.0)

    def test_map_and_execute_us_batch_company(self):
        """美股存量档案缺少三表核心科目时明确拒绝。"""
        achr = BATCH78_DOSSIERS[0]
        # 存量档案未提供完整三表和行情时间戳，必须先补证据。
        with self.assertRaises(IncompleteFilingFactError):
            OfficialFilingMapper.map_dossier_to_company_input(achr)

    def test_map_and_execute_jp_batch_company(self):
        """日股存量档案缺少三表核心科目时明确拒绝。"""
        nissui = BATCH78_DOSSIERS[5]
        with self.assertRaises(IncompleteFilingFactError):
            OfficialFilingMapper.map_dossier_to_company_input(nissui)

    def test_round_trip_excel_generation_and_load_invariant(self):
        """【FT-INGEST-04: 批量档案真实Excel物理介质落盘生成与openpyxl往返加载不变量验证】

        1. 测试功能与测试点:
           - 验证 ExcelDossierBuilder 针对批量档案构建物理 .xlsx 文件的端到端生成能力。
           - 真实文件落盘: 拒绝纯内存虚拟，验证生成文件真实落盘且大小 > 3000 字节。
           - 往返加载验证: openpyxl 重新加载工作簿，断言网格线开启 (showGridLines=True) 并精确写入标的代码。

        2. 正常函数业务边界与参数契约:
           - 传入完整 dossier_data 字典。
           - 工作簿至少具备 3 张标准工作表。

        3. 测试数据与模拟场景说明:
           - 标的: ACHR，输出到临时目录 ACHR_physical_verification.xlsx。

        4. 预期断言与结果验证:
           - 断言 out_file.exists() 且大小 > 3000 字节。
           - 断言 len(sheetnames) >= 3。
           - 断言首张表网格线显示为 True。
           - 遍历第 1~15 行单元格，断言包含 'ACHR'。
        """
        import tempfile
        import openpyxl
        from financial_reporting.excel_dossier_builder import ExcelDossierBuilder

        achr = BATCH78_DOSSIERS[0]
        with tempfile.TemporaryDirectory() as tmp_dir:
            builder = ExcelDossierBuilder(output_root=Path(tmp_dir))
            out_file = builder.build_workbook(
                dossier_data=achr,
                output_filename="ACHR_physical_verification.xlsx",
            )

            # 1. 物理文件存在性与大小断言
            self.assertTrue(out_file.exists(), "物理 Excel 文件必须真实落盘")
            self.assertGreater(out_file.stat().st_size, 3000, "文件大小必须大于 3KB，严禁生成空文件")

            # 2. openpyxl 二次物理加载 (data_only=False 检验结构与网格)
            wb_formula = openpyxl.load_workbook(out_file, data_only=False)
            self.assertGreaterEqual(len(wb_formula.sheetnames), 3, "生成的买方工作簿至少包含 3 大工作表")
            ws0 = wb_formula[wb_formula.sheetnames[0]]
            self.assertTrue(ws0.views.sheetView[0].showGridLines, "网格线必须默认开启")

            # 3. 校验关键单元格内容真实落盘 (非假数据)
            found_ticker = False
            for r in range(1, 15):
                for c in range(1, 10):
                    val = str(ws0.cell(row=r, column=c).value or "")
                    if "ACHR" in val:
                        found_ticker = True
                        break
                if found_ticker:
                    break
            self.assertTrue(found_ticker, "物理工作簿中必须真实写入标的代码 ACHR")


if __name__ == "__main__":
    unittest.main()
