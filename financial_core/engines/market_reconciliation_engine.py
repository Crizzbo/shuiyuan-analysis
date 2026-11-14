"""全市场逐标的目标日覆盖对账与平账引擎 (Universe Coverage Reconciliation Engine).

遵循买方机构级数据治理与刚性平账自检底线：
1. 以 (market, symbol, target_date) 为唯一对账主键；
2. 刚性平账核算：标的分母 = 已匹配 + 停牌未交易 + 待补数 + 未映射 + 上游异常；
3. 准确分离“历史日线已存在”与“目标交易日真实落盘”；
4. 输出买方通俗商业语言解读，去工程符号化。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ReconciliationSummary:
    """全市场目标交易日覆盖对账平账总表。"""
    market: str
    target_trading_day: str
    as_of: str
    universe_count: int
    matched_count: int
    no_trade_count: int
    pending_count: int
    unmapped_count: int
    error_count: int
    coverage_rate_pct: float
    active_trade_rate_pct: float
    unmapped_symbols: List[str]
    is_balanced: bool
    balance_diff: int
    narrative_zh: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "target_trading_day": self.target_trading_day,
            "as_of": self.as_of,
            "universe_count": self.universe_count,
            "matched_count": self.matched_count,
            "no_trade_count": self.no_trade_count,
            "pending_count": self.pending_count,
            "unmapped_count": self.unmapped_count,
            "error_count": self.error_count,
            "coverage_rate_pct": round(self.coverage_rate_pct, 2),
            "active_trade_rate_pct": round(self.active_trade_rate_pct, 2),
            "unmapped_symbols": self.unmapped_symbols,
            "is_balanced": self.is_balanced,
            "balance_diff": self.balance_diff,
            "narrative_zh": self.narrative_zh,
        }


class MarketReconciliationEngine:
    """全市场目标交易日覆盖对账与平账引擎。"""

    # 已核实无法映射到公开行情供应商的特殊证券代码（保留底账待办）
    KNOWN_UNMAPPED: Dict[str, Set[str]] = {
        "US": {"NONE."},
        "JP": {"25935", "50765", "75505", "92015", "92025", "94345", "94346"},
    }

    @classmethod
    def get_known_unmapped(cls, market: str) -> Set[str]:
        return cls.KNOWN_UNMAPPED.get(market.upper(), set())

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
        """执行目标交易日全市场全息对账核算与平账自检。

        Args:
            market: 市场代码 "US" 或 "JP"
            target_date: 目标交易日 YYYY-MM-DD
            universe_symbols: 该市场官方登记全量代码列表 (分母)
            archived_records: 归档数据字典 {symbol: [OHLCV rows]}
            error_symbols: 采集失败或上游报错的代码集合
            as_of: 核验时间戳
        """
        market_upper = market.upper()
        if as_of is None:
            as_of = datetime.now(timezone.utc).isoformat(timespec="seconds")

        error_set = error_symbols or set()
        unmapped_set = cls.get_known_unmapped(market_upper)

        universe_set = set(universe_symbols)
        universe_count = len(universe_set)

        matched_count = 0
        no_trade_count = 0
        pending_count = 0
        unmapped_count = 0
        error_count = 0

        target_date_clean = target_date[:10]

        for symbol in universe_set:
            if symbol in unmapped_set:
                unmapped_count += 1
                continue

            records = archived_records.get(symbol)
            if records:
                # 检查日线时序中是否有精确匹配目标交易日的记录
                target_row = next(
                    (row for row in records if str(row.get("Date", ""))[:10] == target_date_clean),
                    None
                )
                if target_row is not None:
                    close = target_row.get("Close")
                    vol = target_row.get("Volume", 0)
                    has_valid_close = (
                        isinstance(close, (int, float)) and
                        math.isfinite(close) and
                        close > 0
                    )
                    # 成交量大于 0 且价格有效为正常匹配交易
                    if has_valid_close and vol and vol > 0:
                        matched_count += 1
                    else:
                        # 停牌、全天未成交或无量基准
                        no_trade_count += 1
                else:
                    # 存在历史记录但缺少目标交易日数据 (属于待补充最新日)
                    pending_count += 1
            elif symbol in error_set:
                error_count += 1
            else:
                pending_count += 1

        # 刚性平账自检
        accounted_total = matched_count + no_trade_count + pending_count + unmapped_count + error_count
        balance_diff = universe_count - accounted_total
        is_balanced = (balance_diff == 0)

        coverage_pct = ((matched_count + no_trade_count) / universe_count * 100.0) if universe_count > 0 else 0.0
        active_pct = (matched_count / universe_count * 100.0) if universe_count > 0 else 0.0

        market_name = "美股" if market_upper == "US" else "日股"
        narrative = (
            f"{market_name}目标交易日 ({target_date_clean}) 全市场对账完成：全库标的 {universe_count} 家，"
            f"目标日行情有效匹配 {matched_count} 家，停牌无成交 {no_trade_count} 家，"
            f"待拉取补数 {pending_count} 家，未映射特殊证券 {unmapped_count} 家，来源异常 {error_count} 家。"
            f"目标日有效覆盖率 {coverage_pct:.1f}%。"
        ) if is_balanced else (
            f"警告：{market_name}对账底账未平账，差额 {balance_diff} 家！"
        )

        return ReconciliationSummary(
            market=market_upper,
            target_trading_day=target_date_clean,
            as_of=as_of,
            universe_count=universe_count,
            matched_count=matched_count,
            no_trade_count=no_trade_count,
            pending_count=pending_count,
            unmapped_count=unmapped_count,
            error_count=error_count,
            coverage_rate_pct=coverage_pct,
            active_trade_rate_pct=active_pct,
            unmapped_symbols=sorted(unmapped_set & universe_set),
            is_balanced=is_balanced,
            balance_diff=balance_diff,
            narrative_zh=narrative,
        )
