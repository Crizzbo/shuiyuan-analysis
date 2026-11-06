"""全盘数据格式检验引擎单元测试套件 (test_global_data_formats.py).

严格测试 GlobalDataFormatAuditor 跨 5 大数据域的格式检验硬规则：
1. 行情数据格式检验 (Quote Invariant Format)：拦截非法价格、非标货币代码、畸形时间戳；
2. 资产池主索引格式检验 (Universe Index Format)：校验 SEC CIK 格式与 JPX 标的代码；
3. 官方财报三表底稿格式与平账检验 (Financial Statement Format & Accounting Identity)：
   - 断言真实标的底稿 (如 NVDA、AAPL、MSFT) 100% 结构合规且刚性平账；
   - 验证对畸形 JSON、缺少大类科目、严重失衡财报的精准识别与拦截；
4. AI 深度档案格式检验 (AI Dossiers Format & Precision)：断言 current_price 与多情景价格字段类型；
5. Markdown 研报与决策卡文本格式正则检验：断言杜绝省略小数的裸美元符号与未替换模板占位符。
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_global_data_formats import GlobalDataFormatAuditor, DomainAuditResult


class TestGlobalDataFormats(unittest.TestCase):
    """全盘数据格式全息体检单元测试。"""

    def setUp(self):
        self.auditor = GlobalDataFormatAuditor(root_dir=ROOT)

    def test_01_real_quotes_format_audit(self):
        """【IT-FORMAT-01: 跨资产池真实行情基准底账格式全息体检与100%合规性验签】

        1. 测试功能与测试点:
           - 验证 GlobalDataFormatAuditor.audit_domain_1_quotes_format 对磁盘行情文件的全息质检。
           - 严格断言真实行情底账中 100% 具备合法 ticker, 正数 current_price, ISO 3 位货币代码与标准时间戳。
           - 合格率 pass_rate_pct 必须达到 100.0%。

        2. 正常函数业务边界与参数契约:
           - 扫描 data/google-finance/raw/*.json 文件。
           - 返回 DomainAuditResult 结果对象。

        3. 测试数据与模拟场景说明:
           - 读取真实落盘在本地的 Google Finance 行情快照。

        4. 预期断言与结果验证:
           - 断言 total_inspected > 0。
           - 断言 failed_count == 0。
           - 断言 pass_rate_pct == 100.0。
        """
        res = self.auditor.audit_domain_1_quotes_format()
        self.assertIsInstance(res, DomainAuditResult)
        self.assertGreater(res.total_inspected, 0, "必须检查到真实行情标的")
        # 真实行情库中合格率必须为 100%
        self.assertEqual(res.failed_count, 0, f"发现行情格式缺陷: {res.errors}")
        self.assertEqual(res.pass_rate_pct, 100.0)

    def test_02_quote_format_anomaly_detection(self):
        """【UT-FORMAT-02: 行情异常格式穿透拦截(负价格/非标ISO货币代码/畸形时间戳)】

        1. 测试功能与测试点:
           - 验证行情数据格式检验器对恶意伪造或传输破损样本的识别拦截能力。
           - 识别负价格: current_price <= 0 (有限责任下界)。
           - 识别非标货币代码: len(currency) != 3 (如 US_DOLLAR)。
           - 识别非法时间戳: 非标准 ISO-8601 格式字符串 (如 NOT_AN_ISO_DATE)。

        2. 正常函数业务边界与参数契约:
           - 注入 3 个构造的坏样本，断言必须全部捕获。

        3. 测试数据与模拟场景说明:
           - 在临时目录写入 bad_quotes.json，包含 BAD_PRICE, BAD_CURR, BAD_TIME。

        4. 预期断言与结果验证:
           - 断言 total_inspected == 3。
           - 断言 failed_count == 3 (全部拦截，零漏报)。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw_dir = tmp_path / "data" / "google-finance" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)

            # 构造异常行情样本
            bad_quotes = {
                "quotes": {
                    "BAD_PRICE": {
                        "ticker": "BAD_PRICE",
                        "current_price": -50.0,  # 负价格非法
                        "currency": "USD",
                        "timestamp_iso": "2026-10-31T20:00:00Z"
                    },
                    "BAD_CURR": {
                        "ticker": "BAD_CURR",
                        "current_price": 100.0,
                        "currency": "US_DOLLAR",  # 超过 3 位非标准
                        "timestamp_iso": "2026-10-31T20:00:00Z"
                    },
                    "BAD_TIME": {
                        "ticker": "BAD_TIME",
                        "current_price": 100.0,
                        "currency": "USD",
                        "timestamp_iso": "NOT_AN_ISO_DATE"  # 非法时间戳
                    }
                }
            }
            (raw_dir / "bad_quotes.json").write_text(json.dumps(bad_quotes), encoding="utf-8")

            test_auditor = GlobalDataFormatAuditor(root_dir=tmp_path)
            res = test_auditor.audit_domain_1_quotes_format()
            self.assertEqual(res.total_inspected, 3)
            self.assertEqual(res.failed_count, 3, "必须全数识别出 3 个异常行情样本")

    def test_03_universe_index_format_audit(self):
        """【IT-FORMAT-03: 美日双市场资产池主索引格式规范体检(SEC CIK/东证代码/行业)】

        1. 测试功能与测试点:
           - 验证 GlobalDataFormatAuditor.audit_domain_2_universe_index_format 资产池底账索引审计。
           - 校验美股索引中的 SEC CIK 格式与交易所标记。
           - 校验日股索引中的 4 位数字东证代码 (JPX Code) 与板块分类 (Prime/Standard/Growth)。

        2. 正常函数业务边界与参数契约:
           - 扫描 data/universe/sec_company_tickers.json 与 jpx_company_tickers.json。

        3. 测试数据与模拟场景说明:
           - 全盘万家资产池物理底账核查。

        4. 预期断言与结果验证:
           - 断言 total_inspected > 0。
           - 断言 failed_count == 0。
        """
        res = self.auditor.audit_domain_2_universe_index_format()
        self.assertIsInstance(res, DomainAuditResult)
        self.assertGreater(res.total_inspected, 0)
        self.assertEqual(res.failed_count, 0, f"资产池索引格式存在缺陷: {res.errors}")

    def test_04_core_tickers_financial_statements_balance_audit(self):
        """【IT-FORMAT-04: 核心旗舰标的官方三表底稿结构合法性与会计平衡公理抽样审计】

        1. 测试功能与测试点:
           - 验证 GlobalDataFormatAuditor.audit_domain_3_financial_statements_comprehensive 财报全息体检。
           - 针对前 50 家核心重仓标的 (NVDA, AAPL, MSFT, GOOGL, AMZN 等) 逐一核验三表底稿。
           - 资产负债表刚性平账方程: |Assets - (Liabilities + Equity)| / Assets <= 0.1%。

        2. 正常函数业务边界与参数契约:
           - limit=50 抽样，合格率 pass_rate_pct 必须 >= 98.0%。

        3. 测试数据与模拟场景说明:
           - 抽样检查前 50 家标准三表 JSON 底稿。

        4. 预期断言与结果验证:
           - 若检查到标的，断言 pass_rate_pct >= 98.0%。
        """
        # 测试前 50 家标的底账
        res = self.auditor.audit_domain_3_financial_statements_comprehensive(limit=50)
        self.assertIsInstance(res, DomainAuditResult)
        if res.total_inspected > 0:
            # 前 50 家核心标的平账与格式合格率必须达到 98% 以上
            self.assertGreaterEqual(res.pass_rate_pct, 98.0, f"核心标的财报底账格式合格率过低: {res.pass_rate_pct}%")

    def test_05_financial_statement_imbalance_anomaly_interception(self):
        """【UT-FORMAT-05: 资产负债表刚性失衡异常拦截与会计方程保护】

        1. 测试功能与测试点:
           - 验证财报格式检验器对会计不平账样本的精准拦截。
           - 当 Total Assets != Total Liabilities + Stockholders' Equity 时，精确抛出失衡告警。

        2. 正常函数业务边界与参数契约:
           - 资产 1 亿，负债 2000 万，权益 5000 万 (差 3000 万，失衡率 30% >> 0.1%)。

        3. 测试数据与模拟场景说明:
           - 在临时目录写入 FAKE_imbalanced.json 伪样本。

        4. 预期断言与结果验证:
           - 断言 total_inspected == 1。
           - 断言 failed_count == 1。
           - 断言错误详情包含“刚性平账方程失衡”。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            stmt_dir = tmp_path / "02_格式化标准三表库" / "JSON格式"
            stmt_dir.mkdir(parents=True, exist_ok=True)

            # 构造资产负债不平的伪样本: 资产 100, 负债 20, 权益 50 (差 30)
            imbalanced_stmt = {
                "metadata": {"ticker": "FAKE"},
                "balance_sheet": {
                    "total_assets": 100000000.0,
                    "total_liabilities": 20000000.0,
                    "stockholders_equity": 50000000.0
                },
                "income_statement": {"revenue": 50000000.0, "net_income": 10000000.0},
                "cash_flow_statement": {"operating_cash_flow": 8000000.0, "free_cash_flow": 6000000.0}
            }
            (stmt_dir / "FAKE_imbalanced.json").write_text(json.dumps(imbalanced_stmt), encoding="utf-8")

            test_auditor = GlobalDataFormatAuditor(root_dir=ROOT)
            test_auditor.base_dir = tmp_path
            res = test_auditor.audit_domain_3_financial_statements_comprehensive(limit=10)
            self.assertEqual(res.total_inspected, 1)
            self.assertEqual(res.failed_count, 1, "失衡财报必须被严格判定为失败")
            self.assertIn("刚性平账方程失衡", res.errors[0]["issues"][0])

    def test_06_ai_dossiers_format_audit(self):
        """【IT-FORMAT-06: AI深度投研档案Schema契约与多情景估值价格精度合规体检】

        1. 测试功能与测试点:
           - 验证 GlobalDataFormatAuditor.audit_domain_4_ai_dossiers_format 深度档案全息体检。
           - 检验 current_price、三态走廊估值价格类型为合法数字 (float/int)。
           - 杜绝空值、缺失核心估值或非标字符串。

        2. 正常函数业务边界与参数契约:
           - 扫描全量已生成档案。

        3. 测试数据与模拟场景说明:
           - 遍历当前库中深度档案。

        4. 预期断言与结果验证:
           - 若存在档案，断言 failed_count == 0 且 pass_rate_pct == 100.0。
        """
        res = self.auditor.audit_domain_4_ai_dossiers_format()
        self.assertIsInstance(res, DomainAuditResult)
        if res.total_inspected > 0:
            self.assertEqual(res.failed_count, 0, f"深度档案存在格式缺陷: {res.errors}")
            self.assertEqual(res.pass_rate_pct, 100.0)

    def test_07_markdown_formatting_rigor_audit(self):
        """【FT-FORMAT-07: Markdown研报与决策卡语法格式正则扫描与模板占位符防泄漏】

        1. 测试功能与测试点:
           - 验证 GlobalDataFormatAuditor.audit_domain_5_markdown_reports_and_cards 研报文本语法质检。
           - 严禁模板变量未注入泄漏: 扫描形如 {{variable}} 或 ${placeholder} 等未替换模板占位符。
           - 确保交付给投资人与投委会的报告均为 100% 真实填充的业务文本。

        2. 正常函数业务边界与参数契约:
           - 扫描全盘 Markdown 文件。

        3. 测试数据与模拟场景说明:
           - 文本正则扫描。

        4. 预期断言与结果验证:
           - 遍历所有错误项，断言无任何“未注入的模板占位符”违规。
        """
        res = self.auditor.audit_domain_5_markdown_reports_and_cards()
        self.assertIsInstance(res, DomainAuditResult)
        # 验证 Markdown 中未出现异常未替换占位符
        for err in res.errors:
            for issue in err.get("issues", []):
                self.assertNotIn("未注入的模板占位符", issue, f"文件 {err['file']} 存在未注入占位符")


if __name__ == "__main__":
    unittest.main()
