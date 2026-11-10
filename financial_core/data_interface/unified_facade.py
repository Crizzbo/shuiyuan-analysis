# -*- coding: utf-8 -*-
"""统一金融数据接口与特征加工门面 (data_interface/unified_facade.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 单一事实来源 (SSOT)：系统所有选股、回测、研报与风控流程的统一数据加工中枢；
2. 零 Token 本地纯物理转换：秒级清洗非标行情、财报、期权、宏观时序；
3. 双模工作支持：
   - 模式一：纯数据加工 (prepare_*) -> 输出强类型 Standard Input Dataclass；
   - 模式二：直通执行 (execute_*) -> 加工后直接驱动底层纯净金融引擎产出评估结论。
"""

from typing import Any, Dict, List, Optional

from .contracts import (
    StandardBar,
    MarketDataFeatureInput,
    ForensicsAccountingInput,
    CreditStructuralInput,
    LiquidityStressInput,
    OptionSurfaceFlowInput,
    MacroRegimeInput,
    UnifiedFeatureBundle,
)
from .market_adapter import MarketDataAdapter
from .accounting_adapter import FinancialStatementAdapter
from .derivative_adapter import DerivativeFlowAdapter
from .macro_adapter import MacroLiquidityAdapter

# 导入底层金融计算引擎
from ..engines.merton_default_engine import MertonStructuralDefaultEngine, MertonDefaultMetrics
from ..engines.amihud_liquidity_engine import AmihudLiquidityEngine, AmihudLiquidityMetrics
from ..engines.option_skew_flow_engine import OptionSkewFlowEngine, OptionSkewMetrics
from ..engines.forensics_and_trailing_exit_engine import ForensicsAndTrailingExitEngine, BeneishScoreResult
from ..engines.market_regime_switching_engine import MarketRegimeSwitchingEngine, MarketRegimeVerdict


