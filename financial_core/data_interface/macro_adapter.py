# -*- coding: utf-8 -*-
"""宏观流动性与基准时序数据接口适配器 (data_interface/macro_adapter.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 点时零前视截断：大盘基准日线仅保留 <= as_of_date 的已实现数据；
2. 宏观无风险利率对齐：提取或对齐 10Y 美债等基准收益率；
3. 输出纯净标准输入契约：MacroRegimeInput。
"""

from typing import Any, Dict, List, Optional

from .contracts import MacroRegimeInput
from .market_adapter import MarketDataAdapter


class MacroLiquidityAdapter:
    """宏观流动性与基准时序适配器：为宏观状态机与 HMM 阀门准备清洗后的标准输入."""

    @classmethod
    def extract_macro_regime_input(
        cls,
        as_of_date: str,
        benchmark_symbol: str,
        raw_benchmark_bars: List[Dict[str, Any]],
        current_risk_free_rate: float = 0.04,
        vol_crisis_threshold: float = 0.28,
        vol_calm_threshold: float = 0.22,
    ) -> MacroRegimeInput:
        """清洗并截断基准大盘日线，生成宏观状态机输入契约."""
        # 严格执行点时截断与标准化
        pit_bars = MarketDataAdapter.filter_pit_bars(raw_benchmark_bars, as_of_date)

        # 转换为状态机期望的标准字典列表
        standard_dicts = [
            {
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "turnover": b.turnover,
                "adj_close": b.adj_close,
            }
            for b in pit_bars
        ]

        return MacroRegimeInput(
            as_of_date=as_of_date,
            benchmark_symbol=benchmark_symbol.upper(),
            historical_benchmark_bars=standard_dicts,
            current_risk_free_rate=max(0.0, float(current_risk_free_rate)),
            vol_crisis_threshold=float(vol_crisis_threshold),
            vol_calm_threshold=float(vol_calm_threshold),
        )
