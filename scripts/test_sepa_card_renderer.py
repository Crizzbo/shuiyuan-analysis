"""米奈尔维尼 SEPA 买方操盘决策卡片渲染与多模态输出全息回归测试 (Test SEPA Card Renderer).

严格遵循《全局工程与协作规范》与《全栈工程命名架构与状态空间规范 (08-全栈工程命名架构与状态空间规范.md)》:
1. HTML 矢量卡片渲染验证 (A4 打印优化、墨绿/红/金黄徽章自适应、价格走廊排版);
2. 投委会 Markdown 备忘录文本卡片验证 (关键防线与操盘指令);
3. Excel 工作簿 Section 写入与样式核验 (FAST Standard, 单元格格式, 背景色与高亮);
4. 强类型对象与原始字典双重自适应验证 (_normalize_sepa_result);
5. Excel Dossier Builder 深度档案集成端到端实测验证。
"""

import unittest
from pathlib import Path
import json
import sys
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.sepa_buy_signal_engine import (
    SepaBuySignalEngine,
    SepaInputFacts,
    SepaPriceBoundaries,
    SepaBuySignalResult,
    BuySignalTier,
    TrendStageState,
    VcpContractionStatus,
)
from financial_reporting.sepa_card_renderer import SepaCardRenderer, _normalize_sepa_result
from financial_reporting.excel_dossier_builder import ExcelDossierBuilder


