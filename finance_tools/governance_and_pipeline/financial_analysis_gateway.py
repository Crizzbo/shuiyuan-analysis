# -*- coding: utf-8 -*-
"""买方金融计算与行业因果分析统一业务网关 (financial_analysis_gateway.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 单一事实来源 (SSOT)：统一协调调度底层纯净引擎 (financial_core) 与数据接口层 (data_interface)；
2. 零外部黑盒依赖：纯标准库与项目内原生引擎协同，零网络硬调用；
3. 全面覆盖买方核心分析维度：
   - 细分行业结构化知识与因果敏感性分析 (Industry Analysis)
   - 通用商业物理动力学分析 (Universal Physical Dynamics)
   - 法务会计防舞弊核算 (Beneish M-Score Forensics)
   - KMV-Merton 结构化信用违约与破产预警 (Credit Risk Analysis)
   - Amihud 微观流动性冲击与动态滑点测算 (Liquidity Stress Analysis)
   - 期权偏度与主力大单异动分析 (Option Skew & Flow Analysis)
   - 宏观状态机与动态资产配置建议 (Macro Regime Switching)
   - 全息买方综合诊断 (Comprehensive Quantamental Diagnosis)
"""

from dataclasses import dataclass, field, asdict
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 引入底层纯净金融核心与数据接口
from financial_core.data_interface import (
    StandardBar,
    MarketDataFeatureInput,
    ForensicsAccountingInput,
    CreditStructuralInput,
    LiquidityStressInput,
    OptionSurfaceFlowInput,
    MacroRegimeInput,
    UnifiedFeatureBundle,
    MarketDataAdapter,
    FinancialStatementAdapter,
    DerivativeFlowAdapter,
    MacroLiquidityAdapter,
    UnifiedFinancialDataInterfaceFacade,
)
from financial_core.engines.industry_knowledge_manager import IndustryKnowledgeManager
from financial_core.engines.industry_causal_registry import IndustryCausalStrategyRegistry, IndustryCausalFacts
from financial_core.engines.industry_taxonomy_bridge import IndustryTaxonomyBridge
from financial_core.engines.universal_physical_dynamics_engine import (
    UniversalPhysicalDynamicsEngine,
    UniversalDynamicsProfile,
)
from financial_core.engines.forensics_and_trailing_exit_engine import (
    ForensicsAndTrailingExitEngine,
    BeneishScoreResult,
)
from financial_core.engines.merton_default_engine import (
    MertonStructuralDefaultEngine,
    MertonDefaultMetrics,
)
from financial_core.engines.amihud_liquidity_engine import (
    AmihudLiquidityEngine,
    AmihudLiquidityMetrics,
)
from financial_core.engines.option_skew_flow_engine import (
    OptionSkewFlowEngine,
    OptionSkewMetrics,
)
from financial_core.engines.market_regime_switching_engine import (
    MarketRegimeSwitchingEngine,
    MarketRegimeVerdict,
    MarketRegime,
)


@dataclass(frozen=True)
class IndustryAnalysisReport:
    """行业结构化分析结果契约."""
    industry_id: str
    industry_name_zh: str
    sector_id: str
    sector_name_zh: str
    macro_sector_id: str
    macro_sector_name_zh: str
    description: str
    key_drivers: List[str]
    accounting_focus: List[str]
    causal_sensitivities: Dict[str, Any]
    representative_tickers: List[str]
    moat_types: List[str]
    risk_factors: List[str]


@dataclass(frozen=True)
class ComprehensiveAnalysisReport:
    """全景买方综合诊断报告契约."""
    symbol: str
    as_of_date: str
    market: str
    industry_report: Optional[IndustryAnalysisReport] = None
    physics_report: Optional[Dict[str, Any]] = None
    forensics_report: Optional[Dict[str, Any]] = None
    credit_report: Optional[Dict[str, Any]] = None
    liquidity_report: Optional[Dict[str, Any]] = None
    option_report: Optional[Dict[str, Any]] = None
    regime_report: Optional[Dict[str, Any]] = None
    executive_summary_zh: str = ""
    actionable_verdict: str = "NEUTRAL"


