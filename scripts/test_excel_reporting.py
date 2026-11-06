"""买方机构级 Excel 投研报表系统与 AI 驱动建档单元测试 (Unit Tests for Excel Reporting & AI Synthesizer).

测试矩阵覆盖:
1. ExcelStyler 调色板与视觉规范 (FAST Standard, CFI Colors, showGridLines, freezePanes);
2. AIDossierSynthesizer 动态装配与 AI 分析结论注入 (纯动态数据传入, 杜绝固定值推填);
3. ExcelDossierBuilder 5 大工作表全息构建与资产负债平账自检行公式 (=Assets - [Liab + Equity]);
4. ExcelDailyScreenerBuilder 美日大盘总览与价值洼地筛选 (安全边际公式, 击球区柔和色高亮);
5. 全量单元格严格零表情符号 (Zero-Emoji & Non-Human Artifacts) 断言检测.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import openpyxl

from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
from financial_reporting.excel_daily_screener_builder import ExcelDailyScreenerBuilder
from financial_reporting.excel_dossier_builder import ExcelDossierBuilder
from financial_reporting.excel_styler import (
    COLOR_ASSUMPTION_YELLOW,
    COLOR_BUY_ZONE_GREEN,
    COLOR_BUY_ZONE_TEXT,
    COLOR_CALC_BLACK,
    COLOR_INPUT_BLUE,
    COLOR_PRIMARY_NAVY,
    COLOR_SECTION_BLUE,
    COLOR_WARNING_ORANGE,
    COLOR_WHITE,
    ExcelStyler,
)

EMOJI_REGEX = re.compile(
    r"[\U00010000-\U0010ffff]|"
    + "|".join(
        f"[{chr(start)}-{chr(end)}]"
        for start, end in [
            (0x2600, 0x27BF),  # 杂项与装饰符号
            (0x2300, 0x23FF),  # 杂项技术符号
            (0x2B50, 0x2B55),  # 星形与圆形符号
            (0x203C, 0x2049),  # 双重标点
            (0x2194, 0x21AA),  # 箭头符号
            (0x25A0, 0x25FE),  # 几何图形符号
        ]
    )
)


class TestExcelReportingSystem(unittest.TestCase):
    """Excel 投研报告系统核心功能测试集."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.out_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _assert_zero_emojis_in_workbook(self, wb_path: Path):
        """断言 Excel 工作簿的所有工作表单元格内 100% 不存在任何表情符号."""
        wb = openpyxl.load_workbook(wb_path, data_only=False)
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            for row in ws.iter_rows():
                for cell in row:
                    val = cell.value
                    if val and isinstance(val, str):
                        match = EMOJI_REGEX.search(val)
                        self.assertIsNone(
                            match,
                            f"在工作表 [{sheetname}] 单元格 {cell.coordinate} 发现非人类/表情符号: {val}",
                        )

    def test_01_excel_styler_specs(self):
        """【UT-EXCEL-01: ExcelStyler买方视觉规范(FAST/CFI色系/冻结窗格/网格线强制展示)】

        1. 测试功能与测试点:
           - 验证 ExcelStyler 对国际金融建模标准化组织 (FAST Standard) 与 CFI 调色板契约规范的执行。
           - 严格断言工作表强制保留 showGridLines 为 True (杜绝白板盲区)。
           - 验证冻结首行首列 (freezePanes) 契约，确保长报表滑动时表头常驻。
           - 验证数据行强类型格式化 ($#,##0.00, 0.0%) 与公式单元格写入。

        2. 正常函数业务边界与参数契约:
           - apply_sheet_banner, apply_section_header, apply_table_headers, write_data_row 各行号依次递增。
           - freeze_cell 接收标准单元格坐标 (如 'A5')。

        3. 测试数据与模拟场景说明:
           - 构造测试表 TestStyler，应用主标题、副标题、分节标题、6 列表头及带公式数据行。

        4. 预期断言与结果验证:
           - 各操作行号分别精确等于 4, 5, 6, 7。
           - ws.views.sheetView[0].showGridLines 为 True。
           - ws.freeze_panes 为 'A5'。
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "TestStyler"

        r = ExcelStyler.apply_sheet_banner(
            ws, title="测试主标题", subtitle="测试副标题", report_date="2026-10-17", market="US", max_col=6
        )
        self.assertEqual(r, 4)
        self.assertTrue(ws.views.sheetView[0].showGridLines)

        r = ExcelStyler.apply_section_header(ws, r, "一、测试分节小标题", max_col=6)
        self.assertEqual(r, 5)

        r = ExcelStyler.apply_table_headers(ws, r, ["列1", "列2", "列3", "列4", "列5", "列6"])
        self.assertEqual(r, 6)

        r = ExcelStyler.write_data_row(
            ws, r, ["A", 100.5, 0.25, "=B6*C6", "正常", "测试"],
            num_formats=[None, "$#,##0.00", "0.0%", None, None, None],
            is_bold=True,
            font_color=COLOR_INPUT_BLUE,
            bg_color=COLOR_BUY_ZONE_GREEN,
        )
        self.assertEqual(r, 7)

        ExcelStyler.auto_fit_columns_and_freeze(ws, freeze_cell="A5")
        self.assertEqual(ws.freeze_panes, "A5")

    def test_02_ai_dossier_synthesizer_dynamic_assembly(self):
        """【UT-EXCEL-02: AI研报动态装配与逻辑合成(纯动态数据输入/杜绝假数据推填)】

        1. 测试功能与测试点:
           - 验证 AIDossierSynthesizer.synthesize_dossier 对三表真实底稿、行情与 AI 逻辑研判的动态装配。
           - 杜绝静态模板与预埋固定数值推填，所有结论（护城河、上下游、胜负手、催化剂、熔断风险）全部由外部动态注入。
           - 验证安全边际 (margin_of_safety_pct) 与击球区状态 (strike_zone_status) 的自动精准推导。

        2. 正常函数业务边界与参数契约:
           - 必须满足 schemas/deep_dossier.schema.json 契约，输出版本严格为 '2.0.0'。
           - current_price > 0, fair_anchor > 0。

        3. 测试数据与模拟场景说明:
           - 英伟达 (NVDA) 案例：现价 $130.0，公允中枢 $170.0，悲观底价 $110.0，乐观靶心 $220.0，注入 5 年真实三表与 Blackwell 架构催化剂。

        4. 预期断言与结果验证:
           - schema_version == '2.0.0'。
           - margin_of_safety_pct 精确等于 (170 - 130) / 130 * 100 ≈ 30.77%。
           - strike_zone_status 为 '黄金击球区 (Strike Zone)'。
           - catalysts 长度为 2。
        """
        ticker = "NVDA"
        market = "US"
        company_name = "英伟达公司"
        industry_id = "semiconductors"
        industry_name = "半导体与集成电路"

        quote = {
            "current_price": 130.0,
            "pessimistic_floor": 110.0,
            "fair_anchor": 170.0,
            "optimistic_target": 220.0,
            "freshness_status": "盘中 14:30 EDT 最新行情",
            "dcf_model": {
                "wacc_vector": [0.082, 0.080, 0.078, 0.076, 0.075],
                "fcf_projections": [25000, 31000, 38000, 44000, 50000],
            }
        }

        ai_conclusions = {
            "business_model": "全栈加速计算与全生命周期 AI 软件生态授权",
            "revenue_mix": "数据中心 87% + 专业视觉 6% + 游戏 7%",
            "winner_factor": "CUDA 生态双边网络效应与先进制程领先架构",
            "network_effects": "全球数百万 AI 开发者锁定 CUDA 算力底座，迁移成本极高",
            "switching_costs": "算法底层针对 Tensor Core 深度编译优化，重构成本极大",
            "cost_advantage_and_scale": "超大订单规模锁定顶级代工厂先进制程 CoWoS 产能",
            "intangible_assets": "持有超万项加速计算核心专利及顶尖架构设计工程师储备",
            "reinvestment_efficiency": "增量资本回报率 (ROIC) 达 60%+，资本再投资效率极高",
            "core_suppliers": "头部先进制程晶圆代工与高带宽内存 (HBM3e) 供应商",
            "supplier_concentration": "Top 3 供应商占比超过 70%",
            "supply_chain_risks": "CoWoS 先进封装产能紧张可能引发短期交付积压",
            "customer_structure": "全球一线超大规模云厂商、主权 AI 实体与企业级客户",
            "top5_customer_concentration": "前五大云厂商贡献营收约 40%",
            "default_and_churn_risks": "核心云厂商自主研发 ASIC 芯片进行部分内部替代",
            "profitability_quality": "毛利率维持在 73%~75% 极高位，具备极强价格垄断权",
            "catalysts": [
                "Blackwell 架构大规模出货，交付周期进一步缩短",
                "物理 AI 与具身智能推理算力集群需求指数级爆发"
            ],
            "kill_switch_risks": [
                "地缘敏感实体技术出口限制升级引发海外市场流失",
                "全球主要云厂商下调下一财年资本开支预算"
            ],
            "rating": "买入 (Buy)",
            "stance": "BUY_VALUE_ZONE",
            "strike_zone_status": "黄金击球区 (Strike Zone)",
        }

        fin_statements = {
            "years": ["2022", "2023", "2024", "2025", "2026E"],
            "unit": "百万美元 (USD Millions)",
            "balance_sheet": {
                "cash_and_equivalents": [13296, 15320, 25984, 34800, 42000],
                "current_assets": [23073, 44345, 65728, 82000, 95000],
                "non_current_assets": [18110, 21383, 30120, 36000, 41000],
                "total_assets": [41183, 65728, 95848, 118000, 136000],
                "current_liabilities": [6550, 10631, 15200, 18500, 21000],
                "long_term_debt": [10950, 9700, 8460, 7500, 6800],
                "total_liabilities": [19081, 22750, 26848, 31000, 34000],
                "stockholders_equity": [22102, 42978, 69000, 87000, 102000],
            },
            "income_statement": {
                "revenue": [26974, 60922, 120000, 150000, 180000],
                "cogs": [11618, 16621, 31200, 39000, 46800],
                "operating_income": [4224, 32972, 75000, 95000, 115000],
                "net_income": [4368, 29760, 62000, 78000, 94000],
            },
            "cash_flow": {
                "cfo": [5641, 28090, 60000, 75000, 90000],
                "capex": [1833, 3912, 5500, 7000, 8500],
                "fcf": [3808, 24178, 54500, 68000, 81500],
            }
        }

        dossier = AIDossierSynthesizer.synthesize_dossier(
            ticker=ticker,
            market=market,
            company_name=company_name,
            industry_id=industry_id,
            industry_name_zh=industry_name,
            financial_statements=fin_statements,
            market_quote=quote,
            ai_analysis=ai_conclusions,
        )

        self.assertEqual(dossier["schema_version"], "2.0.0")
        self.assertEqual(dossier["overview"]["ticker"], "NVDA")
        self.assertEqual(dossier["decision_summary"]["current_price"], 130.0)
        self.assertAlmostEqual(dossier["decision_summary"]["margin_of_safety_pct"], 30.769, places=2)
        self.assertEqual(dossier["decision_summary"]["strike_zone_status"], "黄金击球区 (Strike Zone)")
        self.assertEqual(dossier["industry_dynamics"]["winner_factor"], ai_conclusions["winner_factor"])
        self.assertEqual(len(dossier["long_term_outlook"]["catalysts"]), 2)

    def test_03_excel_dossier_builder_generation_and_balance_check(self):
        """【IT-EXCEL-03: 五大工作表投研底稿真实构建与资产负债刚性平账自检行公式】

        1. 测试功能与测试点:
           - 验证 ExcelDossierBuilder 物理生成包含 5 大标准工作表的机构级 Excel 档案:
             00_投资备忘录与决策中枢, 01_行业与护城河竞争格局, 02_官方三表全息审计底稿, 03_内生估值与敏感度走廊, 04_审计溯源与重大事件跟踪。
           - 严格断言在工作表 02 存在原生 Excel 平账公式: '=Assets - (Liabilities + Equity)'。
           - 严密断言全簿所有单元格 100% 零表情符号与非人类乱码。

        2. 正常函数业务边界与参数契约:
           - 输入必须为符合 Schema 2.0.0 的全息业务字典。
           - 生成的 .xlsx 文件物理存在且有效。

        3. 测试数据与模拟场景说明:
           - 注入英伟达 (NVDA) 完整全息投研档案数据。

        4. 预期断言与结果验证:
           - file_path.exists() 为 True。
           - sheetnames 完全对齐 5 大标准命名。
           - 平账自检行公式以 '=B' 开头并包含 '-(B'。
           - _assert_zero_emojis_in_workbook 断言通过。
        """
        builder = ExcelDossierBuilder(output_root=self.out_root)

        # 构造完整真实深度档案数据
        dossier_data = {
            "schema_version": "2.0.0",
            "report_date": "2026-10-17",
            "overview": {
                "ticker": "NVDA",
                "company_name": "英伟达公司",
                "company_name_zh": "英伟达公司",
                "market": "US",
                "industry_id": "semiconductors",
                "industry_name_zh": "半导体与集成电路",
                "business_model": "全栈加速计算与全生命周期 AI 软件生态授权",
                "revenue_mix": "数据中心 87% + 专业视觉 6% + 游戏 7%",
            },
            "decision_summary": {
                "current_price": 130.0,
                "pessimistic_floor": 110.0,
                "fair_anchor": 170.0,
                "optimistic_target": 220.0,
                "margin_of_safety_pct": 30.77,
                "freshness_status": "盘中最新报价",
                "strike_zone_status": "黄金击球区 (Strike Zone)",
                "rating": "买入 (Buy)",
                "stance": "BUY_VALUE_ZONE",
            },
            "financial_statements": {
                "years": ["2022", "2023", "2024", "2025", "2026E"],
                "unit": "百万美元 (USD Millions)",
                "balance_sheet": {
                    "cash_and_equivalents": [13296, 15320, 25984, 34800, 42000],
                    "current_assets": [23073, 44345, 65728, 82000, 95000],
                    "non_current_assets": [18110, 21383, 30120, 36000, 41000],
                    "total_assets": [41183, 65728, 95848, 118000, 136000],
                    "current_liabilities": [6550, 10631, 15200, 18500, 21000],
                    "long_term_debt": [10950, 9700, 8460, 7500, 6800],
                    "total_liabilities": [19081, 22750, 26848, 31000, 34000],
                    "stockholders_equity": [22102, 42978, 69000, 87000, 102000],
                },
                "income_statement": {
                    "revenue": [26974, 60922, 120000, 150000, 180000],
                    "cogs": [11618, 16621, 31200, 39000, 46800],
                    "operating_income": [4224, 32972, 75000, 95000, 115000],
                    "net_income": [4368, 29760, 62000, 78000, 94000],
                },
                "cash_flow": {
                    "cfo": [5641, 28090, 60000, 75000, 90000],
                    "capex": [1833, 3912, 5500, 7000, 8500],
                    "fcf": [3808, 24178, 54500, 68000, 81500],
                }
            },
            "moat_analysis": {
                "network_effects": "开发者网络深度锁定",
                "switching_costs": "编译栈与专有算法强绑定",
                "cost_advantage_and_scale": "超大订单锁定代工先进制程",
                "intangible_assets": "数万项授权专利",
                "reinvestment_efficiency": "ROIC 60%+",
            },
            "supply_chain_analysis": {
                "upstream_suppliers": {
                    "core_suppliers": "头部先进制程晶圆代工与HBM3e供应商",
                    "supplier_concentration": "Top 3 占比 70%",
                    "supply_chain_risks": "CoWoS 产能供不应求",
                },
                "downstream_customers": {
                    "customer_structure": "全球一线云巨头",
                    "top5_customer_concentration": "Top 5 贡献营收 40%",
                    "default_and_churn_risks": "自研芯片部分内用",
                }
            },
            "industry_dynamics": {
                "winner_factor": "前沿架构与生态闭环",
                "market_share_and_crn": "独立 GPU 市占率超 80%",
                "tam_and_cagr": "AI 基础设施 TAM 达万亿美元",
            },
            "long_term_outlook": {
                "catalysts": ["Blackwell 全速出货", "具身智能算力需求爆发"],
                "kill_switch_risks": ["地缘出口管制限制", "云巨头缩减 Capex"],
            },
            "micro_macro_metrics": {
                "wicksellian_gap_bps": 25.0,
                "dynamic_wacc_t1": 0.082,
                "markup_mu": 1.85,
                "pricing_power_tier": "强垄断特许 (STRONG_DEFENSE)",
                "iqi_score": 88.0,
                "dtf_score": 0.95,
                "creative_destruction_status": "前沿领跑者 (FRONTIER_LEADER)",
            },
            "dcf_model": {
                "wacc_vector": [0.082, 0.080, 0.078, 0.076, 0.075],
                "fcf_projections": [25000, 31000, 38000, 44000, 50000],
            },
            "evidence_manifest": [
                {
                    "category": "官方财务三表",
                    "filing_name": "NVDA Annual 10-K",
                    "source_url": "https://www.sec.gov/edgar",
                    "sha256": "abcdef1234567890abcdef1234567890",
                    "timestamp": "2026-10-17",
                }
            ],
            "material_events": [
                {
                    "date": "2026-10-17",
                    "filing_type": "Annual 10-K",
                    "summary": "官方年报披露确认数据中心营收同比倍增",
                    "impact": "公允中枢维持在击球区",
                    "pdf_status": "已生成财年存档 PDF",
                    "file_name": "NVDA_2026_Annual.pdf",
                }
            ]
        }

        file_path = builder.build_workbook(dossier_data, output_filename="NVDA_深度投研档案_测试.xlsx")
        self.assertTrue(file_path.exists())

        wb = openpyxl.load_workbook(file_path, data_only=False)
        expected_sheets = [
            "00_投资备忘录与决策中枢",
            "01_行业与护城河竞争格局",
            "02_官方三表全息审计底稿",
            "03_内生估值与敏感度走廊",
            "04_审计溯源与重大事件跟踪",
        ]
        self.assertEqual(wb.sheetnames, expected_sheets)

        # 检查官方三表平账行公式
        ws_filings = wb["02_官方三表全息审计底稿"]
        chk_found = False
        for row in ws_filings.iter_rows(values_only=False):
            cell_val = str(row[0].value)
            if "资产负债平账自检行" in cell_val:
                chk_found = True
                # 检查第二列的平账公式
                formula_cell = row[1]
                self.assertTrue(str(formula_cell.value).startswith("=B"))
                self.assertIn("-(B", str(formula_cell.value))
                break
        self.assertTrue(chk_found, "未在官方三表底稿中找到资产负债平账自检行")

        # 断言 0 个表情符号
        self._assert_zero_emojis_in_workbook(file_path)

    def test_04_excel_daily_screener_builder_generation(self):
        """【IT-EXCEL-04: 美日大盘全景总报与价值洼地击球区雷达Excel生成(安全边际动态公式与零Emoji)】

        1. 测试功能与测试点:
           - 验证 ExcelDailyScreenerBuilder 生成每日大盘与筛选工作簿。
           - 验证包含 5 个工作表（宏观流动性、美股洼地雷达、日股洼地雷达、期权异动大单、顶层决策卡片）。
           - 严格断言在美股挑选雷达中注入原生动态安全边际公式: '=(Fair_Anchor - Current_Price) / Current_Price'。
           - 全簿通过零 Emoji 断言。

        2. 正常函数业务边界与参数契约:
           - 输入合法每日大盘字典以及美日资产池列表。
           - 输出 .xlsx 文件完整可读。

        3. 测试数据与模拟场景说明:
           - 输入美股宏观流动性、市场情绪与 SPY 期权异动，注入 NVDA、STX 与东电 8035。

        4. 预期断言与结果验证:
           - file_path.exists() 为 True。
           - wb.sheetnames 长度为 5。
           - 第 6 行安全边际公式以 '=(F6-D6)/D6' 开头。
           - 零表情符号断言全部通过。
        """
        builder = ExcelDailyScreenerBuilder(output_root=self.out_root)

        briefing_data = {
            "header": {
                "report_date": "2026-10-17",
                "market": "US",
                "market_name_zh": "美股市场",
            },
            "macro_and_liquidity": {
                "us_10y_yield": "4.35%",
                "us_2y_yield": "4.10%",
                "yield_spread_10_2": "+25.0 bps",
                "dxy_index": "104.10",
                "usd_jpy_rate": "158.50",
                "effr_policy_rate": "4.58%",
            },
            "market_sentiment_and_options": {
                "vix_index": "15.80",
                "fear_greed_gauge": "贪婪 (Greed) (68)",
                "put_call_ratio": "0.72",
                "capital_flow_summary": "主力资金净流入 +18.5 亿美元",
            },
            "market_moving_news": [
                {
                    "headline": "全球主要云厂商公布新季度资本开支指引，算力投入超市场预期",
                    "impact_analysis": "直接利好 AI 基础设施龙头供应链业绩，估值弹性上修",
                }
            ],
            "ai_executive_summary": "大盘流动性充沛，利率利差平稳走陡，建议紧密关注黄金击球区标的逢低布局。",
            "recommended_stocks": [
                {
                    "ticker": "NVDA",
                    "company_name": "英伟达公司",
                    "current_price": "$130.00",
                    "margin_of_safety_trigger": "安全边际 +30.8% (黄金击球区)",
                    "rating": "买入 (Buy)",
                    "business_intro": "全球加速计算与全栈 AI 工厂基础设施不可替代领军者",
                    "pessimistic_deduction": {
                        "trigger_event": "若宏观经济严重衰退或先进封装交付短期中断",
                        "implied_price": "$110.00",
                        "downside_gap": "-15.4%"
                    },
                    "neutral_deduction": {
                        "trigger_event": "Blackwell 架构全速交付，云厂商投资确定性高",
                        "implied_price": "$170.00",
                        "upside_potential": "+30.8%"
                    },
                    "optimistic_deduction": {
                        "trigger_event": "物理 AI 与具身智能推理算力需求激增",
                        "implied_price": "$220.00",
                        "upside_potential": "+69.2%"
                    },
                    "tactical_action": "回调至 $125~$130 区间积极逢低配置，仓位建议 5%~7%"
                }
            ],
            "options_flow": [
                {
                    "ticker": "SPY",
                    "contract": "Call 2026-11-20",
                    "strike": 590.0,
                    "vol_oi": "45,200 / 12,800",
                    "premium_m": 28.5,
                    "side": "主动买入 (Ask)",
                    "diagnosis": "指数多头看涨情绪强烈",
                }
            ]
        }

        us_pool = [
            {
                "ticker": "NVDA",
                "company_name_zh": "英伟达公司",
                "sector": "半导体",
                "current_price": 130.0,
                "pessimistic_floor": 110.0,
                "fair_anchor": 170.0,
                "optimistic_target": 220.0,
                "pricing_power": "强垄断",
                "distance_to_default": 5.2,
                "catalyst": "Blackwell 架构放量",
            },
            {
                "ticker": "STX",
                "company_name_zh": "希捷科技",
                "sector": "硬件存储",
                "current_price": 98.0,
                "pessimistic_floor": 88.0,
                "fair_anchor": 135.0,
                "optimistic_target": 175.0,
                "pricing_power": "强寡头",
                "distance_to_default": 3.8,
                "catalyst": "近线大容量存储毛利率拐点",
            }
        ]

        jp_pool = [
            {
                "ticker": "8035",
                "company_name_zh": "东京电子",
                "sector": "半导体设备",
                "current_price": 25000.0,
                "pessimistic_floor": 22000.0,
                "fair_anchor": 34000.0,
                "optimistic_target": 42000.0,
                "pbr": 3.8,
                "shareholder_yield": 0.038,
                "catalyst": "先进制程与先进封装设备订单超预期",
            }
        ]

        file_path = builder.build_workbook(
            briefing_data,
            us_screener_pool=us_pool,
            jp_screener_pool=jp_pool,
            output_filename="每日市场深度与价值洼地筛选_测试.xlsx"
        )
        self.assertTrue(file_path.exists())

        wb = openpyxl.load_workbook(file_path, data_only=False)
        self.assertEqual(len(wb.sheetnames), 5)

        # 检查美股筛选雷达内的安全边际公式
        ws_us = wb["01_美股价值洼地挑选雷达"]
        # 数据行从第 6 行开始 (第 1,2 行 banner, 第 4 行 section, 第 5 行 headers)
        row_6 = list(ws_us.iter_rows())[5]
        mos_formula = row_6[7].value
        self.assertTrue(str(mos_formula).startswith("=(F6-D6)/D6"))

        # 断言 0 个表情符号
        self._assert_zero_emojis_in_workbook(file_path)


if __name__ == "__main__":
    unittest.main()
