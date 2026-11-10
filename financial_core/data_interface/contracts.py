# -*- coding: utf-8 -*-
"""金融数据接口层标准输入契约 (data_interface/contracts.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 单一事实来源 (SSOT)：为所有金融计算引擎提供统一、强类型、不可变的输入数据模型；
2. 架构独立纯净：位于 financial_core 内部，零外层逆向依赖；
3. 防御性契约：
   - 字段带严格类型标注与默认安全值；
   - 显式区分缺失值与真实零值；
   - 贯穿币种 (currency)、市场 (market) 与时间戳 (as_of_date)。
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class StandardBar:
    """标准化点时行情日 K 线契约."""
    date: str               # 交易日期 YYYY-MM-DD
    open: float             # 开盘价
    high: float             # 最高价
    low: float              # 最低价
    close: float            # 收盘价
    volume: float           # 成交量 (股数)
    turnover: float         # 成交金额 ($ 或 ¥)
    adj_close: float        # 前复权收盘价


@dataclass(frozen=True)
class MarketDataFeatureInput:
    """行情技术特征标准输入契约 (供动量、波动率与均线模型计算)."""
    symbol: str
    as_of_date: str
    currency: str
    bars_count: int
    latest_close: float
    historical_closes: List[float]
    historical_volumes: List[float]
    historical_turnovers: List[float]
    log_returns_20d: List[float]
    sma20: float
    sma50: float
    sma200: float
    realized_vol20_annualized: float
    highest_22d: float
    lowest_22d: float
    atr22: float


@dataclass(frozen=True)
class ForensicsAccountingInput:
    """法务会计防舞弊标准输入契约 (供 Beneish M-Score 八维模型计算)."""
    symbol: str
    as_of_date: str
    reporting_currency: str
    # 当期财务指标
    curr_sales: float
    curr_cogs: float
    curr_receivables: float
    curr_current_assets: float
    curr_ppe_net: float
    curr_securities: float
    curr_total_assets: float
    curr_depreciation: float
    curr_sga: float
    curr_long_term_debt: float
    curr_current_liabilities: float
    curr_net_income: float
    curr_cfo: float
    # 上年同期财务指标
    prev_sales: float
    prev_cogs: float
    prev_receivables: float
    prev_current_assets: float
    prev_ppe_net: float
    prev_securities: float
    prev_total_assets: float
    prev_depreciation: float
    prev_sga: float
    prev_long_term_debt: float
    prev_current_liabilities: float


@dataclass(frozen=True)
class CreditStructuralInput:
    """结构化信用与偿债违约标准输入契约 (供 KMV-Merton 违约距离模型计算)."""
    symbol: str
    as_of_date: str
    equity_market_cap: float      # 股权总市值 E ($ 或 ¥)
    short_term_debt: float        # 短期借款与一年内到期非流动负债 STD
    long_term_debt: float         # 长期借款与长期应付债券 LTD
    default_point_debt: float     # 违约触发点债务面值 D = STD + 0.5 * LTD
    risk_free_rate: float         # 无风险基准利率 r (如 10Y 国债)
    equity_volatility: float      # 股权历史年化波动率 sigma_E
    time_horizon_years: float = 1.0


@dataclass(frozen=True)
class LiquidityStressInput:
    """微观流动性冲击与非线性滑点标准输入契约 (供 Amihud 模型计算)."""
    symbol: str
    as_of_date: str
    market: str                   # US / JP
    sample_bars: List[Dict[str, Any]]
    intended_order_value: float   # 拟交易买入金额 ($ 或 ¥)
    average_daily_turnover_20d: float


@dataclass(frozen=True)
class OptionSurfaceFlowInput:
    """期权偏度与主力大单异动标准输入契约 (供 Option Skew & Flow 模型计算)."""
    symbol: str
    as_of_date: str
    underlying_price: float
    call_volume: float
    put_volume: float
    call_open_interest: float
    put_open_interest: float
    iv_25d_put: float
    iv_25d_call: float
    iv_front_month_atm: float
    iv_back_month_atm: float


@dataclass(frozen=True)
class MacroRegimeInput:
    """宏观流动性与大盘状态标准输入契约 (供 HMM 与状态机切换引擎计算)."""
    as_of_date: str
    benchmark_symbol: str
    historical_benchmark_bars: List[Dict[str, Any]]
    current_risk_free_rate: float = 0.04
    vol_crisis_threshold: float = 0.28
    vol_calm_threshold: float = 0.22


@dataclass(frozen=True)
class UnifiedFeatureBundle:
    """全息加工产物统一集成数据包."""
    symbol: str
    as_of_date: str
    market_input: Optional[MarketDataFeatureInput] = None
    forensics_input: Optional[ForensicsAccountingInput] = None
    credit_input: Optional[CreditStructuralInput] = None
    liquidity_input: Optional[LiquidityStressInput] = None
    option_input: Optional[OptionSurfaceFlowInput] = None
    macro_input: Optional[MacroRegimeInput] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