class UnifiedFinancialDataInterfaceFacade:
    """统一金融数据接口层门面：将多源异构原始数据加工为各金融引擎标准计算输入."""

    def __init__(self) -> None:
        # 初始化底层计算引擎实例 (懒加载/常驻)
        self.merton_engine = MertonStructuralDefaultEngine()
        self.amihud_engine = AmihudLiquidityEngine()
        self.option_engine = OptionSkewFlowEngine()
        self.forensics_engine = ForensicsAndTrailingExitEngine()
        self.regime_engine = MarketRegimeSwitchingEngine()

    # =========================================================================
    # 一、 数据准备加工管道 (Prepare Layer -> Standard Input Dataclasses)
    # =========================================================================

    @staticmethod
    def prepare_market_features(
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        as_of_date: Optional[str] = None,
        currency: str = "USD",
    ) -> MarketDataFeatureInput:
        """加工行情技术与已实现波动率特征."""
        return MarketDataAdapter.extract_market_features(
            symbol=symbol,
            raw_bars=raw_bars,
            as_of_date=as_of_date,
            currency=currency,
        )

    @staticmethod
    def prepare_liquidity_input(
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        as_of_date: Optional[str] = None,
        market: str = "US",
        intended_order_value: float = 50_000.0,
    ) -> LiquidityStressInput:
        """加工 Amihud 流动性冲击输入."""
        return MarketDataAdapter.extract_liquidity_input(
            symbol=symbol,
            raw_bars=raw_bars,
            as_of_date=as_of_date,
            market=market,
            intended_order_value=intended_order_value,
        )

    @staticmethod
    def prepare_forensics_input(
        symbol: str,
        raw_financials: Dict[str, Any],
        as_of_date: Optional[str] = None,
        currency: str = "USD",
    ) -> ForensicsAccountingInput:
        """加工 Beneish M-Score 八维财务舞弊输入."""
        return FinancialStatementAdapter.extract_forensics_input(
            symbol=symbol,
            raw_financials=raw_financials,
            as_of_date=as_of_date,
            currency=currency,
        )

    @staticmethod
    def prepare_credit_structural_input(
        symbol: str,
        raw_financials: Dict[str, Any],
        equity_market_cap: float,
        equity_volatility: float,
        risk_free_rate: float = 0.04,
        as_of_date: Optional[str] = None,
    ) -> CreditStructuralInput:
        """加工 Merton 结构化信用违约输入."""
        return FinancialStatementAdapter.extract_credit_structural_input(
            symbol=symbol,
            raw_financials=raw_financials,
            equity_market_cap=equity_market_cap,
            equity_volatility=equity_volatility,
            risk_free_rate=risk_free_rate,
            as_of_date=as_of_date,
        )

    @staticmethod
    def prepare_option_skew_input(
        symbol: str,
        underlying_price: float,
        raw_derivative_data: Dict[str, Any],
        as_of_date: Optional[str] = None,
    ) -> OptionSurfaceFlowInput:
        """加工期权偏度与异动流输入."""
        return DerivativeFlowAdapter.extract_option_skew_input(
            symbol=symbol,
            underlying_price=underlying_price,
            raw_derivative_data=raw_derivative_data,
            as_of_date=as_of_date,
        )

    @staticmethod
    def prepare_macro_regime_input(
        as_of_date: str,
        benchmark_symbol: str,
        raw_benchmark_bars: List[Dict[str, Any]],
        current_risk_free_rate: float = 0.04,
    ) -> MacroRegimeInput:
        """加工宏观状态机输入."""
        return MacroLiquidityAdapter.extract_macro_regime_input(
            as_of_date=as_of_date,
            benchmark_symbol=benchmark_symbol,
            raw_benchmark_bars=raw_benchmark_bars,
            current_risk_free_rate=current_risk_free_rate,
        )

    def prepare_unified_bundle(
        self,
        symbol: str,
        as_of_date: str,
        raw_bars: Optional[List[Dict[str, Any]]] = None,
        raw_financials: Optional[Dict[str, Any]] = None,
        raw_derivative: Optional[Dict[str, Any]] = None,
        raw_benchmark_bars: Optional[List[Dict[str, Any]]] = None,
        market: str = "US",
        currency: str = "USD",
        equity_market_cap: Optional[float] = None,
        risk_free_rate: float = 0.04,
    ) -> UnifiedFeatureBundle:
        """一键加工全息集成特征包."""
        m_input = None
        l_input = None
        if raw_bars:
            m_input = self.prepare_market_features(symbol, raw_bars, as_of_date, currency)
            l_input = self.prepare_liquidity_input(symbol, raw_bars, as_of_date, market)

        f_input = None
        c_input = None
        if raw_financials:
            f_input = self.prepare_forensics_input(symbol, raw_financials, as_of_date, currency)
            cap = equity_market_cap if equity_market_cap is not None else 10_000_000_000.0
            vol = m_input.realized_vol20_annualized if m_input else 0.25
            c_input = self.prepare_credit_structural_input(
                symbol=symbol,
                raw_financials=raw_financials,
                equity_market_cap=cap,
                equity_volatility=vol,
                risk_free_rate=risk_free_rate,
                as_of_date=as_of_date,
            )

        o_input = None
        if raw_derivative:
            price = m_input.latest_close if m_input else 100.0
            o_input = self.prepare_option_skew_input(symbol, price, raw_derivative, as_of_date)

        mac_input = None
        if raw_benchmark_bars:
            mac_input = self.prepare_macro_regime_input(
                as_of_date=as_of_date,
                benchmark_symbol="SPY" if market == "US" else "1306.T",
                raw_benchmark_bars=raw_benchmark_bars,
                current_risk_free_rate=risk_free_rate,
            )

        return UnifiedFeatureBundle(
            symbol=symbol,
            as_of_date=as_of_date,
            market_input=m_input,
            forensics_input=f_input,
            credit_input=c_input,
            liquidity_input=l_input,
            option_input=o_input,
            macro_input=mac_input,
            metadata={"market": market, "currency": currency},
        )

    # =========================================================================
    # 二、 直通执行计算管道 (Execute Layer -> Directly invoke Engines)
    # =========================================================================

    def execute_amihud_liquidity(
        self,
        liquidity_input: LiquidityStressInput,
    ) -> AmihudLiquidityMetrics:
        """从标准流动性输入直接驱动 Amihud 计算."""
        return self.amihud_engine.evaluate_liquidity(
            symbol=liquidity_input.symbol,
            bars=liquidity_input.sample_bars,
            market=liquidity_input.market,
            intended_order_value=liquidity_input.intended_order_value,
        )

    def execute_merton_credit(
        self,
        credit_input: CreditStructuralInput,
    ) -> MertonDefaultMetrics:
        """从标准信用结构输入直接驱动 Merton 结构化违约距离计算."""
        return self.merton_engine.evaluate_credit_default_risk(
            equity_market_cap=credit_input.equity_market_cap,
            short_term_debt=credit_input.short_term_debt,
            long_term_debt=credit_input.long_term_debt,
            equity_volatility_annual=credit_input.equity_volatility,
            risk_free_rate=credit_input.risk_free_rate,
            time_horizon_years=credit_input.time_horizon_years,
        )

    def execute_option_skew(
        self,
        option_input: OptionSurfaceFlowInput,
    ) -> OptionSkewMetrics:
        """从标准期权输入直接驱动期权偏度与资金异动流计算."""
        return self.option_engine.evaluate_skew_and_flow(
            symbol=option_input.symbol,
            underlying_price=option_input.underlying_price,
            call_volume=option_input.call_volume,
            put_volume=option_input.put_volume,
            call_open_interest=option_input.call_open_interest,
            put_open_interest=option_input.put_open_interest,
            iv_25d_put=option_input.iv_25d_put,
            iv_25d_call=option_input.iv_25d_call,
            iv_front_month_atm=option_input.iv_front_month_atm,
            iv_back_month_atm=option_input.iv_back_month_atm,
        )

    def execute_beneish_forensics(
        self,
        forensics_input: ForensicsAccountingInput,
    ) -> BeneishScoreResult:
        """从标准法务会计输入直接驱动 Beneish M-Score 八维舞弊核算."""
        return self.forensics_engine.compute_beneish_m_score(
            curr_sales=forensics_input.curr_sales,
            curr_cogs=forensics_input.curr_cogs,
            curr_receivables=forensics_input.curr_receivables,
            curr_current_assets=forensics_input.curr_current_assets,
            curr_ppe_net=forensics_input.curr_ppe_net,
            curr_securities=forensics_input.curr_securities,
            curr_total_assets=forensics_input.curr_total_assets,
            curr_depreciation=forensics_input.curr_depreciation,
            curr_sga=forensics_input.curr_sga,
            curr_long_term_debt=forensics_input.curr_long_term_debt,
            curr_current_liabilities=forensics_input.curr_current_liabilities,
            curr_net_income=forensics_input.curr_net_income,
            curr_cfo=forensics_input.curr_cfo,
            prev_sales=forensics_input.prev_sales,
            prev_cogs=forensics_input.prev_cogs,
            prev_receivables=forensics_input.prev_receivables,
            prev_current_assets=forensics_input.prev_current_assets,
            prev_ppe_net=forensics_input.prev_ppe_net,
            prev_securities=forensics_input.prev_securities,
            prev_total_assets=forensics_input.prev_total_assets,
            prev_depreciation=forensics_input.prev_depreciation,
            prev_sga=forensics_input.prev_sga,
            prev_long_term_debt=forensics_input.prev_long_term_debt,
            prev_current_liabilities=forensics_input.prev_current_liabilities,
        )

    def execute_macro_regime(
        self,
        macro_input: MacroRegimeInput,
    ) -> MarketRegimeVerdict:
        """从标准宏观输入直接驱动状态机与 HMM 判定."""
        return self.regime_engine.detect_regime(
            as_of_date=macro_input.as_of_date,
            historical_benchmark_bars=macro_input.historical_benchmark_bars,
        )
