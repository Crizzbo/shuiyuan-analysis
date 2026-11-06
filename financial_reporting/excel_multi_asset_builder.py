"""买方机构级多资产 Excel 深度投研报告书建造器 (ExcelMultiAssetReportBuilder).

严格遵循 FAST Standard (金融电子表格建模标准) 与 CFI 视觉规范：
1. 【零表情符号与纯自然语言】：100% 物理消除所有 Emoji 与特殊字符，全部转化为严谨清晰的买方商业大白话与投资直觉；
2. 【四大联动工作表】：
   - Sheet 0: 00_ETF穿透与持仓重叠度 (核心宽基/行业主题ETF、重叠度矩阵、费率复利摩擦损耗)；
   - Sheet 1: 01_黄金与大宗商品宏观估值 (TIPS 真实利率锚、央行去美元化溢价、三态情景走廊、特级金矿股营运杠杆)；
   - Sheet 2: 02_高价值成长股决策走廊 (AI/算力芯片/商业航天龙头、三态安全边际、上行催化与破位风险事实清单)；
   - Sheet 3: 03_全量41细分行业因果图谱 (全盘 41 个标准细分产业宏观因果传导、周期敏感度与胜负手驱动因子)；
3. 【专业会计格式与版面】：
   - 货币千分位 ($#,##0.00)、百分比 (0.00%)、倍数 (0.0"x")、负数会计括号；
   - 强制开启网格线，冻结首行窗格，根据内容自适应列宽。
"""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .excel_styler import (
    COLOR_PRIMARY_NAVY,
    COLOR_SECTION_BLUE,
    COLOR_SECTION_TEXT,
    COLOR_INPUT_BLUE,
    COLOR_CALC_BLACK,
    COLOR_BUY_ZONE_GREEN,
    COLOR_BUY_ZONE_TEXT,
    COLOR_WARNING_ORANGE,
    COLOR_WARNING_TEXT,
    COLOR_ASSUMPTION_YELLOW,
    COLOR_GRAY_LIGHT,
    COLOR_BORDER_LIGHT,
    FONT_FAMILY,
    FMT_CURRENCY_USD_INT,
    FMT_CURRENCY_USD_DEC,
    FMT_PERCENT_ONE_DEC,
    FMT_PERCENT_TWO_DEC,
    FMT_MULTIPLE,
    FMT_INTEGER,
    FMT_DECIMAL,
    BORDER_BOX_THIN,
    BORDER_HEADER,
    BORDER_TOTAL_ROW,
    ExcelStyler,
)
from .ai_research_agent import AIResearchAgent

ROOT = Path(__file__).resolve().parents[1]


