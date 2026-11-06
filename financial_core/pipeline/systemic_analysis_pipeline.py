"""水源股票系统性投研分析主管道 (Systemic Equity Analysis Pipeline).

将时效门禁、三表平账、法证手术刀、宏观压力传导、买方估值集群、
微观筹码博弈、期权因果链以及异动归因有机熔铸为一体的端到端系统级分析中枢。

流水线六大核心工序 (Six Pipeline Stages):
  Stage 1: 前置时钟新鲜度与官方财报平账刚性门禁 (Pre-flight Gatekeepers);
  Stage 2: 法证手术刀证据解剖与真实所有者收益穿透 (Forensic Scalpel & Quality);
  Stage 3: 跨市场宏观冲击与流动性压力加压 (Macro Stress Testing & WACC Adjustment);
  Stage 4: 买方估值算力集群执行 (Constrained DCF / rNPV / Hard Runway);
  Stage 5: 微观筹码博弈与衍生品 Greeks 因果解构 (Microstructure & Options Causal);
  Stage 6: 价格落差归因与买方顶层决策卡片合成 (Price Gap Attribution & Decision Card).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import math

from ..engines.integrated_three_statement_engine import IntegratedThreeStatementEngine, BaselineFinancials
from ..engines.forensic_surgical_scalpel import ForensicSurgicalScalpel, ForensicInputData, ForensicDissectionResult
from ..engines.business_quality_and_moat_engine import BusinessQualityAndMoatEngine, OwnerEarningsInput, LiquorConsumerFleshInput, TechHardwareFleshInput
from ..engines.macro_shock_transmission_engine import MacroShockTransmissionEngine, MacroShockInput
from ..engines.unit_economics_engine import UnitEconomicsEngine, PipelineAsset
from ..engines.consensus_surprise_engine import ConsensusSurpriseEngine, ConsensusDataInput
from ..engines.microstructure_flow_engine import MicrostructureFlowEngine, MicrostructureInput
from ..engines.catalyst_calendar_engine import CatalystCalendarEngine, CorporateEvent
from ..engines.options_causal_analyzer import OptionsCausalAnalyzer, OptionContractInput, UnderlyingScenarios
from ..engines.american_option_tree_engine import AmericanOptionTreeEngine, AmericanOptionTreeInput
from ..engines.price_shock_attribution_engine import (
    PriceShockAttributionEngine,
    GuidanceTerminalImpact,
    OperatingLeverageImpact,
    DilutionOverhangImpact,
    DealerGammaDragImpact,
)
from ..engines.volatility_surface_engine import VolatilitySurfaceGreeksEngine
from ..engines.micro_founded_macro_engine import (
    MicroFoundedMacroEngine,
    MicroFoundedMacroInput,
    MicroFoundedMacroCompositeResult,
)
from ..engines.causal_inference_engine import (
    QuantitativeCausalInferenceEngine,
    CausalInferenceResult,
)


@dataclass
class SystemicCompanyInput:
    """系统性分析输入全景字典 (不可变证据底账)."""
    ticker: str
    company_name: str
    sector: str                       # 例如 "Biotech", "TechHardware", "LiquorConsumer", "General"
    
    # 1. 实时行情与时效凭证
    quote_timestamp: str              # 行情时间戳 (例如 "2026-10-14 15:45:00 EDT")
    market_session: str               # 交易时段 ("regular_trading", "pre_market", "after_hours", "closed")
    current_price: float              # 当前最新价
    baseline_reference_price: float   # 冲击前或前期估值基准价
    
    # 2. 官方财报与附注证据底账 (来自 10-K/Q)
    reported_cash: float
    restricted_cash: float            # 附注中披露的受限保证金
    debt_covenant_min_cash: float     # 借贷协议最低保留资金红线
    total_debt: float
    total_assets: float
    total_liabilities: float
    stockholders_equity: float
    reported_operating_cash_flow: float
    reported_capex: float
    maintenance_capex_ratio: float    # 维持性开支占比 (通常 0.70)
    stock_based_compensation: float   # 股权激励 SBC
    reported_revenue: float
    reported_operating_income: float
    reported_net_income: float
    shares_outstanding: float
    
    # 存货细分 (存货附注)
    raw_materials: float = 0.0
    work_in_process: float = 0.0
    finished_goods: float = 0.0
    prior_finished_goods: float = 0.0
    revenue_growth_pct: float = 0.0
    
    # 研发与客户附注
    total_rd_spent: float = 0.0
    capitalized_rd_amount: float = 0.0
    top_customer_share: float = 0.0
    top_customer_risk_flag: bool = False
    pipeline_rnpv_value: float = 0.0  # 在研管线 rNPV 概率折现总值
    
    # 3. 宏观基准输入
    us_10y_yield: float = 0.044
    usdjpy_rate: float = 152.0
    vix_index: float = 20.0
    usdjpy_daily_change_pct: float = 0.0
    fed_liquidity_drain_billion: float = 50.0
    company_beta: float = 1.2
    
    # 4. 行业特异性微观变量 (白酒/芯片)
    factory_quote: float = 0.0        # 出厂价
    real_wholesale_quote: float = 0.0 # 场外批发价
    contract_liabilities_drain_pct: float = 0.0
    current_dio_days: float = 0.0
    prior_dio_days: float = 0.0
    
    # 5. 微观筹码与衍生品
    short_interest_shares: float = 0.0
    free_float_shares: float = 1.0
    cost_to_borrow_pct: float = 2.0
    average_volume_30d: float = 1.0
    option_target_strike: float = 0.0
    option_expiry_days: int = 30
    option_implied_vol: float = 0.40
    is_call_option: bool = True


@dataclass
class SystemicDecisionCard:
    """最终输出的顶层买方独立投资决策卡片."""
    ticker: str
    company_name: str
    recommendation_tier: str          # 核心评级: STRONG_BUY / ACCUMULATE / NEUTRAL_HOLD / HIGH_RISK_AVOID
    fair_value_anchor: float          # 法证调整后内生公允价值锚点
    current_price: float              # 当前市价
    margin_of_safety_pct: float       # 安全边际百分比
    pessimistic_floor_price: float    # 悲观底价防线
    pessimistic_trigger: str          # 导致跌破底价的具体触发事件
    optimistic_target_price: float    # 乐观靶心价格
    optimistic_trigger: str           # 达成乐观靶心的具体催化路径
    hard_runway_months: float         # 硬现金跑道寿命 (月)
    earnings_quality_grade: str       # 财报品质评级
    forensic_red_flags: List[str]     # 手术刀切出的致命红旗清单
    options_verdict: str              # 期权专项研判 (防虚值陷阱)
    price_gap_attribution_summary: str # 价格落差的主要驱动力分账总结
    hard_runway_desc: str = ""        # 跑道定性描述 (持续净流入 / 破红线)
    wicksellian_gap_bps: Optional[float] = None # 维克塞尔自然利率缺口基点
    dynamic_wacc_t1: Optional[float] = None  # 伍德福德前瞻首期 WACC %
    pricing_power_tier: Optional[str] = None # 霍尔微观定价权评级
    distance_to_frontier: Optional[float] = None # 阿吉翁技术前沿距离 DTF
    institutional_quality_score: Optional[float] = None # 阿西莫格鲁制度质量指数 IQI
    micro_founded_macro_verdict: str = ""    # 诺奖微观基础宏观全景评级
    primary_catalysts: List[str] = field(default_factory=list) # 核心催化事实清单 (通俗商业投资大白话)
    key_risks: List[str] = field(default_factory=list)         # 核心破位事实清单 (通俗商业投资大白话)


class SystemicAnalysisPipeline:
    """系统性投研分析主管道总装中枢."""

    def __init__(self):
        self.version = "1.5.0"
        self.scalpel = ForensicSurgicalScalpel()
        self.quality_engine = BusinessQualityAndMoatEngine()
        self.macro_engine = MacroShockTransmissionEngine()
        self.micro_macro_engine = MicroFoundedMacroEngine()
        self.causal_engine = QuantitativeCausalInferenceEngine()
        self.runway_engine = IntegratedThreeStatementEngine()
        self.microstructure_engine = MicrostructureFlowEngine()
        self.american_tree_engine = AmericanOptionTreeEngine()
        self.price_shock_engine = PriceShockAttributionEngine()
        self.volatility_engine = VolatilitySurfaceGreeksEngine()

    def run_systemic_analysis(self, inp: SystemicCompanyInput) -> Dict[str, Any]:
        """运行全套六道工序端到端全景解剖."""
        
        # ================= STAGE 1: 前置时效与平账门禁 =================
        # 1.1 资产负债表平账核验与输入合法性校验 (Task 07 刚性门禁)
        rejection_reasons = []
        if inp.shares_outstanding <= 0:
            rejection_reasons.append(f"非法流通股本数量 ({inp.shares_outstanding})，必须为正数")
        if math.isnan(inp.current_price) or inp.current_price <= 0:
            rejection_reasons.append(f"标的现价非法或非正数 ({inp.current_price})")
        if math.isnan(inp.total_assets) or inp.total_assets <= 0:
            rejection_reasons.append(f"总资产非法或非正数 ({inp.total_assets})")

        bs_discrepancy = abs(inp.total_assets - (inp.total_liabilities + inp.stockholders_equity))
        bs_tolerance = max(1.0, inp.total_assets * 0.01)  # 允许 1% 舍入微差或最小 1.0 单位
        if bs_discrepancy > bs_tolerance:
            rejection_reasons.append(
                f"资产负债表严重失衡: 总资产 ({inp.total_assets:,.0f}) 与 "
                f"[负债 ({inp.total_liabilities:,.0f}) + 股东权益 ({inp.stockholders_equity:,.0f})] "
                f"相差 {bs_discrepancy:,.0f}，超出容差 {bs_tolerance:,.0f}"
            )

        is_market_open = inp.market_session in ["regular_trading", "pre_market", "after_hours"]
        gatekeeper_report = {
            "quote_timestamp": inp.quote_timestamp,
            "market_session": inp.market_session,
            "is_fresh_quote": is_market_open,
            "session_warning": "正常交易时段现价" if is_market_open else "【前一交易日收盘基准，已阻断盘中假数据】",
            "passed": len(rejection_reasons) == 0,
            "rejection_reasons": rejection_reasons,
        }

        # 触发硬阻断：严禁在资产负债表不平账或非法输入下继续执行估值
        if len(rejection_reasons) > 0:
            return {
                "ticker": inp.ticker,
                "pipeline_version": self.version,
                "pipeline_status": "BLOCKED",
                "block_reason": "；".join(rejection_reasons),
                "stage_1_gatekeepers": gatekeeper_report,
                "stage_2_forensic_scalpel": None,
                "stage_3_macro_stress": None,
                "stage_4_valuation": None,
                "stage_5_microstructure_and_options": None,
                "stage_6_price_gap_attribution": None,
                "final_institutional_decision_card": None,
            }

        # ================= STAGE 2: 法证手术刀证据解剖 =================
        forensic_data = ForensicInputData(
            ticker=inp.ticker,
            company_name=inp.company_name,
            reported_cash_and_equivalents=inp.reported_cash,
            restricted_cash_in_notes=inp.restricted_cash,
            debt_covenant_minimum_cash=inp.debt_covenant_min_cash,
            raw_materials=inp.raw_materials,
            work_in_process=inp.work_in_process,
            finished_goods=inp.finished_goods,
            prior_finished_goods=inp.prior_finished_goods,
            revenue_growth_pct=inp.revenue_growth_pct,
            total_rd_spent=inp.total_rd_spent,
            capitalized_rd_amount=inp.capitalized_rd_amount,
            reported_operating_income=inp.reported_operating_income,
            reported_net_income=inp.reported_net_income,
            top_customer_share=inp.top_customer_share,
            top_3_customers_share=inp.top_customer_share * 1.5,
            top_customer_risk_flag=inp.top_customer_risk_flag,
            factory_quote=inp.factory_quote,
            real_market_wholesale_quote=inp.real_wholesale_quote,
            channel_contract_liabilities_drain_pct=inp.contract_liabilities_drain_pct,
        )
        scalpel_result = self.scalpel.dissect(forensic_data)

        # 2.2 巴菲特所有者收益穿透
        owner_earnings_input = OwnerEarningsInput(
            reported_net_income=inp.reported_net_income,
            depreciation_amortization=inp.reported_capex * 0.8,
            total_capex=inp.reported_capex,
            maintenance_capex_ratio=inp.maintenance_capex_ratio,
            stock_based_compensation=inp.stock_based_compensation,
            working_capital_change=0.0,
            shares_outstanding=inp.shares_outstanding,
        )
        owner_earnings_res = self.quality_engine.compute_owner_earnings(owner_earnings_input)

        # ================= STAGE 3: 跨市场宏观冲击加压 =================
        debt_to_equity = inp.total_debt / max(1.0, inp.stockholders_equity)
        macro_input = MacroShockInput(
            us_10y_yield=inp.us_10y_yield,
            usdjpy_rate=inp.usdjpy_rate,
            vix_index=inp.vix_index,
            usdjpy_daily_change_pct=inp.usdjpy_daily_change_pct,
            fed_liquidity_drain_billion=inp.fed_liquidity_drain_billion,
            company_beta=inp.company_beta,
            company_debt_to_equity=debt_to_equity,
            base_wacc=0.09,
        )
        macro_shock_res = self.macro_engine.evaluate_macro_shock(macro_input)
        shocked_wacc = macro_shock_res["shocked_wacc_pct"] / 100.0

        # 3.2 诺奖微观基础宏观综合评估 (Woodford / Hall / Acemoglu / Aghion)
        ticker_str = inp.ticker.strip().upper()
        if (ticker_str.isdigit() and len(ticker_str) == 4) or ticker_str.startswith("TYO:") or ticker_str.endswith(".T"):
            domicile = "JP"
            rule_of_law = 88.0
        elif (ticker_str.isdigit() and len(ticker_str) == 6) or ticker_str.startswith("SH:") or ticker_str.startswith("SZ:"):
            domicile = "CN"
            rule_of_law = 75.0
        else:
            domicile = "US"
            rule_of_law = 86.0

        micro_macro_input = MicroFoundedMacroInput(
            ticker=inp.ticker,
            country_domicile=domicile,
            sector=inp.sector,
            policy_rate=inp.us_10y_yield,
            expected_inflation_1y=0.025,
            natural_rate_r_star=0.0125,
            equity_beta=inp.company_beta,
            credit_spread=0.0180,
            reported_revenue=inp.reported_revenue,
            reported_cogs=max(1.0, inp.reported_revenue - inp.reported_operating_income),
            reported_gross_margin_pct=max(5.0, min(95.0, (inp.reported_operating_income / max(1.0, inp.reported_revenue) + 0.30) * 100.0)),
            reported_capex=inp.reported_capex,
            cash_and_equivalents=inp.reported_cash,
            total_debt=inp.total_debt,
            annual_fcf=inp.reported_operating_cash_flow - inp.reported_capex,
            macro_vix=inp.vix_index,
            pricing_pass_through_elasticity=0.85 if inp.sector in ["LiquorConsumer", "TechHardware"] else 0.65,
            rule_of_law_score=rule_of_law,
            rd_expenses=inp.total_rd_spent,
            patent_portfolio_quality_score=80.0 if inp.sector in ["TechHardware", "Biotech"] else 60.0,
            sensitive_technology_sector=(inp.sector in ["TechHardware", "Biotech"]),
        )
        micro_macro_res = self.micro_macro_engine.evaluate(micro_macro_input)

        # 融合伍德福德动态 WACC 首期折现率
        endogenous_wacc = max(shocked_wacc, micro_macro_res.effective_initial_wacc_pct / 100.0)
        aghion_g_adj = micro_macro_res.terminal_growth_rate_adj_bps / 10000.0

        # ================= STAGE 4: 买方估值算力集群 =================
        # 4.1 动态硬现金跑道 (Task 12 严格修正：区分真实造血与持续净烧钱)
        real_liquid_pool = scalpel_result.unrestricted_liquid_cash - inp.total_debt
        net_annual_fcf = inp.reported_operating_cash_flow - inp.reported_capex

        if net_annual_fcf >= 0:
            hard_runway = -1.0  # 哨兵标记: 持续净流入
            hard_runway_desc = "持续净现金流入 (营运造血完全覆盖资本开支，无需消耗资金储备)"
        else:
            monthly_burn = abs(net_annual_fcf) / 12.0
            if real_liquid_pool <= 0:
                hard_runway = 0.0
                hard_runway_desc = "偿债红线已破 (受限后可动用资金净额为负)"
            else:
                hard_runway = max(0.0, real_liquid_pool) / max(0.01, monthly_burn)
                hard_runway_desc = f"{hard_runway:.1f} 个月"

        # 4.2 基准公允价值内生锚点与真实多情景测算 (Task 10 杜绝虚假固定倍率)
        true_fcf = inp.reported_operating_cash_flow - inp.reported_capex - inp.stock_based_compensation
        combined_haircut = min(50.0, scalpel_result.final_equity_value_haircut_pct + micro_macro_res.governance_terminal_haircut_pct * 0.15)
        haircut_multiplier = (1.0 - combined_haircut / 100.0)

        # 检查是否为负净资产/资不抵债架构 (如 BA, SBUX, MCD 巨额回购后权益为负)
        is_negative_equity = (inp.stockholders_equity <= 0)

        if true_fcf > 0:
            # 持续造血型企业: 三情景严格按明确的 (WACC, g) 真实复算，实施分母除零/除负硬保护
            # 悲观情景: 高通胀紧缩 WACC 飙升至 endogenous_wacc + 2%, 永续增长率仅 1%
            pess_wacc = max(0.08, endogenous_wacc + 0.02)
            pess_g = max(0.005, min(0.02, 0.01 + min(0.0, aghion_g_adj)))
            pess_denom = max(0.01, pess_wacc - pess_g)
            pess_ev = ((true_fcf * (1.0 + pess_g)) / pess_denom) + real_liquid_pool
            pessimistic_floor = round(max(0.1, (pess_ev / max(1.0, inp.shares_outstanding)) * haircut_multiplier), 2)

            # 中性基准情景: endogenous_wacc, 永续增长率 2.5% + 阿吉翁调整
            neut_wacc = max(0.07, endogenous_wacc)
            neut_g = max(0.01, min(0.040, 0.025 + aghion_g_adj))
            neut_denom = max(0.015, neut_wacc - neut_g)
            neut_ev = ((true_fcf * (1.0 + neut_g)) / neut_denom) + real_liquid_pool
            raw_fair_price = neut_ev / max(1.0, inp.shares_outstanding)
            fair_value_anchor = round(max(0.2, raw_fair_price * haircut_multiplier), 2)

            # 乐观靶行情景: 宏观降息 WACC 下修至 7.5%, 永续增长率 3.5%
            opt_wacc = max(0.065, endogenous_wacc - 0.015)
            opt_g = max(0.02, min(0.050, 0.035 + max(0.0, aghion_g_adj)))
            opt_denom = max(0.02, opt_wacc - opt_g)
            opt_ev = ((true_fcf * (1.0 + opt_g)) / opt_denom) + real_liquid_pool
            optimistic_target = round(max(fair_value_anchor * 1.05, (opt_ev / max(1.0, inp.shares_outstanding)) * haircut_multiplier), 2)

            if is_negative_equity:
                valuation_model_name = "DCF_FCF_Discount_Buyback_Negative_Equity"
            else:
                valuation_model_name = "DCF_FCF_Discount"
        else:
            # 亏损在研型企业: 悲观为清算净现金底，中性为净现金+核心营收+rNPV，乐观为管线获批预期
            pipeline_val = getattr(inp, "pipeline_rnpv_value", 0.0)
            pessimistic_floor = round(max(0.2, (real_liquid_pool / max(1.0, inp.shares_outstanding)) * haircut_multiplier), 2)
            raw_fair_price = (real_liquid_pool + inp.reported_revenue * 1.2 + pipeline_val) / max(1.0, inp.shares_outstanding)
            fair_value_anchor = round(max(0.5, raw_fair_price * haircut_multiplier), 2)
            optimistic_target = round(max(fair_value_anchor * 1.1, (real_liquid_pool + inp.reported_revenue * 2.5 + pipeline_val * 1.5) / max(1.0, inp.shares_outstanding) * haircut_multiplier), 2)
            valuation_model_name = "rNPV_and_Net_Cash_Liquidation"

        # 强制单调估值走廊约束: 悲观底 <= 0.90 * 公允锚点 < 公允锚点 < 1.10 * 公允锚点 <= 乐观靶心
        pessimistic_floor = round(min(fair_value_anchor * 0.90, pessimistic_floor), 2)
        optimistic_target = round(max(fair_value_anchor * 1.10, optimistic_target), 2)

        # ================= STAGE 5: 微观筹码博弈与美式期权 =================
        micro_input = MicrostructureInput(
            ticker=inp.ticker,
            current_price=inp.current_price,
            float_shares=inp.free_float_shares / 1e6,
            short_interest_shares=inp.short_interest_shares / 1e6,
            average_daily_volume_30d=inp.average_volume_30d / 1e6,
            cost_to_borrow_pct=inp.cost_to_borrow_pct,
        )
        micro_res = self.microstructure_engine.evaluate(micro_input)

        # 衍生品美式期权二叉树敏感度与解析希腊字母
        if inp.option_target_strike > 0:
            tree_input = AmericanOptionTreeInput(
                spot_price=inp.current_price,
                strike_price=inp.option_target_strike,
                time_to_expiry_years=inp.option_expiry_days / 365.0,
                risk_free_rate=inp.us_10y_yield,
                implied_vol=inp.option_implied_vol,
                is_call=inp.is_call_option,
                steps=100,
            )
            tree_res = self.american_tree_engine.price_crr_tree(tree_input)
            
            # 使用解析全阶希腊字母引擎计算真实 Theta 时间衰减与 Delta 风险敞口
            greeks = self.volatility_engine.calculate_option_greeks(
                spot=inp.current_price,
                strike=inp.option_target_strike,
                time_to_expiry_years=max(1e-4, inp.option_expiry_days / 365.0),
                risk_free_rate=inp.us_10y_yield,
                dividend_yield=0.0,
                volatility=inp.option_implied_vol,
                option_type="call" if inp.is_call_option else "put",
            )
            theta_daily_pct = abs(greeks.theta_daily) / max(0.01, greeks.theoretical_price) * 100.0
            options_verdict = (
                f"行权价 {inp.option_target_strike} 美式期权理论公允价 ${tree_res['american_price']:.3f} "
                f"(含提前行权溢价 +${tree_res['early_exercise_premium']:.3f}, Delta: {greeks.delta:+.3f})。"
                f"每日时间损耗 (解析解 Theta) 达 -${abs(greeks.theta_daily):.3f} ({theta_daily_pct:.1f}%/日)，"
                f"若未来半程横盘将亏损超 50%，严禁单边买入虚值赌徒策略。"
            )
        else:
            options_verdict = "未选定特定期权合约，现货主导策略。"

        # ================= STAGE 6: 价格落差归因与决策卡片 =================
        price_gap = inp.current_price - inp.baseline_reference_price
        guidance_impact = GuidanceTerminalImpact(
            previous_guidance_growth=0.20,
            revised_guidance_growth=0.15,
            wacc=shocked_wacc,
            terminal_growth=0.02,
            base_share_price=inp.baseline_reference_price,
            terminal_value_weight=0.70,
        )
        attribution_res = self.price_shock_engine.attribute_shock(
            base_price=inp.baseline_reference_price,
            actual_price=inp.current_price,
            guidance=guidance_impact,
        )

        # 计算安全边际
        margin_of_safety = ((fair_value_anchor - inp.current_price) / max(0.01, inp.current_price)) * 100.0
        
        # 评级判定 (Task 13: 程序仅反映量化客观信号，最终决策交给 AI 投研日记归纳)
        if len(scalpel_result.forensic_red_flags) > 0:
            rec_tier = "FORENSIC_ALERT_ACTIVE"
        elif hard_runway >= 0 and hard_runway < 12.0:
            rec_tier = "RUNWAY_DEFICIT_WARNING"
        elif margin_of_safety > 25.0:
            rec_tier = "DISCOUNT_BUFFER_OBSERVED"
        elif margin_of_safety < -25.0:
            rec_tier = "PREMIUM_OVERVALUED"
        else:
            rec_tier = "BALANCED_FAIR_OBSERVATION"

        # 映射宏观压力传导的股票价值冲击
        macro_shock_res["equity_shock_pct"] = -macro_shock_res["valuation_haircut_pct"]

        # Stage 6 核心: 量化因果推导网络 (彻底取代单一硬编码模板，输出买方商业事实)
        causal_res = self.causal_engine.infer_catalysts_and_risks(
            company_info={
                "ticker": inp.ticker,
                "company_name": inp.company_name,
                "sector": inp.sector,
                "current_price": inp.current_price,
                "factory_quote": inp.factory_quote,
                "real_wholesale_quote": inp.real_wholesale_quote,
                "contract_liabilities_drain_pct": inp.contract_liabilities_drain_pct,
                "current_dio_days": inp.current_dio_days,
                "cost_to_borrow_pct": inp.cost_to_borrow_pct,
                "debt_covenant_min_cash": inp.debt_covenant_min_cash,
                "top_customer_share": inp.top_customer_share,
                "top_customer_risk_flag": inp.top_customer_risk_flag,
            },
            forensic_result={
                "unrestricted_cash": scalpel_result.unrestricted_liquid_cash,
                "inventory_verdict": scalpel_result.inventory_toxicity_verdict,
                "red_flags": scalpel_result.forensic_red_flags,
            },
            macro_shock_result=macro_shock_res,
            valuation_result={
                "hard_runway_months": hard_runway,
                "hard_runway_desc": hard_runway_desc,
                "margin_of_safety_pct": margin_of_safety,
                "fair_value_anchor": fair_value_anchor,
            },
            microstructure_result={
                "squeeze_score": micro_res.squeeze_score,
                "short_percent_of_float": micro_res.short_percent_of_float,
            },
            micro_founded_macro_result={
                "pricing_power_tier": micro_macro_res.hall_result.pricing_power_tier,
                "micro_markup_ratio": micro_macro_res.hall_result.micro_markup_ratio,
                "distance_to_technology_frontier": micro_macro_res.aghion_result.distance_to_technology_frontier,
            },
            attribution_result={
                "gamma_drag_impact": getattr(attribution_res, "dealer_gamma_drag_impact", 0.0) if hasattr(attribution_res, "dealer_gamma_drag_impact") else (attribution_res.get("dealer_gamma_drag_impact", 0.0) if isinstance(attribution_res, dict) else 0.0),
            },
        )

        decision_card = SystemicDecisionCard(
            ticker=inp.ticker,
            company_name=inp.company_name,
            recommendation_tier=rec_tier,
            fair_value_anchor=round(fair_value_anchor, 2),
            current_price=round(inp.current_price, 2),
            margin_of_safety_pct=round(margin_of_safety, 2),
            pessimistic_floor_price=pessimistic_floor,
            pessimistic_trigger=causal_res.top_pessimistic_trigger,
            optimistic_target_price=optimistic_target,
            optimistic_trigger=causal_res.top_optimistic_trigger,
            hard_runway_months=round(hard_runway, 1) if hard_runway >= 0 else 0.0,
            earnings_quality_grade=owner_earnings_res["earnings_quality_verdict"],
            forensic_red_flags=scalpel_result.forensic_red_flags,
            options_verdict=options_verdict,
            price_gap_attribution_summary=f"基准价与现价落差 ${price_gap:.2f}，已解释其中 {attribution_res['explained_ratio_pct']}%，主要由前瞻指引下修与宏观加压驱动。",
            hard_runway_desc=hard_runway_desc,
            wicksellian_gap_bps=micro_macro_res.woodford_result.wicksellian_rate_gap_bps,
            dynamic_wacc_t1=micro_macro_res.effective_initial_wacc_pct,
            pricing_power_tier=micro_macro_res.hall_result.pricing_power_tier,
            distance_to_frontier=micro_macro_res.aghion_result.distance_to_technology_frontier,
            institutional_quality_score=micro_macro_res.acemoglu_result.institutional_quality_index,
            micro_founded_macro_verdict=micro_macro_res.integrated_macro_verdict,
            primary_catalysts=causal_res.primary_catalysts,
            key_risks=causal_res.key_risks,
        )

        return {
            "ticker": inp.ticker,
            "pipeline_version": self.version,
            "pipeline_status": "SUCCESS",
            "stage_1_gatekeepers": gatekeeper_report,
            "stage_2_forensic_scalpel": {
                "unrestricted_cash": scalpel_result.unrestricted_liquid_cash,
                "covenant_buffer": scalpel_result.covenant_safety_buffer,
                "inventory_verdict": scalpel_result.inventory_toxicity_verdict,
                "true_operating_income": scalpel_result.true_operating_income,
                "final_equity_haircut_pct": scalpel_result.final_equity_value_haircut_pct,
                "red_flags": scalpel_result.forensic_red_flags,
            },
            "stage_3_macro_stress": {
                **macro_shock_res,
                "micro_founded_macro": {
                    "wicksellian_rate_gap_bps": micro_macro_res.woodford_result.wicksellian_rate_gap_bps,
                    "is_monetary_restrictive": micro_macro_res.woodford_result.is_monetary_restrictive,
                    "dynamic_wacc_vector": micro_macro_res.dynamic_wacc_vector,
                    "effective_initial_wacc_pct": micro_macro_res.effective_initial_wacc_pct,
                    "micro_markup_ratio": micro_macro_res.hall_result.micro_markup_ratio,
                    "pricing_power_tier": micro_macro_res.hall_result.pricing_power_tier,
                    "shocked_gross_margin_pct": micro_macro_res.shocked_gross_margin_pct,
                    "precautionary_capex_curtailment_pct": micro_macro_res.hall_result.precautionary_capex_curtailment_pct,
                    "institutional_quality_index": micro_macro_res.acemoglu_result.institutional_quality_index,
                    "institution_type": micro_macro_res.acemoglu_result.institution_type,
                    "institutional_risk_spread_bps": micro_macro_res.acemoglu_result.institutional_risk_spread_bps,
                    "distance_to_technology_frontier": micro_macro_res.aghion_result.distance_to_technology_frontier,
                    "schumpeterian_survival_status": micro_macro_res.aghion_result.schumpeterian_survival_status,
                    "terminal_growth_rate_adj_bps": micro_macro_res.terminal_growth_rate_adj_bps,
                    "governance_terminal_haircut_pct": micro_macro_res.governance_terminal_haircut_pct,
                    "integrated_macro_verdict": micro_macro_res.integrated_macro_verdict,
                },
            },
            "stage_4_valuation": {
                "raw_fair_price": round(raw_fair_price, 2),
                "forensic_adjusted_fair_price": round(fair_value_anchor, 2),
                "hard_runway_months": round(hard_runway, 1) if hard_runway >= 0 else None,
                "hard_runway_desc": hard_runway_desc,
                "pessimistic_floor": pessimistic_floor,
                "optimistic_target": optimistic_target,
                "valuation_model_used": valuation_model_name,
                "owner_earnings_summary": owner_earnings_res,
            },
            "stage_5_microstructure_and_options": {
                "squeeze_score": micro_res.squeeze_score,
                "squeeze_risk": micro_res.squeeze_risk_level,
                "options_verdict": options_verdict,
            },
            "stage_6_price_gap_attribution": attribution_res,
            "final_institutional_decision_card": decision_card.__dict__,
        }
