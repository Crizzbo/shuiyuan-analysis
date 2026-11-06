"""金融分析与 Skill 解耦架构综合回归与安全准入测试 (Test Financial Core Decoupling).

覆盖工程整改清单 2026-10-15 各项规范验收：
1. financial_core 金融分析核心独立运行能力 (零依赖 Skill/Agent);
2. 强类型 contracts 契约完整性与 DTO 字典/JSON 序列化;
3. Task 02: 正式入口禁止静默载入演示样本，必须显式声明 allow_demo_sample=True;
4. Task 05 & 06: 时区感知时效性门禁 (实时、延迟、未来时间拒绝、旧日降级、不可变 QuoteSnapshot);
5. Task 07: Stage 1 资产负债表平账失败与非法股数/现价刚性阻断 (BLOCKED_ACCOUNTING_DISCREPANCY);
6. Task 11: 无校准胜率依据时凯利仓位严格为 None (杜绝虚假 5%/15%);
7. Task 12: 现金跑道修正，造血企业不报虚假烧钱跑道;
8. Task 14: 期权未算项显式为 None;
9. Task 15: 按需调度 AnalysisMode.FORENSIC_ONLY;
10. Task 16: 贯穿市场与多币种符号 (USD/$, CNY/¥, JPY/¥);
11. AI 投研日记槽位挂载与 Markdown 决策卡片呈现.
"""

import unittest
from pathlib import Path
import sys
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.api import FinancialAnalysisSystem
from financial_core.contracts import (
    AnalysisMode,
    FinancialAnalysisResult,
    DecisionCardData,
)
from financial_core.pipeline import SystemicCompanyInput
from skill_gateway.freshness import QuoteFreshnessVerifier, QuoteSnapshot
from skill_gateway.gateway import SkillGateway, default_gateway


