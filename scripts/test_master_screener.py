"""单元测试：千家资产池顶层动态雷达与价值洼地主看板建造器 (test_master_screener.py).

验证要点：
1. 包含 4 张标准命名工作表；
2. Sheet 0 Top-30 榜单按折价率严格降序排位，数量不超过 30；
3. HYPERLINK 原生公式正确注入；
4. 美股与日股工作表分流、格式化与自动筛选合规；
5. 行业聚类统计正确；
6. 100% 物理消除 Emoji 符号；
7. 网格线与首行冻结生效。
"""

import os
from pathlib import Path
import re
import sys
import unittest
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_reporting.excel_master_screener_builder import ExcelMasterScreenerBuilder
from financial_reporting.ai_research_agent import EMOJI_PATTERN


class TestExcelMasterScreenerBuilder(unittest.TestCase):
    """主看板建造器全息测试套件."""

    def setUp(self):
        self.builder = ExcelMasterScreenerBuilder(base_date="2026-10-18")
        self.temp_excel = os.path.join(
            os.path.dirname(__file__), "temp_test_master_screener.xlsx"
        )

        # 构造 35 个测试样本（包含美股、日股、正负折价率）
        self.mock_targets = []
        for i in range(1, 26):
            self.mock_targets.append({
                "ticker": f"US_{i:02d}",
                "company_name": f"美股龙头企业_{i}",
                "market": "US",
                "industry_id": "semiconductors" if i % 2 == 0 else "software",
                "industry_name": "前沿半导体" if i % 2 == 0 else "企业级软件",
                "current_price": 100.0 + i * 2,
                "pessimistic_floor": 60.0 + i,
                "neutral_fair_value": 80.0 + i * 4,
                "optimistic_target": 120.0 + i * 6,
                "margin_of_safety_pct": (i - 10) * 4.5,  # 从负到正
                "objective_signal": "BUY_ZONE" if (i - 10) * 4.5 > 15 else "FAIR_VALUE",
                "quote_timestamp": "2026-10-18 16:00:00 EDT",
                "catalyst_summary": f"测试买点催化事实 {i}",
                "excel_path": f"reports/excel_dossiers/US/US_{i:02d}_深度投研档案.xlsx",
            })

        for j in range(1, 11):
            self.mock_targets.append({
                "ticker": f"72{j:02d}",
                "company_name": f"日股东证企业_{j}",
                "market": "JP",
                "industry_id": "autos" if j % 2 == 0 else "machinery",
                "industry_name": "全球汽车混动" if j % 2 == 0 else "高端自动化机械",
                "current_price": 2000.0 + j * 50,
                "pessimistic_floor": 1400.0 + j * 30,
                "neutral_fair_value": 2600.0 + j * 80,
                "optimistic_target": 3500.0 + j * 100,
                "margin_of_safety_pct": 25.0 + j * 2.0,  # 全正击球区
                "objective_signal": "BUY_ZONE",
                "quote_timestamp": "2026-10-18 15:00:00 JST",
                "catalyst_summary": f"日股增持回购与出海催化 {j}",
                "excel_path": f"reports/excel_dossiers/JP/72{j:02d}_深度投研档案.xlsx",
            })

    def tearDown(self):
        if os.path.exists(self.temp_excel):
            try:
                os.remove(self.temp_excel)
            except Exception:
                pass

    def test_builder_generates_all_four_sheets(self):
        """【FT-SCREENER-01: 主看板四张标准工作表生成契约与物理落盘】

        1. 测试功能与测试点:
           - 验证 ExcelMasterScreenerBuilder 顶层聚合建造器能否完整生成 4 张符合机构规范命名与顺序的工作表。
           - 验证输出文件能否在本地文件系统中物理正确落盘。

        2. 正常函数业务边界与参数契约:
           - targets: 字典列表，每个元素代表一个标的资产的全息分析结果。
           - output_path: 目标 Excel 文件的合法路径。
           - 工作簿必须包含且仅包含指定的 4 张工作表，且顺序严格单调固定。

        3. 测试数据与模拟场景说明:
           - 模拟输入: 传入包含 25 只美股（正负折价率交错）与 10 只日股（高安全边际）共计 35 只标的资产池。
           - 边界条件: 目标输出路径为临时路径 temp_test_master_screener.xlsx。

        4. 预期断言与结果验证:
           - 断言工作表名称列表精确匹配: ['00_价值洼地与击球区雷达', '01_美股资产池全息扫描', '02_日股资产池全息扫描', '03_行业估值与安全边际分布']。
           - 断言 os.path.exists(temp_excel) 为 True。
        """
        wb = self.builder.build_master_screener(
            targets=self.mock_targets,
            output_path=self.temp_excel,
        )
        expected_sheets = [
            "00_价值洼地与击球区雷达",
            "01_美股资产池全息扫描",
            "02_日股资产池全息扫描",
            "03_行业估值与安全边际分布",
        ]
        self.assertEqual(wb.sheetnames, expected_sheets)
        self.assertTrue(os.path.exists(self.temp_excel))

    def test_top_30_ranking_and_hyperlink(self):
        """【FT-SCREENER-02: Top-30 价值洼地雷达排序算法与底层底账穿透超链接】

        1. 测试功能与测试点:
           - 验证 Sheet 0 '00_价值洼地与击球区雷达' 的排位算法：必须且仅按折价率（安全边际）单调降序排列。
           - 验证收录上限限制：上榜标的数严格不得超过 30 家（Top-30 准则）。
           - 验证单元格公式生成：必须注入原生的 =HYPERLINK(...) 公式，指向个股 5-Sheet Excel 深度底账。

        2. 正常函数业务边界与参数契约:
           - margin_of_safety_pct: 浮点数，支持负数（溢价）到正数（折价/安全边际）。
           - 排位算法必须跨越美股与日股进行全球资产池统一排序。

        3. 测试数据与模拟场景说明:
           - 模拟 35 只标的（超过 30 限制），折价率从负值到高达 45.0% 的击球区。
           - 模拟各标的对应的 excel_path 相对路径。

        4. 预期断言与结果验证:
           - 断言上榜行数 <= 30 且 > 0。
           - 断言第 i 项折价率 >= 第 i+1 项折价率（严格降序）。
           - 断言穿透列为以 '=HYPERLINK("' 开头的公式，文本中包含 '打开5-Sheet底账'。
        """
        wb = self.builder.build_master_screener(
            targets=self.mock_targets,
            output_path=self.temp_excel,
        )
        ws = wb["00_价值洼地与击球区雷达"]

        # 表头位于第 9 行 (由 apply_sheet_banner + 4 行卡片 + 呼吸行计算)
        # 数据从第 11 行开始
        # 寻找包含 "排名" 的列头行
        header_row = None
        for r in range(1, 15):
            if ws.cell(row=r, column=1).value == "排名":
                header_row = r
                break
        self.assertIsNotNone(header_row, "未找到 Top-30 榜单列头行")

        # 读取数据行
        ranks = []
        margins = []
        row_idx = header_row + 1
        while ws.cell(row=row_idx, column=1).value is not None:
            val = ws.cell(row=row_idx, column=1).value
            if isinstance(val, int):
                ranks.append(val)
                margin_val = ws.cell(row=row_idx, column=10).value
                margins.append(float(margin_val))

                # 检查超链接公式
                link_val = str(ws.cell(row=row_idx, column=13).value)
                self.assertTrue(
                    link_val.startswith('=HYPERLINK("'),
                    f"单元格必须为 HYPERLINK 公式: {link_val}",
                )
                self.assertIn("打开5-Sheet底账", link_val)

            row_idx += 1

        self.assertLessEqual(len(ranks), 30, "Top-30 榜单标的数不得超过 30")
        self.assertGreater(len(ranks), 0, "Top-30 榜单必须收录有效标的")

        # 断言折价率严格单调递减
        for idx in range(len(margins) - 1):
            self.assertGreaterEqual(
                margins[idx],
                margins[idx + 1],
                f"第 {idx+1} 项与第 {idx+2} 项折价率未降序排列",
            )

    def test_us_and_jp_universe_sheets(self):
        """【FT-SCREENER-03: 美股与日股资产池分流全息扫描及视图冻结】

        1. 测试功能与测试点:
           - 验证美股资产池 (01) 与日股资产池 (02) 严格根据 market 字段完成物理数据分流。
           - 验证工作表视图格式化配置: 必须开启 AutoFilter 自动筛选，且冻结窗格定位在 A5。

        2. 正常函数业务边界与参数契约:
           - market: 严格区分 'US' 与 'JP'，分别流向对应的全息工作表。
           - 冻结窗格: 统一锁定首部 KPI 徽标与表头行，提升买方交互体验。

        3. 测试数据与模拟场景说明:
           - 模拟包含 25 只美股与 10 只日股的混合输入，分别检验 ws_us 与 ws_jp 的渲染状态。

        4. 预期断言与结果验证:
           - 断言 ws_us.auto_filter.ref 与 ws_jp.auto_filter.ref 均非空。
           - 断言两张表的 freeze_panes 属性精确等于 'A5'。
        """
        wb = self.builder.build_master_screener(
            targets=self.mock_targets,
            output_path=self.temp_excel,
        )

        ws_us = wb["01_美股资产池全息扫描"]
        ws_jp = wb["02_日股资产池全息扫描"]

        self.assertIsNotNone(ws_us.auto_filter.ref, "美股工作表必须开启自动筛选 AutoFilter")
        self.assertIsNotNone(ws_jp.auto_filter.ref, "日股工作表必须开启自动筛选 AutoFilter")
        self.assertEqual(ws_us.freeze_panes, "A5", "美股工作表窗格必须冻结在 A5")
        self.assertEqual(ws_jp.freeze_panes, "A5", "日股工作表窗格必须冻结在 A5")

    def test_industry_stats_sheet(self):
        """【FT-SCREENER-04: 行业估值与安全边际分布聚类统计】

        1. 测试功能与测试点:
           - 验证 Sheet 03 '03_行业估值与安全边际分布' 的中观行业聚合计算。
           - 验证不同产业门类（半导体、软件、汽车、机械）在多市场资产池中的汇总归集完整性。

        2. 正常函数业务边界与参数契约:
           - industry_id: 必须映射至受支持的行业编码或通用行业桶。
           - 统计项涵盖: 标的覆盖总数、平均估值、击球区标的数占比等。

        3. 测试数据与模拟场景说明:
           - 模拟构造中已明确分配 semiconductors, software, autos, machinery 四个行业代码。

        4. 预期断言与结果验证:
           - 遍历第 5~20 行行业代码，断言上述 4 个核心行业代码均被正确聚类统计并落盘展示。
        """
        wb = self.builder.build_master_screener(
            targets=self.mock_targets,
            output_path=self.temp_excel,
        )
        ws_ind = wb["03_行业估值与安全边际分布"]

        # 验证包含半导体、软件、汽车、机械等行业
        industries_found = set()
        for r in range(5, 20):
            ind_code = ws_ind.cell(row=r, column=1).value
            if ind_code:
                industries_found.add(str(ind_code))

        self.assertIn("semiconductors", industries_found)
        self.assertIn("software", industries_found)
        self.assertIn("autos", industries_found)
        self.assertIn("machinery", industries_found)

    def test_zero_emoji_cleanliness(self):
        """【FT-SCREENER-05: 单元格文本全盘物理消除 Emoji 符号】

        1. 测试功能与测试点:
           - 依据全局工程规范与买方机构级严谨标准，检验生成的全量工作簿中 100% 物理消除非标准的 Emoji 符号（如火箭、涨跌图示、警示符号等）。

        2. 正常函数业务边界与参数契约:
           - 全量工作表全量单元格的文本值（排除 Excel 原生公式 = 开头）。
           - 匹配规则: EMOJI_PATTERN 字符集正则。

        3. 测试数据与模拟场景说明:
           - 遍历 build_master_screener 生成的全部 4 张工作表的所有单元格数据行。

        4. 预期断言与结果验证:
           - 断言 emoji_hits 违规命中列表长度严格等于 0。
        """
        wb = self.builder.build_master_screener(
            targets=self.mock_targets,
            output_path=self.temp_excel,
        )

        emoji_hits = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for val in row:
                    if isinstance(val, str) and not val.startswith("="):
                        if EMOJI_PATTERN.search(val):
                            emoji_hits.append((ws.title, val))

        self.assertEqual(
            len(emoji_hits),
            0,
            f"主看板工作簿中存在 Emoji 违规遗留: {emoji_hits}",
        )


if __name__ == "__main__":
    unittest.main()
