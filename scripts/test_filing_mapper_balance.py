"""单元测试: 官方财报底账摄入与资产负债表刚性平账自检测试 (Filing Mapper & Balance Sheet Integrity Tests).

测试覆盖:
1. 资产负债表刚性平账自检 (±0.1% 容差边界, BalanceSheetIdentityError 拦截)
2. SEC EDGAR 10-K/Q 官方 XBRL 底账解析与双向契约组装 (SystemicCompanyInput + FirmFinancialFact)
3. JPX EDINET / TDnet 日股决算短信科目解析与日元计价映射
4. 多币种与量纲自愈 (usd_million, cny_hundred_million, jpy_million)
5. 自由现金流自洽性验证 (FCF = OCF - Capex)
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.filing_mapper import (
    OfficialFilingMapper,
    BalanceSheetIdentityError,
)
from financial_core.engines.firm_value_added_bridge_engine import FirmFinancialFact
from financial_core.engines.forensic_surgical_scalpel import (
    ForensicSurgicalScalpel,
    ForensicInputData,
)
from financial_core.pipeline import SystemicCompanyInput


class TestFilingMapperBalance(unittest.TestCase):
    """【单元与集成测试】财报底账摄入、资产负债刚性平账自检与法证联动测试套件."""

    def test_verify_balance_sheet_identity_strict_boundary(self):
        """【UT-FILING-01: 资产负债表千分之一刚性平账自检边界断言】

        1. 测试功能与测试点:
           - 验证 OfficialFilingMapper.verify_balance_sheet_identity 资产负债平账公式:
             Total Assets = Total Liabilities + Stockholders' Equity
           - 验证 ±0.1% (千分之一) 相对容差边界处理，确保真实舍入误差可通过，破损数据被刚性熔断阻断。

        2. 正常函数业务边界与参数契约:
           - total_assets: 浮点数，必须 > 0.0。
           - total_liabilities: 浮点数，>= 0.0。
           - stockholders_equity: 浮点数，有限实数（允许资不抵债负净资产）。
           - 相对偏差 rel_diff = |Assets - (Liabilities + Equity)| / Assets。
           - 若 rel_diff <= 0.0010，返回 (True, diff, rel_diff)；若 > 0.0010，刚性抛出 BalanceSheetIdentityError。

        3. 测试数据与模拟场景说明:
           - 场景 1 (完全平账): Assets=1000.0, Liab=600.0, Eq=400.0，偏差恒等于 0.0。
           - 场景 2 (允许微小舍入误差): Assets=1,000,000.0, Liab=599,700.0, Eq=400,000.0 (差异 300，偏差 0.03% < 0.10%)。
           - 场景 3 (破损超限拦截): Assets=1,000,000.0, Liab=600,000.0, Eq=401,500.0 (差异 1,500，偏差 0.15% > 0.10%)。

        4. 预期断言与结果验证:
           - 场景 1 & 2 断言 is_ok 为 True，rel_diff 小于 0.0010。
           - 场景 3 断言触发 with self.assertRaises(BalanceSheetIdentityError)，且异常信息明确指出超出 0.1% 容差。
        """
        # 1. 严格平账 (1000 = 600 + 400)
        is_ok, diff, rel_diff = OfficialFilingMapper.verify_balance_sheet_identity(
            total_assets=1000.0,
            total_liabilities=600.0,
            stockholders_equity=400.0,
        )
        self.assertTrue(is_ok)
        self.assertEqual(diff, 0.0)
        self.assertEqual(rel_diff, 0.0)

        # 2. 允许微小舍入误差 (如 1,000,000 资产，差异 500，偏差 0.05% < 0.10%)
        is_ok_round, diff_round, rel_round = OfficialFilingMapper.verify_balance_sheet_identity(
            total_assets=1_000_000.0,
            total_liabilities=599_700.0,
            stockholders_equity=400_000.0, # 差异 300, 相对 0.03%
        )
        self.assertTrue(is_ok_round)
        self.assertEqual(diff_round, 300.0)
        self.assertLess(rel_round, 0.0010)

        # 3. 破损超限 (如 1,000,000 资产，差异 1,500，偏差 0.15% > 0.10%)，必须阻断抛出 BalanceSheetIdentityError
        with self.assertRaises(BalanceSheetIdentityError) as ctx:
            OfficialFilingMapper.verify_balance_sheet_identity(
                total_assets=1_000_000.0,
                total_liabilities=600_000.0,
                stockholders_equity=401_500.0, # 差异 1,500
            )
        self.assertIn("超出 0.1% 刚性容差限度", str(ctx.exception))

    def test_map_sec_edgar_filing_dual_contracts(self):
        """【UT-FILING-02: SEC EDGAR 官方10-K事实底账双向契约映射】

        1. 测试功能与测试点:
           - 验证将 SEC EDGAR 官方 10-K 原生 XBRL 事实标签字典同时映射为系统两大数据契约:
             A) SystemicCompanyInput (全量美金绝对标量)
             B) FirmFinancialFact (统一标准化百万美元量纲)
           - 验证现金流勾稽: FCF = CFO - CapEx。
           - 验证总市值计算: MarketCap = SharesOutstanding * Price。

        2. 正常函数业务边界与参数契约:
           - financial_unit: 'usd_million'，表示事实金额以百万美元计。
           - facts 包含必需三表核心项目，且资产负债必须满足平账前置校验。

        3. 测试数据与模拟场景说明:
           - 标的: 微软 (MSFT) 2024 财年真实官方三表底账。
           - 输入数据: 营收 245,123M, 资产 512,163M, 负债 243,686M, 权益 268,477M (平账 243686 + 268477 = 512163)。
           - 经营现金流 118,548M, 资本开支 44,477M, 股本 7,430M 股, 现价 $420.0。

        4. 预期断言与结果验证:
           - 断言 comp_input 为 SystemicCompanyInput 实例，绝对金额单位正确放大 10^6。
           - 断言 firm_fact 为 FirmFinancialFact 实例，annual_fcf_million 精确等于 74,071.0。
           - 断言市值 market_cap_billion 精确约等于 3,120.6B 美元。
        """
        sec_filing = {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "market": "US",
            "financial_unit": "usd_million",
            "facts": {
                "Revenues": 245123.0,
                "OperatingIncomeLoss": 109433.0,
                "NetIncomeLoss": 88136.0,
                "Assets": 512163.0,
                "Liabilities": 243686.0,
                "StockholdersEquity": 268477.0, # 243686 + 268477 = 512163 (完美平账)
                "NetCashProvidedByUsedInOperatingActivities": 118548.0,
                "PaymentsToAcquirePropertyPlantAndEquipment": 44477.0,
                "CashAndCashEquivalentsAtCarryingValue": 34700.0,
                "CommonStockSharesOutstanding": 7430.0,
                "market_price": 420.0,
                "sector": "Information Technology",
                "sector_id": "TECH_SOFTWARE",
            }
        }

        comp_input, firm_fact = OfficialFilingMapper.map_sec_edgar_filing(sec_filing)

        # 验证 SystemicCompanyInput (全量美金绝对值)
        self.assertIsInstance(comp_input, SystemicCompanyInput)
        self.assertEqual(comp_input.ticker, "MSFT")
        self.assertEqual(comp_input.reported_revenue, 245123.0 * 1_000_000.0)
        self.assertEqual(comp_input.reported_operating_income, 109433.0 * 1_000_000.0)
        self.assertEqual(comp_input.total_assets, 512163.0 * 1_000_000.0)
        self.assertEqual(comp_input.total_liabilities, 243686.0 * 1_000_000.0)
        self.assertEqual(comp_input.stockholders_equity, 268477.0 * 1_000_000.0)
        self.assertEqual(comp_input.current_price, 420.0)

        # 验证 FirmFinancialFact (百万美元标准化)
        self.assertIsInstance(firm_fact, FirmFinancialFact)
        self.assertEqual(firm_fact.ticker, "MSFT")
        self.assertEqual(firm_fact.sector_id, "TECH_SOFTWARE")
        self.assertEqual(firm_fact.revenue_million, 245123.0)
        self.assertEqual(firm_fact.capex_million, 44477.0)
        # FCF = 118548 - 44477 = 74071
        self.assertEqual(firm_fact.annual_fcf_million, 74071.0)
        self.assertEqual(firm_fact.country_id, "US")
        # 市值 = 7430M shares * $420 = 3120.6B
        self.assertAlmostEqual(firm_fact.market_cap_billion, 3120.6, places=1)

    def test_map_jpx_edinet_filing_and_currency(self):
        """【UT-FILING-03: JPX EDINET日文决算短信科目与亿元量纲计价映射】

        1. 测试功能与测试点:
           - 验证东证 EDINET / TDnet 日文财报决算短信（Kessan Tanshin）专属科目字典映射解析。
           - 验证日股独有的“億円 (jpy_hundred_million)”向系统标准“百万单位 (million)”和绝对元单位的数学转换。

        2. 正常函数业务边界与参数契约:
           - financial_unit: 'jpy_hundred_million' (1 億円 = 100 百万円 = 10^8 円)。
           - 日文原件标签包括: '売上高', '営業利益', '総資産', '負債合計', '純資産', '営業活動によるキャッシュフロー', '設備投資'。

        3. 测试数据与模拟场景说明:
           - 标的: 东京电子 (Tokyo Electron 8035.T) 真实决算短信。
           - 营收 18,305 億円, 营业利润 4,562 億円, 总资产 22,450 億円, 负债 6,850 億円, 净资产 15,600 億円 (平账 6850 + 15600 = 22450)。
           - 经营现金流 4,120 億円, 设备投资 1,250 億円, 现价 24,500 円。

        4. 预期断言与结果验证:
           - 断言 comp_input.reported_revenue 正确转换为 18305.0 * 10^8 円。
           - 断言 firm_fact.revenue_million 正确转换为 1,830,500 百万円。
           - 断言 firm_fact.annual_fcf_million 正确计算为 (4120 - 1250) * 100 = 287,000 百万円。
        """
        jpx_filing = {
            "ticker": "8035.T",
            "company_name": "東京エレクトロン株式会社",
            "market": "JP",
            "currency": "JPY",
            "financial_unit": "jpy_hundred_million", # 億円
            "facts": {
                "売上高": 18305.0, # 1兆8305億円
                "営業利益": 4562.0,
                "当期純利益": 3639.0,
                "総資産": 22450.0,
                "負債合計": 6850.0,
                "純資産": 15600.0, # 6850 + 15600 = 22450 (平账)
                "営業活動によるキャッシュフロー": 4120.0,
                "設備投資": 1250.0,
                "現金及び預金": 4800.0,
                "発行済株式総数": 4.65, # 4.65 亿股
                "market_price": 24500.0,
                "sector": "Semiconductor Equipment",
                "sector_id": "TECH_SEMI",
            }
        }

        comp_input, firm_fact = OfficialFilingMapper.map_jpx_edinet_filing(jpx_filing)

        # 验证 SystemicCompanyInput
        self.assertIsInstance(comp_input, SystemicCompanyInput)
        self.assertEqual(comp_input.ticker, "8035.T")
        # 18305 * 100_000_000 = 1,830,500,000,000
        self.assertEqual(comp_input.reported_revenue, 18305.0 * 100_000_000.0)
        self.assertEqual(comp_input.current_price, 24500.0)

        # 验证 FirmFinancialFact (百万为基准)
        # 18305 億円 = 1,830,500 百万円
        self.assertIsInstance(firm_fact, FirmFinancialFact)
        self.assertEqual(firm_fact.ticker, "8035.T")
        self.assertEqual(firm_fact.market, "JP")
        self.assertEqual(firm_fact.country_id, "JP")
        self.assertEqual(firm_fact.revenue_million, 18305.0 * 100.0)
        self.assertEqual(firm_fact.annual_fcf_million, (4120.0 - 1250.0) * 100.0)

    def test_broken_filing_balance_raises_error(self):
        """【UT-FILING-04: 破损财报底账不平衡物理阻断与异常抛出】

        1. 测试功能与测试点:
           - 验证当底账中存在资产负债表严重不平衡（Assets != Liabilities + Equity）时，主管道能够物理中断，严禁破损数据进入分析流水线。

        2. 正常函数业务边界与参数契约:
           - map_sec_edgar_filing 内部在实例化数据对象前，强制前置调用 verify_balance_sheet_identity。

        3. 测试数据与模拟场景说明:
           - 模拟伪造或损坏的假财报: 资产 5,000M, 负债 2,000M, 所有者权益 2,500M。
           - 负债与权益之和为 4,500M，较资产 5,000M 缺失 500M，相对偏差高达 10.0% (远超 0.1% 容差)。

        4. 预期断言与结果验证:
           - 断言调用 map_sec_edgar_filing 时立即抛出 BalanceSheetIdentityError 异常。
        """
        broken_filing = {
            "ticker": "FRAUD_INC",
            "company_name": "Broken Balance Sheet Corp",
            "financial_unit": "usd_million",
            "facts": {
                "Revenues": 1000.0,
                "OperatingIncomeLoss": 200.0,
                "NetIncomeLoss": 150.0,
                "Assets": 5000.0,
                "Liabilities": 2000.0,
                "StockholdersEquity": 2500.0, # 2000 + 2500 = 4500 != 5000 (差异 500, 相对偏差 10%)
            }
        }

        with self.assertRaises(BalanceSheetIdentityError):
            OfficialFilingMapper.map_sec_edgar_filing(broken_filing)

    def test_sec_filing_footnotes_parsing(self):
        """【UT-FILING-05: SEC 10-K 附注深层事实标签多维提取解析】

        1. 测试功能与测试点:
           - 验证 SEC 10-K 官方附注细分标签的提取映射能力，涵盖：存货三阶段构成（原材料、在制品、产成品）、研发费用与软件资本化、受限资金与借款契约补偿性余额、大客户集中度。

        2. 正常函数业务边界与参数契约:
           - 附注细分字段为可选或特定行业强制项，缺失时平滑回退，提供时精确映射。

        3. 测试数据与模拟场景说明:
           - 标的: TECH，提供原材料 400M、在制品 600M、产成品 1200M；研发总额 1500M，软件资本化 300M (资本化率 20%)；受限资金 600M，借款契约最低保证金 500M；第一大客户占比 35% 且带有风险标记。

        4. 预期断言与结果验证:
           - 断言 comp_input 各附注字段均精确映射并转换为元（* 10^6）。
           - 断言 top_customer_share 等于 0.35 且 top_customer_risk_flag 为 True。
        """
        sec_footnote_filing = {
            "ticker": "TECH",
            "company_name": "Tech Innovations Inc.",
            "financial_unit": "usd_million",
            "facts": {
                "Revenues": 10000.0,
                "OperatingIncomeLoss": 2000.0,
                "NetIncomeLoss": 1500.0,
                "Assets": 20000.0,
                "Liabilities": 8000.0,
                "StockholdersEquity": 12000.0,
                "CashAndCashEquivalentsAtCarryingValue": 3000.0,
                # 附注标签
                "InventoryRawMaterialsAndSupplies": 400.0,
                "InventoryWorkInProcess": 600.0,
                "InventoryFinishedGoods": 1200.0,
                "ResearchAndDevelopmentExpense": 1500.0,
                "CapitalizedComputerSoftwareGross": 300.0, # 资本化比率 300 / 1500 = 20% > 12%
                "RestrictedCashAndCashEquivalentsAtCarryingValue": 600.0, # 受限 20%
                "CompensatingBalances": 500.0,
                "top_customer_share": 0.35,
                "top_customer_risk_flag": True,
            }
        }

        comp_input, _ = OfficialFilingMapper.map_sec_edgar_filing(sec_footnote_filing)

        self.assertEqual(comp_input.raw_materials, 400.0 * 1_000_000.0)
        self.assertEqual(comp_input.work_in_process, 600.0 * 1_000_000.0)
        self.assertEqual(comp_input.finished_goods, 1200.0 * 1_000_000.0)
        self.assertEqual(comp_input.total_rd_spent, 1500.0 * 1_000_000.0)
        self.assertEqual(comp_input.capitalized_rd_amount, 300.0 * 1_000_000.0)
        self.assertEqual(comp_input.restricted_cash, 600.0 * 1_000_000.0)
        self.assertEqual(comp_input.debt_covenant_min_cash, 500.0 * 1_000_000.0)
        self.assertEqual(comp_input.top_customer_share, 0.35)
        self.assertTrue(comp_input.top_customer_risk_flag)

    def test_jpx_filing_footnotes_parsing(self):
        """【UT-FILING-06: JPX EDINET 决算短信日文附注标签多维提取解析】

        1. 测试功能与测试点:
           - 验证东证有価証券報告書及短信日文附注标签的提取能力：包括原材料及び貯蔵品、仕掛品、商品及び製品、研究開発費、開発費、担保預金。

        2. 正常函数业务边界与参数契约:
           - 量纲: 'jpy_hundred_million' (億円)。日文特定财务术语同义词归一化。

        3. 测试数据与模拟场景说明:
           - 标的: 索尼集团 (Sony 6758.T)，提供原材料 3500 億円、仕挂品 2200 億円、制品 4300 億円、研发费 7500 億円、开发费资本化 1200 億円、担保预金 1500 億円。

        4. 预期断言与结果验证:
           - 断言各项日文附注均成功提取并正确放大 10^8 円。
        """
        jpx_footnote_filing = {
            "ticker": "6758.T",
            "company_name": "ソニーグループ株式会社",
            "market": "JP",
            "currency": "JPY",
            "financial_unit": "jpy_hundred_million",
            "facts": {
                "売上高": 130000.0,
                "営業利益": 12000.0,
                "当期純利益": 9700.0,
                "総資産": 320000.0,
                "負債合計": 240000.0,
                "純資産": 80000.0,
                "現金及び預金": 18000.0,
                # 日文附注
                "原材料及び貯蔵品": 3500.0,
                "仕掛品": 2200.0,
                "商品及び製品": 4300.0,
                "研究開発費": 7500.0,
                "開発費": 1200.0,
                "担保預金": 1500.0,
            }
        }

        comp_input, _ = OfficialFilingMapper.map_jpx_edinet_filing(jpx_footnote_filing)

        self.assertEqual(comp_input.raw_materials, 3500.0 * 100_000_000.0)
        self.assertEqual(comp_input.work_in_process, 2200.0 * 100_000_000.0)
        self.assertEqual(comp_input.finished_goods, 4300.0 * 100_000_000.0)
        self.assertEqual(comp_input.total_rd_spent, 7500.0 * 100_000_000.0)
        self.assertEqual(comp_input.capitalized_rd_amount, 1200.0 * 100_000_000.0)
        self.assertEqual(comp_input.restricted_cash, 1500.0 * 100_000_000.0)

    def test_forensic_scalpel_integration_with_mapped_footnotes(self):
        """【IT-FILING-07: 财报附注底账与法证手术刀全息联动削减】

        1. 测试功能与测试点:
           - 验证从 SEC 底账提取的附注标签完整流经 ForensicSurgicalScalpel（法证手术刀）核心引擎。
           - 验证四大买方机构致命红旗检出与利润/估值惩罚性削减:
             1) 资金受限红旗
             2) 激进研发资本化红旗与营业利润真实还原
             3) 产成品库存飙升滞销红旗
             4) 大客户单一依赖脆弱性红旗

        2. 正常函数业务边界与参数契约:
           - 资本化研发费用必须从报告营业利润中刚性扣除: True Operating Income = Reported Operating Income - Capitalized R&D。
           - 估值折价率综合累计 haircut_pct > 20%。

        3. 测试数据与模拟场景说明:
           - 构造激进财技企业 RISK_TECH: 报告营业利润 800M，研发费用资本化 250M (资本化率 25% 远超 12% 警戒线)；现金 1000M 中受限 250M、补偿余额 100M；产成品库存从 400M 飙升至 800M (+100%)，而营收增速仅 10%；单一客户占比 40%。

        4. 预期断言与结果验证:
           - 断言红旗文本中命中全部四大致命警报。
           - 断言真实营业利润被核减至 550M (800M - 250M)。
           - 断言权益折价率 final_equity_value_haircut_pct > 20.0%。
        """
        sec_filing = {
            "ticker": "RISK_TECH",
            "company_name": "Aggressive Capitalizer Corp",
            "financial_unit": "usd_million",
            "facts": {
                "Revenues": 5000.0,
                "OperatingIncomeLoss": 800.0,
                "NetIncomeLoss": 600.0,
                "Assets": 10000.0,
                "Liabilities": 4000.0,
                "StockholdersEquity": 6000.0,
                "CashAndCashEquivalentsAtCarryingValue": 1000.0,
                "InventoryRawMaterials": 200.0,
                "InventoryWorkInProcess": 300.0,
                "InventoryFinishedGoods": 800.0,
                "prior_finished_goods": 400.0, # 产成品翻倍 (+100%)
                "revenue_growth_pct": 0.10,     # 营收仅增长 10%, 产成品激增滞销
                "ResearchAndDevelopmentExpense": 1000.0,
                "CapitalizedComputerSoftwareGross": 250.0, # 25% 研发支出资本化 (远超 12% 红线)
                "RestrictedCashAndCashEquivalentsAtCarryingValue": 250.0, # 25% 受限
                "CompensatingBalances": 100.0,
                "top_customer_share": 0.40,
                "top_customer_risk_flag": True,
            }
        }

        comp_input, _ = OfficialFilingMapper.map_sec_edgar_filing(sec_filing)

        # 构造法证输入并执行手术刀
        forensic_input = ForensicInputData(
            ticker=comp_input.ticker,
            company_name=comp_input.company_name,
            reported_cash_and_equivalents=comp_input.reported_cash,
            restricted_cash_in_notes=comp_input.restricted_cash,
            debt_covenant_minimum_cash=comp_input.debt_covenant_min_cash,
            raw_materials=comp_input.raw_materials,
            work_in_process=comp_input.work_in_process,
            finished_goods=comp_input.finished_goods,
            prior_finished_goods=comp_input.prior_finished_goods,
            revenue_growth_pct=comp_input.revenue_growth_pct,
            total_rd_spent=comp_input.total_rd_spent,
            capitalized_rd_amount=comp_input.capitalized_rd_amount,
            reported_operating_income=comp_input.reported_operating_income,
            reported_net_income=comp_input.reported_net_income,
            top_customer_share=comp_input.top_customer_share,
            top_customer_risk_flag=comp_input.top_customer_risk_flag,
        )

        scalpel = ForensicSurgicalScalpel()
        res = scalpel.dissect(forensic_input)

        # 断言: 检出受限现金、研发资本化、存货激增、大客户替代四大致命红旗
        red_flag_text = " ".join(res.forensic_red_flags)
        self.assertIn("受限资金占比高达", red_flag_text)
        self.assertIn("研发支出资本化", red_flag_text)
        self.assertIn("产成品库存飙升", red_flag_text)
        self.assertIn("高危单点依赖", red_flag_text)

        # 真实营业利润被削减 (800M - 250M = 550M)
        self.assertEqual(res.true_operating_income, (800.0 - 250.0) * 1_000_000.0)
        self.assertGreater(res.final_equity_value_haircut_pct, 20.0)


if __name__ == "__main__":
    unittest.main()