class TestFinancialCoreDecoupling(unittest.TestCase):
    """测试金融分析核心独立性、解耦架构与安全门禁."""

    def setUp(self):
        self.fin_system = FinancialAnalysisSystem()
        self.gateway = SkillGateway()

    def test_financial_core_independent_execution(self):
        """【IT-DECOUPLE-01: 金融分析核心独立运行与正式环境未核验样本刚性阻断】

        1. 测试功能与测试点:
           - 验证 financial_core 金融分析核心脱离上层 Skill/Agent 上下文独立运行能力。
           - 演示模式: allow_demo_sample=True 时正确运行 RXRX 与五粮液 (000858) 样本。
           - 正式模式: allow_demo_sample=False 时刚性阻断未核验样本，抛出 BLOCKED_MISSING_EVIDENCE。

        2. 正常函数业务边界与参数契约:
           - analyze_equity 接收 ticker 与 allow_demo_sample 标志。
           - 返回 FinancialAnalysisResult 契约对象。

        3. 测试数据与模拟场景说明:
           - 标的: RXRX 与五粮液 (000858)。

        4. 预期断言与结果验证:
           - 演示模式下 execution_success 为 True，包含 decision_card, macro_stress 等。
           - 正式模式下 execution_success 为 False，execution_status == 'BLOCKED_MISSING_EVIDENCE'。
        """
        # 1. 显式开启 allow_demo_sample=True 运行样本
        res_rxrx: FinancialAnalysisResult = self.fin_system.analyze_equity(
            "RXRX", allow_demo_sample=True
        )
        self.assertTrue(res_rxrx.execution_success)
        self.assertEqual(res_rxrx.ticker, "RXRX")
        self.assertTrue(res_rxrx.is_demo_sample)
        self.assertIsInstance(res_rxrx.decision_card, DecisionCardData)
        self.assertGreater(len(res_rxrx.valuation_scenarios), 0)
        self.assertIsNotNone(res_rxrx.macro_stress)
        self.assertIsNotNone(res_rxrx.option_pricing)

        # 验证五粮液 000858
        res_wly: FinancialAnalysisResult = self.fin_system.analyze_equity(
            "000858", allow_demo_sample=True
        )
        self.assertTrue(res_wly.execution_success)
        self.assertEqual(res_wly.ticker, "000858")
        self.assertEqual(res_wly.company_name, "五粮液")
        self.assertGreater(res_wly.decision_card.forensic_red_flags_count, 0)

        # 2. Task 02 阻断测试：正式模式下默认禁止加载未核验的硬编码样本
        res_blocked: FinancialAnalysisResult = self.fin_system.analyze_equity(
            "RXRX", allow_demo_sample=False
        )
        self.assertFalse(res_blocked.execution_success)
        self.assertEqual(res_blocked.execution_status, "BLOCKED_MISSING_EVIDENCE")
        self.assertIn("未提供经核实的官方财报三表底账", res_blocked.block_reason)

    def test_financial_core_contracts_serialization(self):
        """【UT-DECOUPLE-02: 金融契约强类型DTO字典与JSON序列化无损转换】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisResult 契约数据对象的 to_dict() 序列化能力。
           - 验证原生 json.dumps 转换无异常，支持网络/跨进程安全传输。

        2. 正常函数业务边界与参数契约:
           - 序列化生成纯字典，所有内部浮点数与状态枚举无循环引用。

        3. 测试数据与模拟场景说明:
           - 基于 RXRX 分析结果执行序列化。

        4. 预期断言与结果验证:
           - 字典包含 decision_card, valuation_scenarios, raw_forensic_metrics。
           - JSON 字符串包含 'RXRX' 与 'Recursion Pharmaceuticals'。
        """
        res: FinancialAnalysisResult = self.fin_system.analyze_equity(
            "RXRX", allow_demo_sample=True
        )
        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("decision_card", d)
        self.assertIn("valuation_scenarios", d)
        self.assertIn("raw_forensic_metrics", d)

        # 验证 JSON dump 无异常
        json_str = json.dumps(d, ensure_ascii=False)
        self.assertIn("RXRX", json_str)
        self.assertIn("Recursion Pharmaceuticals", json_str)

    def test_quote_freshness_verifier(self):
        """【UT-DECOUPLE-03: 交易时段感知与时效性门禁(盘中实时/延迟/未来时间拦截/旧日降级)】

        1. 测试功能与测试点:
           - 验证 QuoteFreshnessVerifier 的 5 大时效判定状态:
             1. 盘中 <= 20 分钟延迟 -> LIVE_REALTIME (实时行情)；
             2. 盘中 > 20 分钟延迟 -> DELAYED_QUOTE (延迟行情)；
             3. 穿越未来时间戳 -> INVALID_FUTURE_TIME (刚性拦截)；
             4. 跨交易日旧行情 -> PREVIOUS_CLOSE (降级为前收盘基准)；
             5. 休市/收盘时段 -> PREVIOUS_CLOSE。

        2. 正常函数业务边界与参数契约:
           - quote_timestamp 带有效时区，clock_override 用于冻结测试时钟。

        3. 测试数据与模拟场景说明:
           - 美股 2026-10-14 14:35:00 EDT 基准时间。

        4. 预期断言与结果验证:
           - 依次断言各个场景的 freshness_grade 与 display_badge 符合契约。
        """
        tz_ny = ZoneInfo("America/New_York")
        simulated_now = datetime(2026, 10, 14, 14, 35, 0, tzinfo=tz_ny)

        # 1. 盘中常规交易 (延迟 5 分钟 <= 20 分钟 -> 实时行情)
        audit_live = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-14 14:30:00 EDT",
            market_session="regular_trading",
            ticker="RXRX",
            clock_override=simulated_now,
        )
        self.assertTrue(audit_live.is_live_session)
        self.assertEqual(audit_live.freshness_grade, "LIVE_REALTIME")
        self.assertIn("实时行情", audit_live.display_badge)

        # 2. 超过 20 分钟延迟行情 (延迟 40 分钟 -> 降级为 DELAYED_QUOTE)
        audit_delayed = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-14 13:55:00 EDT",
            market_session="regular_trading",
            ticker="RXRX",
            clock_override=simulated_now,
        )
        self.assertFalse(audit_delayed.is_live_session)
        self.assertEqual(audit_delayed.freshness_grade, "DELAYED_QUOTE")
        self.assertIn("延迟行情", audit_delayed.display_badge)

        # 3. 反例：未来时间戳必须刚性拦截 (INVALID_FUTURE_TIME)
        audit_future = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-14 15:30:00 EDT",
            market_session="regular_trading",
            ticker="RXRX",
            clock_override=simulated_now,
        )
        self.assertFalse(audit_future.is_live_session)
        self.assertEqual(audit_future.freshness_grade, "INVALID_FUTURE_TIME")
        self.assertIn("未来时间", audit_future.display_badge)

        # 4. 反例：非同一交易日（旧日）行情降级为前收盘基准 (PREVIOUS_CLOSE)
        audit_old = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-10 14:30:00 EDT",
            market_session="regular_trading",
            ticker="RXRX",
            clock_override=simulated_now,
        )
        self.assertFalse(audit_old.is_live_session)
        self.assertEqual(audit_old.freshness_grade, "PREVIOUS_CLOSE")
        self.assertIn("前收盘基准", audit_old.display_badge)

        # 5. 休市 / 收盘基准
        audit_closed = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-14 15:00:00 CST",
            market_session="closed",
            ticker="000858",
            clock_override=datetime(2026, 10, 14, 18, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        )
        self.assertFalse(audit_closed.is_live_session)
        self.assertIn("前收盘基准", audit_closed.display_badge)

    def test_skill_gateway_adapter(self):
        """【IT-DECOUPLE-04: Skill网关适配器全景集成与买方投研卡输出】

        1. 测试功能与测试点:
           - 验证 SkillGateway.handle_equity_analysis 外部请求接入网关。
           - 组装包含买方独立投研、估值走廊、法证解剖与 AI 投研日记槽位的多模态 Markdown 卡片。

        2. 正常函数业务边界与参数契约:
           - 传入模式与投研日记文本。

        3. 测试数据与模拟场景说明:
           - 标的 RXRX，注入 REC-994 二期临床日记。

        4. 预期断言与结果验证:
           - 决策卡片包含 '买方独立投研'、'Valuation Matrix'、'Forensic Dissection'、'AI Research Journal'。
           - 正式模式 (allow_demo=False) 阻断返回 status == 'blocked'。
        """
        # 允许演示样本模式
        response = self.gateway.handle_equity_analysis(
            ticker="RXRX",
            market_session="regular_trading",
            quote_timestamp="2026-10-14 10:30:00 EDT",
            mode="full_systemic",
            allow_demo=True,
            ai_journal="【AI 投研日记】通过管线穿透分析，REC-994 二期临床临近读出，技术面受做空费率 28.5% 挤压。",
        )
        self.assertIn("买方独立投研", response["markdown_card"])
        self.assertIn("Valuation Matrix", response["markdown_card"])
        self.assertIn("Forensic Dissection", response["markdown_card"])
        self.assertIn("AI Research Journal", response["markdown_card"])
        self.assertIn("REC-994 二期临床临近读出", response["markdown_card"])

        # 正式模式无底账阻断
        blocked_resp = self.gateway.handle_equity_analysis(
            ticker="RXRX",
            allow_demo=False,
        )
        self.assertEqual(blocked_resp["status"], "blocked")
        self.assertEqual(blocked_resp["execution_status"], "BLOCKED_MISSING_EVIDENCE")

    def test_unknown_ticker_handling(self):
        """【UT-DECOUPLE-05: 未知标的底账缺失刚性防御阻断】

        1. 测试功能与测试点:
           - 验证网关针对完全未知且未核验标的的防御性拦截。
           - 拒绝抛出未捕获异常，统一返回强类型阻断信息。

        2. 正常函数业务边界与参数契约:
           - 传入不存在代码 UNKNOWN_TICKER_999。

        3. 测试数据与模拟场景说明:
           - 未建档标的调用。

        4. 预期断言与结果验证:
           - status == 'blocked'。
           - execution_status == 'BLOCKED_MISSING_EVIDENCE'。
        """
        response = self.gateway.handle_equity_analysis("UNKNOWN_TICKER_999")
        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["execution_status"], "BLOCKED_MISSING_EVIDENCE")
        self.assertIn("未提供经核实的官方财报三表底账", response["message"])

    def test_stage_1_balance_sheet_discrepancy_blocking(self):
        """【UT-DECOUPLE-06: 资产负债表刚性失衡异常拦截(BLOCKED_ACCOUNTING_DISCREPANCY)】

        1. 测试功能与测试点:
           - 验证系统级输入在资产 != 负债 + 权益时，直接在工位 1 予以熔断。
           - 杜绝会计失衡数据流入下游任何折现与估值模型。

        2. 正常函数业务边界与参数契约:
           - 失衡率超过容差阀值。

        3. 测试数据与模拟场景说明:
           - 资产 10 亿 != 负债 3 亿 + 权益 6 亿 (差 1 亿)。

        4. 预期断言与结果验证:
           - execution_success 为 False。
           - execution_status == 'BLOCKED_ACCOUNTING_DISCREPANCY'。
        """
        # 构造不平账输入：资产 10亿 != 负债 3亿 + 权益 6亿 (差异 1亿 > 容差 1000万)
        imbalanced_inp = SystemicCompanyInput(
            ticker="IMBALANCED_CORP",
            company_name="Imbalanced Corp",
            sector="General",
            quote_timestamp="2026-10-14 10:00:00 EDT",
            market_session="regular_trading",
            current_price=25.0,
            baseline_reference_price=25.0,
            reported_cash=100_000_000.0,
            restricted_cash=0.0,
            debt_covenant_min_cash=0.0,
            total_debt=100_000_000.0,
            total_assets=1_000_000_000.0,          # 资产 10亿
            total_liabilities=300_000_000.0,       # 负债 3亿
            stockholders_equity=600_000_000.0,     # 权益 6亿 -> 负债+权益 = 9亿 != 10亿
            reported_operating_cash_flow=50_000_000.0,
            reported_capex=20_000_000.0,
            maintenance_capex_ratio=0.7,
            stock_based_compensation=0.0,
            reported_revenue=200_000_000.0,
            reported_operating_income=40_000_000.0,
            reported_net_income=30_000_000.0,
            shares_outstanding=10_000_000,
            us_10y_yield=0.045,
            usdjpy_rate=150.0,
            vix_index=20.0,
            usdjpy_daily_change_pct=0.0,
            company_beta=1.0,
            short_interest_shares=100_000,
            free_float_shares=9_000_000,
            cost_to_borrow_pct=1.0,
            average_volume_30d=500_000,
        )

        res = self.fin_system.analyze_equity("IMBALANCED_CORP", company_input=imbalanced_inp)
        self.assertFalse(res.execution_success)
        self.assertEqual(res.execution_status, "BLOCKED_ACCOUNTING_DISCREPANCY")
        self.assertIn("资产负债表严重失衡", res.block_reason)
        self.assertEqual(res.decision_card.objective_signal, "BLOCKED_ACCOUNTING_DISCREPANCY")

    def test_stage_1_invalid_shares_or_price_blocking(self):
        """【UT-DECOUPLE-07: 非法流通股本与负价格刚性拦截】

        1. 测试功能与测试点:
           - 验证当总流通股本 shares_outstanding <= 0 时，引擎主动拦截除零风险。

        2. 正常函数业务边界与参数契约:
           - shares_outstanding 必须为正整数。

        3. 测试数据与模拟场景说明:
           - 传入 shares_outstanding = 0。

        4. 预期断言与结果验证:
           - execution_status == 'BLOCKED_ACCOUNTING_DISCREPANCY'。
           - block_reason 包含 '非法流通股本'。
        """
        # 股数为 0
        invalid_shares_inp = SystemicCompanyInput(
            ticker="ZERO_SHARES",
            company_name="Zero Shares Corp",
            sector="General",
            quote_timestamp="2026-10-14 10:00:00 EDT",
            market_session="regular_trading",
            current_price=10.0,
            baseline_reference_price=10.0,
            reported_cash=50.0,
            restricted_cash=0.0,
            debt_covenant_min_cash=0.0,
            total_debt=50.0,
            total_assets=200.0,
            total_liabilities=100.0,
            stockholders_equity=100.0,
            reported_operating_cash_flow=20.0,
            reported_capex=10.0,
            maintenance_capex_ratio=0.5,
            stock_based_compensation=0.0,
            reported_revenue=100.0,
            reported_operating_income=20.0,
            reported_net_income=15.0,
            shares_outstanding=0,          # 非法股数
            us_10y_yield=0.045,
            usdjpy_rate=150.0,
            vix_index=20.0,
            usdjpy_daily_change_pct=0.0,
            company_beta=1.0,
            short_interest_shares=0,
            free_float_shares=0,
            cost_to_borrow_pct=1.0,
            average_volume_30d=10_000,
        )
        res = self.fin_system.analyze_equity("ZERO_SHARES", company_input=invalid_shares_inp)
        self.assertFalse(res.execution_success)
        self.assertEqual(res.execution_status, "BLOCKED_ACCOUNTING_DISCREPANCY")
        self.assertIn("非法流通股本", res.block_reason)

    def test_currency_and_market_symbols(self):
        """【UT-DECOUPLE-08: 美中美日跨市场多币种代码与符号推断(USD/CNY/JPY)】

        1. 测试功能与测试点:
           - 验证 infer_market_and_currency 跨市场币种与符号映射。
           - 覆盖美股 (US, USD, $), A股 (CN, CNY, ¥), 日股 (JP, JPY, ¥)。

        2. 正常函数业务边界与参数契约:
           - 接收代码字符串，返回 (market, currency, symbol)。

        3. 测试数据与模拟场景说明:
           - NVDA, 000858, 7203。

        4. 预期断言与结果验证:
           - 美股返回 ('US', 'USD', '$')。
           - A股返回 ('CN', 'CNY', '¥')。
           - 日股返回 ('JP', 'JPY', '¥')。
        """
        # 美股
        m_us, curr_us, sym_us = FinancialAnalysisSystem.infer_market_and_currency("NVDA")
        self.assertEqual((m_us, curr_us, sym_us), ("US", "USD", "$"))

        # A股
        m_cn, curr_cn, sym_cn = FinancialAnalysisSystem.infer_market_and_currency("000858")
        self.assertEqual((m_cn, curr_cn, sym_cn), ("CN", "CNY", "¥"))

        # 日股
        m_jp, curr_jp, sym_jp = FinancialAnalysisSystem.infer_market_and_currency("7203")
        self.assertEqual((m_jp, curr_jp, sym_jp), ("JP", "JPY", "¥"))

    def test_uncalibrated_kelly_is_none(self):
        """【UT-DECOUPLE-09: 无校准胜率依据时凯利仓位严格置空(None)】

        1. 测试功能与测试点:
           - 验证未经历史样本校准胜率时，杜绝硬编码伪造 5% 或 15% 仓位建议。
           - 契约约束 kelly_fraction 必须返回严格 None。

        2. 正常函数业务边界与参数契约:
           - 没有贝叶斯胜率底账时凯利公式置空。

        3. 测试数据与模拟场景说明:
           - RXRX 样本分析。

        4. 预期断言与结果验证:
           - 断言 decision_card.kelly_fraction is None。
        """
        res = self.fin_system.analyze_equity("RXRX", allow_demo_sample=True)
        self.assertIsNone(res.decision_card.kelly_fraction)

    def test_forensic_only_analysis_mode(self):
        """【UT-DECOUPLE-10: 纯法证审计按需轻量调度模式(FORENSIC_ONLY)】

        1. 测试功能与测试点:
           - 验证 mode=AnalysisMode.FORENSIC_ONLY 轻量调度能力。
           - 仅触发财务手术刀法证审计，不调度长短期情景 DCF 与美式期权计算。

        2. 正常函数业务边界与参数契约:
           - AnalysisMode.FORENSIC_ONLY。

        3. 测试数据与模拟场景说明:
           - 五粮液 (000858) 样本。

        4. 预期断言与结果验证:
           - forensic_findings 列表非空。
           - valuation_scenarios 长度为 0，macro_stress 与 option_pricing 均为 None。
        """
        res = self.fin_system.analyze_equity(
            "000858",
            mode=AnalysisMode.FORENSIC_ONLY,
            allow_demo_sample=True,
        )
        self.assertTrue(res.execution_success)
        self.assertEqual(res.analysis_mode, "forensic_only")
        self.assertGreater(len(res.forensic_findings), 0)
        # 验证未调度 DCF 与期权
        self.assertEqual(len(res.valuation_scenarios), 0)
        self.assertIsNone(res.macro_stress)
        self.assertIsNone(res.option_pricing)

    def test_cash_runway_positive_free_cash_flow(self):
        """【UT-DECOUPLE-11: 持续造血企业硬跑道表述修正(持续净现金流入)】

        1. 测试功能与测试点:
           - 验证当企业 FCF > 0 (持续造血) 时，硬现金跑道描述杜绝虚假输出 '315个月' 或 '999个月'。
           - 规范表述为 '持续净现金流入'。

        2. 正常函数业务边界与参数契约:
           - 造血企业现金流判断。

        3. 测试数据与模拟场景说明:
           - 五粮液 (000858)。

        4. 预期断言与结果验证:
           - runway_desc 包含 '持续净现金流入'，绝不包含 '315' 或 '999'。
        """
        res = self.fin_system.analyze_equity("000858", allow_demo_sample=True)
        self.assertTrue(res.execution_success)
        runway_desc = res.decision_card.hard_runway_desc
        self.assertIn("持续净现金流入", runway_desc)
        self.assertNotIn("315", runway_desc)
        self.assertNotIn("999", runway_desc)

    def test_trading_hours_gatekeeper_rejects_midnight_claim(self):
        """【UT-DECOUPLE-12: 交易所钟点纠偏-凌晨休市虚假盘中现价刚性纠偏】

        1. 测试功能与测试点:
           - 验证 QuoteFreshnessVerifier 对虚假声称常规交易 (regular_trading) 的凌晨时间戳纠偏。
           - 美股凌晨 03:00 强制降级并标注为休市前收盘基准。

        2. 正常函数业务边界与参数契约:
           - 闭市钟点核验。

        3. 测试数据与模拟场景说明:
           - 模拟周三凌晨 03:00 EDT。

        4. 预期断言与结果验证:
           - is_live_session 为 False，freshness_grade == 'PREVIOUS_CLOSE'。
           - 包含 '休市' 与 '营业钟点纠偏'。
        """
        tz_ny = ZoneInfo("America/New_York")
        # 设定在周三凌晨 03:00:00 (美股闭市时段)
        midnight_clock = datetime(2026, 10, 14, 3, 5, 0, tzinfo=tz_ny)
        audit_midnight = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-14 03:00:00 EDT",
            market_session="regular_trading",  # 虚假声称常规交易
            ticker="NVDA",
            clock_override=midnight_clock,
        )
        self.assertFalse(audit_midnight.is_live_session)
        self.assertEqual(audit_midnight.freshness_grade, "PREVIOUS_CLOSE")
        self.assertIn("休市", audit_midnight.display_badge)
        self.assertIn("营业钟点纠偏", audit_midnight.session_notice)

    def test_trading_hours_gatekeeper_accepts_valid_intraday(self):
        """【UT-DECOUPLE-13: 交易日标准交易区间实时行情通过校验】

        1. 测试功能与测试点:
           - 验证工作日 09:30-16:00 美股开市区间内，延迟 <= 20 分钟的行情被判定为实时行情。

        2. 正常函数业务边界与参数契约:
           - 采样时间在常规时段内。

        3. 测试数据与模拟场景说明:
           - 周三下午 14:35:00 EDT。

        4. 预期断言与结果验证:
           - is_live_session 为 True，freshness_grade == 'LIVE_REALTIME'，包含 '实时行情'。
        """
        tz_ny = ZoneInfo("America/New_York")
        # 设定在周三下午 14:35:00 (美股 09:30-16:00 常规交易区间)
        intraday_clock = datetime(2026, 10, 14, 14, 35, 0, tzinfo=tz_ny)
        audit_live = QuoteFreshnessVerifier.verify_quote(
            quote_timestamp="2026-10-14 14:30:00 EDT",
            market_session="regular_trading",
            ticker="NVDA",
            clock_override=intraday_clock,
        )
        self.assertTrue(audit_live.is_live_session)
        self.assertEqual(audit_live.freshness_grade, "LIVE_REALTIME")
        self.assertIn("实时行情", audit_live.display_badge)

    def test_negative_equity_company_valuation_protection(self):
        """【UT-DECOUPLE-14: 负净资产/回购型企业(BA/SBUX/MCD)估值模型与除零保护】

        1. 测试功能与测试点:
           - 验证针对负净资产但持续造血企业 (如星巴克、波音、麦当劳) 的除零与负分母保护。
           - 自动接入专用负净资产 DCF 管道，平稳产出正数公允价值。

        2. 正常函数业务边界与参数契约:
           - stockholders_equity < 0, operating_cash_flow > 0。

        3. 测试数据与模拟场景说明:
           - SBUX_MOCK: 资产 200 亿，负债 250 亿，净资产 -50 亿，经营现金流 40 亿。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - neutral_fair_value > 0.0。
           - 估值模型标记包含 'Negative_Equity'。
        """
        # 构造负净资产但持续造血的企业（资产 20亿 = 负债 25亿 + 股东权益 -5亿）
        neg_equity_inp = SystemicCompanyInput(
            ticker="SBUX_MOCK",
            company_name="Starbucks Mock Negative Equity",
            sector="General",
            quote_timestamp="2026-10-14 14:00:00 EDT",
            market_session="regular_trading",
            current_price=85.0,
            baseline_reference_price=90.0,
            reported_cash=2_000_000_000.0,
            restricted_cash=0.0,
            debt_covenant_min_cash=0.0,
            total_debt=15_000_000_000.0,
            total_assets=20_000_000_000.0,
            total_liabilities=25_000_000_000.0,
            stockholders_equity=-5_000_000_000.0,  # 负净资产 -50亿
            reported_operating_cash_flow=4_000_000_000.0,  # 正向造血
            reported_capex=1_000_000_000.0,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=200_000_000.0,
            reported_revenue=30_000_000_000.0,
            reported_operating_income=5_000_000_000.0,
            reported_net_income=3_500_000_000.0,
            shares_outstanding=1_150_000_000,
            us_10y_yield=0.045,
            usdjpy_rate=150.0,
            vix_index=19.0,
            usdjpy_daily_change_pct=0.0,
            company_beta=1.0,
            short_interest_shares=10_000_000,
            free_float_shares=1_100_000_000,
            cost_to_borrow_pct=1.0,
            average_volume_30d=5_000_000,
        )
        res = self.fin_system.analyze_equity("SBUX_MOCK", company_input=neg_equity_inp)
        self.assertTrue(res.execution_success)
        self.assertGreater(res.decision_card.neutral_fair_value, 0.0)
        # 验证估值模型被正确标记为负净资产/回购专用 DCF 管道
        self.assertIn("Negative_Equity", res.valuation_scenarios[0].valuation_model_used)

    def test_official_filing_mapper_seagate(self):
        """【IT-DECOUPLE-15: 希捷科技(STX)官方财报底账自动映射与端到端估值平账】

        1. 测试功能与测试点:
           - 验证 OfficialFilingMapper.load_from_file 解析希捷 (STX) 磁盘真实财报。
           - 资产负债表刚性平账自检，端到端跑通估值引擎。

        2. 正常函数业务边界与参数契约:
           - inputs.json 真实物理存在。

        3. 测试数据与模拟场景说明:
           - 希捷科技 data/seagate/2026-10-11/inputs.json。

        4. 预期断言与结果验证:
           - 资产与负债加权益误差 <= 1.0。
           - execution_success 为 True，中性公允价 > 50.0。
        """
        from financial_core.engines.filing_mapper import OfficialFilingMapper
        stx_json = Path("data/seagate/2026-10-11/inputs.json")
        self.assertTrue(stx_json.exists())

        inp = OfficialFilingMapper.load_from_file(stx_json)
        self.assertEqual(inp.ticker, "STX")
        self.assertAlmostEqual(inp.total_assets, inp.total_liabilities + inp.stockholders_equity, delta=1.0)

        res = self.fin_system.analyze_equity("STX", company_input=inp, allow_demo_sample=True)
        self.assertTrue(res.execution_success)
        self.assertEqual(res.ticker, "STX")
        self.assertGreater(res.decision_card.neutral_fair_value, 50.0)

    def test_run_systemic_equity_analysis_rejects_mock_fallback(self):
        """【IT-DECOUPLE-16: 系统脚本彻底废除假数据模板暗门与权限安全拦截】

        1. 测试功能与测试点:
           - 验证 get_preset_company_input 在未传 allow_demo 时的权限拦截。
           - 严禁对未收录标的静默回退假模板，刚性抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - 未授权访问样本抛出 PermissionError，未核验标的抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 标的 RXRX 与 TSLA。

        4. 预期断言与结果验证:
           - 断言分别抛出 PermissionError 与 ValueError。
        """
        from scripts.run_systemic_equity_analysis import get_preset_company_input
        # 未传 --allow-demo 时访问样本必须阻断
        with self.assertRaises(PermissionError):
            get_preset_company_input("RXRX", allow_demo=False)
        # 未核验标的绝不回退至假模板，必须抛出 ValueError
        with self.assertRaises(ValueError):
            get_preset_company_input("TSLA", allow_demo=True)

    def test_physical_decoupling_zero_finance_tools_dependency(self):
        """【UT-DECOUPLE-17: 架构级单向解耦-financial_core零依赖finance_tools纯净性断言】

        1. 测试功能与测试点:
           - 验证架构红线：financial_core（底层金融核心引擎）必须物理级纯净。
           - 扫描 financial_core 目录下全量 Python 源码，严禁任何代码包含 'finance_tools' 字符串。

        2. 正常函数业务边界与参数契约:
           - 零逆向依赖，底层纯相对导入。

        3. 测试数据与模拟场景说明:
           - 遍历 financial_core 全盘文件。

        4. 预期断言与结果验证:
           - 核心源码文件中 'finance_tools' 出现次数严格为 0。
        """
        core_dir = ROOT / "financial_core"
        py_files = list(core_dir.rglob("*.py"))
        self.assertGreater(len(py_files), 5)
        for pf in py_files:
            content = pf.read_text(encoding="utf-8")
            self.assertNotIn(
                "finance_tools",
                content,
                f"架构违规：物理隔离失败！文件 {pf.relative_to(ROOT)} 中依然残留对 finance_tools 的依赖！"
            )

    def test_unpreset_sample_blocked_not_found(self):
        """【UT-DECOUPLE-18: 未预设演示样本安全阻断(BLOCKED_SAMPLE_NOT_FOUND)】

        1. 测试功能与测试点:
           - 验证当请求标的未在预设样本库时，系统安全输出 BLOCKED_SAMPLE_NOT_FOUND。
           - 拒绝抛出未捕获的 NoneType AttributeError，保障服务鲁棒性。

        2. 正常函数业务边界与参数契约:
           - 输入未收录的 NVDA (演示模式下)。

        3. 测试数据与模拟场景说明:
           - 模拟非预设样本。

        4. 预期断言与结果验证:
           - execution_status == 'BLOCKED_SAMPLE_NOT_FOUND'。
           - 总结词包含 '预设样本未命中阻断'。
        """
        res = self.fin_system.analyze_equity("NVDA", allow_demo_sample=True)
        self.assertFalse(res.execution_success)
        self.assertEqual(res.execution_status, "BLOCKED_SAMPLE_NOT_FOUND")
        self.assertEqual(res.decision_card.objective_signal, "BLOCKED_SAMPLE_NOT_FOUND")
        self.assertIn("预设样本未命中阻断", res.decision_card.summary_verdict)
        self.assertIn("NVDA", res.decision_card.summary_verdict)

    def test_quote_freshness_gateway_dst_and_weekend(self):
        """【UT-DECOUPLE-19: 冬夏令时(EST/EDT)时差与周末闭市精准识别】

        1. 测试功能与测试点:
           - 验证 QuoteFreshnessGateway 对美股冬令时 (EST) 与夏令时 (EDT) 的自动切换。
           - 验证周末闭市硬规则: 周六日即使采样时间在日中，也刚性识别为前收盘基准 (previous_close_baseline)。

        2. 正常函数业务边界与参数契约:
           - 时区解析完全符合 IANA 标准。

        3. 测试数据与模拟场景说明:
           - 冬令时 1 月 14 日 08:45 EST (盘前)。
           - 夏令时 10 月 14 日 14:30 EDT (盘中)。
           - 周末 10 月 17 日周六 11:00 EDT。

        4. 预期断言与结果验证:
           - 冬令时判定为 pre_market，包含 '盘前最新'。
           - 夏令时判定为 regular_trading，包含 '盘中现价'。
           - 周六判定为 previous_close_baseline，包含 '前收盘基准'。
        """
        from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway

        # 1. 冬令时 EST 盘前时段 (08:45 EST -> local 8.75h, 4.0 <= 8.75 < 9.5 为 pre_market)
        res_winter = QuoteFreshnessGateway.verify_quote(
            price=150.0,
            currency="$",
            quote_timestamp="2026-01-14 08:45:00 EST",
            market="US",
            current_time_iso="2026-01-14T13:50:00Z", # UTC 13:50 -> EST 08:50 (采样5分钟前)
        )
        self.assertTrue(res_winter.is_valid)
        self.assertTrue(res_winter.is_fresh_today)
        self.assertEqual(res_winter.session_status, "pre_market")
        self.assertIn("盘前最新", res_winter.formatted_label)

        # 2. 夏令时 EDT 盘中现价 (14:30 EDT -> local 14.5h, 9.5 <= 14.5 <= 16.0 为 regular_trading)
        res_summer = QuoteFreshnessGateway.verify_quote(
            price=132.8,
            currency="$",
            quote_timestamp="2026-10-14 14:30:00 EDT",
            market="US",
            current_time_iso="2026-10-14T18:35:00Z",
        )
        self.assertTrue(res_summer.is_valid)
        self.assertTrue(res_summer.is_fresh_today)
        self.assertEqual(res_summer.session_status, "regular_trading")
        self.assertIn("盘中现价", res_summer.formatted_label)

        # 3. 周末休市判定 (2026-10-17 为周六，即使时间落在 11:00 也必须标记为 previous_close_baseline)
        res_weekend = QuoteFreshnessGateway.verify_quote(
            price=130.0,
            currency="$",
            quote_timestamp="2026-10-17 11:00:00 EDT",
            market="US",
            current_time_iso="2026-10-17T15:05:00Z",
        )
        self.assertTrue(res_weekend.is_valid)
        self.assertEqual(res_weekend.session_status, "previous_close_baseline")
        self.assertIn("前收盘基准", res_weekend.formatted_label)


if __name__ == "__main__":
    unittest.main()

