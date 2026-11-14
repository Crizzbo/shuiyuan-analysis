"""全市场目标日覆盖对账工具门面 (Market Reconciliation Manager Facade).

作为向下兼容与工具中继层，调用底层 financial_core 核心算法引擎。
"""

from typing import Any, Dict, List, Optional, Set

from financial_core.engines.market_reconciliation_engine import (
    MarketReconciliationEngine,
    ReconciliationSummary,
)


class MarketReconciliationManager:
    """全市场目标交易日覆盖对账与平账中继门面。"""

    @classmethod
    def get_known_unmapped(cls, market: str) -> Set[str]:
        return MarketReconciliationEngine.get_known_unmapped(market)

    @classmethod
    def reconcile_target_day(
        cls,
        market: str,
        target_date: str,
        universe_symbols: List[str],
        archived_records: Dict[str, List[Dict[str, Any]]],
        *,
        error_symbols: Optional[Set[str]] = None,
        as_of: Optional[str] = None,
    ) -> ReconciliationSummary:
        return MarketReconciliationEngine.reconcile_target_day(
            market=market,
            target_date=target_date,
            universe_symbols=universe_symbols,
            archived_records=archived_records,
            error_symbols=error_symbols,
            as_of=as_of,
        )
