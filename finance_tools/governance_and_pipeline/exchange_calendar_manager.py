"""交易日历与目标交易日推导工具层门面 (Exchange Calendar Manager Facade).

作为向下兼容与工具中继层，调用底层 financial_core 核心算法引擎。
"""

from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from financial_core.engines.exchange_calendar_engine import (
    ExchangeCalendarEngine,
    TradingDayStatus,
    NEW_YORK_TZ,
    TOKYO_TZ,
)


class ExchangeCalendarManager:
    """交易所交易日历中继与管理门面。"""

    @classmethod
    def is_trading_day(cls, market: str, val: Union[date, datetime, str]) -> bool:
        return ExchangeCalendarEngine.is_trading_day(market, val)

    @classmethod
    def get_previous_trading_day(cls, market: str, val: Union[date, datetime, str]) -> date:
        return ExchangeCalendarEngine.get_previous_trading_day(market, val)

    @classmethod
    def get_next_trading_day(cls, market: str, val: Union[date, datetime, str]) -> date:
        return ExchangeCalendarEngine.get_next_trading_day(market, val)

    @classmethod
    def resolve_target_trading_day(cls, market: str, now_dt: Optional[datetime] = None) -> date:
        return ExchangeCalendarEngine.resolve_target_trading_day(market, now_dt)

    @classmethod
    def get_session_status(cls, market: str, now_dt: Optional[datetime] = None) -> TradingDayStatus:
        return ExchangeCalendarEngine.get_session_status(market, now_dt)
