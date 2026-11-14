"""官方交易所交易日历与目标交易日推导引擎 (Exchange Trading Calendar Engine).

遵循买方机构级交易日历与会话规范，解决开盘前执行时点与目标行情交易日脱节问题：
1. 覆盖美股 (NYSE / NASDAQ) 与日股 (JPX / 东证) 官方交易日历与法定节假日体系；
2. 支持开盘日前置核验、周末休市、法定节假日与振替休日判定；
3. 解耦定时任务计划执行时间与目标行情交易日 (Target Trading Day)：
   - 盘前窗口 (如美股 08:00、日股 07:30)：自动前推至上一个已收盘完成的交易日；
   - 盘后窗口 (如美股 16:00、日股 15:30 之后)：若当日为交易日则归档当日，休市则前推；
   - 跨周末与节假日：自动对齐最近有效闭市交易日。
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import zoneinfo

NEW_YORK_TZ = zoneinfo.ZoneInfo("America/New_York")
TOKYO_TZ = zoneinfo.ZoneInfo("Asia/Tokyo")


def _to_date(val: Union[date, datetime, str]) -> date:
    """转换为标准 date 对象。"""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        # 兼容 YYYY-MM-DD 或 ISO 格式
        return date.fromisoformat(val[:10])
    raise TypeError(f"不支持的日期类型: {type(val)}")


def _easter_date(year: int) -> date:
    """计算指定年份复活节星期日 (Meeus/Jones/Butcher 算法，西方教会公历法)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """获取指定年月第 n 个星期几 (weekday: 0=周一, 6=周日, n: 1, 2, 3, 4, -1=最后)."""
    if n > 0:
        d = date(year, month, 1)
        shift = (weekday - d.weekday()) % 7
        d += timedelta(days=shift + (n - 1) * 7)
        return d
    else:
        # 倒数第 1 个 (最后 1 个)
        if month == 12:
            d = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            d = date(year, month + 1, 1) - timedelta(days=1)
        shift = (d.weekday() - weekday) % 7
        return d - timedelta(days=shift)


@dataclass(frozen=True)
class TradingDayStatus:
    """交易日与时段状态。"""
    market: str
    target_trading_day: str          # 权威目标行情交易日 YYYY-MM-DD
    is_today_trading_day: bool       # 当地日期今日是否开盘
    is_open_now: bool                # 当前时点是否处于盘中正常交易时段
    session_phase: str               # PRE_MARKET, REGULAR_TRADING, AFTER_HOURS, CLOSED_WEEKEND, CLOSED_HOLIDAY, CLOSED_NIGHT
    session_label_zh: str            # 去工程符号化的自然中文时段说明
    local_time_str: str              # 交易所当地时间字符串
    tz_name: str                     # 时区代码 (如 EDT, EST, JST)


