"""官方交易所日历、全市场目标交易日覆盖对账与东证相场表解析器单元测试。

验证《SPEC-43 美日股全市场盘前采集调查》中五大核心要求：
1. 美股与日股交易所官方交易日历、节假日与振替休日判定；
2. 开盘前计划时点与目标交易日推导 (跨周末、节假日、盘前时段)；
3. 全市场逐标的目标日覆盖对账刚性平账自检 (Universe = Matched + NoTrade + Pending + Unmapped + Error)；
4. 东证日刊《株式相場表》批量解析与综合 OHLCV 金融合成规则。
"""

from datetime import date, datetime, timezone
import unittest
import zoneinfo

from financial_core.engines.exchange_calendar_engine import (
    ExchangeCalendarEngine,
    NEW_YORK_TZ,
    TOKYO_TZ,
)
from financial_core.engines.market_reconciliation_engine import (
    MarketReconciliationEngine,
)
from financial_core.engines.jpx_official_quotations_parser import (
    JpxOfficialQuotationsParser,
)


class ExchangeCalendarEngineTest(unittest.TestCase):
    def test_us_holidays_2026(self):
        holidays_2026 = ExchangeCalendarEngine.get_us_holidays(2026)
        # 元旦
        self.assertIn(date(2026, 1, 1), holidays_2026)
        # MLK Day: 1月第3个周一 (2026-01-19)
        self.assertIn(date(2026, 1, 19), holidays_2026)
        # 总统日: 2月第3个周一 (2026-02-16)
        self.assertIn(date(2026, 2, 16), holidays_2026)
        # 耶稣受难日 Good Friday (2026-04-03)
        self.assertIn(date(2026, 4, 3), holidays_2026)
        # 阵亡将士纪念日 Memorial Day: 5月最后一个周一 (2026-05-25)
        self.assertIn(date(2026, 5, 25), holidays_2026)
        # 六月节 Juneteenth (2026-06-19)
        self.assertIn(date(2026, 6, 19), holidays_2026)
        # 独立日 (2026-07-04 周六，提前至周五 2026-07-03 休市)
        self.assertIn(date(2026, 7, 3), holidays_2026)
        # 劳动节 Labor Day: 9月第1个周一 (2026-09-07)
        self.assertIn(date(2026, 9, 7), holidays_2026)
        # 感恩节 Thanksgiving: 11月第4个周四 (2026-11-26)
        self.assertIn(date(2026, 11, 26), holidays_2026)
        # 圣诞节 (2026-12-25)
        self.assertIn(date(2026, 12, 25), holidays_2026)

    def test_jp_holidays_2026(self):
        holidays_2026 = ExchangeCalendarEngine.get_jp_holidays(2026)
        # 年末年始休业日
        self.assertIn(date(2026, 1, 1), holidays_2026)
        self.assertIn(date(2026, 1, 2), holidays_2026)
        self.assertIn(date(2026, 1, 3), holidays_2026)
        self.assertIn(date(2026, 12, 31), holidays_2026)
        # 成人の日: 1月第2个周一 (2026-01-12)
        self.assertIn(date(2026, 1, 12), holidays_2026)
        # 建国記念の日 (2026-02-11)
        self.assertIn(date(2026, 2, 11), holidays_2026)
        # 天皇誕生日 (2026-02-23)
        self.assertIn(date(2026, 2, 23), holidays_2026)
        # 春分の日 (2026-03-20)
        self.assertIn(date(2026, 3, 20), holidays_2026)
        # 昭和の日 (2026-04-29)
        self.assertIn(date(2026, 4, 29), holidays_2026)
        # 憲法記念日 2026-05-03 (周日)，由于5/4为みどりの日、5/5为こどもの日，顺延至 5/6 振替休日
        self.assertIn(date(2026, 5, 3), holidays_2026)
        self.assertIn(date(2026, 5, 4), holidays_2026)
        self.assertIn(date(2026, 5, 5), holidays_2026)
        self.assertIn(date(2026, 5, 6), holidays_2026)
        # 文化の日 (2026-11-03)
        self.assertIn(date(2026, 11, 3), holidays_2026)
        # 勤労感謝の日 (2026-11-23)
        self.assertIn(date(2026, 11, 23), holidays_2026)

    def test_target_trading_day_resolution(self):
        # 1. 跨周末：2026-11-15 (周日) 无论何时执行，美日股目标日均为上周五 2026-11-13
        sun_dt = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(ExchangeCalendarEngine.resolve_target_trading_day("JP", sun_dt), date(2026, 11, 13))
        self.assertEqual(ExchangeCalendarEngine.resolve_target_trading_day("US", sun_dt), date(2026, 11, 13))

        # 2. 周一早间盘前：2026-11-16 07:30 JST (日股盘前)，今日未开盘，目标日为上周五 2026-11-13
        mon_jp_pre = datetime(2026, 11, 16, 7, 30, tzinfo=TOKYO_TZ)
        self.assertEqual(ExchangeCalendarEngine.resolve_target_trading_day("JP", mon_jp_pre), date(2026, 11, 13))

        # 3. 美股工作日早间盘前：2026-11-16 08:00 EST (美股盘前)，今日未开盘，目标日为上周五 2026-11-13
        mon_us_pre = datetime(2026, 11, 16, 8, 0, tzinfo=NEW_YORK_TZ)
        self.assertEqual(ExchangeCalendarEngine.resolve_target_trading_day("US", mon_us_pre), date(2026, 11, 13))

        # 4. 日股工作日收盘后：2026-11-16 16:00 JST (收盘竞价后)，今日已完成，目标日为今日 2026-11-16
        mon_jp_post = datetime(2026, 11, 16, 16, 0, tzinfo=TOKYO_TZ)
        self.assertEqual(ExchangeCalendarEngine.resolve_target_trading_day("JP", mon_jp_post), date(2026, 11, 16))

        # 5. 日股假期：2026-11-03 (文化の日 周二) 触发，目标日向前回退至 2026-11-02 (周一)
        holiday_jp = datetime(2026, 11, 3, 10, 0, tzinfo=TOKYO_TZ)
        self.assertEqual(ExchangeCalendarEngine.resolve_target_trading_day("JP", holiday_jp), date(2026, 11, 2))


