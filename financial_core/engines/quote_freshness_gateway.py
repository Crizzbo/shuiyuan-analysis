"""行情时效性与时区/交易时段感知门禁网关 (Quote Freshness & Session Gateway).

遵循 Google Python 编程风格指南与《SPEC-11 云端无头每日行情与研报自动化调度流水线规格书》，
贯彻 2026-10-14 行情数据时效性与当日新鲜度强制核验硬约束：
1. 毫秒级时区感知 (UTC, EDT, EST, JST, CST) 与时间戳解析；
2. 交易时段状态识别：pre_market, regular_trading, after_hours, previous_close_baseline；
3. 超期阻断断路器：超 24 小时数据严禁充当盘中实时市价；
4. 规范化买方行情标签渲染 (例如: [2026-10-14 16:00 EDT 前收盘基准] $132.80)。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Optional, Tuple

try:
    import zoneinfo

    NYC_TZ = zoneinfo.ZoneInfo("America/New_York")
    TYO_TZ = zoneinfo.ZoneInfo("Asia/Tokyo")
    SHA_TZ = zoneinfo.ZoneInfo("Asia/Shanghai")
except Exception:
    NYC_TZ = None
    TYO_TZ = None
    SHA_TZ = None


@dataclass(frozen=True)
class QuoteVerificationResult:
    """行情时效核验结果数据类.

    Attributes:
        is_valid: 行情数据是否合法有效且未超期被阻断.
        is_fresh_today: 行情是否产生于当前交易日 (日期匹配).
        session_status: 交易时段状态标识代号 (pre_market, regular_trading, after_hours,
            previous_close_baseline, stale_blocked).
        formatted_label: 符合买方机构展示标准的去工程符号化富文本标签 (例如: $132.80
            [2026-10-14 16:00 EDT 前收盘基准]).
        age_hours: 采样时间距离当前基准时间的滞后小时数 (浮点数).
        message: 核验说明或超期阻断详细警示信息.
    """

    is_valid: bool
    is_fresh_today: bool
    session_status: str
    formatted_label: str
    age_hours: float
    message: str


class QuoteFreshnessGateway:
    """买方机构级行情时效性与交易时段门禁网关 (Google Python Style Guide 架构设计)."""

    MAX_STALENESS_HOURS: float = 24.0

    @classmethod
    def parse_iso_or_tz_timestamp(cls, timestamp_str: str) -> Tuple[datetime, str]:
        """解析多时区时间戳字符串，返回带有时区信息的 UTC datetime 及原始时区标签.

        Args:
            timestamp_str: 待解析的时间戳字符串 (如 '2026-10-15 16:00 EDT' 或
                '2026-10-15T20:00:00Z').

        Returns:
            Tuple[datetime, str]: (UTC 对应 aware datetime, 原始时区标签字符串).

        Raises:
            ValueError: 当时间戳格式无法被任何已知规则解析时抛出.
        """
        clean_str = timestamp_str.strip()
        tz_label = "UTC"

        match_tz = re.search(r"\b(EDT|EST|JST|CST|UTC|GMT)\b", clean_str)
        if match_tz:
            tz_label = match_tz.group(1)
            time_part = re.sub(r"\b(EDT|EST|JST|CST|UTC|GMT)\b", "", clean_str).strip()

            dt_naive = None
            known_formats = (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
            )
            for fmt in known_formats:
                try:
                    dt_naive = datetime.strptime(time_part, fmt)
                    break
                except ValueError:
                    continue

            if dt_naive is None:
                dt_naive = datetime.fromisoformat(time_part)

            offset_hours = 0
            if tz_label == "EDT":
                offset_hours = -4
            elif tz_label == "EST":
                offset_hours = -5
            elif tz_label == "JST":
                offset_hours = 9
            elif tz_label == "CST":
                offset_hours = 8

            tz = timezone(timedelta(hours=offset_hours))
            dt_aware = dt_naive.replace(tzinfo=tz)
            return dt_aware.astimezone(timezone.utc), tz_label

        # 检查是否包含显式时区（如 Z 或 +00:00, -04:00）
        if not (clean_str.endswith("Z") or re.search(r"[+-]\d{2}:?\d{2}$", clean_str)):
            raise ValueError(f"时间戳缺少明确时区标识: {timestamp_str}")

        iso_formatted = clean_str.replace("Z", "+00:00")
        dt_aware = datetime.fromisoformat(iso_formatted)
        if dt_aware.tzinfo is None:
            raise ValueError(f"时间戳未包含有效时区信息: {timestamp_str}")
        return dt_aware.astimezone(timezone.utc), "UTC"

    @classmethod
    def _get_market_tz(cls, market: str, orig_tz: str) -> timezone:
        """获取市场所在交易所当地时区 (私有辅助方法)."""
        if market == "US":
            if NYC_TZ:
                return NYC_TZ
            offset = -5 if orig_tz == "EST" else -4
            return timezone(timedelta(hours=offset))
        if market == "JP":
            return TYO_TZ or timezone(timedelta(hours=9))
        if market == "CN":
            return SHA_TZ or timezone(timedelta(hours=8))
        return timezone.utc

    @classmethod
    def verify_quote(
        cls,
        price: float,
        currency: str,
        quote_timestamp: str,
        market: str = "US",
        current_time_iso: Optional[str] = None,
        max_staleness_hours: Optional[float] = None,
    ) -> QuoteVerificationResult:
        """【时效硬约束】全面核验行情时效性与所在市场交易时段状态.

        Args:
            price: 标的证券报价金额 (如 132.80).
            currency: 货币符号 (如 '$' 或 '¥').
            quote_timestamp: 原始行情采样时间戳 (如 '2026-10-15 16:00 EDT').
            market: 标的所属交易市场代码，支持 'US', 'JP', 'CN' (默认 'US').
            current_time_iso: 当前基准时间戳 (ISO 格式，留空则自动取当前 UTC 时间).
            max_staleness_hours: 允许的最大滞后小时数 (默认取类属性 MAX_STALENESS_HOURS
                24.0h).

        Returns:
            QuoteVerificationResult 结构化核验结果.

        Raises:
            ValueError: 当价格非法 (<= 0 或 NaN/Inf) 或时间戳无时区时抛出.
        """
        # 1. 严格价格数值校验 (拒绝 <= 0, NaN, Inf)
        if not isinstance(price, (int, float)) or math.isnan(price) or math.isinf(price) or price <= 0:
            raise ValueError(f"非法价格输入: {price}")

        limit_hours = (
            max_staleness_hours
            if max_staleness_hours is not None
            else cls.MAX_STALENESS_HOURS
        )
        if current_time_iso:
            now_dt = datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
        else:
            now_dt = datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)

        try:
            q_dt_utc, orig_tz = cls.parse_iso_or_tz_timestamp(quote_timestamp)
        except Exception as err:
            return QuoteVerificationResult(
                is_valid=False,
                is_fresh_today=False,
                session_status="invalid_timestamp",
                formatted_label=f"{currency}{price:.2f} (时间戳格式非法)",
                age_hours=999.0,
                message=f"时间戳解析失败: {err}",
            )

        age_seconds = (now_dt - q_dt_utc).total_seconds()
        # 未来行情硬阻断 (超前 60 秒以上)
        if age_seconds < -60.0:
            return QuoteVerificationResult(
                is_valid=False,
                is_fresh_today=False,
                session_status="future_quote_blocked",
                formatted_label=f"【阻断】{currency}{price:.2f} [未来时间戳阻断]",
                age_hours=age_seconds / 3600.0,
                message=f"行情时间戳早于当前系统基准时间 (未来时间 {abs(age_seconds)/60:.1f} 分钟)，已被安全阻断！",
            )

        age_hours = max(0.0, age_seconds / 3600.0)

        # 超过 24 小时硬阻断
        if age_hours > limit_hours:
            return QuoteVerificationResult(
                is_valid=False,
                is_fresh_today=False,
                session_status="stale_blocked",
                formatted_label=f"【阻断】{currency}{price:.2f} [超期 {age_hours:.1f}h]",
                age_hours=age_hours,
                message=(
                    f"【严重超期阻断】行情数据滞后 {age_hours:.1f} 小时 "
                    f"(阈值 {limit_hours:.0f}h)，严禁冒充实时市价！"
                ),
            )

        market_tz = cls._get_market_tz(market, orig_tz)
        q_local = q_dt_utc.astimezone(market_tz)
        now_local = now_dt.astimezone(market_tz)
        is_today = (q_local.date() == now_local.date()) and (q_dt_utc.date() == now_dt.date())

        session_status = cls._determine_session_status(
            q_dt_utc=q_dt_utc,
            is_today=is_today,
            market=market,
            orig_tz=orig_tz,
            now_dt_utc=now_dt,
        )

        status_zh_map = {
            "pre_market": "盘前最新",
            "regular_trading": "盘中现价",
            "lunch_break": "午间休市",
            "after_hours": "盘后基准",
            "previous_close_baseline": "前收盘基准",
        }
        status_zh = status_zh_map.get(session_status, "前收盘基准")
        formatted_label = (
            f"{currency}{price:,.2f} [{quote_timestamp.strip()} {status_zh}]"
        )

        return QuoteVerificationResult(
            is_valid=True,
            is_fresh_today=is_today,
            session_status=session_status,
            formatted_label=formatted_label,
            age_hours=age_hours,
            message=f"时效核验通过 ({status_zh}, 采样于 {age_hours:.1f} 小时前)",
        )

    @classmethod
    def _determine_session_status(
        cls,
        q_dt_utc: datetime,
        is_today: bool,
        market: str,
        orig_tz: str,
        now_dt_utc: Optional[datetime] = None,
    ) -> str:
        """判定目标市场的具体交易时段 (私有辅助方法)."""
        if not is_today:
            return "previous_close_baseline"

        market_tz = cls._get_market_tz(market, orig_tz)
        q_local = q_dt_utc.astimezone(market_tz)

        if q_local.weekday() >= 5:
            return "previous_close_baseline"

        q_h = q_local.hour + q_local.minute / 60.0

        if market == "US":
            if 4.0 <= q_h < 9.5:
                return "pre_market"
            if 9.5 <= q_h <= 16.0:
                return "regular_trading"
            if 16.0 < q_h <= 20.0:
                return "after_hours"
            return "previous_close_baseline"

        if market == "JP":
            # 东京市场：9:00~11:30 早盘，11:30~12:30 午休，12:30~15:30 午盘，15:30~17:00 盘后
            if 11.5 < q_h < 12.5:
                return "lunch_break"
            if 8.0 <= q_h < 9.0:
                return "pre_market"
            if (9.0 <= q_h <= 11.5) or (12.5 <= q_h <= 15.5):
                return "regular_trading"
            if 15.5 < q_h <= 17.0:
                return "after_hours"
            return "previous_close_baseline"

        if market == "CN":
            if 11.5 < q_h < 13.0:
                return "lunch_break"
            if 9.0 <= q_h < 9.5:
                return "pre_market"
            if (9.5 <= q_h <= 11.5) or (13.0 <= q_h <= 15.0):
                return "regular_trading"
            if 15.0 < q_h <= 15.5:
                return "after_hours"
            return "previous_close_baseline"

        return "previous_close_baseline"
