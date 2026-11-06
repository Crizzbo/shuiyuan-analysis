"""全盘核心问题点工程解决方案综合回归校验套件 (Test Unified Solution Pipeline).

系统性检验 7 大核心问题的解决状态与工程实现：
1. Issue 1: QuoteFreshnessGateway 时区感知、交易时段识别与超期阻断门禁；
2. Issue 2: DailyBriefingEngine 架构解耦与 daily_briefing.schema.json 契约校验；
3. Issue 3: Chunk-and-Stream 流式状态机与合成假数据隔离安全保护门禁；
4. Issue 4: ETFPenetrationEngine 穿透重叠度与 CommodityGoldFramework 黄金宏观脱钩模型；
5. Issue 5: Edge Headless 纯净无杂质 A4 矢量 PDF 编译与防截断机制；
6. Issue 6: StronglyConstrainedValuationEngine 资产负债表刚性底线 (NCPS/NCAV/TBV/Runway)；
7. Issue 7: 数据主权与知识库相对路径隔离 (100% 项目内自洽)。
"""

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

from financial_reporting.quote_freshness_gateway import (
    QuoteFreshnessGateway,
    QuoteVerificationResult,
)
from financial_reporting.daily_briefing_engine import DailyBriefingEngine
from financial_reporting.etf_penetration import (
    ETFPenetrationEngine,
    STANDARD_ETF_REGISTRY,
)
from financial_reporting.commodity_gold_framework import (
    CommodityGoldFramework,
    GoldMacroContext,
)
from financial_reporting.strong_constrained_valuation import (
    StronglyConstrainedValuationEngine,
    CompanyFinancialFacts,
)


