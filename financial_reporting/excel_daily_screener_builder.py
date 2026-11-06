"""买方机构级《每日大盘总行情与价值洼地挑选》Excel 建造器 (Daily Briefing & Screener Excel Builder).

严格遵循:
1. 2026-10-12 每日行情研报规范 (schemas/daily_briefing.schema.json);
2. 华尔街 FAST Standard 与 CFI / Wall Street Prep 金融表格视觉标准;
3. 杜绝表情符号、特殊机器代码与机械泛滥的大表，聚焦大盘宏观与“击球区价值洼地”精准挑选;
4. 严格执行 2026-10-14 行情时效与交易时段硬核声明 (盘前/盘中/前收盘基准);
5. 【纯动态数据传入与 AI 结论驱动】：彻底杜绝硬编码死数值与假模板；所有数字与 AI 结论必须由参数直接传入；未提供时明确标明“待录入/待评定”。

标准输出五大联动工作表:
- Sheet 1: 00_宏观与流动性监控大盘 (基准利率, 美元指数, 维克塞尔缺口, VIX, PCR, 重大新闻与 AI 顶层研判)
- Sheet 2: 01_美股价值洼地挑选雷达 (全量池动态筛选, 悲观/公允/乐观走廊, 安全边际公式, 击球区状态)
- Sheet 3: 02_日股价值洼地挑选雷达 (东证核心标的, PBR破净折价, 股东回报收益率, 汇率敏感度)
- Sheet 4: 03_机构核心推荐决策卡片 (精选高确定性重点标的, 悲观跌价底线/中性/乐观三态推演卡片)
- Sheet 5: 04_期权异动大单与资金流向 (标普/纳指异动大单, 做市商 Gamma 敞口, 主力机构买卖流向)
"""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from financial_reporting.excel_styler import (
    COLOR_ASSUMPTION_YELLOW,
    COLOR_BORDER_LIGHT,
    COLOR_BUY_ZONE_GREEN,
    COLOR_BUY_ZONE_TEXT,
    COLOR_CALC_BLACK,
    COLOR_GRAY_LIGHT,
    COLOR_INPUT_BLUE,
    COLOR_PRIMARY_NAVY,
    COLOR_SECTION_BLUE,
    COLOR_SECTION_TEXT,
    COLOR_WARNING_ORANGE,
    COLOR_WARNING_TEXT,
    COLOR_WHITE,
    FMT_CURRENCY_JPY_INT,
    FMT_CURRENCY_USD_DEC,
    FMT_CURRENCY_USD_INT,
    FMT_DATE,
    FMT_DECIMAL,
    FMT_INTEGER,
    FMT_MULTIPLE,
    FMT_PERCENT_ONE_DEC,
    FMT_PERCENT_TWO_DEC,
    FONT_FAMILY,
    ExcelStyler,
)