class MarketReconciliationEngineTest(unittest.TestCase):
    def test_balanced_reconciliation(self):
        universe = ["AAPL", "MSFT", "GOOGL", "AMZN", "NONE."]
        target_date = "2026-11-13"

        # 构造归档记录
        # AAPL: 包含目标交易日，正常成交
        # MSFT: 包含目标交易日，停牌 0 成交量
        # GOOGL: 只有旧日期 2026-11-12，缺少目标交易日 -> PENDING
        # AMZN: 采集中报错 -> ERROR
        # NONE.: 已知未映射 -> UNMAPPED
        archived = {
            "AAPL": [{"Date": "2026-11-13", "Close": 230.5, "Volume": 45000000}],
            "MSFT": [{"Date": "2026-11-13", "Close": 420.0, "Volume": 0}],
            "GOOGL": [{"Date": "2026-11-12", "Close": 175.0, "Volume": 20000000}],
        }
        error_symbols = {"AMZN"}

        summary = MarketReconciliationEngine.reconcile_target_day(
            market="US",
            target_date=target_date,
            universe_symbols=universe,
            archived_records=archived,
            error_symbols=error_symbols,
        )

        self.assertTrue(summary.is_balanced)
        self.assertEqual(summary.balance_diff, 0)
        self.assertEqual(summary.universe_count, 5)
        self.assertEqual(summary.matched_count, 1)      # AAPL
        self.assertEqual(summary.no_trade_count, 1)     # MSFT
        self.assertEqual(summary.pending_count, 1)      # GOOGL (缺少目标日)
        self.assertEqual(summary.unmapped_count, 1)     # NONE.
        self.assertEqual(summary.error_count, 1)        # AMZN
        self.assertEqual(summary.coverage_rate_pct, 40.0) # (1+1)/5 = 40%
        self.assertIn("NONE.", summary.unmapped_symbols)


class JpxOfficialQuotationsParserTest(unittest.TestCase):
    def test_assemble_normal_bar(self):
        # 正常全天交易标的
        bar = JpxOfficialQuotationsParser.assemble_bar(
            code="7203",
            name="トヨタ自動車",
            session_date="2026-11-13",
            morning_ohlc=("2,800", "2,850", "2,790", "2,840"),
            afternoon_ohlc=("2,835", "2,860", "2,820", "2,855"),
            volume_val="15,400",  # 15,400 千株 = 15,400,000 股
            volume_multiplier=1000,
        )
        self.assertEqual(bar.code, "7203")
        self.assertEqual(bar.open, 2800.0)    # 前场始值
        self.assertEqual(bar.high, 2860.0)    # 全天最高
        self.assertEqual(bar.low, 2790.0)     # 全天最低
        self.assertEqual(bar.close, 2855.0)   # 后场终值
        self.assertEqual(bar.volume, 15400000)
        self.assertFalse(bar.is_suspended)

    def test_assemble_suspended_bar(self):
        # 全天停牌无成交标的
        bar = JpxOfficialQuotationsParser.assemble_bar(
            code="9999",
            name="休止銘柄",
            session_date="2026-11-13",
            morning_ohlc=("-", "-", "-", "-"),
            afternoon_ohlc=("-", "-", "-", "-"),
            volume_val="-",
        )
        self.assertIsNone(bar.open)
        self.assertIsNone(bar.close)
        self.assertEqual(bar.volume, 0)
        self.assertTrue(bar.is_suspended)

    def test_assemble_morning_only_bar(self):
        # 仅前场成交标的
        bar = JpxOfficialQuotationsParser.assemble_bar(
            code="1301",
            name="極洋",
            session_date="2026-11-13",
            morning_ohlc=("3,500", "3,520", "3,480", "3,510"),
            afternoon_ohlc=("-", "-", "-", "-"),
            volume_val="20",
        )
        self.assertEqual(bar.open, 3500.0)
        self.assertEqual(bar.close, 3510.0)   # 后场无终值，取前场终值
        self.assertEqual(bar.volume, 20000)
        self.assertFalse(bar.is_suspended)


if __name__ == "__main__":
    unittest.main()