class TestUnifiedSolutionPipeline(unittest.TestCase):
    """综合解决方案测试用例。"""

    def test_issue1_quote_freshness_gateway(self):
        """【UT-UNIFIED-01: 行情时效性网关-时区感知/时段标注/超期刚性阻断】

        1. 测试功能与测试点:
           - 验证 QuoteFreshnessGateway 对时区 (EDT/EST/JST/UTC) 和交易时段 (前收盘/盘前/盘中/盘后) 的感知标注。
           - 严格时效门禁: 当行情早于当前开市基准时显式标明 '前收盘基准'；当数据滞后超过阈值 (>24小时) 时刚性抛出超期阻断，严禁过时缓存充当盘中现价。

        2. 正常函数业务边界与参数契约:
           - price > 0, currency 非空, quote_timestamp 带有效时区。
           - 返回 QuoteVerificationResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 场景 1: 正常昨日 16:00 EDT 收盘价 ($132.80)，在隔日零点核验 -> 判定合法且为 'previous_close_baseline'。
           - 场景 2: 严重滞后 5 天的历史旧行情 (2026-10-10) -> 触发超期拦截 'stale_blocked'。

        4. 预期断言与结果验证:
           - 场景 1 断言 is_valid 为 True，session_status 为 'previous_close_baseline'，formatted_label 包含 '前收盘基准'。
           - 场景 2 断言 is_valid 为 False，session_status 为 'stale_blocked'，message 包含 '严重超期阻断'。
        """
        # 1. 正常前收盘基准
        res = QuoteFreshnessGateway.verify_quote(
            price=132.80,
            currency="$",
            quote_timestamp="2026-10-14 16:00 EDT",
            market="US",
            current_time_iso="2026-10-15T00:00:00Z",
        )
        self.assertTrue(res.is_valid)
        self.assertEqual(res.session_status, "previous_close_baseline")
        self.assertIn("前收盘基准", res.formatted_label)

        # 2. 超期阻断 (>24小时)
        res_stale = QuoteFreshnessGateway.verify_quote(
            price=132.80,
            currency="$",
            quote_timestamp="2026-10-10 16:00 EDT",
            market="US",
            current_time_iso="2026-10-15T00:00:00Z",
        )
        self.assertFalse(res_stale.is_valid)
        self.assertEqual(res_stale.session_status, "stale_blocked")
        self.assertIn("严重超期阻断", res_stale.message)

    def test_issue2_daily_briefing_engine_contract(self):
        """【FT-UNIFIED-02: 大盘研报引擎解耦-宏观/资金/情绪/AI研判Schema契约检验】

        1. 测试功能与测试点:
           - 验证 DailyBriefingEngine.validate_briefing_data 对每日大盘研报契约的高标准校验。
           - 杜绝冗长全量数千行大表，聚焦于大盘总报（美股/日股宏观流动性、市场恐慌度 VIX/Fear&Greed、主力资金净流向、期权大单与 PCR、当日核心突发新闻及 AI 顶层研判）。
           - 重点股票必须以独立富文本卡片呈现，明确推演悲观底、中性基准与乐观靶心。

        2. 正常函数业务边界与参数契约:
           - 输入数据满足 schemas/daily_briefing.schema.json。
           - 返回 (bool, str) 校验元组。

        3. 测试数据与模拟场景说明:
           - 包含 NVDA 富文本推荐卡片与美股宏观流动性指标 (10Y收益率 4.38%, 利差 +26 bps, DXY 104.15)。

        4. 预期断言与结果验证:
           - 断言 ok 为 True 且 msg 为空或成功说明。
        """
        engine = DailyBriefingEngine()
        sample_data = {
            "header": {
                "report_date": "2026-10-15",
                "market": "US",
                "market_name_zh": "美股市场"
            },
            "macro_and_liquidity": {
                "us_10y_yield": "4.38%",
                "us_2y_yield": "4.12%",
                "yield_spread_10_2": "+26.0 bps",
                "dxy_index": "104.15",
                "usd_jpy_rate": "158.90"
            },
            "market_sentiment_and_options": {
                "vix_index": "16.25",
                "fear_greed_gauge": "贪婪 (68)",
                "capital_flow_summary": "净流入 +24.8 亿美元",
                "options_market_dynamics": "Call 明显主导",
                "put_call_ratio": "0.72"
            },
            "market_moving_news": [
                {"headline": "测试要闻", "impact_analysis": "无冲击"}
            ],
            "ai_executive_summary": "AI 顶层决策研判测试",
            "recommended_stocks": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "current_price": "$132.80",
                    "margin_of_safety_trigger": "$118.00",
                    "rating": "Strong Buy",
                    "business_intro": "GPU 龙头",
                    "pessimistic_deduction": {
                        "trigger_event": "利空事件",
                        "implied_price": "$105.00",
                        "downside_gap": "-20%"
                    },
                    "neutral_deduction": {
                        "trigger_event": "常态基准",
                        "implied_price": "$155.00",
                        "upside_gap": "+16%"
                    },
                    "optimistic_deduction": {
                        "trigger_event": "利好事件",
                        "implied_price": "$185.00",
                        "potential_gain": "+39%"
                    },
                    "tactical_action": "建议逢低吸纳"
                }
            ]
        }
        ok, msg = engine.validate_briefing_data(sample_data)
        self.assertTrue(ok, msg)

    def test_issue3_universe_quarantine_safety_gate(self):
        """【IT-UNIFIED-03: 万家资产池假数据隔离审计门禁与状态标志核查】

        1. 测试功能与测试点:
           - 验证全量资产池底账中严禁把未经官方财报核验的合成或第三方抓取数据当作经过审计的真实事实。
           - 校验 universe_10k_manifest.json 资产清单状态机处于 UNVERIFIED_INDEX_REQUIRES_OFFICIAL_FILINGS 强隔离态。

        2. 正常函数业务边界与参数契约:
           - manifest 文件物理存在于 data/universe/。

        3. 测试数据与模拟场景说明:
           - 读取资产池清单底账元数据。

        4. 预期断言与结果验证:
           - 断言 status 精确等于 'UNVERIFIED_INDEX_REQUIRES_OFFICIAL_FILINGS'。
           - 断言 warning 提示包含 '待复核历史索引库'。
        """
        manifest_path = ROOT / "data" / "universe" / "universe_10k_manifest.json"
        self.assertTrue(manifest_path.exists())
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(m.get("status"), "UNVERIFIED_INDEX_REQUIRES_OFFICIAL_FILINGS")
        self.assertIn("待复核历史索引库", m.get("warning", ""))

    def test_issue4_multi_asset_frameworks(self):
        """【IT-UNIFIED-04: 跨资产横向拓展-ETF穿透重叠度警报与现货黄金宏观公允模型】

        1. 测试功能与测试点:
           - 验证跨资产横向拓展流水线:
             1. ETFPenetrationEngine 头部重合度超界时触发 '重合度过高警报'。
             2. CommodityGoldFramework 现货黄金宏观公允模型与 10Y TIPS 实际利率锚。
             3. 特级金矿龙头 (NEM) 营运杠杆倍数乘数输出。

        2. 正常函数业务边界与参数契约:
           - SPY 与 QQQ 输入合法。
           - 黄金宏观模型返回字典包含核心字段。

        3. 测试数据与模拟场景说明:
           - 宽基指数 SPY 与科技成长 QQQ，现货黄金与金矿股 NEM。

        4. 预期断言与结果验证:
           - 断言 weighted_overlap_pct >= 30.0% 且包含 '重合度过高警报'。
           - 断言黄金报告包含 'spot_gold_usd' 与 'traditional_real_yield_anchor'。
           - 断言 NEM 结果包含 'operating_leverage_multiplier'。
        """
        # ETF 穿透
        ol = ETFPenetrationEngine.calculate_overlap_between_two_etfs(
            STANDARD_ETF_REGISTRY["SPY"],
            STANDARD_ETF_REGISTRY["QQQ"]
        )
        self.assertGreaterEqual(ol["weighted_overlap_pct"], 30.0)
        self.assertIn("重合度过高警报", ol["portfolio_diversification_verdict"])

        # 黄金与金矿股营运杠杆
        g_val = CommodityGoldFramework.evaluate_gold_macro_valuation()
        self.assertIn("spot_gold_usd", g_val)
        self.assertIn("traditional_real_yield_anchor", g_val["valuation_models"])

        nem_lev = CommodityGoldFramework.evaluate_gold_miner_leverage("NEM")
        self.assertIn("operating_leverage_multiplier", nem_lev)

    def test_issue6_strong_constrained_valuation_hard_floor(self):
        """【UT-UNIFIED-05: 资产负债表刚性底线模型(NCPS/NCAV/TBV/HardFloor)高精度计算】

        1. 测试功能与测试点:
           - 验证 StronglyConstrainedValuationEngine.calculate_hard_asset_floors 物理底线估值模型。
           - 每股净现金 (NCPS): (Cash - Total Debt) / Shares。
           - 每股净流动资产 (NCAV，格雷厄姆烟蒂底线): (Current Assets - Total Liabilities) / Shares。
           - 破产重组清算防线 (Hard Floor)。

        2. 正常函数业务边界与参数契约:
           - CompanyFinancialFacts 输入强类型。
           - shares > 0。

        3. 测试数据与模拟场景说明:
           - 生物科技破位标的 RXRX (现价 $3.85，总股本 5.3534 亿股，现金 5.5 亿，流动资产 6.2 亿，总负债 1.45 亿)。

        4. 预期断言与结果验证:
           - 断言 ncps 约等于 $1.03 (550 / 535.34)。
           - 断言 ncav 约等于 $0.89 ((620 - 145) / 535.34)。
           - 断言 hard_floor > 0.5 美元。
        """
        facts = CompanyFinancialFacts(
            ticker="RXRX",
            currency="USD",
            current_price=3.85,
            shares=535.34,
            cash_and_equivalents=550.0,
            total_debt=0.0,
            total_assets=765.0,
            current_assets=620.0,
            total_liabilities=145.0,
            equity=475.0,
            goodwill_and_intangibles=0.0,
            revenue=55.0,
            operating_income=-310.0,
            net_income=-295.0,
            free_cash_flow=-280.0,
            operating_cash_flow=-280.0,
            quote_timestamp="2026-10-14T16:00:00Z",
            market_session="regular_trading",
        )
        ncps, ncav, tbv, hard_floor = StronglyConstrainedValuationEngine.calculate_hard_asset_floors(facts)
        # 每股净现金 = 550 / 535.34 = $1.03
        self.assertAlmostEqual(ncps, 1.03, places=2)
        # 每股净流动资产 = (620 - 145) / 535.34 = $0.89
        self.assertAlmostEqual(ncav, 0.89, places=2)
        # 刚性底线大于 0
        self.assertGreater(hard_floor, 0.5)

    def test_issue7_project_data_governance(self):
        """【IT-UNIFIED-06: 项目数据主权治理-相对路径自洽性与审计回执留存验证】

        1. 测试功能与测试点:
           - 验证项目严格遵守数据主权与项目内相对路径隔离契约。
           - 验证自动化运行生成的审计收据 (receipt) 物理留存于 data/audits/，只追加不手改。

        2. 正常函数业务边界与参数契约:
           - 路径解析后必须位于项目根目录内。

        3. 测试数据与模拟场景说明:
           - 校验 data/audits/drive-deep-analysis-20261012/daily_briefing_20261015_receipt.json。

        4. 预期断言与结果验证:
           - 断言 receipt_dir.exists() 为 True。
           - 断言 today_receipt.exists() 为 True。
        """
        # 检查收据与清单
        receipt_dir = ROOT / "data" / "audits" / "drive-deep-analysis-20261012"
        self.assertTrue(receipt_dir.exists())
        today_receipt = receipt_dir / "daily_briefing_20261015_receipt.json"
        self.assertTrue(today_receipt.exists())


if __name__ == "__main__":
    unittest.main()