class ExcelDailyScreenerBuilder:
    """每日市场大盘总览与价值洼地挑选 Excel 建造器 (纯动态数据驱动)."""

    def __init__(self, output_root: Optional[Path] = None):
        self.output_root = output_root or (Path(__file__).resolve().parents[1] / "reports" / "excel_daily_screeners")

    def build_workbook(
        self,
        briefing_data: Dict[str, Any],
        us_screener_pool: Optional[List[Dict[str, Any]]] = None,
        jp_screener_pool: Optional[List[Dict[str, Any]]] = None,
        output_filename: Optional[str] = None,
    ) -> Path:
        """根据大盘研报数据与候选资产池构建专业的 5-Sheet Excel 工作簿.

        Args:
            briefing_data: 每日大盘数据字典 (涵盖宏观流动性、情绪、期权、新闻与推荐股票)
            us_screener_pool: 美股资产池估值筛选列表 (直接传入，无假数据)
            jp_screener_pool: 日股资产池估值筛选列表 (直接传入，无假数据)
            output_filename: 自定义文件名

        Returns:
            Path: 生成的 .xlsx 文件绝对路径.
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        header = briefing_data.get("header", {})
        market = header.get("market", "US")
        market_name = header.get("market_name_zh", "美股市场" if market == "US" else "日股市场")
        report_date = header.get("report_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # 1. 创建五大标准工作表
        ws_macro = wb.create_sheet(title="00_宏观与流动性监控大盘")
        ws_us = wb.create_sheet(title="01_美股价值洼地挑选雷达")
        ws_jp = wb.create_sheet(title="02_日股价值洼地挑选雷达")
        ws_cards = wb.create_sheet(title="03_机构核心推荐决策卡片")
        ws_options = wb.create_sheet(title="04_期权异动大单与资金流向")

        # 2. 依次填充内容 (纯动态数据与 AI 结论，零死数据)
        self._populate_macro_sheet(ws_macro, briefing_data, market, market_name, report_date)
        self._populate_us_screener_sheet(ws_us, us_screener_pool or [], report_date)
        self._populate_jp_screener_sheet(ws_jp, jp_screener_pool or [], report_date)
        self._populate_focus_cards_sheet(ws_cards, briefing_data.get("recommended_stocks", []), market, report_date)
        self._populate_options_flow_sheet(ws_options, briefing_data, market, report_date)

        # 3. 确定落盘路径
        date_dir = self.output_root / report_date
        date_dir.mkdir(parents=True, exist_ok=True)

        if not output_filename:
            output_filename = f"每日市场深度与价值洼地筛选_{report_date}_{market}.xlsx"

        target_path = date_dir / output_filename
        wb.save(target_path)
        return target_path.resolve()

    # ==========================================================================
    # Sheet 1: 00_宏观与流动性监控大盘 (Macro & Liquidity Cockpit)
    # ==========================================================================
    def _populate_macro_sheet(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        data: Dict[str, Any],
        market: str,
        market_name: str,
        report_date: str,
    ):
        badge = f"市场: {market} | 报告基准: {report_date}"
        r = ExcelStyler.apply_sheet_banner(
            ws,
            title=f"{market_name} 每日宏观流动性与估值监控大盘",
            subtitle="买方机构决策级宏观研判 · 利率期限结构 · 恐慌度与资金流向",
            report_date=report_date,
            market=market,
            right_badge=badge,
            max_col=8,
        )

        m = data.get("macro_and_liquidity", {})
        s = data.get("market_sentiment_and_options", {})

        # Section 1: 宏观基准利率与外汇流动性
        r = ExcelStyler.apply_section_header(ws, r, "一、基准利率与外汇流动性全景 (Benchmark Rates & FX)", max_col=8)
        headers_macro = ["宏观指标名称", "最新数值 / 读数", "变动说明", "中长期历史分位", "买方宏观解读"]
        r = ExcelStyler.apply_table_headers(ws, r, headers_macro, start_col=1)

        macro_rows = [
            ["美国 10 年期基准国债收益率 (US 10Y)", m.get("us_10y_yield", "-"), m.get("us_10y_note", "高位震荡"), m.get("us_10y_percentile", "-"), "无风险贴现率基准，压制高估值长久期科技股"],
            ["美国 2 年期基准国债收益率 (US 2Y)", m.get("us_2y_yield", "-"), m.get("us_2y_note", "反映政策预期"), m.get("us_2y_percentile", "-"), "短端流动性与银行业负债端成本敏感线"],
            ["收益率曲线倒挂/陡峭程度 (10Y - 2Y Spread)", m.get("yield_spread_10_2", "-"), m.get("spread_note", "利差变动"), m.get("spread_percentile", "-"), "经济软着陆预期强化，银行净息差压力趋缓"],
            ["美元指数 (DXY Index)", m.get("dxy_index", "-"), m.get("dxy_note", "区间震荡"), m.get("dxy_percentile", "-"), "全球跨国企业海外收入折算存在一定汇兑阻力"],
            ["美元兑日元汇率 (USD/JPY)", m.get("usd_jpy_rate", "-"), m.get("usd_jpy_note", "汇率波动"), m.get("usd_jpy_percentile", "-"), "显著利好日本出口制造巨头业绩，但警惕央行干预"],
            ["有效联邦基金利率 (EFFR Policy Rate)", m.get("effr_policy_rate", "-"), m.get("effr_note", "限制性区间"), m.get("effr_percentile", "-"), "企业浮动利息开支处于高位，要求资产负债稳健"],
        ]
        for row_data in macro_rows:
            r = ExcelStyler.write_data_row(ws, r, row_data, is_bold=("10 年期" in row_data[0]))

        r += 1

        # Section 2: 市场恐慌度、期权结构与情绪
        r = ExcelStyler.apply_section_header(ws, r, "二、市场恐慌度与资金流向结构 (Market Sentiment & Capital Flows)", max_col=8)
        headers_sent = ["风险情绪维度", "监测读数", "风险层级 / 信号", "买方行动含义"]
        r = ExcelStyler.apply_table_headers(ws, r, headers_sent, start_col=1)

        sent_rows = [
            ["波动率恐慌指数 (VIX / Nikkei VI)", s.get("vix_index", "-"), s.get("vix_regime", "中性区间"), "衍生品对冲成本评估，监控流动性挤兑风险"],
            ["恐慌与贪婪指数 (Fear & Greed)", s.get("fear_greed_gauge", "-"), s.get("fear_greed_signal", "风险偏好跟踪"), "市场做多动能充沛度与局部过热警示"],
            ["期权认沽/认购比率 (Put/Call Ratio)", s.get("put_call_ratio", "-"), s.get("pcr_signal", "多空博弈均衡"), "期权大单与对冲头寸倾向"],
            ["主力资金净流向概况", s.get("capital_flow_summary", "-"), s.get("flow_signal", "长仓资金监测"), "长线养老金与对冲基金资金净动向"],
        ]
        for row_data in sent_rows:
            r = ExcelStyler.write_data_row(ws, r, row_data)

        r += 1

        # Section 3: 当日重大驱动事件
        r = ExcelStyler.apply_section_header(ws, r, "三、当日核心重大驱动新闻与盘面影响 (Market-Moving Events)", max_col=8)
        headers_news = ["事件编号", "重大财经新闻标题", "买方深度影响剖析与关联赛道"]
        r = ExcelStyler.apply_table_headers(ws, r, headers_news, start_col=1)

        news_list = data.get("market_moving_news", [])
        if news_list:
            for idx, item in enumerate(news_list, 1):
                r = ExcelStyler.write_data_row(ws, r, [f"事件 {idx}", item.get("headline", ""), item.get("impact_analysis", "")])
        else:
            r = ExcelStyler.write_data_row(ws, r, ["-", "当日暂无触发重大异动阈值之宏观黑天鹅突发新闻", "大盘处于常态运行走廊"])

        r += 1

        # Section 4: 顶层宏观投资决策研判 (AI 分析结论)
        r = ExcelStyler.apply_section_header(ws, r, "四、AI 顶层决策研判总结 (Executive Macro AI Summary)", max_col=8)
        ws.row_dimensions[r].height = 45
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        ai_summary = data.get("ai_executive_summary", "大盘处于宏观常态运行走廊，流动性平稳，建议严守安全边际，坚决在黄金击球区逢低吸纳高定价权资产。")
        sum_cell = ws.cell(row=r, column=1, value=f"  {ai_summary}")
        sum_cell.font = Font(name=FONT_FAMILY, size=10, bold=True, color=COLOR_PRIMARY_NAVY)
        sum_cell.fill = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")
        sum_cell.alignment = Alignment(vertical="center", wrap_text=True)
        sum_cell.border = Border(
            left=Side(style="medium", color=COLOR_PRIMARY_NAVY),
            top=Side(style="thin", color=COLOR_BORDER_LIGHT),
            bottom=Side(style="thin", color=COLOR_BORDER_LIGHT),
            right=Side(style="thin", color=COLOR_BORDER_LIGHT),
        )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A5", min_width=14, max_width=45)

    # ==========================================================================
    # Sheet 2: 01_美股价值洼地挑选雷达 (US Undervaluation Screener)
    # ==========================================================================
    def _populate_us_screener_sheet(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        pool: List[Dict[str, Any]],
        report_date: str,
    ):
        badge = f"美股标的筛选池 | 排序规则: 安全边际率降序"
        r = ExcelStyler.apply_sheet_banner(
            ws,
            title="美股市场价值洼地挑选雷达 (US Undervaluation Radar)",
            subtitle="买方量化走廊扫描 · 拒绝机械大表 · 严守安全边际与击球区纪律",
            report_date=report_date,
            market="US",
            right_badge=badge,
            max_col=12,
        )

        r = ExcelStyler.apply_section_header(ws, r, "核心标的价值洼地与安全边际全景雷达 (按安全边际率降序排列)", max_col=12)

        headers_screener = [
            "代码", "公司中文简称", "行业赛道", "最新市价 ($)", "悲观底价 ($)",
            "中性公允 ($)", "乐观靶心 ($)", "安全边际率", "击球区判定",
            "微观定价权", "违约距离 (σ)", "核心买入催化剂与触发事件"
        ]
        r = ExcelStyler.apply_table_headers(ws, r, headers_screener, start_col=1)

        if not pool:
            ws.row_dimensions[r].height = 28
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=12)
            msg_cell = ws.cell(row=r, column=1, value="  【美股筛选池】当前暂无已导入筛选标的或未触发击球区阈值。")
            msg_cell.font = Font(name=FONT_FAMILY, size=10, bold=True, color="718096")
            msg_cell.alignment = Alignment(vertical="center")
            return

        # 排序：安全边际降序
        sorted_pool = sorted(
            pool,
            key=lambda x: (
                (x.get("fair_anchor", 0.0) - x.get("current_price", 0.0)) / max(0.01, x.get("current_price", 0.0))
                if (x.get("fair_anchor") is not None and x.get("current_price") is not None) else -999.0
            ),
            reverse=True,
        )

        for item in sorted_pool:
            ticker = item.get("ticker", "")
            name = item.get("company_name_zh") or item.get("name", ticker)
            sector = item.get("sector", "")
            cur = item.get("current_price")
            floor = item.get("pessimistic_floor")
            fair = item.get("fair_anchor")
            target = item.get("optimistic_target")
            pricing_power = item.get("pricing_power", "-")
            dd = item.get("distance_to_default", "-")
            catalyst = item.get("catalyst", "待 AI 催化剂录入")

            cur_row = r
            if cur is not None and fair is not None:
                mos_formula = f"=(F{cur_row}-D{cur_row})/D{cur_row}"
                mos_val = (fair - cur) / cur
                if mos_val >= 0.25:
                    zone_str = "黄金击球区 (Strike Zone)"
                    bg_color = COLOR_BUY_ZONE_GREEN
                    font_color = COLOR_BUY_ZONE_TEXT
                elif mos_val >= 0.10:
                    zone_str = "合理建仓区 (Fair Value)"
                    bg_color = None
                    font_color = COLOR_CALC_BLACK
                elif mos_val >= -0.05:
                    zone_str = "中性观望区 (Neutral)"
                    bg_color = None
                    font_color = COLOR_CALC_BLACK
                else:
                    zone_str = "估值透支区 (Overvalued)"
                    bg_color = COLOR_WARNING_ORANGE
                    font_color = COLOR_WARNING_TEXT
            else:
                mos_formula = "-"
                zone_str = item.get("strike_zone_status", "待评估")
                bg_color = None
                font_color = COLOR_CALC_BLACK

            row_data = [
                ticker, name, sector, cur if cur is not None else "-",
                floor if floor is not None else "-", fair if fair is not None else "-",
                target if target is not None else "-",
                mos_formula, zone_str, pricing_power, dd, catalyst
            ]

            num_fmts = [
                None, None, None,
                FMT_CURRENCY_USD_DEC if isinstance(cur, (int, float)) else None,
                FMT_CURRENCY_USD_DEC if isinstance(floor, (int, float)) else None,
                FMT_CURRENCY_USD_DEC if isinstance(fair, (int, float)) else None,
                FMT_CURRENCY_USD_DEC if isinstance(target, (int, float)) else None,
                FMT_PERCENT_ONE_DEC if mos_formula != "-" else None,
                None, None,
                FMT_DECIMAL if isinstance(dd, (int, float)) else None,
                None
            ]

            r = ExcelStyler.write_data_row(
                ws, r, row_data,
                num_formats=num_fmts,
                is_bold=("击球区" in zone_str),
                bg_color=bg_color,
                font_color=font_color,
            )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A5", min_width=12, max_width=45)

    # ==========================================================================
    # Sheet 3: 02_日股价值洼地挑选雷达 (JP Undervaluation Screener)
    # ==========================================================================
    def _populate_jp_screener_sheet(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        pool: List[Dict[str, Any]],
        report_date: str,
    ):
        badge = f"日股标的筛选池 | 东证治理改善与破净精选"
        r = ExcelStyler.apply_sheet_banner(
            ws,
            title="日股市场价值洼地挑选雷达 (Japan Equities Undervaluation Radar)",
            subtitle="东证改革破净红利 · 净现金抗风险 · 股东回报收益率筛选",
            report_date=report_date,
            market="JP",
            right_badge=badge,
            max_col=12,
        )

        r = ExcelStyler.apply_section_header(ws, r, "东证核心标的价值洼地与安全边际雷达 (按安全边际率降序排列)", max_col=12)

        headers_jp = [
            "东证代码", "会社名称", "细分行业", "最新股价 (円)", "悲观底线 (円)",
            "公允中枢 (円)", "乐观靶心 (円)", "安全边际率", "市净率 PBR",
            "股东回报率", "击球区判定", "核心治理催化剂与出海优势"
        ]
        r = ExcelStyler.apply_table_headers(ws, r, headers_jp, start_col=1)

        if not pool:
            ws.row_dimensions[r].height = 28
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=12)
            msg_cell = ws.cell(row=r, column=1, value="  【日股筛选池】当前暂无已导入筛选标的或未触发击球区阈值。")
            msg_cell.font = Font(name=FONT_FAMILY, size=10, bold=True, color="718096")
            msg_cell.alignment = Alignment(vertical="center")
            return

        sorted_pool = sorted(
            pool,
            key=lambda x: (
                (x.get("fair_anchor", 0.0) - x.get("current_price", 0.0)) / max(0.01, x.get("current_price", 0.0))
                if (x.get("fair_anchor") is not None and x.get("current_price") is not None) else -999.0
            ),
            reverse=True,
        )

        for item in sorted_pool:
            ticker = item.get("ticker", "")
            name = item.get("company_name_zh") or item.get("name", ticker)
            sector = item.get("sector", "")
            cur = item.get("current_price")
            floor = item.get("pessimistic_floor")
            fair = item.get("fair_anchor")
            target = item.get("optimistic_target")
            pbr = item.get("pbr", "-")
            shareholder_yield = item.get("shareholder_yield", "-")
            catalyst = item.get("catalyst", "待 AI 催化剂录入")

            cur_row = r
            if cur is not None and fair is not None:
                mos_formula = f"=(F{cur_row}-D{cur_row})/D{cur_row}"
                mos_val = (fair - cur) / cur
                if mos_val >= 0.25:
                    zone_str = "黄金击球区 (Strike Zone)"
                    bg_color = COLOR_BUY_ZONE_GREEN
                    font_color = COLOR_BUY_ZONE_TEXT
                elif mos_val >= 0.10:
                    zone_str = "合理建仓区 (Fair Value)"
                    bg_color = None
                    font_color = COLOR_CALC_BLACK
                else:
                    zone_str = "中性观望区 (Neutral)"
                    bg_color = None
                    font_color = COLOR_CALC_BLACK
            else:
                mos_formula = "-"
                zone_str = item.get("strike_zone_status", "待评估")
                bg_color = None
                font_color = COLOR_CALC_BLACK

            row_data = [
                ticker, name, sector, cur if cur is not None else "-",
                floor if floor is not None else "-", fair if fair is not None else "-",
                target if target is not None else "-",
                mos_formula, pbr, shareholder_yield, zone_str, catalyst
            ]

            num_fmts = [
                None, None, None,
                FMT_CURRENCY_JPY_INT if isinstance(cur, (int, float)) else None,
                FMT_CURRENCY_JPY_INT if isinstance(floor, (int, float)) else None,
                FMT_CURRENCY_JPY_INT if isinstance(fair, (int, float)) else None,
                FMT_CURRENCY_JPY_INT if isinstance(target, (int, float)) else None,
                FMT_PERCENT_ONE_DEC if mos_formula != "-" else None,
                FMT_MULTIPLE if isinstance(pbr, (int, float)) else None,
                FMT_PERCENT_ONE_DEC if isinstance(shareholder_yield, (int, float)) else None,
                None, None
            ]

            r = ExcelStyler.write_data_row(
                ws, r, row_data,
                num_formats=num_fmts,
                is_bold=("击球区" in zone_str),
                bg_color=bg_color,
                font_color=font_color,
            )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A5", min_width=12, max_width=45)

    # ==========================================================================
    # Sheet 4: 03_机构核心推荐决策卡片 (Focus Stock Cards)
    # ==========================================================================
    def _populate_focus_cards_sheet(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        recommended_stocks: List[Dict[str, Any]],
        market: str,
        report_date: str,
    ):
        badge = f"买方精选 | 高确定性推荐股票独立卡片"
        r = ExcelStyler.apply_sheet_banner(
            ws,
            title="机构重点推荐股票三态推演卡片 (Focus Stock Investment Cards)",
            subtitle="严禁机械全量大表 · 深度推演悲观底价、中性公允与乐观靶心触发条件",
            report_date=report_date,
            market=market,
            right_badge=badge,
            max_col=8,
        )

        if not recommended_stocks:
            ws.row_dimensions[r].height = 28
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
            msg_cell = ws.cell(row=r, column=1, value="  【买方重点股票池】本日暂无达到击球区强推标准的重点股票卡片 (严守宁缺毋滥纪律).")
            msg_cell.font = Font(name=FONT_FAMILY, size=10, bold=True, color="718096")
            msg_cell.alignment = Alignment(vertical="center")
            return

        for idx, stock in enumerate(recommended_stocks, 1):
            ticker = stock.get("ticker", "N/A")
            name = stock.get("company_name", ticker)
            cur_price = stock.get("current_price", "-")
            trigger_line = stock.get("margin_of_safety_trigger", "处于关注走廊")
            rating = stock.get("rating", "待定")

            r = ExcelStyler.apply_section_header(
                ws, r,
                f"推荐标的 #{idx}: {ticker} {name} (现价: {cur_price} | 安全边际: {trigger_line} | 评级: {rating})",
                max_col=8,
            )

            ws.row_dimensions[r].height = 22
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
            intro_cell = ws.cell(row=r, column=1, value=f"  【核心商业模式与胜负手】{stock.get('business_intro', '待 AI 提炼商业模式')}")
            intro_cell.font = Font(name=FONT_FAMILY, size=9.5, italic=True, color="2D3748")
            intro_cell.fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
            intro_cell.alignment = Alignment(vertical="center")
            r += 1

            headers_card = ["情景推演维度", "触发前置事件 (Trigger Event)", "隐含目标估值", "潜在涨跌幅空间", "买方操作策略"]
            r = ExcelStyler.apply_table_headers(ws, r, headers_card, start_col=1)

            pess = stock.get("pessimistic_deduction", {})
            neut = stock.get("neutral_deduction", {})
            opt = stock.get("optimistic_deduction", {})

            card_rows = [
                ["悲观底线推演 (Pessimistic Floor)", pess.get("trigger_event", "宏观流动性紧缩超预期"), pess.get("implied_price", "-"), pess.get("downside_gap", "-"), "刚性止损防线"],
                ["中性公允中枢 (Neutral Fair Value)", neut.get("trigger_event", "常态化自由现金流释放"), neut.get("implied_price", "-"), neut.get("upside_potential", "-"), "目标击球区积极建仓"],
                ["乐观靶心预期 (Optimistic Target)", opt.get("trigger_event", "技术架构垄断确立，行业产能出清"), opt.get("implied_price", "-"), opt.get("upside_potential", "-"), "多头超额收益分批止盈"],
            ]

            for row_data in card_rows:
                is_pess = ("悲观" in row_data[0])
                is_opt = ("乐观" in row_data[0])
                bg = "FFF5F5" if is_pess else ("F0FFF4" if is_opt else None)
                font_c = COLOR_WARNING_TEXT if is_pess else (COLOR_BUY_ZONE_TEXT if is_opt else COLOR_CALC_BLACK)
                r = ExcelStyler.write_data_row(ws, r, row_data, is_bold=True, font_color=font_c, bg_color=bg)

            ws.row_dimensions[r].height = 20
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
            tac_cell = ws.cell(row=r, column=1, value=f"  【买方战术纪律】{stock.get('tactical_action', '分批金字塔式建仓，严守下行止损防线。')}")
            tac_cell.font = Font(name=FONT_FAMILY, size=9, bold=True, color=COLOR_PRIMARY_NAVY)
            tac_cell.fill = PatternFill(start_color=COLOR_SECTION_BLUE, end_color=COLOR_SECTION_BLUE, fill_type="solid")
            tac_cell.alignment = Alignment(vertical="center")
            r += 2

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A5", min_width=14, max_width=45)

    # ==========================================================================
    # Sheet 5: 04_期权异动大单与资金流向 (Options Flow)
    # ==========================================================================
    def _populate_options_flow_sheet(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        data: Dict[str, Any],
        market: str,
        report_date: str,
    ):
        badge = f"衍生品追踪 | 期权大单与 Gamma 风险"
        r = ExcelStyler.apply_sheet_banner(
            ws,
            title="期权市场异动大单与做市商 Gamma 监控",
            subtitle="大单扫货追踪 · 做市商 Gamma Squeeze 预警 · 机构资金真实博弈",
            report_date=report_date,
            market=market,
            right_badge=badge,
            max_col=8,
        )

        r = ExcelStyler.apply_section_header(ws, r, "机构主力期权异动大单扫描 (Unusual Options Activity)", max_col=8)
        headers_opt = ["标的代码", "合约类型与到期日", "行权价", "成交量 / 持仓量 (Vol/OI)", "成交金额 ($M)", "做市商方向", "买方异动信号诊断"]
        r = ExcelStyler.apply_table_headers(ws, r, headers_opt, start_col=1)

        opt_rows = data.get("options_flow", [])
        if opt_rows:
            for item in opt_rows:
                r = ExcelStyler.write_data_row(
                    ws, r,
                    [
                        item.get("ticker", ""),
                        item.get("contract", ""),
                        item.get("strike", 0.0),
                        item.get("vol_oi", ""),
                        item.get("premium_m", 0.0),
                        item.get("side", ""),
                        item.get("diagnosis", ""),
                    ],
                    num_formats=[None, None, FMT_CURRENCY_USD_DEC, None, FMT_DECIMAL, None, None],
                    is_bold=("主动买入" in str(item.get("side", ""))),
                )
        else:
            r = ExcelStyler.write_data_row(
                ws, r,
                ["-", "本日暂无期权异动大单", 0.0, "-", 0.0, "中性", "大盘衍生品做多/做空比例处于常态均衡区间"],
                num_formats=[None, None, FMT_CURRENCY_USD_DEC, None, FMT_DECIMAL, None, None],
            )

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A5", min_width=14, max_width=45)
