"""时效性与交易时段硬核验门禁 (Quote Freshness & Session Gatekeeper).

解决工程整改清单 Task 05 & Task 06:
1. 真实解析行情时间戳与时区 (涵盖美股 America/New_York、A股 Asia/Shanghai、日股 Asia/Tokyo);
2. 自动处理美股夏令时 (EDT/EST) 与日历交易日/周末;
3. 严禁未来时间、旧日缓存获得实时徽标;
4. 超过 20 分钟延迟强制降级为 DELAYED_QUOTE;
5. 封装不可拆分的不可变 QuoteSnapshot 报价对象，全链路共用同一检验凭据。
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import re
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class QuoteSnapshot:
    """不可拆分的不可变行情报价凭证 (Immutable Quote Snapshot)."""
    ticker: str
    price: float
    currency: str                          # USD, CNY, JPY
    quote_timestamp_str: str               # 原始入参时间戳文本
    market: str                            # US, CN, JP
    market_session: str                    # regular_trading, pre_market, after_hours, closed
    is_live: bool                          # 是否为可采信的盘中实时行情
    freshness_grade: str                   # LIVE_REALTIME, DELAYED_QUOTE, PREVIOUS_CLOSE, STALE_EXPIRED, INVALID_FUTURE_TIME, INVALID_FORMAT
    delay_minutes: Optional[float]         # 较当前时刻的延迟分钟数
    as_of_local_time: str                  # 交易所当地规范化时间 (YYYY-MM-DD HH:MM:SS TZ)
    display_badge: str                     # 前端徽标
    session_notice: str                    # 时效与时段强制披露说明

    @property
    def is_live_session(self) -> bool:
        """向后兼容属性：是否为盘中实时时段."""
        return self.is_live


# 向后兼容别名
FreshnessAudit = QuoteSnapshot


class QuoteFreshnessVerifier:
    """买方级行情时效性与时区核验器."""

    MARKET_TIMEZONES = {
        "US": ZoneInfo("America/New_York"),
        "CN": ZoneInfo("Asia/Shanghai"),
        "JP": ZoneInfo("Asia/Tokyo"),
    }

    CURRENCY_SYMBOLS = {
        "USD": "$",
        "CNY": "¥",
        "JPY": "¥",
    }

    @classmethod
    def infer_market(cls, ticker: str, market_hint: Optional[str] = None) -> Tuple[str, str]:
        """根据标的代码推断市场归属与基准币种."""
        if market_hint and market_hint.upper() in cls.MARKET_TIMEZONES:
            m = market_hint.upper()
            curr = "USD" if m == "US" else ("CNY" if m == "CN" else "JPY")
            return m, curr

        t = ticker.strip().upper()
        if t.isdigit() and len(t) == 6:
            return "CN", "CNY"
        elif t.isdigit() and len(t) == 4:
            return "JP", "JPY"
        elif t.startswith("TYO:") or t.endswith(".T"):
            return "JP", "JPY"
        elif t.startswith("SH:") or t.startswith("SZ:") or t.endswith(".SS") or t.endswith(".SZ"):
            return "CN", "CNY"
        return "US", "USD"

    @classmethod
    def parse_timestamp_with_tz(
        cls, ts_str: str, default_tz: ZoneInfo
    ) -> Optional[datetime]:
        """解析多样化时间戳并统一绑定目标时区."""
        s = ts_str.strip()
        # 1. 尝试 ISO 格式
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=default_tz)
            return dt.astimezone(default_tz)
        except Exception:
            pass

        # 2. 尝试标准 "YYYY-MM-DD HH:MM:SS TZ" 格式
        # 常见时区名映射
        tz_aliases = {
            "EDT": ZoneInfo("America/New_York"),
            "EST": ZoneInfo("America/New_York"),
            "CST": ZoneInfo("Asia/Shanghai"),
            "JST": ZoneInfo("Asia/Tokyo"),
            "UTC": timezone.utc,
        }
        for alias, tz_obj in tz_aliases.items():
            if s.endswith(f" {alias}"):
                base_str = s[:-len(alias)-1].strip()
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
                    try:
                        naive = datetime.strptime(base_str, fmt)
                        return naive.replace(tzinfo=tz_obj).astimezone(default_tz)
                    except ValueError:
                        continue

        # 3. 朴素格式 (假定为交易所当地时区)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
            try:
                naive = datetime.strptime(s, fmt)
                return naive.replace(tzinfo=default_tz)
            except ValueError:
                continue

        return None

    @classmethod
    def verify_quote(
        cls,
        quote_timestamp: str,
        market_session: str = "closed",
        ticker: str = "BENCHMARK",
        price: float = 0.0,
        clock_override: Optional[datetime] = None,
    ) -> QuoteSnapshot:
        """向后兼容的便捷核验入口."""
        return cls.verify_and_build_snapshot(
            ticker=ticker,
            price=price,
            quote_timestamp_str=quote_timestamp,
            market_session=market_session,
            clock_override=clock_override,
        )

    @classmethod
    def get_actual_market_session(cls, market: str, dt_local: datetime) -> Tuple[str, str]:
        """根据交易所当地时间与营业日历，严谨判定该时刻的真实交易时段状态.
        
        Returns:
            (session_type, reason_desc)
            session_type 可取: 'regular_trading', 'pre_market', 'after_hours', 'closed'
        """
        # 1. 周末法定休市检测
        if dt_local.weekday() in (5, 6):
            return "closed", "周末法定休市"

        # 2. 主要法定节假日判定 (月, 日)
        md = (dt_local.month, dt_local.day)
        if market == "US":
            if md in [(1, 1), (6, 19), (7, 4), (12, 25)]:
                return "closed", "美股法定节假日休市"
        elif market == "CN":
            if md in [(1, 1), (5, 1)] or (dt_local.month == 10 and 1 <= dt_local.day <= 7):
                return "closed", "A股法定节假日休市"
        elif market == "JP":
            if md in [(1, 1), (1, 2), (1, 3)]:
                return "closed", "东证新年休市日"

        # 3. 交易所当地钟点营业区间检测 (自午夜起的分钟数)
        minutes = dt_local.hour * 60 + dt_local.minute

        if market == "US":
            # 美东时间 EDT/EST:
            # 04:00 - 09:30 (240 - 570): pre_market 盘前
            # 09:30 - 16:00 (570 - 960): regular_trading 盘中常规
            # 16:00 - 20:00 (960 - 1200): after_hours 盘后
            # 20:00 - 04:00 (次日): closed 夜间休市
            if 570 <= minutes < 960:
                return "regular_trading", "美股常规交易时段 (09:30-16:00 EDT/EST)"
            elif 240 <= minutes < 570:
                return "pre_market", "美股盘前交易时段 (04:00-09:30 EDT/EST)"
            elif 960 <= minutes < 1200:
                return "after_hours", "美股盘后交易时段 (16:00-20:00 EDT/EST)"
            else:
                return "closed", "美股夜间休市时段 (20:00-04:00)"

        elif market == "CN":
            # 北京时间 CST:
            # 09:15 - 09:30 (555 - 570): pre_market 开盘集合竞价
            # 09:30 - 11:30 (570 - 690): regular_trading 早盘连续竞价
            # 11:30 - 13:00 (690 - 780): closed 中午休市
            # 13:00 - 15:00 (780 - 900): regular_trading 午盘连续竞价
            # 15:00 - 09:15 (次日): closed 闭市结算
            if (570 <= minutes < 690) or (780 <= minutes < 900):
                return "regular_trading", "A股连续竞价交易时段 (09:30-11:30 / 13:00-15:00 CST)"
            elif 555 <= minutes < 570:
                return "pre_market", "A股开盘集合竞价时段 (09:15-09:30 CST)"
            elif 690 <= minutes < 780:
                return "closed", "A股中午休市时段 (11:30-13:00 CST)"
            else:
                return "closed", "A股闭市结算时段 (15:00-09:15)"

        elif market == "JP":
            # 东京时间 JST:
            # 09:00 - 11:30 (540 - 690): regular_trading 前场
            # 11:30 - 12:30 (690 - 750): closed 中午休市
            # 12:30 - 15:30 (750 - 930): regular_trading 后场
            # 15:30 - 09:00 (次日): closed 闭市结算
            if (540 <= minutes < 690) or (750 <= minutes < 930):
                return "regular_trading", "东证盘中交易时段 (09:00-11:30 / 12:30-15:30 JST)"
            elif 690 <= minutes < 750:
                return "closed", "东证中午休市时段 (11:30-12:30 JST)"
            else:
                return "closed", "东证闭市结算时段 (15:30-09:00)"

        return "closed", "默认闭市时段"

    @classmethod
    def verify_and_build_snapshot(
        cls,
        ticker: str,
        price: float,
        quote_timestamp_str: str,
        market_session: str = "closed",
        market_hint: Optional[str] = None,
        clock_override: Optional[datetime] = None,
    ) -> QuoteSnapshot:
        """核心方法：严格核验并构建不可变的行情凭据 (QuoteSnapshot)."""
        market, currency = cls.infer_market(ticker, market_hint)
        tz = cls.MARKET_TIMEZONES[market]

        # 当前时刻 (允许注入模拟时钟用于单元测试)
        now_dt = clock_override or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        now_local = now_dt.astimezone(tz)

        parsed_quote_dt = cls.parse_timestamp_with_tz(quote_timestamp_str, tz)
        session_clean = market_session.lower().strip()

        # 异常 1: 时间格式无法解析
        if parsed_quote_dt is None:
            return QuoteSnapshot(
                ticker=ticker,
                price=price,
                currency=currency,
                quote_timestamp_str=quote_timestamp_str,
                market=market,
                market_session=market_session,
                is_live=False,
                freshness_grade="INVALID_FORMAT",
                delay_minutes=None,
                as_of_local_time=quote_timestamp_str,
                display_badge="【时间非法·阻断实时】",
                session_notice=f"致命错误：行情时间戳 '{quote_timestamp_str}' 格式无法解析，已阻断作为实时现价！",
            )

        # 异常 2: 未来时间穿越 (超过当前时钟 5 分钟容差)
        diff_seconds = (now_local - parsed_quote_dt).total_seconds()
        if diff_seconds < -300:
            return QuoteSnapshot(
                ticker=ticker,
                price=price,
                currency=currency,
                quote_timestamp_str=quote_timestamp_str,
                market=market,
                market_session=market_session,
                is_live=False,
                freshness_grade="INVALID_FUTURE_TIME",
                delay_minutes=round(diff_seconds / 60.0, 1),
                as_of_local_time=parsed_quote_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
                display_badge="【时钟穿越·未来时间】",
                session_notice=f"致命安全报警：行情时间戳处于未来 ({quote_timestamp_str} > 当前 {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')})，已阻断！",
            )

        delay_mins = max(0.0, diff_seconds / 60.0)
        is_same_day = (parsed_quote_dt.date() == now_local.date())
        is_weekend = (now_local.weekday() in (5, 6))

        # 真实计算交易所当地时钟的时段状态
        actual_quote_session, actual_quote_reason = cls.get_actual_market_session(market, parsed_quote_dt)
        actual_now_session, actual_now_reason = cls.get_actual_market_session(market, now_local)

        # 判定 1: 非同一交易日或周末 -> 严格为前收盘基准
        if not is_same_day or is_weekend:
            badge = "【前收盘基准·休市】"
            notice = (
                f"时效说明：行情时间戳为 {parsed_quote_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}，"
                f"早于当前交易时段或当前为休市（周末/夜间）。本分析严格基于前一交易日收盘价基准，"
                f"已阻断将历史旧缓存包装成盘中最新价误导决策。"
            )
            return QuoteSnapshot(
                ticker=ticker,
                price=price,
                currency=currency,
                quote_timestamp_str=quote_timestamp_str,
                market=market,
                market_session="closed",
                is_live=False,
                freshness_grade="PREVIOUS_CLOSE",
                delay_minutes=round(delay_mins, 1),
                as_of_local_time=parsed_quote_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
                display_badge=badge,
                session_notice=notice,
            )

        # 判定 2: 时间戳自身处于闭市时段 (例如凌晨3点宣称常规交易) -> 刚性纠偏为闭市
        if actual_quote_session == "closed":
            badge = "【前收盘基准·休市】"
            notice = (
                f"时效与营业钟点纠偏：行情时间戳 {parsed_quote_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                f"处于 {actual_quote_reason}。交易所实际处于休市状态，入参声称的常规交易时段不成立，"
                f"系统已自动纠偏并以收盘结算价格基准开展分析。"
            )
            return QuoteSnapshot(
                ticker=ticker,
                price=price,
                currency=currency,
                quote_timestamp_str=quote_timestamp_str,
                market=market,
                market_session="closed",
                is_live=False,
                freshness_grade="PREVIOUS_CLOSE",
                delay_minutes=round(delay_mins, 1),
                as_of_local_time=parsed_quote_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
                display_badge=badge,
                session_notice=notice,
            )

        # 判定 3: 同一交易日内有效交易时段 (盘中常规、盘前、盘后)
        effective_session = actual_quote_session
        if delay_mins <= 20.0:
            sess_label = {
                "regular_trading": "盘中常规交易",
                "pre_market": "盘前交易",
                "after_hours": "盘后交易",
            }.get(effective_session, effective_session)
            badge = f"【实时行情·{sess_label}】"
            notice = f"行情核验通过：时间戳 {parsed_quote_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}，处于 {sess_label} ({actual_quote_reason})，延迟 {delay_mins:.1f} 分钟。"
            return QuoteSnapshot(
                ticker=ticker,
                price=price,
                currency=currency,
                quote_timestamp_str=quote_timestamp_str,
                market=market,
                market_session=effective_session,
                is_live=True,
                freshness_grade="LIVE_REALTIME",
                delay_minutes=round(delay_mins, 1),
                as_of_local_time=parsed_quote_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
                display_badge=badge,
                session_notice=notice,
            )
        else:
            # 超过20分钟延迟行情
            badge = f"【延迟行情·延迟{int(delay_mins)}分】"
            notice = (
                f"行情提示：时间戳 {parsed_quote_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}，"
                f"较当前时刻已延迟 {delay_mins:.1f} 分钟，交易决策请注意盘中波动拉开的时差。"
            )
            return QuoteSnapshot(
                ticker=ticker,
                price=price,
                currency=currency,
                quote_timestamp_str=quote_timestamp_str,
                market=market,
                market_session=effective_session,
                is_live=False,
                freshness_grade="DELAYED_QUOTE",
                delay_minutes=round(delay_mins, 1),
                as_of_local_time=parsed_quote_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
                display_badge=badge,
                session_notice=notice,
            )

        # 盘前前或已收盘
        badge = "【收盘结算基准】"
        notice = f"行情说明：当前交易日已收盘或尚未开市，基于收盘价格基准分析。"
        return QuoteSnapshot(
            ticker=ticker,
            price=price,
            currency=currency,
            quote_timestamp_str=quote_timestamp_str,
            market=market,
            market_session="closed",
            is_live=False,
            freshness_grade="PREVIOUS_CLOSE",
            delay_minutes=round(delay_mins, 1),
            as_of_local_time=parsed_quote_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
            display_badge=badge,
            session_notice=notice,
        )