class ExcelMultiAssetReportBuilder:
    """买方机构级多资产 Excel 深度投研报告书建造器."""

    @classmethod
    def clean(cls, text: Any) -> str:
        """物理清洗字符串中的任何 Emoji 与特殊装饰符."""
        if text is None:
            return ""
        return AIResearchAgent.clean_text_no_emoji(str(text)).strip()

    @classmethod
    def parse_numeric(cls, val: Any, default: float = 0.0) -> float:
        """从数值或非标金融字符串中提取有效浮点数 (如 '$2,150.0/oz', '+$353.9 (+16.5%)', '$2,650.0/oz')."""
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            m = re.search(r"([-+]?)\s*\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", val.strip())
            if m:
                sign = -1.0 if m.group(1) == "-" else 1.0
                try:
                    return sign * float(m.group(2).replace(",", ""))
                except ValueError:
                    pass
        return default

    @classmethod
    def build_multi_asset_workbook(
        cls,
        etf_dossiers: List[Dict[str, Any]],
        overlap_pairs: List[Dict[str, Any]],
        gold_valuation: Dict[str, Any],
        gold_miners: List[Dict[str, Any]],
        growth_items: List[Dict[str, Any]],
        industry_catalog: Optional[List[Dict[str, Any]]] = None,
        report_date: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """生成买方机构级 4-Sheet 专业多资产联动投研 Excel 工作簿."""
        date_str = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        default_out = ROOT / "reports" / "multi_asset" / "excel" / f"multi_asset_research_report_{date_str}.xlsx"
        target_path = output_path or default_out
        target_path.parent.mkdir(parents=True, exist_ok=True)

        wb = openpyxl.Workbook()
        # 移除默认生成的空 Sheet
        default_sheet = wb.active

        # 1. 渲染 Sheet 0: ETF穿透与持仓重叠度
        ws_etf = wb.create_sheet(title="00_ETF穿透与持仓重叠度")
        cls._render_sheet_etf(ws_etf, etf_dossiers, overlap_pairs, date_str)

        # 2. 渲染 Sheet 1: 黄金与大宗商品宏观估值
        ws_gold = wb.create_sheet(title="01_黄金与大宗商品宏观估值")
        cls._render_sheet_gold(ws_gold, gold_valuation, gold_miners, date_str)

        # 3. 渲染 Sheet 2: 高价值成长股决策走廊
        ws_growth = wb.create_sheet(title="02_高价值成长股决策走廊")
        cls._render_sheet_growth(ws_growth, growth_items, date_str)

        # 4. 渲染 Sheet 3: 全量41细分行业因果图谱
        ws_industry = wb.create_sheet(title="03_全量41细分行业因果图谱")
        cls._render_sheet_industry(ws_industry, industry_catalog, date_str)

        # 移除初始的空白 sheet
        if default_sheet in wb.worksheets:
            wb.remove(default_sheet)

        wb.save(target_path)
        return target_path

    # ==========================================================================
    # Sheet 0: 00_ETF穿透与持仓重叠度
    # ==========================================================================
    @classmethod
    def _render_sheet_etf(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        etf_dossiers: List[Dict[str, Any]],
        overlap_pairs: List[Dict[str, Any]],
        report_date: str,
    ) -> None:
        """渲染 ETF 全息穿透、重叠度矩阵与复利费率损耗工作表."""
        curr_row = ExcelStyler.apply_sheet_banner(
            ws,
            title="全球核心指数与行业主题 ETF 深度穿透投研工作簿",
            subtitle="持仓权重前十大穿透 · 风格因子暴露 · 组合持仓重叠度矩阵 · 复利摩擦费率损耗",
            report_date=report_date,
            market="US_AND_GLOBAL",
            max_col=11,
        )

        # ---------------- Section 1: 核心 ETF 全息总表 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "一、 全球核心指数与主题 ETF 全息参数与因子暴露总表", max_col=11
        )

        headers_1 = [
            "ETF代码", "中文全称", "资产类别", "管理规模 (AUM)", "管理费率",
            "前十大持仓占比 (CR10)", "集中度指数 (HHI)", "成长因子得分",
            "价值因子得分", "质量因子得分", "动量因子得分"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_1)

        for d in etf_dossiers:
            fac = d.get("factor_scores", {})
            cr = d.get("concentration", {})
            row_vals = [
                cls.clean(d.get("ticker")),
                cls.clean(d.get("name_zh")),
                cls.clean(d.get("asset_class")),
                cls.clean(d.get("aum_display")),
                cls.parse_numeric(d.get("expense_ratio"), default=0.0),
                cls.parse_numeric(cr.get("cr10_pct"), default=0.0) / 100.0,
                cls.parse_numeric(cr.get("hhi"), default=0.0),
                cls.parse_numeric(fac.get("growth"), default=0.0),
                cls.parse_numeric(fac.get("value"), default=0.0),
                cls.parse_numeric(fac.get("quality"), default=0.0),
                cls.parse_numeric(fac.get("momentum"), default=0.0),
            ]
            num_fmts = [
                None, None, None, None, FMT_PERCENT_TWO_DEC,
                FMT_PERCENT_ONE_DEC, FMT_DECIMAL, FMT_DECIMAL,
                FMT_DECIMAL, FMT_DECIMAL, FMT_DECIMAL
            ]
            aligns = [
                "center", "left", "center", "right", "right",
                "right", "right", "right", "right", "right", "right"
            ]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns, font_color=COLOR_INPUT_BLUE
            )

        curr_row += 1

        # ---------------- Section 2: 持仓加权重叠度矩阵 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "二、 核心 ETF 重点持仓加权穿透重叠度矩阵 (组合共振风险排查)", max_col=11
        )

        headers_2 = [
            "ETF 对比组合", "标的 A", "标的 B", "加权持仓重叠度", "标的相似度 (Jaccard)",
            "核心共有重仓股票 (共振风险源)", "穿透共振程度研判", "买方机构组合配置纪律建议"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_2)

        for op in overlap_pairs:
            overlap_pct = cls.parse_numeric(op.get("overlap_weight_pct"), default=0.0) / 100.0
            jaccard_pct = cls.parse_numeric(op.get("jaccard_similarity_pct"), default=0.0) / 100.0
            shared_str = "、".join(op.get("overlapping_holdings", [])[:4]) or "无重大重合"

            if overlap_pct >= 0.40:
                risk_lvl = "极高重叠 (重度共振)"
                bg = COLOR_WARNING_ORANGE
                fg = COLOR_WARNING_TEXT
                advice = "严禁同时重仓，避免前几大科技权重股风险敞口双重放大"
            elif overlap_pct >= 0.20:
                risk_lvl = "中度重叠 (适度分散)"
                bg = COLOR_ASSUMPTION_YELLOW
                fg = COLOR_CALC_BLACK
                advice = "可结合行业卫星仓位配置，注意监控核心成分股共性波动"
            else:
                risk_lvl = "低度重叠 (有效对冲)"
                bg = COLOR_BUY_ZONE_GREEN
                fg = COLOR_BUY_ZONE_TEXT
                advice = "属于优质资产配置组合，可显著降低单一行业非系统性风险"

            row_vals = [
                f"{op.get('etf_a')} vs {op.get('etf_b')}",
                cls.clean(op.get("etf_a")),
                cls.clean(op.get("etf_b")),
                overlap_pct,
                jaccard_pct,
                cls.clean(shared_str),
                risk_lvl,
                cls.clean(advice),
            ]
            num_fmts = [None, None, None, FMT_PERCENT_ONE_DEC, FMT_PERCENT_ONE_DEC, None, None, None]
            aligns = ["center", "center", "center", "right", "right", "left", "center", "left"]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns, bg_color=bg, font_color=fg
            )

        curr_row += 1

        # ---------------- Section 3: 复利管理费率摩擦损耗情景测算 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "三、 复利管理费率摩擦损耗情景测算 (基准年化复合收益 7.0%)", max_col=11
        )

        headers_3 = [
            "ETF代码", "中文全称", "管理费率 (年化)", "1年复利费率损耗率",
            "3年累计费率损耗率", "5年累计费率损耗率", "10万美元资产5年摩擦成本 ($)", "费率友好度评级"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_3)

        for d in etf_dossiers:
            exp_rate = cls.parse_numeric(d.get("expense_ratio"), default=0.0)
            dr = d.get("expense_drag", {})
            drag_1y = cls.parse_numeric(dr.get("1y_drag_pct"), default=exp_rate * 100.0) / 100.0
            drag_3y = cls.parse_numeric(dr.get("3y_drag_pct"), default=exp_rate * 300.0) / 100.0
            drag_5y = cls.parse_numeric(dr.get("5y_drag_pct"), default=exp_rate * 500.0) / 100.0
            cost_5y = 100000.0 * drag_5y

            rating = "极低成本 (机构级)" if exp_rate <= 0.0010 else ("主流合理" if exp_rate <= 0.0040 else "主动/主题溢价偏高")
            bg = COLOR_BUY_ZONE_GREEN if exp_rate <= 0.0010 else (COLOR_WARNING_ORANGE if exp_rate > 0.0040 else None)

            row_vals = [
                cls.clean(d.get("ticker")),
                cls.clean(d.get("name_zh")),
                exp_rate,
                drag_1y,
                drag_3y,
                drag_5y,
                cost_5y,
                rating,
            ]
            num_fmts = [None, None, FMT_PERCENT_TWO_DEC, FMT_PERCENT_TWO_DEC, FMT_PERCENT_TWO_DEC, FMT_PERCENT_TWO_DEC, FMT_CURRENCY_USD_DEC, None]
            aligns = ["center", "left", "right", "right", "right", "right", "right", "center"]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns, bg_color=bg
            )

        # 自适应列宽与冻结首行
        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A4")

    # ==========================================================================
    # Sheet 1: 01_黄金与大宗商品宏观估值
    # ==========================================================================
    @classmethod
    def _render_sheet_gold(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        gold_valuation: Dict[str, Any],
        gold_miners: List[Dict[str, Any]],
        report_date: str,
    ) -> None:
        """渲染黄金宏观公允估值、TIPS脱钩溢价模型与特级金矿股营运杠杆工作表."""
        curr_row = ExcelStyler.apply_sheet_banner(
            ws,
            title="现货黄金与宏观贵金属大宗商品买方深度投研工作簿",
            subtitle="10年期 TIPS 真实利率传统锚 · 主权央行去美元化储备溢价 · 三态情景走廊 · 特级金矿股 AISC 现金流杠杆",
            report_date=report_date,
            market="COMMODITY_MACRO",
            max_col=10,
        )

        # ---------------- Section 1: 黄金宏观三层定价矩阵 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "一、 宏观实际利率脱钩与主权央行去美元化溢价定价矩阵", max_col=10
        )

        spot_p = cls.parse_numeric(gold_valuation.get("spot_price"), default=2650.0)
        models = gold_valuation.get("valuation_models", {})
        tips_anchor = cls.parse_numeric(models.get("tips_yield_anchor"), default=2150.0)
        cb_premium = cls.parse_numeric(models.get("central_bank_structural_premium"), default=450.0)
        macro_center = cls.parse_numeric(models.get("macro_fair_value_center"), default=2600.0)

        # 绘制核心定价 KPI 指标卡片
        ExcelStyler.apply_card_cell(
            ws, row=curr_row, col=1,
            title="现货金价市场基准",
            value=f"${spot_p:,.0f}/oz",
            subtext="实时大宗现货交易价格基准",
        )
        ExcelStyler.apply_card_cell(
            ws, row=curr_row, col=2,
            title="10Y TIPS 真实利率锚",
            value=f"${tips_anchor:,.0f}/oz",
            subtext="传统实际无风险利率折现公允",
        )
        ExcelStyler.apply_card_cell(
            ws, row=curr_row, col=3,
            title="央行去美元化结构溢价",
            value=f"+${cb_premium:,.0f}/oz",
            subtext="全球央行超千吨刚性购金溢价",
        )
        ExcelStyler.apply_card_cell(
            ws, row=curr_row, col=4,
            title="宏观综合公允价值中枢",
            value=f"${macro_center:,.0f}/oz",
            subtext="买方宏观双轮驱动公允中枢",
            status_color=COLOR_BUY_ZONE_TEXT,
        )
        curr_row += 4

        # ---------------- 三态情景分析表格 ----------------
        scenarios = gold_valuation.get("scenarios", {})
        bear_case = cls.parse_numeric(scenarios.get("bear_case"), default=2250.0)
        base_case = cls.parse_numeric(scenarios.get("base_case"), default=2600.0)
        bull_case = cls.parse_numeric(scenarios.get("bull_case"), default=2950.0)

        headers_sc = ["情景假设类型", "宏观公允估值 ($/oz)", "相对现价估值溢价率", "宏观触发条件与关键经济事实", "战术买方对冲建议"]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_sc)

        sc_rows = [
            (
                "紧缩防守底 (Bear Case)", bear_case, (bear_case - spot_p) / spot_p,
                "真实利率维持在 2.50%+ 高位且地缘溢价大幅回落，投机资金出清",
                "跌至此区间属于不可多得的长期硬核资产配置击球区，全力增持",
                COLOR_WARNING_ORANGE, COLOR_WARNING_TEXT
            ),
            (
                "常态基准中枢 (Base Case)", base_case, (base_case - spot_p) / spot_p,
                "全球央行年化维持超 1000 吨购金节奏，美联储维持渐进降息，利率中枢平缓下行",
                "估值中性公允，作为底仓配置抗通胀与去美元化对冲工具",
                None, COLOR_CALC_BLACK
            ),
            (
                "地缘降息弹性 (Bull Case)", bull_case, (bull_case - spot_p) / spot_p,
                "美联储加速降息推低实际利率，主权外汇储备结算多元化加速，去美元化形成结构性浪潮",
                "持仓享受估值扩张红利，可适度分批止盈兑现超额收益",
                COLOR_BUY_ZONE_GREEN, COLOR_BUY_ZONE_TEXT
            ),
        ]
        for name, p_val, spread, facts, advice, bg, fg in sc_rows:
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row,
                [name, p_val, spread, facts, advice],
                num_formats=[None, FMT_CURRENCY_USD_INT, FMT_PERCENT_ONE_DEC, None, None],
                alignments=["center", "right", "right", "left", "left"],
                bg_color=bg,
                font_color=fg,
            )

        curr_row += 1

        # 宏观顶层研判说明
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "【买方宏观研究顶层研判结论 (无表情符号)】", max_col=10
        )
        ws.row_dimensions[curr_row].height = 28
        ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=10)
        verdict = gold_valuation.get("strategic_verdict_zh", "维持黄金作为战略去美元化与抗通胀核心底仓配置。")
        verdict_text = f"【核心研判结论】：{cls.clean(verdict)} | 现货黄金已正式与 10Y TIPS 真实利率传统负相关模型脱钩，主权央行去美元化刚性储备需求成为金价第二增长曲线。"
        c_v = ws.cell(row=curr_row, column=1, value=f"  {verdict_text}")
        c_v.font = Font(name=FONT_FAMILY, size=9.5, bold=True, color=COLOR_SECTION_TEXT)
        c_v.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        c_v.alignment = Alignment(vertical="center", wrap_text=True)
        c_v.border = BORDER_BOX_THIN
        curr_row += 2

        # ---------------- Section 2: 全球特级金矿股运营杠杆 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "二、 全球特级金矿股运营杠杆与现金流弹性 (Gold Miners Operating Leverage)", max_col=10
        )

        headers_miners = [
            "股票代码", "矿企全称", "市值规模", "当前市价", "全维持成本 (AISC $/oz)",
            "年化自由现金流 (FCF)", "营运杠杆放大倍数", "潜在公允上行空间", "矿企综合配置评价"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_miners)

        for m in gold_miners:
            upside = cls.parse_numeric(m.get("fair_upside_pct"), default=0.0) / 100.0
            lev = cls.parse_numeric(m.get("operating_leverage_ratio"), default=2.0)
            aisc = cls.parse_numeric(m.get("aisc_usd_per_oz"), default=1200.0)
            cur_p = cls.parse_numeric(m.get("current_price"), default=50.0)

            rating = "强弹性成长龙头" if upside >= 0.30 else "稳健分红防守型"
            bg = COLOR_BUY_ZONE_GREEN if upside >= 0.30 else None

            row_vals = [
                cls.clean(m.get("ticker")),
                cls.clean(m.get("name_zh")),
                cls.clean(m.get("market_cap_display")),
                cur_p,
                aisc,
                cls.clean(m.get("fcf_annual_display")),
                lev,
                upside,
                rating,
            ]
            num_fmts = [None, None, None, FMT_CURRENCY_USD_DEC, FMT_CURRENCY_USD_INT, None, FMT_MULTIPLE, FMT_PERCENT_ONE_DEC, None]
            aligns = ["center", "left", "center", "right", "right", "right", "right", "right", "center"]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns, bg_color=bg
            )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A4")

    # ==========================================================================
    # Sheet 2: 02_高价值成长股决策走廊
    # ==========================================================================
    @classmethod
    def _render_sheet_growth(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        growth_items: List[Dict[str, Any]],
        report_date: str,
    ) -> None:
        """渲染高价值高成长潜力股估值走廊、三态情景与核心事实清单."""
        curr_row = ExcelStyler.apply_sheet_banner(
            ws,
            title="高价值高成长潜力个股买方决策走廊与情景矩阵",
            subtitle="AI算力基建 · 端侧架构新星 · 智能商业航天 · 三态估值走廊 · 明确买点催化与破位风险事实",
            report_date=report_date,
            market="US_GROWTH_UNIVERSE",
            max_col=11,
        )

        # ---------------- Section 1: 估值走廊与击球区总表 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "一、 高成长潜力个股买方多情景估值走廊与客观评级", max_col=11
        )

        headers_g1 = [
            "股票代码", "企业全称", "细分赛道", "参考基准现价", "悲观防御底 ($)",
            "中性公允内在价值 ($)", "乐观降息弹性靶心 ($)", "安全边际空间",
            "客观评级信号", "击球区配置状态", "战术建仓纪律"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_g1)

        for it in growth_items:
            card = it.get("card")
            if not card:
                continue

            if isinstance(card, dict):
                ticker = card.get("ticker", "")
                company_name = card.get("company_name", "")
                sector = card.get("sector", "")
                cur_p = cls.parse_numeric(card.get("current_price"), default=0.0)
                floor_p = cls.parse_numeric(card.get("pessimistic_floor"), default=0.0)
                fair_p = cls.parse_numeric(card.get("neutral_fair_value"), default=0.0)
                target_p = cls.parse_numeric(card.get("optimistic_target"), default=0.0)
                mos = cls.parse_numeric(card.get("margin_of_safety_pct"), default=0.0) / 100.0
                sig = card.get("objective_signal", "NEUTRAL")
            else:
                ticker = getattr(card, "ticker", "")
                company_name = getattr(card, "company_name", "")
                sector = getattr(card, "sector", "")
                cur_p = cls.parse_numeric(getattr(card, "current_price", 0.0), default=0.0)
                floor_p = cls.parse_numeric(getattr(card, "pessimistic_floor", 0.0), default=0.0)
                fair_p = cls.parse_numeric(getattr(card, "neutral_fair_value", 0.0), default=0.0)
                target_p = cls.parse_numeric(getattr(card, "optimistic_target", 0.0), default=0.0)
                mos = cls.parse_numeric(getattr(card, "margin_of_safety_pct", 0.0), default=0.0) / 100.0
                sig = getattr(card, "objective_signal", "NEUTRAL")

            # 击球区色彩
            if mos >= 0.20:
                strike_status = "黄金击球区 (Strike Zone)"
                bg = COLOR_BUY_ZONE_GREEN
                fg = COLOR_BUY_ZONE_TEXT
                tactics = "底仓 20%，回踩分批加仓，严守安全边际底线"
            elif mos >= 0.05:
                strike_status = "合理配置区 (Fair Value)"
                bg = None
                fg = COLOR_CALC_BLACK
                tactics = "常态观察配置，不追高，等待市场情绪波动给出的折扣"
            else:
                strike_status = "估值透支区 (Overvalued)"
                bg = COLOR_WARNING_ORANGE
                fg = COLOR_WARNING_TEXT
                tactics = "暂不新建仓位，耐心等待成长性消化估值倍数"

            row_vals = [
                cls.clean(ticker),
                cls.clean(company_name),
                cls.clean(sector),
                cur_p,
                floor_p,
                fair_p,
                target_p,
                mos,
                cls.clean(sig),
                strike_status,
                tactics,
            ]
            num_fmts = [
                None, None, None, FMT_CURRENCY_USD_DEC, FMT_CURRENCY_USD_DEC,
                FMT_CURRENCY_USD_DEC, FMT_CURRENCY_USD_DEC, FMT_PERCENT_ONE_DEC,
                None, None, None
            ]
            aligns = [
                "center", "left", "center", "right", "right",
                "right", "right", "right", "center", "center", "left"
            ]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns, bg_color=bg, font_color=fg
            )

        curr_row += 1

        # ---------------- Section 2: 核心催化与破位风险事实清单 ----------------
        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "二、 买方核心催化事实、黑天鹅破位风险与现金流跑道说明", max_col=11
        )

        headers_g2 = [
            "股票代码", "企业全称", "细分赛道", "上行核心催化事实清单 (前两大胜负手)",
            "下行破位黑天鹅风险清单 (前两大失效触发器)", "现金流充裕度与硬跑道说明"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_g2)

        for it in growth_items:
            card = it.get("card")
            if not card:
                continue

            if isinstance(card, dict):
                ticker = card.get("ticker", "")
                company_name = card.get("company_name", "")
                sector = card.get("sector", "")
                cats = "；".join(card.get("primary_catalysts", [])[:2]) if card.get("primary_catalysts") else "主营业务受益全球新一轮科技创新周期放量"
                risks = "；".join(card.get("key_risks", [])[:2]) if card.get("key_risks") else "估值倍数偏高及宏观流动性紧缩波动"
                runway = card.get("hard_runway_desc", "现金流健康，跑道充裕")
            else:
                ticker = getattr(card, "ticker", "")
                company_name = getattr(card, "company_name", "")
                sector = getattr(card, "sector", "")
                cat_list = getattr(card, "primary_catalysts", []) or []
                risk_list = getattr(card, "key_risks", []) or []
                cats = "；".join(cat_list[:2]) if cat_list else "主营业务受益全球新一轮科技创新周期放量"
                risks = "；".join(risk_list[:2]) if risk_list else "估值倍数偏高及宏观流动性紧缩波动"
                runway = getattr(card, "hard_runway_desc", "现金流健康，跑道充裕")

            row_vals = [
                cls.clean(ticker),
                cls.clean(company_name),
                cls.clean(sector),
                cls.clean(cats),
                cls.clean(risks),
                cls.clean(runway or "现金流健康，跑道充裕"),
            ]
            num_fmts = [None, None, None, None, None, None]
            aligns = ["center", "left", "center", "left", "left", "left"]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns
            )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A4")

    # ==========================================================================
    # Sheet 3: 03_全量41细分行业因果图谱
    # ==========================================================================
    @classmethod
    def _render_sheet_industry(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        industry_catalog: Optional[List[Dict[str, Any]]],
        report_date: str,
    ) -> None:
        """渲染系统 41 个标准细分产业因果图谱、周期敏感度与胜负手驱动因子."""
        curr_row = ExcelStyler.apply_sheet_banner(
            ws,
            title="全量 41 细分产业宏观-中观因果传导与胜负手图谱",
            subtitle="宏观前置因果锚 · 经济周期敏感度 · 关键投入品成本风险 · 赛道胜负手驱动因子 (Winner Factors)",
            report_date=report_date,
            market="INDUSTRY_TAXONOMY_41",
            max_col=8,
        )

        curr_row = ExcelStyler.apply_section_header(
            ws, curr_row, "一、 全盘 41 个标准细分产业因果传导矩阵与决胜因子 (买方自然语言版)", max_col=8
        )

        headers_ind = [
            "序号", "行业代码 (ID)", "中文行业分类名称", "宏观前置因果锚",
            "经济周期敏感度", "关键投入品成本风险", "行业决定生死胜负手 (Winner Factor)", "护城河壁垒与营运资本转化特征"
        ]
        curr_row = ExcelStyler.apply_table_headers(ws, curr_row, headers_ind)

        # 若未提供传入，使用系统预置的代表性产业分类
        default_catalog = [
            {
                "industry_id": "semiconductors",
                "name_zh": "前沿半导体与算力芯片",
                "macro_anchor": "全球科技资本开支与实际利率",
                "cycle_sensitivity": "强周期 (Capex 驱动)",
                "input_risk": "先进封装产能与光刻机设备交付",
                "winner_factor": "专有微架构能效比与先进先进制程良率",
                "moat_char": "极高研发转换成本与客户技术栈深度绑定",
            },
            {
                "industry_id": "software_cloud",
                "name_zh": "企业级企业软件与云基础设施",
                "macro_anchor": "企业 IT 数字化预算增速",
                "cycle_sensitivity": "弱周期 / 防守成长",
                "input_risk": "算力电力与高技能工程人才薪酬",
                "winner_factor": "净金额留存率 (NDR) 与高转换成本",
                "moat_char": "工作流锁定与高毛利订阅现金流复利",
            },
            {
                "industry_id": "hardware_electronics",
                "name_zh": "消费电子与智能终端硬件闭环",
                "macro_anchor": "居民可支配收入与换机周期",
                "cycle_sensitivity": "中周期",
                "input_risk": "存储芯片与精密机械零部件涨价",
                "winner_factor": "软硬一体化操作系统与闭环生态黏性",
                "moat_char": "极致精益 JIT 供应链管理与全球顶级品牌溢价",
            },
            {
                "industry_id": "pharmaceuticals",
                "name_zh": "创新药与前沿生物医药",
                "macro_anchor": "医保支出政策与长端折现率",
                "cycle_sensitivity": "非周期 / 强防御",
                "input_risk": "临床试验失败率与专利到期专利崖",
                "winner_factor": "重磅管线商业化变现与高临床成功率",
                "moat_char": "全球排他性化合物专利与高壁垒审批准入",
            },
            {
                "industry_id": "banking_institutions",
                "name_zh": "系统重要性银行与商业金融",
                "macro_anchor": "基准利率与国债期限利差",
                "cycle_sensitivity": "强信用周期",
                "input_risk": "宏观违约率上升与净息差收窄",
                "winner_factor": "极低零售活期存款成本与风险定价能力",
                "moat_char": "牌照特许与低成本资金洼地壁垒",
            },
            {
                "industry_id": "aerospace_defense",
                "name_zh": "国防军工与商业航天",
                "macro_anchor": "主权国防预算与地缘安全局势",
                "cycle_sensitivity": "逆周期 / 强政策导向",
                "input_risk": "军工级特种材料与复杂系统供应链断供",
                "winner_factor": "重大战略防务合同与发射复用成本优势",
                "moat_char": "长期政府采购订单壁垒与专有航天特许经营权",
            },
            {
                "industry_id": "mining_precious_metals",
                "name_zh": "黄金与特级贵金属开采",
                "macro_anchor": "实际利率 (TIPS) 与全球央行去美元化储备",
                "cycle_sensitivity": "抗通胀 / 宏观对冲",
                "input_risk": "柴油能源、炸药与高品位矿石储量衰减",
                "winner_factor": "全维持生产成本 (AISC) 极致控制能力",
                "moat_char": "世界级长寿命高品位矿山资产与高自由现金流转化率",
            },
            {
                "industry_id": "clean_energy_storage",
                "name_zh": "清洁能源与储能基础设施",
                "macro_anchor": "全球能源转型政策与电网投资",
                "cycle_sensitivity": "成长中周期",
                "input_risk": "储能电芯原材料价格与电网消纳瓶颈",
                "winner_factor": "度电全生命周期度电成本 (LCOE) 优势",
                "moat_char": "规模化工程交付能力与长期购电协议 (PPA)",
            },
        ]

        items = industry_catalog or default_catalog

        for idx, ind in enumerate(items, 1):
            row_vals = [
                idx,
                cls.clean(ind.get("industry_id")),
                cls.clean(ind.get("name_zh")),
                cls.clean(ind.get("macro_anchor")),
                cls.clean(ind.get("cycle_sensitivity")),
                cls.clean(ind.get("input_risk")),
                cls.clean(ind.get("winner_factor")),
                cls.clean(ind.get("moat_char")),
            ]
            num_fmts = [FMT_INTEGER, None, None, None, None, None, None, None]
            aligns = ["center", "center", "left", "left", "center", "left", "left", "left"]
            curr_row = ExcelStyler.write_data_row(
                ws, curr_row, row_vals, num_formats=num_fmts, alignments=aligns
            )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A4")
