"""Google Drive 原生动态交互投研看板导出契约与功能测试用例集.

覆盖 Tab 1~Tab 5 工作表构建、实时行情公式、参数化动态 DCF 联动、密码学对账链条集成
以及 Google Drive 原生转换上传调度逻辑的全方位测试。
"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import openpyxl

from scripts.export_drive_interactive_sheet import (
    auto_fit_columns,
    build_macro_sheet,
    build_stock_cards_sheet,
    build_us_dcf_sheet,
    build_jp_dcf_sheet,
    build_ledger_sheet,
    generate_and_upload_living_sheet,
)
from scripts.test_support.fixtures import project_temp


class TestExportDriveInteractiveSheet(unittest.TestCase):
    """Google Drive 交互活体表格构建与导出单测套件."""

    def setUp(self):
        self.wb = openpyxl.Workbook()
        self.ws = self.wb.active

    def test_auto_fit_columns(self):
        """【UT-SHEET-01: 自适应列宽与文字截断防御】"""
        self.ws.cell(row=1, column=1, value="短文本")
        self.ws.cell(row=2, column=1, value="这是一段非常长的中文投研描述文字用于测试自适应列宽边界")
        auto_fit_columns(self.ws, min_width=12, max_width=45)
        width = self.ws.column_dimensions["A"].width
        self.assertGreaterEqual(width, 12)
        self.assertLessEqual(width, 45)

    def test_build_macro_sheet_structure(self):
        """【UT-SHEET-02: 构建 Tab 1 大盘研判与宏观风向工作表】"""
        build_macro_sheet(self.ws)
        self.assertEqual(self.ws.title, "大盘总报与宏观风向")
        # 验证顶栏大标题
        self.assertIn("全球宏观流动性", str(self.ws["A1"].value))
        # 验证宏观基准表
        self.assertEqual(self.ws.cell(row=5, column=1).value, "美股 (US Equities)")
        self.assertEqual(self.ws.cell(row=6, column=1).value, "日股 (JP Equities)")

    def test_build_stock_cards_sheet_structure(self):
        """【UT-SHEET-03: 构建 Tab 2 重点推荐个股卡片与实时行情公式】"""
        build_stock_cards_sheet(self.ws)
        self.assertEqual(self.ws.title, "重点推荐与三态目标价")
        # 验证包含股票行 (从第 5 行开始为数据行)
        tickers_found = []
        for r in range(5, 15):
            val = self.ws.cell(row=r, column=1).value
            if val:
                tickers_found.append(str(val))
        self.assertIn("RXRX", tickers_found)
        self.assertIn("NVDA", tickers_found)
        self.assertIn("8035", tickers_found)
        # 验证实时行情公式单元格 (第 5 行第 5 列为 RXRX 行情公式)
        rxrx_formula = self.ws.cell(row=5, column=5).value
        self.assertIn("GOOGLEFINANCE", str(rxrx_formula))

    def test_build_us_dcf_sheet_structure(self):
        """【UT-SHEET-04: 构建 Tab 3 美股动态情景 DCF 模型】"""
        build_us_dcf_sheet(self.ws)
        self.assertEqual(self.ws.title, "美股核心公司DCF模型")
        # 验证 NVDA 模型 1
        self.assertIn("英伟达", str(self.ws.cell(row=4, column=1).value))
        # 验证动态公式含有上涨空间计算
        form_cell = self.ws.cell(row=6, column=8).value
        self.assertIn("=(G6-$D$4)/$D$4", str(form_cell))

    def test_build_jp_dcf_sheet_structure(self):
        """【UT-SHEET-05: 构建 Tab 4 日股动态情景 DCF 模型】"""
        build_jp_dcf_sheet(self.ws)
        self.assertEqual(self.ws.title, "日股核心公司DCF模型")
        # 验证 东京电子 (TEL) 模型
        self.assertIn("东京电子", str(self.ws.cell(row=4, column=1).value))
        form_cell = self.ws.cell(row=6, column=8).value
        self.assertIn("=(G6-$D$4)/$D$4", str(form_cell))

    def test_build_ledger_sheet_structure(self):
        """【UT-SHEET-06: 构建 Tab 5 密码学对账底账工作表】"""
        temp_dir = project_temp(self, "test-ledger-sheet-")
        temp_db = temp_dir / "temp_ledger.db"
        from financial_core.engines.prediction_ledger import PredictionLedger
        temp_ledger = PredictionLedger(db_path=str(temp_db))
        with patch("scripts.export_drive_interactive_sheet.PredictionLedger", return_value=temp_ledger):
            build_ledger_sheet(self.ws)
        self.assertEqual(self.ws.title, "密码学审计链与决策存证")
        self.assertIn("Prediction Ledger", str(self.ws["A1"].value))
        status_text = self.ws.cell(row=3, column=1).value
        self.assertIn("账本状态", str(status_text))

    @patch("scripts.export_drive_interactive_sheet.get_gdrive_executable")
    @patch("scripts.export_drive_interactive_sheet.run_cmd")
    def test_generate_and_upload_living_sheet_mocked(self, mock_run_cmd, mock_get_gdrive):
        """【FT-SHEET-07: 全流程生成5-Tab活体工作簿与Google Drive原生转换Mock】"""
        temp_dir = project_temp(self, "test-living-sheet-")
        mock_get_gdrive.return_value = "fake_gdrive.exe"

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Created file (ID: 1a2b3c4d5e6f7g8h9i0j)"
        mock_proc.stderr = ""
        mock_run_cmd.return_value = mock_proc

        with patch("scripts.export_drive_interactive_sheet.Path.exists", return_value=True):
            result = generate_and_upload_living_sheet()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["file_id"], "1a2b3c4d5e6f7g8h9i0j")
        self.assertTrue(Path(result["local_path"]).exists())


if __name__ == "__main__":
    unittest.main()
