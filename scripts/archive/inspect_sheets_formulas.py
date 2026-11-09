"""全盘检查与核实 Excel/Google Sheets 活体表格公式 (inspect_sheets_formulas.py)."""

import sys
from pathlib import Path
import openpyxl

if len(sys.argv) > 1:
    target_xlsx = Path(sys.argv[1])
else:
    target_xlsx = Path(__file__).resolve().parents[1] / "reports" / "interactive_dossiers" / "NVDA_英伟达_深度分析活体交互模型.xlsx"

if not target_xlsx.exists():
    print(f"目标文件不存在: {target_xlsx}")
else:
    wb = openpyxl.load_workbook(target_xlsx, data_only=False)
    print(f"打开工作簿: {target_xlsx.name}")
    for s_name in wb.sheetnames:
        ws = wb[s_name]
        print(f"\n==========================================")
        print(f"[工作表] (Tab): {s_name}")
        print(f"==========================================")
        count = 0
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                cell = ws.cell(row=r, column=c)
                v = str(cell.value or "")
                if v.startswith("="):
                    count += 1
                    print(f"  [{cell.coordinate}] 原生公式: {v}")
        if count == 0:
            print("  (该标签页暂无动态公式)")
