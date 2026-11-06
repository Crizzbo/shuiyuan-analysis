"""买方机构级 Excel 投研样式与排版引擎 (Institutional Excel Styler).

严格遵循 FAST Standard (金融分析电子表格规范) 与 CFI / Wall Street Prep 财务建模视觉准则:
1. 【字体与层级】：主表头 14pt 加粗，分节小标题 11pt 加粗，数据单元格 10pt，统一使用微软雅黑/Aptos;
2. 【严格色彩语法 (Color Coding)】：
   - 深蓝字 (#002060): 历史客观事实与外部输入 (Hardcoded Inputs);
   - 纯黑字 (#000000): 表内动态公式与派生计算 (Formulas & Calculations);
   - 翠绿字 (#008000): 跨工作表引用 (Cross-Sheet Links);
   - 淡黄底 (#FFF2CC): 核心敏感度开关与估值假设 (Assumptions / Toggles);
   - 浅绿底 (#E2EFDA): 击球区/低估买点高亮 (Value Buy Zone);
   - 浅橙/浅红底 (#FCE4D6): 平账报警或破产高危警示 (Warning / Distress);
   - 深蓝底白字 (#1F4E79 / #FFFFFF): 机构经典主标头与表格列头;
   - 浅蓝底 (#DDEBF7): 分类小标题栏;
3. 【会计格式与负数表达】：货币与数字必须使用千分位，负数强制使用会计括号 ($#,##0);
4. 【版面体验】：强制开启工作表网格线 (showGridLines=True)，设置冻结窗格与自适应列宽。
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# 1. 买方标准调色板 (Color Palette)
# ==============================================================================
COLOR_PRIMARY_NAVY = "1F4E79"       # 主题深蓝
COLOR_WHITE = "FFFFFF"              # 纯白
COLOR_SECTION_BLUE = "DDEBF7"       # 次级小标题浅蓝
COLOR_SECTION_TEXT = "1F4E79"       # 次级标题文字深蓝
COLOR_INPUT_BLUE = "002060"         # CFI 输入深蓝 (Hardcoded Input)
COLOR_CALC_BLACK = "000000"         # 公式计算纯黑
COLOR_LINK_GREEN = "008000"         # 跨表链接绿
COLOR_ASSUMPTION_YELLOW = "FFF2CC"  # 核心假设可调节淡黄底
COLOR_BUY_ZONE_GREEN = "E2EFDA"     # 价值洼地/击球区柔和浅绿
COLOR_BUY_ZONE_TEXT = "276A3C"      # 击球区文字深绿
COLOR_WARNING_ORANGE = "FCE4D6"     # 平账报警/预警柔和浅橙
COLOR_WARNING_TEXT = "C00000"       # 预警深红
COLOR_GRAY_LIGHT = "F2F2F2"         # 合计行灰底
COLOR_BORDER_LIGHT = "D9D9D9"       # 细浅灰边框
COLOR_BORDER_NAVY = "1F4E79"        # 深蓝主边框

# 字体家族
FONT_FAMILY = "Microsoft YaHei"

# ==============================================================================
# 2. 会计与金融数字格式 (Number Formats)
# ==============================================================================
FMT_CURRENCY_USD_INT = '$#,##0;($#,##0);"-"'
FMT_CURRENCY_USD_DEC = '$#,##0.00;($#,##0.00);"-"'
FMT_CURRENCY_JPY_INT = '¥#,##0;(¥#,##0);"-"'
FMT_PERCENT_ONE_DEC = '0.0%'
FMT_PERCENT_TWO_DEC = '0.00%'
FMT_MULTIPLE = '0.0"x"'
FMT_INTEGER = '#,##0;(#,##0);"-"'
FMT_DECIMAL = '#,##0.00;(#,##0.00);"-"'
FMT_DATE = 'YYYY-MM-DD'
FMT_TEXT = '@'

# ==============================================================================
# 3. 边框预设
# ==============================================================================
BORDER_THIN_BOTTOM = Border(bottom=Side(style="thin", color=COLOR_BORDER_LIGHT))
BORDER_BOX_THIN = Border(
    left=Side(style="thin", color=COLOR_BORDER_LIGHT),
    right=Side(style="thin", color=COLOR_BORDER_LIGHT),
    top=Side(style="thin", color=COLOR_BORDER_LIGHT),
    bottom=Side(style="thin", color=COLOR_BORDER_LIGHT),
)
BORDER_HEADER = Border(
    left=Side(style="thin", color=COLOR_PRIMARY_NAVY),
    right=Side(style="thin", color=COLOR_PRIMARY_NAVY),
    top=Side(style="medium", color=COLOR_PRIMARY_NAVY),
    bottom=Side(style="medium", color=COLOR_PRIMARY_NAVY),
)
BORDER_TOTAL_ROW = Border(
    top=Side(style="thin", color=COLOR_PRIMARY_NAVY),
    bottom=Side(style="double", color=COLOR_PRIMARY_NAVY),
)


class ExcelStyler:
    """买方级专业 Excel 排版与样式工具类."""

    @classmethod
    def apply_sheet_banner(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        title: str,
        subtitle: str,
        report_date: str,
        market: str = "US",
        right_badge: Optional[str] = None,
        max_col: int = 10,
    ) -> int:
        """在工作表顶部创建标准的买方机构级双行主表头横幅 (Banner).

        Returns:
            int: 下一个可用的数据起始行号 (通常为 4 或 5).
        """
        # 保证网格线开启
        ws.views.sheetView[0].showGridLines = True

        # 第 1 行：主标题与报告属性
        ws.row_dimensions[1].height = 28
        title_cell = ws.cell(row=1, column=1, value=f"  {title}")
        title_cell.font = Font(name=FONT_FAMILY, size=14, bold=True, color=COLOR_WHITE)
        title_cell.fill = PatternFill(start_color=COLOR_PRIMARY_NAVY, end_color=COLOR_PRIMARY_NAVY, fill_type="solid")
        title_cell.alignment = Alignment(vertical="center")

        badge_text = right_badge or f"市场: {market} | 报告基准: {report_date}"
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col - 2)

        # 填充主标头合并区域其余单元格背景
        for col in range(2, max_col - 1):
            cell = ws.cell(row=1, column=col)
            cell.fill = PatternFill(start_color=COLOR_PRIMARY_NAVY, end_color=COLOR_PRIMARY_NAVY, fill_type="solid")

        # 右侧元信息单元格
        ws.merge_cells(start_row=1, start_column=max_col - 1, end_row=1, end_column=max_col)
        info_cell = ws.cell(row=1, column=max_col - 1, value=badge_text)
        info_cell.font = Font(name=FONT_FAMILY, size=9.5, bold=True, color="DDEBF7")
        info_cell.fill = PatternFill(start_color=COLOR_PRIMARY_NAVY, end_color=COLOR_PRIMARY_NAVY, fill_type="solid")
        info_cell.alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(row=1, column=max_col).fill = PatternFill(start_color=COLOR_PRIMARY_NAVY, end_color=COLOR_PRIMARY_NAVY, fill_type="solid")

        # 第 2 行：副标题与规范徽标
        ws.row_dimensions[2].height = 18
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
        sub_cell = ws.cell(row=2, column=1, value=f"  {subtitle} | 机构契约: FAST Standard & CFI Model Rigor")
        sub_cell.font = Font(name=FONT_FAMILY, size=9, italic=True, color="4A5568")
        sub_cell.fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
        sub_cell.alignment = Alignment(vertical="center")

        # 第 3 行为呼吸空行
        ws.row_dimensions[3].height = 8

        return 4

    @classmethod
    def apply_section_header(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        row: int,
        title: str,
        max_col: int = 10,
    ) -> int:
        """渲染大分类模块的浅蓝小标题栏 (Section Subheader)."""
        ws.row_dimensions[row].height = 22
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max_col)
        cell = ws.cell(row=row, column=1, value=f"  {title}")
        cell.font = Font(name=FONT_FAMILY, size=11, bold=True, color=COLOR_SECTION_TEXT)
        cell.fill = PatternFill(start_color=COLOR_SECTION_BLUE, end_color=COLOR_SECTION_BLUE, fill_type="solid")
        cell.alignment = Alignment(vertical="center")
        cell.border = Border(
            top=Side(style="thin", color=COLOR_PRIMARY_NAVY),
            bottom=Side(style="thin", color=COLOR_PRIMARY_NAVY),
        )
        return row + 1

    @classmethod
    def apply_table_headers(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        row: int,
        headers: List[str],
        start_col: int = 1,
    ) -> int:
        """渲染数据表格的深蓝加粗列头栏."""
        ws.row_dimensions[row].height = 22
        for idx, h in enumerate(headers):
            c = ws.cell(row=row, column=start_col + idx, value=h)
            c.font = Font(name=FONT_FAMILY, size=10, bold=True, color=COLOR_WHITE)
            c.fill = PatternFill(start_color=COLOR_PRIMARY_NAVY, end_color=COLOR_PRIMARY_NAVY, fill_type="solid")
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDER_HEADER
        return row + 1

    @classmethod
    def write_data_row(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        row: int,
        values: List[Any],
        start_col: int = 1,
        num_formats: Optional[List[Optional[str]]] = None,
        alignments: Optional[List[str]] = None,
        is_bold: bool = False,
        font_color: str = COLOR_CALC_BLACK,
        bg_color: Optional[str] = None,
        border: Optional[Border] = BORDER_BOX_THIN,
    ) -> int:
        """写入单行数据，精准控制买方色彩编码、千分位与对齐."""
        ws.row_dimensions[row].height = 19
        for idx, val in enumerate(values):
            col = start_col + idx
            c = ws.cell(row=row, column=col, value=val)

            # 字体与色彩
            c.font = Font(name=FONT_FAMILY, size=9.5, bold=is_bold, color=font_color)

            # 数字格式
            if num_formats and idx < len(num_formats) and num_formats[idx]:
                c.number_format = num_formats[idx]

            # 背景底色
            if bg_color:
                c.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")

            # 对齐方式
            align_h = "left"
            if alignments and idx < len(alignments):
                align_h = alignments[idx]
            elif isinstance(val, (int, float)):
                align_h = "right"
            elif isinstance(val, str) and (val.startswith("=") or len(val) <= 10):
                align_h = "center"

            c.alignment = Alignment(horizontal=align_h, vertical="center")

            # 边框
            if border:
                c.border = border

        return row + 1

    @classmethod
    def apply_card_cell(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        row: int,
        col: int,
        title: str,
        value: str,
        subtext: str = "",
        status_color: Optional[str] = None,
    ):
        """在指定网格绘制一个买方指标卡片 (Metric Tile)."""
        c_title = ws.cell(row=row, column=col, value=title)
        c_title.font = Font(name=FONT_FAMILY, size=8.5, color="718096", bold=True)
        c_title.alignment = Alignment(horizontal="center", vertical="center")

        c_val = ws.cell(row=row + 1, column=col, value=value)
        val_color = status_color or COLOR_PRIMARY_NAVY
        c_val.font = Font(name=FONT_FAMILY, size=13, bold=True, color=val_color)
        c_val.alignment = Alignment(horizontal="center", vertical="center")

        c_sub = ws.cell(row=row + 2, column=col, value=subtext)
        c_sub.font = Font(name=FONT_FAMILY, size=8, color="A0AEC0", italic=True)
        c_sub.alignment = Alignment(horizontal="center", vertical="center")

        # 边框包裹
        fill_bg = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for r in range(row, row + 3):
            cell = ws.cell(row=r, column=col)
            cell.fill = fill_bg
            cell.border = BORDER_BOX_THIN

    @classmethod
    def auto_fit_columns_and_freeze(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        freeze_cell: str = "A5",
        min_width: int = 12,
        max_width: int = 45,
    ):
        """自动调整列宽至最佳视觉宽度，并冻结表头窗格 (Freeze Panes)."""
        ws.freeze_panes = freeze_cell
        ws.views.sheetView[0].showGridLines = True

        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                val = cell.value
                if val is not None:
                    # 避免长标题或公式破坏列宽
                    val_str = str(val)
                    if not val_str.startswith("=") and len(val_str) < 60:
                        # 区分中英文字符宽度
                        width = sum(2 if ord(char) > 127 else 1 for char in val_str)
                        if width > max_len:
                            max_len = width
            fitted_width = max(min_width, min(max_len + 3, max_width))
            ws.column_dimensions[col_letter].width = fitted_width