class FinancialAnalysisGateway:
    """买方金融计算与行业分析统一业务网关."""

    _instance: Optional["FinancialAnalysisGateway"] = None

    def __init__(self) -> None:
        self.facade = UnifiedFinancialDataInterfaceFacade()
        self.industry_mgr = IndustryKnowledgeManager.get_instance()
        self.causal_registry = IndustryCausalStrategyRegistry()
        self.taxonomy_bridge = IndustryTaxonomyBridge()
        self.physics_engine = UniversalPhysicalDynamicsEngine()

    @classmethod
    def get_instance(cls) -> "FinancialAnalysisGateway":
        """单例访问入口."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =========================================================================
    # 1. 行业深度因果与知识画像分析
    # =========================================================================
    def analyze_industry(self, target: str) -> IndustryAnalysisReport:
        """分析指定细分行业或由股票代码反查行业知识画像与敏感性因果链.

        target: 可以是行业ID (如 'semiconductors')、中文行业名 (如 '半导体') 或股票代码 (如 'NVDA').
        """
        clean_target = str(target).strip()

        # 尝试通过股票代码映射行业
        mapped_industry_id = ""
        # 优先委托 TaxonomyBridge 的归一化解析
        try:
            rec = self.taxonomy_bridge.resolve_industry_from_ticker_or_sector(clean_target, "")
            if rec and rec.industry_id != "general":
                mapped_industry_id = rec.industry_id
        except Exception:
            pass

        if not mapped_industry_id:
            try:
                rec = self.taxonomy_bridge.get_record(clean_target)
                if rec and rec.industry_id:
                    mapped_industry_id = rec.industry_id
            except Exception:
                pass

        if not mapped_industry_id:
            mapped_industry_id = "software"  # 稳健兜底行业

        # 获取行业知识档案
        prof = self.industry_mgr.get_profile(mapped_industry_id)

        # 获取因果注册表敏感性
        causal_data = {}
        try:
            facts = self.causal_registry.evaluate_industry_causal_facts(
                industry_id=mapped_industry_id,
                company_metrics={},
                forensic_findings={},
                macro_shock_data={},
            )
            if facts:
                causal_data = {
                    "industry_catalysts": facts.industry_catalysts,
                    "industry_risks": facts.industry_risks,
                    "leading_optimistic_trigger": facts.leading_optimistic_trigger,
                    "leading_pessimistic_trigger": facts.leading_pessimistic_trigger,
                    "valuation_route": facts.valuation_route,
                }
        except Exception:
            causal_data = {"note": "通用行业基准因果传导"}

        # 提炼行业核心驱动与风险
        key_drivers = getattr(prof, "key_drivers", ["资本开支(CapEx)周期", "终端渗透率", "供需剪刀差"])
        accounting_focus = getattr(prof, "accounting_focus", ["存货周转天数(DIO)", "毛利率韧性", "研发资本化率"])
        moat_types = getattr(prof, "moat_types", ["技术专利壁垒", "高昂转换成本", "规模经济"])
        risk_factors = getattr(prof, "risk_factors", ["地缘贸易摩擦", "技术路径迭代", "宏观流动性紧缩"])
        rep_tickers = getattr(prof, "representative_tickers", ["NVDA", "TSM", "AAPL", "MSFT"])

        return IndustryAnalysisReport(
            industry_id=prof.industry_id,
            industry_name_zh=prof.industry_name_zh,
            sector_id=prof.sector_id,
            sector_name_zh=prof.sector_name_zh,
            macro_sector_id=prof.macro_sector_id,
            macro_sector_name_zh=prof.macro_sector_name_zh,
            description=prof.description_zh or f"{prof.industry_name_zh}细分行业买方投研知识档案",
            key_drivers=key_drivers if isinstance(key_drivers, list) else [str(key_drivers)],
            accounting_focus=accounting_focus if isinstance(accounting_focus, list) else [str(accounting_focus)],
            causal_sensitivities=causal_data,
            representative_tickers=rep_tickers if isinstance(rep_tickers, list) else [str(rep_tickers)],
            moat_types=moat_types if isinstance(moat_types, list) else [str(moat_types)],
            risk_factors=risk_factors if isinstance(risk_factors, list) else [str(risk_factors)],
        )

    # =========================================================================
    # 2. 通用商业物理动力学分析
    # =========================================================================
    def analyze_physics(
        self,
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        as_of_date: Optional[str] = None,
        market_cap: float = 100_000_000_000.0,
        annual_revenue: float = 20_000_000_000.0,
    ) -> Dict[str, Any]:
        """运行商业物理动力学分析 (质量、动量、动能/势能比率、阻尼震荡、逃逸速度)."""
        pit_bars = MarketDataAdapter.filter_pit_bars(raw_bars, as_of_date)
        bars_count = len(pit_bars)
        if bars_count < 5:
            # 基础数据不足时返回安全兜底
            return {
                "symbol": symbol,
                "status": "INSUFFICIENT_DATA",
                "mass": 100.0,
                "kinetic_energy": 0.0,
                "potential_barrier": 1.0,
                "kinetic_to_potential_ratio": 0.0,
                "is_escape_velocity_achieved": False,
                "damping_ratio": 0.5,
                "breakout_energy_quality": "WEAK",
            }

        closes = [b.close for b in pit_bars]
        highs = [b.high for b in pit_bars]
        lows = [b.low for b in pit_bars]
        volumes = [b.volume for b in pit_bars]
        eff_date = as_of_date or pit_bars[-1].date

        prof = self.physics_engine.analyze_ticker_dynamics(
            ticker=symbol,
            as_of_date=eff_date,
            close_prices=closes,
            high_prices=highs,
            low_prices=lows,
            volumes=volumes,
            shares_outstanding=max(1.0, market_cap / max(1.0, closes[-1])),
        )

        pd = prof.price_dynamics
        vd = prof.valuation_distribution
        sc = prof.supply_chain_dynamics

        # 计算动能/势能比率 (基于趋势速度与停滞底价安全垫)
        k_ratio = round(max(0.01, (pd.trend_velocity_annual_pct + 50.0) / 50.0), 3)
        escape_velocity = pd.momentum_acceleration_pct > 0 and pd.trend_velocity_annual_pct > 20.0

        return {
            "symbol": symbol,
            "status": "COMPLETED",
            "as_of_date": eff_date,
            "rebound_half_life_days": round(pd.rebound_half_life_days, 1),
            "trend_velocity_annual_pct": round(pd.trend_velocity_annual_pct, 2),
            "momentum_acceleration_pct": round(pd.momentum_acceleration_pct, 2),
            "panic_calming_days": round(pd.panic_calming_days, 1),
            "annualized_realized_vol_pct": round(pd.annualized_realized_vol_pct, 2),
            "equilibrium_mu_price": round(pd.equilibrium_mu_price, 2),
            "zero_growth_floor_price": round(vd.zero_growth_floor_price, 2),
            "steady_state_value_price": round(vd.steady_state_value_price, 2),
            "optimistic_target_price": round(vd.optimistic_target_price, 2),
            "current_vs_floor_gap_pct": round(vd.current_vs_floor_gap_pct, 2),
            "cash_conversion_cycle_days": round(sc.cash_conversion_cycle_days, 1),
            "kinetic_to_potential_ratio": k_ratio,
            "is_escape_velocity_achieved": escape_velocity,
            "business_physics_summary_zh": prof.business_physics_summary_zh,
            "breakout_power_verdict": "STRONG_ESCAPE" if escape_velocity else (
                "POTENTIAL_BREAKOUT" if k_ratio >= 1.0 else "TRAPPED_IN_GRAVITY"
            ),
        }

    # =========================================================================
    # 3. 法务会计防舞弊核算 (Beneish M-Score)
    # =========================================================================
    def analyze_forensics(
        self,
        symbol: str,
        raw_financials: Dict[str, Any],
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行 Beneish M-Score 八维法务造假排查与 Chandelier Exit 止损位推演."""
        b_input = FinancialStatementAdapter.extract_forensics_input(
            symbol=symbol,
            raw_financials=raw_financials,
            as_of_date=as_of_date,
        )
        res = self.facade.execute_beneish_forensics(b_input)
        m = res.metrics
        return {
            "symbol": symbol,
            "m_score": round(res.m_score, 3),
            "is_manipulation_suspect": res.is_manipulation_suspect,
            "risk_rating": res.risk_rating,
            "manipulation_probability_pct": round(res.manipulation_probability_pct, 2),
            "flagged_dimensions": res.flagged_dimensions,
            "variables": {
                "DSRI_应收账款指数": round(m.dsri, 3),
                "GMI_毛利率变动指数": round(m.gmi, 3),
                "AQI_资产质量指数": round(m.aqi, 3),
                "SGI_营业收入增长指数": round(m.sgi, 3),
                "DEPI_折旧率变动指数": round(m.depi, 3),
                "SGAI_销售管理费用指数": round(m.sgai, 3),
                "LVGI_财务杠杆变动指数": round(m.lvgi, 3),
                "TATA_总权责发生额比率": round(m.tata, 3),
            },
            "interpretation_zh": (
                "M-Score > -1.78，高度怀疑财务粉饰与激进权责发生制操纵！"
                if res.is_manipulation_suspect
                else "M-Score处于安全区间，未发现严重操纵痕迹。"
            ),
        }

    # =========================================================================
    # 4. KMV-Merton 结构化信用违约与破产预警
    # =========================================================================
    def analyze_credit(
        self,
        symbol: str,
        raw_financials: Dict[str, Any],
        equity_market_cap: float,
        equity_volatility: float,
        risk_free_rate: float = 0.04,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行 KMV-Merton 结构化信用违约风险测算 (违约距离、违约概率)."""
        c_input = FinancialStatementAdapter.extract_credit_structural_input(
            symbol=symbol,
            raw_financials=raw_financials,
            equity_market_cap=equity_market_cap,
            equity_volatility=equity_volatility,
            risk_free_rate=risk_free_rate,
            as_of_date=as_of_date,
        )
        res = self.facade.execute_merton_credit(c_input)
        return {
            "symbol": symbol,
            "default_point_debt": round(c_input.default_point_debt, 2),
            "distance_to_default_DD": round(res.distance_to_default, 2),
            "implied_default_probability": round(res.expected_default_freq, 6),
            "is_black_swan_alert": res.is_black_swan_alert,
            "credit_health_status": res.credit_health_grade,
        }

    # =========================================================================
    # 5. Amihud 微观流动性冲击与动态滑点
    # =========================================================================
    def analyze_liquidity(
        self,
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        intended_order_value: float = 50_000.0,
        market: str = "US",
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """测算 Amihud 微观流动性冲击、非线性滑点与资金容量上限."""
        l_input = MarketDataAdapter.extract_liquidity_input(
            symbol=symbol,
            raw_bars=raw_bars,
            as_of_date=as_of_date,
            market=market,
            intended_order_value=intended_order_value,
        )
        res = self.facade.execute_amihud_liquidity(l_input)
        return {
            "symbol": res.symbol,
            "market": market.upper(),
            "amihud_illiquidity_ratio": f"{res.amihud_illiquidity_ratio:.4e}",
            "is_illiquid_trap": res.is_illiquid_trap,
            "recommended_max_order_size": round(res.recommended_max_order_size, 2),
            "market_impact_penalty_bps": round(res.market_impact_penalty_bps, 2),
            "total_effective_slippage_bps": round(10.0 + res.market_impact_penalty_bps, 2),
            "liquidity_tier": res.capacity_tier,
        }

    # =========================================================================
    # 6. 期权偏度与异动分析
    # =========================================================================
    def analyze_options(
        self,
        symbol: str,
        underlying_price: float,
        raw_derivative: Dict[str, Any],
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """测算期权偏度 (25D Risk Reversal Skew)、PCR 与主力异动流."""
        opt_input = DerivativeFlowAdapter.extract_option_skew_input(
            symbol=symbol,
            underlying_price=underlying_price,
            raw_derivative_data=raw_derivative,
            as_of_date=as_of_date,
        )
        res = self.facade.execute_option_skew(opt_input)
        return {
            "symbol": res.symbol,
            "skew_25d_risk_reversal": round(res.skew_25delta, 4),
            "term_structure_ratio": round(res.term_structure_ratio, 4),
            "put_call_volume_ratio": round(res.put_call_volume_ratio, 3),
            "is_overnight_crash_alert": res.is_overnight_crash_alert,
            "dealer_gamma_regime": res.dealer_gamma_exposure_regime,
            "tail_risk_verdict": res.flow_sentiment_regime,
        }

    # =========================================================================
    # 7. 宏观状态机与动态资产配置建议
    # =========================================================================
    def analyze_macro_regime(
        self,
        benchmark_symbol: str = "SPY",
        raw_benchmark_bars: Optional[List[Dict[str, Any]]] = None,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """运行 3 状态高斯 HMM 状态机识别宏观状态与总仓位预算."""
        bars = raw_benchmark_bars or [
            {"date": f"2024-01-{(i % 28) + 1:02d}", "close": 470.0 + i * 0.5, "turnover": 5000000000.0}
            for i in range(1, 60)
        ]
        mac_input = MacroLiquidityAdapter.extract_macro_regime_input(
            as_of_date=as_of_date or bars[-1]["date"],
            benchmark_symbol=benchmark_symbol,
            raw_benchmark_bars=bars,
        )
        engine = MarketRegimeSwitchingEngine(min_benchmark_bars=50)
        res = engine.detect_regime(
            as_of_date=mac_input.as_of_date,
            historical_benchmark_bars=mac_input.historical_benchmark_bars,
        )
        reg_str = res.regime.value if hasattr(res.regime, "value") else str(res.regime)
        return {
            "benchmark_symbol": benchmark_symbol,
            "regime_state": reg_str,
            "state_name_zh": {
                "BULL_MOMENTUM": "牛市主升浪（进攻态）",
                "RANGE_BOUND_VALUE": "震荡箱体期（均值回归态）",
                "CRISIS_DEFENSE": "危机避险期（极度防守态）",
            }.get(reg_str, reg_str),
            "recommended_gross_exposure": round(res.position_ceiling_pct, 2),
            "recommended_active_model": res.selected_strategy_model,
            "macro_vix_proxy_vol": round(res.vol20_annualized, 4),
            "trend_valve_open": res.valve_status == "OPEN",
            "rationale_zh": res.rationale_zh,
        }

    # =========================================================================
    # 8. 全景融合综合诊断 (Comprehensive)
    # =========================================================================
    def analyze_comprehensive(
        self,
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        raw_financials: Optional[Dict[str, Any]] = None,
        raw_derivative: Optional[Dict[str, Any]] = None,
        raw_benchmark_bars: Optional[List[Dict[str, Any]]] = None,
        market: str = "US",
        as_of_date: Optional[str] = None,
        equity_market_cap: float = 100_000_000_000.0,
    ) -> ComprehensiveAnalysisReport:
        """一键串联行业、物理动力学、五大公式引擎，生成高维买方综合诊断报告."""
        eff_date = as_of_date or (raw_bars[-1].get("date") if raw_bars else "2026-01-01")

        # 1. 行业知识与敏感性
        ind_rep = self.analyze_industry(symbol)

        # 2. 商业物理动力学
        phy_rep = self.analyze_physics(symbol, raw_bars, as_of_date=eff_date, market_cap=equity_market_cap)

        # 3. 法务防舞弊
        fin_dict = raw_financials or {
            "TotalRevenue": 1000.0,
            "CostOfRevenue": 600.0,
            "AccountsReceivableNetCurrent": 200.0,
            "TotalAssets": 2000.0,
            "ShortTermDebt": 100.0,
            "LongTermDebtNoncurrent": 400.0,
            "NetIncomeCommonStockholders": 150.0,
            "OperatingCashFlow": 180.0,
        }
        for_rep = self.analyze_forensics(symbol, fin_dict, as_of_date=eff_date)

        # 4. 信用违约距离
        latest_c = raw_bars[-1].get("close", 100.0) if raw_bars else 100.0
        cre_rep = self.analyze_credit(
            symbol=symbol,
            raw_financials=fin_dict,
            equity_market_cap=equity_market_cap,
            equity_volatility=phy_rep.get("damping_ratio", 0.3) * 0.8,
            as_of_date=eff_date,
        )

        # 5. 微观流动性冲击
        liq_rep = self.analyze_liquidity(symbol, raw_bars, intended_order_value=50000.0, market=market, as_of_date=eff_date)

        # 6. 期权偏度与异动
        deriv_dict = raw_derivative or {
            "call_volume": 10000.0,
            "put_volume": 8000.0,
            "call_open_interest": 80000.0,
            "put_open_interest": 70000.0,
            "iv_25d_put": 0.30,
            "iv_25d_call": 0.28,
            "iv_front_month_atm": 0.29,
            "iv_back_month_atm": 0.29,
        }
        opt_rep = self.analyze_options(symbol, latest_c, deriv_dict, as_of_date=eff_date)

        # 7. 宏观状态机
        reg_rep = self.analyze_macro_regime("SPY", raw_benchmark_bars, as_of_date=eff_date)

        # 综合裁决判定
        verdict = "NEUTRAL"
        if for_rep.get("is_manipulation_suspect") or cre_rep.get("is_black_swan_alert") or liq_rep.get("is_illiquid_trap"):
            verdict = "HARD_REJECT_DISQUALIFIED"
        elif opt_rep.get("is_overnight_crash_alert") or reg_rep.get("regime_state") == "CRISIS_DEFENSE":
            verdict = "DEFENSIVE_HOLD"
        elif phy_rep.get("is_escape_velocity_achieved") and reg_rep.get("regime_state") == "BULL_MOMENTUM":
            verdict = "STRONG_ACCUMULATE_ROCKET"
        else:
            verdict = "SELECTIVE_ACCUMULATE"

        summary = (
            f"【{symbol} 全息金融与行业诊断】所属细分行业：{ind_rep.industry_name_zh}。\n"
            f"- 物理动力学：{phy_rep.get('breakout_power_verdict')}，动能/势能比为 {phy_rep.get('kinetic_to_potential_ratio')}；\n"
            f"- 法务与信用：Beneish M-Score={for_rep.get('m_score')} ({for_rep.get('risk_rating')})，KMV违约距离={cre_rep.get('distance_to_default_DD')}；\n"
            f"- 流动性与期权：建议最大单笔容量=${liq_rep.get('recommended_max_order_size')}，期权偏度={opt_rep.get('skew_25d_risk_reversal')}；\n"
            f"- 宏观状态：当前处于 {reg_rep.get('state_name_zh')}，建议总仓位上限 {int(reg_rep.get('recommended_gross_exposure', 1.0) * 100)}%。\n"
            f"- 终局执行裁决：【{verdict}】。"
        )

        return ComprehensiveAnalysisReport(
            symbol=symbol,
            as_of_date=eff_date,
            market=market.upper(),
            industry_report=ind_rep,
            physics_report=phy_rep,
            forensics_report=for_rep,
            credit_report=cre_rep,
            liquidity_report=liq_rep,
            option_report=opt_rep,
            regime_report=reg_rep,
            executive_summary_zh=summary,
            actionable_verdict=verdict,
        )