class TestSepaCardRenderer(unittest.TestCase):
    """测试 SEPA 卡片渲染器与报告系统集成."""

    def setUp(self):
        self.engine = SepaBuySignalEngine()

        # 构造 NVDA 真实典型突破样本
        self.facts_breakout = SepaInputFacts(
            ticker="NVDA",
            val_current_price=204.64,
            val_ma_50=185.20,
            val_ma_150=165.40,
            val_ma_200=150.00,
            val_ma_200_20d_ago=145.50,
            val_low_52w=115.00,
            val_high_52w=210.00,
            num_rs_rank=92.0,
            val_pivot_price=200.00,
            pct_recent_contractions=[28.0, 14.0, 6.0, 2.5],
            days_base_duration=56,
            num_current_volume=65000000.0,
            num_avg_volume_50d=35000000.0,
            num_dryup_volume_min=12000000.0,
        )
        self.res_breakout = self.engine.evaluate_buy_signal(self.facts_breakout)

    def test_html_card_rendering_breakout(self):
        """【IT-SCR-01: HTML 操盘决策卡片 - 放量买入触发渲染】

        1. 测试功能与测试点:
           - 验证放量突破买入信号在 HTML 矢量决策卡片中的多模态排版与呈现。
           - 包含 A4 打印优化、墨绿安全徽章自适应、四维价格走廊与操盘指令输出。

        2. 正常函数业务边界与参数契约:
           - 输入为评估完成的 SepaBuySignalResult 对象或兼容字典。
           - market 区分美股 (US, '$') 与日股 (JP, '¥')。

        3. 测试数据与模拟场景说明:
           - NVDA 典型放量突破: 枢轴买点 200.00，现价 204.64，收缩形态 8W 28/2.5 4T。

        4. 预期断言与结果验证:
           - 断言 HTML 包含标题“米奈尔维尼 SEPA 时机与买点决策卡”。
           - 断言包含状态标签“【买入触发】放量突破枢轴买点”与形态代码“8W 28/2.5 4T”。
           - 断言四维价格 $200.00, $186.00, $210.00, $242.00 完整呈现。
           - 断言包含操盘指令“果断击球买入”。
        """
        html = SepaCardRenderer.render_sepa_card_html(self.res_breakout, market="US")
        self.assertIn("米奈尔维尼 SEPA 时机与买点决策卡", html)
        self.assertIn("【买入触发】放量突破枢轴买点", html)
        self.assertIn("8W 28/2.5 4T", html)
        self.assertIn("$200.00", html)   # 枢轴买点
        self.assertIn("$186.00", html)   # 刚性止损 (-7%)
        self.assertIn("$210.00", html)   # 追高上限 (+5%)
        self.assertIn("$242.00", html)   # 3R 移动保本 / 3:1 靶心
        self.assertIn("果断击球买入", html)

    def test_html_card_rendering_extended_overbought(self):
        """【IT-SCR-02: HTML 操盘决策卡片 - 追高超买脱轨拦截与红色警戒】

        1. 测试功能与测试点:
           - 验证股价脱离买点超过 5% 追高上限时的卡片告警渲染机制。
           - 验证输出红色警戒色徽章 (#c53030) 与“严禁追高”刚性警示。

        2. 正常函数业务边界与参数契约:
           - CurrentPrice > PivotPrice * 1.05。

        3. 测试数据与模拟场景说明:
           - NVDA 现价升至 215.00 美元 (超过买点 200.00 达 7.5%)。

        4. 预期断言与结果验证:
           - 断言 HTML 包含“【超买拦截】脱离买点超 5%，严禁追高”。
           - 断言包含操盘指引“严禁追高”。
           - 断言包含警戒背景色“#c53030”。
        """
        facts_over = SepaInputFacts(**{**self.facts_breakout.__dict__, "val_current_price": 215.00})
        res_over = self.engine.evaluate_buy_signal(facts_over)
        html = SepaCardRenderer.render_sepa_card_html(res_over, market="US")

        self.assertIn("【超买拦截】脱离买点超 5%，严禁追高", html)
        self.assertIn("严禁追高", html)
        self.assertIn("#c53030", html)  # 红色警戒徽章

    def test_html_card_rendering_squat_watch(self):
        """【IT-SCR-03: HTML 操盘决策卡片 - 深蹲震仓保护与黄色警戒】

        1. 测试功能与测试点:
           - 验证股价突破后轻微跌破买点但守住均线时的深蹲保护卡片呈现。
           - 验证输出金黄色警戒色徽章 (#d69e2e) 与“坚决不割肉”指引。

        2. 正常函数业务边界与参数契约:
           - StopLoss < CurrentPrice < PivotPrice 且均线未破、量能收敛。

        3. 测试数据与模拟场景说明:
           - NVDA 现价跌至 196.00 美元，缩量至 2500 万股 (均量 3500 万)。

        4. 预期断言与结果验证:
           - 断言 HTML 包含“【深蹲洗盘】缩量回踩守住止损，等待逆转”。
           - 断言包含操盘指引“坚决不割肉”。
           - 断言包含金黄色警示色“#d69e2e”。
        """
        facts_squat = SepaInputFacts(
            **{
                **self.facts_breakout.__dict__,
                "val_current_price": 196.00,
                "num_current_volume": 25000000.0,
            }
        )
        res_squat = self.engine.evaluate_buy_signal(facts_squat)
        html = SepaCardRenderer.render_sepa_card_html(res_squat, market="US")

        self.assertIn("【深蹲洗盘】缩量回踩守住止损，等待逆转", html)
        self.assertIn("坚决不割肉", html)
        self.assertIn("#d69e2e", html)  # 金黄色警戒

    def test_markdown_memo_card(self):
        """【IT-SCR-04: 投委会 Markdown 格式文本备忘录卡片生成】

        1. 测试功能与测试点:
           - 验证面向投委会决策报告的轻量化 Markdown 格式备忘录卡片生成。
           - 包含标准标的代码、技术收敛代码、四维价格与操盘指令。

        2. 正常函数业务边界与参数契约:
           - 严格 Markdown 语法输出，支持终端打印与文档嵌入。

        3. 测试数据与模拟场景说明:
           - NVDA 突破买入评估结果。

        4. 预期断言与结果验证:
           - 断言 Markdown 包含规范标题 '### 【米奈尔维尼 SEPA 时机与买入信号决策卡 (NVDA)】' (零 Emoji 规范)。
           - 断言包含 '`8W 28/2.5 4T`'。
           - 断言包含枢轴买点、刚性止损、超买上限、移动保本价格标签。
        """
        md = SepaCardRenderer.render_sepa_card_markdown(self.res_breakout, market="US")
        self.assertIn("### 【米奈尔维尼 SEPA 时机与买入信号决策卡 (NVDA)】", md)
        self.assertIn("`8W 28/2.5 4T`", md)
        self.assertIn("枢轴买点 (Pivot)**: `$200.00`", md)
        self.assertIn("刚性止损 (-7.0%)**: `$186.00`", md)
        self.assertIn("超买追高上限 (+5.0%)**: `$210.00`", md)
        self.assertIn("移动保本触发 (3R)**: `$242.00`", md)

    def test_excel_section_population(self):
        """【IT-SCR-05: Excel 深度投研档案 Section 独立写入与 FAST 样式】

        1. 测试功能与测试点:
           - 验证 openpyxl 工作表中直接写入 SEPA 决策卡片 Section 的单元格格式与 FAST 建模标准。
           - 验证枢轴买点与止损线数值的数值类型保真 (非死文本)。

        2. 正常函数业务边界与参数契约:
           - ws 为 openpyxl Worksheet。
           - start_row 为起始行号。

        3. 测试数据与模拟场景说明:
           - 在空白工作表第 5 行开始填充 SEPA 结果。

        4. 预期断言与结果验证:
           - 断言结束行号 > 14。
           - 断言成功检索到“枢轴买点价格”对应数值 200.00，“刚性硬止损价”对应 186.00。
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "00_投资备忘录"

        end_row = SepaCardRenderer.populate_sepa_section_excel(ws, start_row=5, result=self.res_breakout, market="US")
        self.assertGreater(end_row, 14)

        # 检查关键单元格文本与格式
        found_pivot = False
        found_stop = False
        for r in range(5, end_row):
            cell_val = str(ws.cell(row=r, column=1).value or "")
            if "枢轴买点价格" in cell_val:
                found_pivot = True
                self.assertEqual(ws.cell(row=r, column=2).value, 200.00)
            if "刚性硬止损价" in cell_val:
                found_stop = True
                self.assertEqual(ws.cell(row=r, column=2).value, 186.00)

        self.assertTrue(found_pivot, "必须成功写入枢轴买点行")
        self.assertTrue(found_stop, "必须成功写入刚性硬止损行")

    def test_dict_input_adaptation(self):
        """【IT-SCR-06: 原始字典与强类型对象双重自适应解析】

        1. 测试功能与测试点:
           - 验证卡片渲染器向下兼容能力: 支持原始 JSON 反序列化得到的嵌套字典，与 Dataclass 无缝兼容。
           - 测试 _normalize_sepa_result 转换器的强鲁棒性。

        2. 正常函数业务边界与参数契约:
           - 输入为 Python dict 数据结构。

        3. 测试数据与模拟场景说明:
           - 传入包含完整字段的纯 Python dict 模拟跨进程或网络传输反序列化数据。

        4. 预期断言与结果验证:
           - HTML 与 Markdown 渲染函数正常工作，成功输出标题与价格 $200.00。
        """
        raw_dict = {
            "ticker": "NVDA",
            "val_current_price": 204.64,
            "status_trend_stage": "Stage_2_Markup",
            "status_vcp_contraction": "Tight_Pivot_Ready",
            "status_buy_signal": "Pivot_Triggered",
            "is_trend_template_passed": True,
            "trend_criteria_checks": {"1": True},
            "technical_footprint_code": "8W 28/2.5 4T",
            "cnt_contractions": 4,
            "is_volume_dryup_confirmed": True,
            "is_breakout_volume_confirmed": True,
            "is_squat_holding": False,
            "price_boundaries": {
                "val_pivot_price": 200.00,
                "val_stop_loss_price": 186.00,
                "val_recommended_stop_price": 190.00,
                "val_risk_unit_usd": 14.00,
                "val_breakeven_trigger_price": 242.00,
                "val_extended_limit_price": 210.00,
                "val_target_profit_price": 242.00,
                "pct_hard_stop_loss": 7.0,
                "pct_recommended_stop_loss": 5.0,
                "pct_current_to_pivot": 2.32,
                "is_within_buy_range": True,
            },
            "directive_action_zh": "【买入触发】果断开火！",
            "meta_trend_stage": {"state_name": "第二阶段主升浪"},
            "meta_vcp_status": {"state_name": "紧密收敛准备突破"},
            "meta_buy_signal": {"state_name": "放量突破买点触发"},
        }

        # 字典直接传入 HTML 渲染
        html = SepaCardRenderer.render_sepa_card_html(raw_dict, market="US")
        self.assertIn("米奈尔维尼 SEPA 时机与买点决策卡", html)
        self.assertIn("$200.00", html)

        # 字典直接传入 Markdown 渲染
        md = SepaCardRenderer.render_sepa_card_markdown(raw_dict, market="US")
        self.assertIn("$200.00", md)

    def test_excel_dossier_builder_integration(self):
        """【IT-SCR-07: Excel Dossier Builder 深度档案端到端集成】

        1. 测试功能与测试点:
           - 验证 ExcelDossierBuilder 在构建 5-Sheet 深度研报工作簿时，成功嵌入 SEPA 操盘决策卡 Section。
           - 验证文件真实物理落盘并使用 openpyxl 检验第一张表（00_投资备忘录与决策中枢）。

        2. 正常函数业务边界与参数契约:
           - 完整 dossier_data 包含 decision_summary, micro_macro_metrics, sepa_result 与 financial_statements。

        3. 测试数据与模拟场景说明:
           - 为 NVDA 生成完备档案并输出至测试输出目录 TEST_SEPA_NVDA_dossier.xlsx。

        4. 预期断言与结果验证:
           - 断言文件物理存在 (generated_file.is_file())。
           - 断言工作簿包含 '00_投资备忘录'。
           - 断言第一张工作表中成功写入 '米奈尔维尼 SEPA' 标题。
        """
        from scripts.test_support.fixtures import project_temp
        test_out_dir = project_temp(self, "test-sepa-card-")
        builder = ExcelDossierBuilder(output_root=test_out_dir)

        dossier_data = {
            "decision_summary": {
                "current_price": 204.64,
                "pessimistic_floor": 145.0,
                "fair_anchor": 215.0,
                "optimistic_target": 280.0,
                "margin_of_safety_pct": 5.06,
                "stance": "逢低布局",
                "rating": "Strong Buy",
                "strike_zone_status": "接近合理击球区",
                "freshness_status": "盘后实时核准",
            },
            "micro_macro_metrics": {
                "wicksellian_gap_bps": 45.0,
                "dynamic_wacc_t1": 0.085,
                "markup_mu": 1.45,
                "iqi_score": 0.92,
                "dtf_score": 0.98,
            },
            "long_term_outlook": {
                "catalysts": ["下一代 Blackwell GPU 架构放量", "主权 AI 云计算采购超预期"],
                "kill_switch_risks": ["先进封装 CoWoS 产能供应链断裂", "云巨头 CapEx 预算紧缩"],
            },
            "sepa_result": self.res_breakout,
            "financial_statements": {
                "years": ["2023", "2024", "2025"],
                "income_statement": {
                    "total_revenue": [26974.0, 60922.0, 120000.0],
                    "gross_profit": [15356.0, 44301.0, 90000.0],
                    "operating_income": [4224.0, 32972.0, 70000.0],
                    "net_income": [4368.0, 29760.0, 62000.0],
                },
                "balance_sheet": {
                    "cash_and_equivalents": [13296.0, 25984.0, 35000.0],
                    "total_assets": [41182.0, 65728.0, 110000.0],
                    "total_liabilities": [19081.0, 22750.0, 35000.0],
                    "total_equity": [22101.0, 42978.0, 75000.0],
                },
                "cash_flow_statement": {
                    "operating_cash_flow": [5641.0, 28090.0, 65000.0],
                    "capital_expenditures": [1833.0, 1076.0, 3000.0],
                    "free_cash_flow": [3808.0, 27014.0, 62000.0],
                },
            },
        }

        generated_file = builder.build_excel_dossier(
            dossier_data=dossier_data,
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            market="US",
            industry_name="半导体",
            report_date="2026-11-03",
            output_filename="TEST_SEPA_NVDA_dossier.xlsx",
        )

        self.assertTrue(generated_file.is_file())

        # 读取生成的真实 Excel 文件，断言 Sheet 1 写入了 SEPA Section
        wb = openpyxl.load_workbook(generated_file, data_only=True)
        self.assertTrue(any("00_投资备忘录" in name for name in wb.sheetnames), f"工作表列表 {wb.sheetnames} 必须包含投资备忘录工作表")
        target_sheetname = next(name for name in wb.sheetnames if "00_投资备忘录" in name)
        ws_memo = wb[target_sheetname]

        found_sepa_header = False
        for row in ws_memo.iter_rows(values_only=True):
            for cell in row:
                if cell and "米奈尔维尼 SEPA" in str(cell):
                    found_sepa_header = True
                    break

        self.assertTrue(found_sepa_header, "深度档案 Excel Sheet 1 必须成功渲染米奈尔维尼 SEPA 操盘卡 Section")


if __name__ == "__main__":
    unittest.main()