class ExchangeCalendarEngine:
    """美股与日股交易所官方交易日历引擎。"""

    # 预置 2024-2027 年固定及天文节假日
    # 包含日本春分、秋分官方公布法定日
    _JP_EQUINOX: Dict[int, Tuple[Tuple[int, int], Tuple[int, int]]] = {
        2024: ((3, 20), (9, 22)),
        2025: ((3, 20), (9, 23)),
        2026: ((3, 20), (9, 23)),
        2027: ((3, 21), (9, 23)),
    }

    @classmethod
    def get_market_tz(cls, market: str) -> zoneinfo.ZoneInfo:
        return NEW_YORK_TZ if market.upper() == "US" else TOKYO_TZ

    @classmethod
    def get_us_holidays(cls, year: int) -> Dict[date, str]:
        """获取美股 (NYSE/NASDAQ) 全年全天休市日。"""
        holidays: Dict[date, str] = {}

        def add_observed(d: date, name: str) -> None:
            # 美股规则：周日顺延周一，周六前移周五
            if d.weekday() == 6:  # 周日
                holidays[d + timedelta(days=1)] = f"{name} (Observed)"
            elif d.weekday() == 5:  # 周六
                holidays[d - timedelta(days=1)] = f"{name} (Observed)"
            else:
                holidays[d] = name

        # 1. 元旦 (New Year's Day)
        add_observed(date(year, 1, 1), "New Year's Day")

        # 2. 马丁·路德·金纪念日 (Martin Luther King Jr. Day): 1月第3个周一
        holidays[_nth_weekday(year, 1, 0, 3)] = "Martin Luther King Jr. Day"

        # 3. 华盛顿诞辰 / 总统日 (Presidents' Day): 2月第3个周一
        holidays[_nth_weekday(year, 2, 0, 3)] = "Presidents' Day"

        # 4. 耶稣受难日 (Good Friday): 复活节前两天
        easter = _easter_date(year)
        holidays[easter - timedelta(days=2)] = "Good Friday"

        # 5. 阵亡将士纪念日 (Memorial Day): 5月最后一个周一
        holidays[_nth_weekday(year, 5, 0, -1)] = "Memorial Day"

        # 6. 六月节 (Juneteenth National Independence Day): 6月19日
        add_observed(date(year, 6, 19), "Juneteenth National Independence Day")

        # 7. 独立日 (Independence Day): 7月4日
        add_observed(date(year, 7, 4), "Independence Day")

        # 8. 劳动节 (Labor Day): 9月第1个周一
        holidays[_nth_weekday(year, 9, 0, 1)] = "Labor Day"

        # 9. 感恩节 (Thanksgiving Day): 11月第4个周四
        holidays[_nth_weekday(year, 11, 3, 4)] = "Thanksgiving Day"

        # 10. 圣诞节 (Christmas Day): 12月25日
        add_observed(date(year, 12, 25), "Christmas Day")

        return holidays

    @classmethod
    def get_jp_holidays(cls, year: int) -> Dict[date, str]:
        """获取东证 (JPX) 全年全天休市日 (含年末年始与振替休日)."""
        holidays: Dict[date, str] = {}

        # 1. 年末年始休业日 (12/31 ~ 1/3)
        holidays[date(year, 1, 1)] = "元日"
        holidays[date(year, 1, 2)] = "正月三が日"
        holidays[date(year, 1, 3)] = "正月三が日"
        holidays[date(year, 12, 31)] = "大晦日 (年末年始休業)"

        # 2. 成人の日: 1月第2个周一
        holidays[_nth_weekday(year, 1, 0, 2)] = "成人の日"

        # 3. 建国記念の日: 2月11日
        holidays[date(year, 2, 11)] = "建国記念の日"

        # 4. 天皇誕生日: 2月23日
        holidays[date(year, 2, 23)] = "天皇誕生日"

        # 5. 春分の日
        sp_m, sp_d = cls._JP_EQUINOX.get(year, ((3, 20), (9, 23)))[0]
        holidays[date(year, sp_m, sp_d)] = "春分の日"

        # 6. 昭和の日: 4月29日
        holidays[date(year, 4, 29)] = "昭和の日"

        # 7. 黄金周 (5/3 憲法記念日, 5/4 みどりの日, 5/5 こどもの日)
        holidays[date(year, 5, 3)] = "憲法記念日"
        holidays[date(year, 5, 4)] = "みどりの日"
        holidays[date(year, 5, 5)] = "こどもの日"

        # 8. 海の日: 7月第3个周一
        holidays[_nth_weekday(year, 7, 0, 3)] = "海の日"

        # 9. 山の日: 8月11日
        holidays[date(year, 8, 11)] = "山の日"

        # 10. 敬老の日: 9月第3个周一
        keiro = _nth_weekday(year, 9, 0, 3)
        holidays[keiro] = "敬老の日"

        # 11. 秋分の日
        at_m, at_d = cls._JP_EQUINOX.get(year, ((3, 20), (9, 23)))[1]
        shubun = date(year, at_m, at_d)
        holidays[shubun] = "秋分の日"

        # 若敬老の日与秋分の日之间相隔一天 (周二)，依国民祝日法该日成为“国民の休日”
        if (shubun - keiro).days == 2:
            holidays[keiro + timedelta(days=1)] = "国民の休日"

        # 12. スポーツの日: 10月第2个周一
        holidays[_nth_weekday(year, 10, 0, 2)] = "スポーツの日"

        # 13. 文化の日: 11月3日
        holidays[date(year, 11, 3)] = "文化の日"

        # 14. 勤労感謝の日: 11月23日
        holidays[date(year, 11, 23)] = "勤労感謝の日"

        # 计算振替休日 (Substituted Holiday):
        # 日本法律：若国民祝日逢周日，顺延至下一个非休假的工作日
        observed: Dict[date, str] = {}
        for h_date, h_name in holidays.items():
            if h_date.weekday() == 6:  # 逢周日
                sub_date = h_date + timedelta(days=1)
                while sub_date in holidays or sub_date in observed:
                    sub_date += timedelta(days=1)
                observed[sub_date] = f"{h_name} 振替休日"
        holidays.update(observed)

        return holidays

    @classmethod
    def is_trading_day(cls, market: str, val: Union[date, datetime, str]) -> bool:
        """判定指定日期在目标交易所是否为开盘交易日。"""
        d = _to_date(val)
        # 周末必然休市
        if d.weekday() >= 5:
            return False
        market_upper = market.upper()
        if market_upper == "US":
            holidays = cls.get_us_holidays(d.year)
        elif market_upper == "JP":
            holidays = cls.get_jp_holidays(d.year)
        else:
            return d.weekday() < 5
        return d not in holidays

    @classmethod
    def get_previous_trading_day(cls, market: str, val: Union[date, datetime, str]) -> date:
        """获取指定日期之前的最近一个开盘交易日 (向前倒推)."""
        d = _to_date(val) - timedelta(days=1)
        while not cls.is_trading_day(market, d):
            d -= timedelta(days=1)
        return d

    @classmethod
    def get_next_trading_day(cls, market: str, val: Union[date, datetime, str]) -> date:
        """获取指定日期之后的最近一个开盘交易日 (向后顺延)."""
        d = _to_date(val) + timedelta(days=1)
        while not cls.is_trading_day(market, d):
            d += timedelta(days=1)
        return d

    @classmethod
    def resolve_target_trading_day(
        cls,
        market: str,
        now_dt: Optional[datetime] = None,
    ) -> date:
        """买方核心算法：根据执行时点推导权威目标行情交易日 (Target Trading Day).

        业务直觉逻辑：
        1. 开盘前 (如美股 08:00、日股 07:30)：今日尚未开盘，目标日必然是上一已完成交易日；
        2. 盘中 (美股 09:30-16:00、日股 09:00-15:30)：当日尚未终局定盘，上一已完成交易日仍是前一交易日；
        3. 盘后已收盘 (美股 >=16:00、日股 >=15:30)：若今日为交易日，目标日即为今日；若今日休市则前推；
        4. 周末或法定节假日：当日无交易，前推至最近已完成交易日。
        """
        market_upper = market.upper()
        tz = cls.get_market_tz(market_upper)
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)
        elif now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)

        local_now = now_dt.astimezone(tz)
        today = local_now.date()
        clock = local_now.hour * 100 + local_now.minute

        # 美股时段划分：09:30 开盘，16:00 收盘
        # 日股时段划分：09:00 开盘，15:30 收盘 (东证新规 2024年11月起)
        open_clock = 930 if market_upper == "US" else 900
        close_clock = 1600 if market_upper == "US" else 1530

        today_is_trading = cls.is_trading_day(market_upper, today)

        if not today_is_trading:
            # 今日休市 (周末或法定假期)，目标日为上一个交易日
            return cls.get_previous_trading_day(market_upper, today)

        if clock < open_clock:
            # 开盘前 (例如日股 07:30，美股 08:00)
            return cls.get_previous_trading_day(market_upper, today)
        elif clock < close_clock:
            # 盘中交易时间：全天四价尚未结算定型，上一完成交易日仍为前一交易日
            return cls.get_previous_trading_day(market_upper, today)
        else:
            # 收盘后：今日四价已固化入账，目标日为今日
            return today

    @classmethod
    def get_session_status(
        cls,
        market: str,
        now_dt: Optional[datetime] = None,
    ) -> TradingDayStatus:
        """获取当前市场交易时段状态对象。"""
        market_upper = market.upper()
        tz = cls.get_market_tz(market_upper)
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)
        elif now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)

        local_now = now_dt.astimezone(tz)
        today = local_now.date()
        clock = local_now.hour * 100 + local_now.minute

        target_day = cls.resolve_target_trading_day(market_upper, now_dt)
        today_is_trading = cls.is_trading_day(market_upper, today)

        open_clock = 930 if market_upper == "US" else 900
        close_clock = 1600 if market_upper == "US" else 1530
        pre_clock = 800 if market_upper == "US" else 730
        after_clock = 2000 if market_upper == "US" else 1700

        tz_name = local_now.strftime("%Z")

        if not today_is_trading:
            if today.weekday() >= 5:
                phase = "CLOSED_WEEKEND"
                label_zh = "周末休市"
            else:
                phase = "CLOSED_HOLIDAY"
                label_zh = "法定休市日"
            is_open = False
        else:
            if clock < pre_clock:
                phase = "CLOSED_NIGHT"
                label_zh = "早间未开盘"
                is_open = False
            elif clock < open_clock:
                phase = "PRE_MARKET"
                label_zh = "盘前采集时段"
                is_open = False
            elif clock <= close_clock:
                phase = "REGULAR_TRADING"
                label_zh = "盘中交易时段"
                is_open = True
            elif clock <= after_clock:
                phase = "AFTER_HOURS"
                label_zh = "盘后结算时段"
                is_open = False
            else:
                phase = "CLOSED_NIGHT"
                label_zh = "夜间休市"
                is_open = False

        local_str = local_now.strftime("%Y-%m-%d %H:%M") + f" {tz_name}"
        return TradingDayStatus(
            market=market_upper,
            target_trading_day=target_day.isoformat(),
            is_today_trading_day=today_is_trading,
            is_open_now=is_open,
            session_phase=phase,
            session_label_zh=label_zh,
            local_time_str=local_str,
            tz_name=tz_name,
        )
