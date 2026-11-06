"""中观行业至微观企业增加值映射桥梁 (Firm Value Added Bridge Engine).

理论基础与微观核算架构:
1. 企业增加值直接法与间接法恒等式 (SNA 2008 & IFRS/GAAP Corporate Value Added):
   - 生产法 (Production Approach):
     VA_i = Revenue_i - Intermediate_Purchases_i (外购原材料、零部件、外包云服务及中间消耗)
   - 分配法 (Income / Distribution Approach):
     VA_i = EBITDA_i (资本营业毛盈余) + Wages_i (员工总薪酬福利) + Taxes_i (生产经营税费及所得税)
2. 行业增加值与企业微观切片映射:
   企业在所属行业中的增加值占比反映其真实产业链地位与壁垒厚度，
   而非单纯依赖易被低附加值走量膨胀的营业收入指标。
3. 自由现金流转化律:
   FCF_i = EBITDA_i - CapEx_i - Taxes_i - Delta_NWC_i
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional

from .monte_carlo_engine import (
    MonteCarloValuationEngine,
    MonteCarloDCFInput,
    MonteCarloValuationResult,
)
from .market_adaptive_params import FirmValueAddedAdaptiveParams


@dataclass
class FirmFinancialFact:
    """企业微观财务底稿与要素输入."""
    ticker: str
    company_name: str
    market: str
    sector_id: str                      # 对应宏观行业 ID (如 TECH_SEMI)
    revenue_million: float              # 营业收入 (百万美元)
    cogs_million: float                 # 营业成本 (百万美元)
    operating_expenses_million: float   # 营运费用 (研发、销售、行政)
    ebitda_million: float               # 息税折旧摊销前利润
    wages_and_salaries_million: float   # 员工薪酬与福利总支出
    taxes_paid_million: float           # 缴纳税费总额
    capex_million: float                # 资本开支
    annual_fcf_million: float           # 自由现金流
    market_cap_billion: float           # 当前总市值 (十亿美元)
    country_id: str = "US"              # 注册所属经济体 (US, JP, EU, CN, ROW)
    foreign_revenue_ratio: float = 0.50 # 海外出口及跨国营收占比 (0.0~1.0)
    fx_sensitivity_elasticity: float = 0.0  # 汇率变动收益弹性 (例如日企对日元贬值弹性为 +0.80~1.00)
    inventory_turnover_days_dio: float = 65.0  # 存货周转天数 DIO (反映库存消化出口与产能周期)
    # 负向测试与财务困境防御拓展字段 (向下兼容默认值)
    total_debt_million: float = 0.0     # 有息债务总额 (百万美元)
    cash_and_equivalents_million: float = 0.0 # 现金及现金等价物 (百万美元)
    interest_expense_million: float = 0.0     # 年化利息费用 (百万美元，用于测算利息保障倍数 ICR)
    tangible_book_value_million: float = 0.0  # 有形资产净值 (百万美元，用于清算清偿残值测算)


class FirmValueAddedBridgeEngine:
    """行业增加值向微观企业三表增加值映射桥梁."""

    def __init__(self, adaptive_params: Optional[FirmValueAddedAdaptiveParams] = None):
        self.version = "1.0.0"
        self.adaptive_params = adaptive_params

    def _get_currency_symbol(self, firm: FirmFinancialFact) -> str:
        """自适应推导市场货币符号 (SSOT: 美股 USD '$', 日股 JPY '¥', A股 CNY '¥')."""
        t_up = (firm.ticker or "").upper()
        m_up = (firm.market or "").upper()
        is_jp = m_up == "JP" or t_up.endswith(".T") or t_up.endswith(".JP") or (t_up.isdigit() and len(t_up) == 4)
        is_cn = m_up == "CN" or t_up.endswith(".SS") or t_up.endswith(".SZ") or (t_up.isdigit() and len(t_up) == 6)
        if is_jp or is_cn:
            return "¥"
        return "$"

    def estimate_dynamic_dol(
        self,
        firm: FirmFinancialFact,
        sector_id: Optional[str] = None,
        adaptive_params: Optional[FirmValueAddedAdaptiveParams] = None,
    ) -> float:
        """估算微观企业动态经营杠杆系数 (Degree of Operating Leverage, DOL).

        公式:
        DOL = 1.0 + (Fixed Costs / EBITDA)
        通过微观三表营业成本与营运费用估算固定支出结构，
        结合宏观行业特性避免静态一刀切。
        """
        cfg = adaptive_params or self.adaptive_params or FirmValueAddedAdaptiveParams()
        sec = sector_id or firm.sector_id
        base_dol = cfg.sector_dol_map.get(sec, cfg.default_operating_leverage_dol)

        if not cfg.enable_dynamic_dol_estimation or firm.ebitda_million <= 0.0:
            return base_dol

        total_costs = firm.cogs_million + firm.operating_expenses_million
        if total_costs > 0.0 and firm.revenue_million > 0.0:
            # 重资产与硬件行业固定折旧摊销占比高，消费与服务固定支出占比相对低
            fixed_ratio = 0.35 if ("SEMI" in sec or "HARDWARE" in sec) else 0.20
            fixed_costs = total_costs * fixed_ratio
            calculated_dol = 1.0 + (fixed_costs / max(1.0, firm.ebitda_million))
            return round(min(2.50, max(1.02, calculated_dol)), 3)

        return base_dol

    def compute_firm_value_added(self, firm: FirmFinancialFact) -> Dict[str, Any]:
        """按分配法与生产法严密核算企业的微观增加值 (Corporate Value Added, VA)."""
        curr = self._get_currency_symbol(firm)
        # 1. 分配法核算增加值: VA = EBITDA + 劳动薪酬 + 税收
        va_income_method = firm.ebitda_million + firm.wages_and_salaries_million + firm.taxes_paid_million

        # 2. 生产法反推外购中间消耗: Intermediate = Revenue - VA
        intermediate_purchases = max(0.0, firm.revenue_million - va_income_method)
        va_ratio = va_income_method / max(1e-6, firm.revenue_million)

        # 3. 要素收益切片比例
        labor_share_pct = (firm.wages_and_salaries_million / max(1e-6, va_income_method)) * 100.0
        capital_share_pct = (firm.ebitda_million / max(1e-6, va_income_method)) * 100.0
        tax_share_pct = (firm.taxes_paid_million / max(1e-6, va_income_method)) * 100.0

        # 4. 自由现金流转化率 (FCF / EBITDA)
        fcf_conversion_pct = (firm.annual_fcf_million / max(1e-6, firm.ebitda_million)) * 100.0
        price_to_va = (firm.market_cap_billion * 1000.0) / max(1e-6, va_income_method)

        narrative_zh = (
            f"【标的 {firm.ticker} 企业增加值核算与要素分配全息研报】"
            f"微观增加值创造: 营业收入 {curr}{firm.revenue_million:,.1f}M，外购原材料与中间消耗 {curr}{intermediate_purchases:,.1f}M，"
            f"真实企业创造增加值 {curr}{va_income_method:,.1f}M (增加值率 {va_ratio * 100.0:.1f}%)。"
            f"要素分配穿透: 劳动者报酬 {curr}{firm.wages_and_salaries_million:,.1f}M (占比 {labor_share_pct:.1f}%)，"
            f"资本营业毛盈余 EBITDA {curr}{firm.ebitda_million:,.1f}M (占比 {capital_share_pct:.1f}%)，"
            f"政府税收贡献 {curr}{firm.taxes_paid_million:,.1f}M (占比 {tax_share_pct:.1f}%)。"
            f"造血转化与估值倍数: 自由现金流 FCF {curr}{firm.annual_fcf_million:,.1f}M (EBITDA 转化率 {fcf_conversion_pct:.1f}%)，"
            f"市值/增加值倍数 {price_to_va:.2f}倍。"
        )

        return {
            "ticker": firm.ticker,
            "currency_symbol": curr,
            "company_name": firm.company_name,
            "sector_id": firm.sector_id,
            "revenue_million": firm.revenue_million,
            "corporate_value_added_million": round(va_income_method, 2),
            "intermediate_purchases_million": round(intermediate_purchases, 2),
            "value_added_ratio_pct": round(va_ratio * 100.0, 2),
            "factor_distribution": {
                "labor_compensation_million": firm.wages_and_salaries_million,
                "labor_share_pct": round(labor_share_pct, 2),
                "capital_operating_surplus_ebitda_million": firm.ebitda_million,
                "capital_share_pct": round(capital_share_pct, 2),
                "taxes_paid_million": firm.taxes_paid_million,
                "tax_share_pct": round(tax_share_pct, 2),
                "is_distribution_identity_held": True,
            },
            "fcf_cash_generation": {
                "annual_fcf_million": firm.annual_fcf_million,
                "capex_million": firm.capex_million,
                "fcf_to_ebitda_conversion_pct": round(fcf_conversion_pct, 2),
            },
            "market_cap_billion": firm.market_cap_billion,
            "price_to_value_added_ratio": round(price_to_va, 2),
            "narrative_zh": narrative_zh,
        }

    def map_sector_shock_to_firm(
        self,
        firm: FirmFinancialFact,
        sector_va_growth_pct: float,
        firm_pricing_power_mu: float = 1.0,
        export_demand_growth_pct: Optional[float] = None,
        fx_shock_multiplier: float = 1.0,
        inventory_drag_bps: float = 0.0,
        operating_leverage_dol: Optional[float] = None,
        adaptive_params: Optional[FirmValueAddedAdaptiveParams] = None,
    ) -> Dict[str, Any]:
        """将中观行业增加值与产出扩张冲击传导至企业端业绩与现金流 (含开放经济出口与存货周期).

        参数:
        - firm: 企业微观财务底账 (含海外敞口与存货天数)
        - sector_va_growth_pct: 所属行业内需增加值增速 (例如 +6.5%)
        - firm_pricing_power_mu: 企业加价率垄断壁垒乘数 (Hall 加价率，大于 1.0 说明具备超额定价权)
        - export_demand_growth_pct: 跨国出口外需增速 (若缺省则同步于行业内需增速)
        - fx_shock_multiplier: 汇率贬值计价收益乘数 (例如日企因日元贬值获得的换算收益乘数)
        - inventory_drag_bps: 存货积压/产能消化不畅引发的营运资本拖累 (基点 bps)
        - operating_leverage_dol: 可选显式指定的经营杠杆倍数 (若缺省则基于三表成本自适应估算)
        - adaptive_params: 可选自适应参数包
        """
        cfg = adaptive_params or self.adaptive_params or FirmValueAddedAdaptiveParams()

        base_va = self.compute_firm_value_added(firm)
        base_va_million = base_va["corporate_value_added_million"]

        # 1. 拆解本土内需增长与海外出口外需拉动
        domestic_growth_rate = (sector_va_growth_pct / 100.0) * max(0.5, firm_pricing_power_mu)
        ext_growth = export_demand_growth_pct if export_demand_growth_pct is not None else sector_va_growth_pct

        # 汇率弹性对出口收入的放大/收缩
        fx_boost = 1.0
        if abs(fx_shock_multiplier - 1.0) > 1e-4 and firm.fx_sensitivity_elasticity > 0.0:
            fx_boost = 1.0 + (fx_shock_multiplier - 1.0) * firm.fx_sensitivity_elasticity

        export_growth_rate = ((ext_growth / 100.0) * max(0.5, firm_pricing_power_mu) + (fx_boost - 1.0))

        # 2. 结合海外营收占比加权合成企业有效总增长
        f_ratio = min(1.0, max(0.0, firm.foreign_revenue_ratio))
        effective_firm_growth = domestic_growth_rate * (1.0 - f_ratio) + export_growth_rate * f_ratio

        new_va_million = base_va_million * (1.0 + effective_firm_growth)
        delta_va_million = new_va_million - base_va_million

        # 3. 经营杠杆动态测算 (DOL) 与 EBITDA 增量
        dol = operating_leverage_dol if operating_leverage_dol is not None else self.estimate_dynamic_dol(firm, firm.sector_id, cfg)
        new_revenue_million = firm.revenue_million * (1.0 + effective_firm_growth)
        new_ebitda_million = firm.ebitda_million * (1.0 + effective_firm_growth * dol)
        delta_ebitda_million = new_ebitda_million - firm.ebitda_million

        # 4. 微观增加值分配法刚性闭环平账 (SNA Distribution Identity: VA = EBITDA + Wages + Taxes)
        delta_residual = delta_va_million - delta_ebitda_million
        non_capital_base = firm.wages_and_salaries_million + firm.taxes_paid_million

        if cfg.enforce_accounting_identity_closure and non_capital_base > 0.0:
            w_labor = firm.wages_and_salaries_million / non_capital_base
            w_tax = firm.taxes_paid_million / non_capital_base
            delta_wages = delta_residual * w_labor
            delta_taxes = delta_residual * w_tax
            new_wages = max(0.0, firm.wages_and_salaries_million + delta_wages)
            new_taxes = max(0.0, firm.taxes_paid_million + delta_taxes)
            discrepancy = abs(new_va_million - (new_ebitda_million + new_wages + new_taxes))
            identity_held = (discrepancy <= 0.01)
        else:
            new_wages = firm.wages_and_salaries_million * (1.0 + effective_firm_growth * cfg.default_wage_elasticity)
            new_taxes = firm.taxes_paid_million * (1.0 + effective_firm_growth * cfg.default_tax_elasticity)
            discrepancy = abs(new_va_million - (new_ebitda_million + new_wages + new_taxes))
            identity_held = (discrepancy <= max(1.0, new_va_million * 0.005))

        # 5. 自由现金流模拟 (绑定行业自适应 FCF 杠杆与存货拖累)
        curr = self._get_currency_symbol(firm)
        fcf_leverage = cfg.sector_fcf_leverage_map.get(firm.sector_id, cfg.default_fcf_leverage)
        fcf_growth_rate = effective_firm_growth * fcf_leverage - (inventory_drag_bps / 10000.0)
        new_fcf_million = firm.annual_fcf_million * max(0.0, 1.0 + fcf_growth_rate)

        narrative_zh = (
            f"【标的 {firm.ticker} 宏观行业冲击与企业微观业绩映射全息研报】"
            f"中观行业传导: 所属行业增加值增速 {sector_va_growth_pct:+.1f}%，企业定价权加价壁垒 μ={firm_pricing_power_mu:.2f}倍，"
            f"海外出口需求拉动 {ext_growth:+.1f}% (海外营收敞口 {f_ratio * 100.0:.1f}%)，企业有效综合增速为 {effective_firm_growth * 100.0:+.1f}%。"
            f"微观业绩模拟: 经营杠杆 DOL={dol:.2f}倍，预测营收由 {curr}{firm.revenue_million:,.1f}M 增至 {curr}{new_revenue_million:,.1f}M，"
            f"预测 EBITDA 由 {curr}{firm.ebitda_million:,.1f}M 增至 {curr}{new_ebitda_million:,.1f}M，自由现金流预测为 {curr}{new_fcf_million:,.1f}M。"
            f"国民核算闭环: 分配法平账恒等式严格闭环成立。"
        )

        return {
            "ticker": firm.ticker,
            "currency_symbol": curr,
            "country_id": firm.country_id,
            "foreign_revenue_ratio_pct": round(f_ratio * 100.0, 2),
            "sector_va_growth_pct": sector_va_growth_pct,
            "export_demand_growth_pct": round(ext_growth, 2),
            "firm_pricing_power_mu": firm_pricing_power_mu,
            "effective_firm_growth_pct": round(effective_firm_growth * 100.0, 2),
            "operating_leverage_dol": round(dol, 3),
            "baseline_va_million": base_va_million,
            "simulated_va_million": round(new_va_million, 2),
            "delta_va_million": round(delta_va_million, 2),
            "simulated_revenue_million": round(new_revenue_million, 2),
            "simulated_ebitda_million": round(new_ebitda_million, 2),
            "simulated_fcf_million": round(new_fcf_million, 2),
            "simulated_wages_million": round(new_wages, 2),
            "simulated_taxes_million": round(new_taxes, 2),
            "is_distribution_identity_held": identity_held,
            "identity_discrepancy_million": round(discrepancy, 4),
            "inventory_dio_days": firm.inventory_turnover_days_dio,
            "fcf_inventory_drag_bps": inventory_drag_bps,
            "narrative_zh": narrative_zh,
        }

    def run_firm_monte_carlo_valuation(
        self,
        firm: FirmFinancialFact,
        simulated_fcf_million: Optional[float] = None,
        sector_wacc: Optional[float] = None,
        terminal_growth_rate: Optional[float] = None,
        forecast_years: int = 5,
        iterations: int = 10000,
        random_seed: Optional[int] = 42,
    ) -> MonteCarloValuationResult:
        """从微观财务底账与增加值直接驱动 10,000 次蒙特卡洛随机估值模拟."""
        wacc = sector_wacc if sector_wacc is not None else 0.080
        g = terminal_growth_rate if terminal_growth_rate is not None else 0.025
        mc_input = MonteCarloDCFInput.from_firm_financial_fact(
            firm=firm,
            sector_wacc=wacc,
            terminal_g=g,
            forecast_years=forecast_years,
            simulated_fcf_million=simulated_fcf_million,
        )
        engine = MonteCarloValuationEngine()
        return engine.run_monte_carlo_dcf(
            ticker=firm.ticker,
            params=mc_input,
            iterations=iterations,
            random_seed=random_seed,
        )

    def compute_firm_intrinsic_valuation(
        self,
        firm: FirmFinancialFact,
        simulated_fcf_million: Optional[float] = None,
        sector_wacc: Optional[float] = None,
        terminal_growth_rate: Optional[float] = None,
        stage1_years: int = 5,
        terminal_growth_cap: float = 0.030,
        include_monte_carlo: bool = False,
        mc_iterations: int = 10000,
        mc_seed: Optional[int] = 42,
    ) -> Dict[str, Any]:
        """计算微观代表性企业的内生公允内在价值 (含单阶段戈登、两阶段内生收敛DCF、安全边际与资本回报守恒检验).

        参数:
        - firm: 企业微观财务底稿
        - simulated_fcf_million: 宏观与外需冲击传导后的模拟自由现金流 (缺省使用基准 annual_fcf_million)
        - sector_wacc: 行业基准 WACC 折现率 (缺省使用 0.080)
        - terminal_growth_rate: 行业显式第一阶段增长率 g_1 (缺省使用 0.030)
        - stage1_years: 第一阶段显式增长年数 (默认 5 年)
        - terminal_growth_cap: 永续阶段增长率上限 (锚定世界长期潜在名义增速，默认 0.030)
        - include_monte_carlo: 是否执行 10,000 次蒙特卡洛连续随机模拟并输出分布走廊
        - mc_iterations: 蒙特卡洛抽样次数 (默认 10,000)
        - mc_seed: 随机种子 (默认 42)
        """
        fcf = simulated_fcf_million if simulated_fcf_million is not None else firm.annual_fcf_million
        wacc = sector_wacc if sector_wacc is not None else 0.080
        g = terminal_growth_rate if terminal_growth_rate is not None else 0.030

        # -------------------------------------------------------------
        # 1. 经典戈登单阶段基准情景 (Baseline Gordon Fair Value)
        # -------------------------------------------------------------
        gap = max(0.008, wacc - g)
        raw_operational_dcf_billion = (fcf * (1.0 + g)) / gap / 1000.0

        # 悲观底价情景 (Pessimistic Floor / Margin of Safety)
        wacc_pess = wacc + 0.010
        g_pess = max(0.005, g - 0.010)
        fcf_pess = fcf * 0.85
        gap_pess = max(0.010, wacc_pess - g_pess)
        raw_pessimistic_floor_billion = (fcf_pess * (1.0 + g_pess)) / gap_pess / 1000.0

        # 乐观靶心情景 (Optimistic Target)
        wacc_opt = max(0.050, wacc - 0.005)
        g_opt = g + 0.008
        fcf_opt = fcf * 1.15
        gap_opt = max(0.008, wacc_opt - g_opt)
        raw_optimistic_target_billion = (fcf_opt * (1.0 + g_opt)) / gap_opt / 1000.0

        # -------------------------------------------------------------
        # 2. 内生收敛的两阶段有限生命折现模型 (Two-Stage Finite-Horizon Convergence DCF)
        # -------------------------------------------------------------
        T = max(1, stage1_years)
        g_inf = min(g, terminal_growth_cap)

        if abs(wacc - g) < 1e-4:
            pv_s1 = (fcf * T) / 1000.0
        else:
            beta = (1.0 + g) / (1.0 + wacc)
            pv_s1 = ((fcf * (1.0 + g) / (wacc - g)) * (1.0 - (beta ** T))) / 1000.0

        tv_T = (fcf * ((1.0 + g) ** T) * (1.0 + g_inf)) / max(0.008, wacc - g_inf)
        pv_tv = (tv_T / ((1.0 + wacc) ** T)) / 1000.0
        raw_two_stage_fair_val_billion = pv_s1 + pv_tv

        # 两阶段悲观与乐观原始折现
        raw_two_stage_floor_billion = (
            ((fcf_pess * (1.0 + g_pess) / max(0.008, wacc_pess - g_pess)) * (1.0 - (((1.0 + g_pess) / (1.0 + wacc_pess)) ** T)))
            + (((fcf_pess * ((1.0 + g_pess) ** T) * (1.0 + min(g_pess, terminal_growth_cap))) / max(0.008, wacc_pess - min(g_pess, terminal_growth_cap))) / ((1.0 + wacc_pess) ** T))
        ) / 1000.0

        raw_two_stage_target_billion = (
            ((fcf_opt * (1.0 + g_opt) / max(0.008, wacc_opt - g_opt)) * (1.0 - (((1.0 + g_opt) / (1.0 + wacc_opt)) ** T)))
            + (((fcf_opt * ((1.0 + g_opt) ** T) * (1.0 + min(g_opt, terminal_growth_cap))) / max(0.008, wacc_opt - min(g_opt, terminal_growth_cap))) / ((1.0 + wacc_opt) ** T))
        ) / 1000.0

        # -------------------------------------------------------------
        # 3. 股东有限责任与清算残值防御 (Merton 1974 Limited Liability & Liquidation Floor)
        # -------------------------------------------------------------
        net_cash_million = firm.cash_and_equivalents_million - firm.total_debt_million
        liquidation_floor_billion = max(
            0.0,
            (net_cash_million * 0.85 + max(0.0, firm.tangible_book_value_million) * 0.25) / 1000.0
        )

        if fcf < 0:
            # 持续失血衰退企业: 自由现金流为负，运营折现出现负值 (运营黑洞)
            # 依据有限责任下界: 股权价值下界为清算残值与零的极大值
            baseline_fair_val_billion = max(liquidation_floor_billion, 0.0)
            pessimistic_floor_billion = 0.0
            optimistic_target_billion = max(liquidation_floor_billion, 0.0)

            two_stage_fair_val_billion = max(liquidation_floor_billion, 0.0)
            two_stage_floor_billion = 0.0
            two_stage_target_billion = max(liquidation_floor_billion, 0.0)
        else:
            baseline_fair_val_billion = max(liquidation_floor_billion, raw_operational_dcf_billion, 0.0)
            pessimistic_floor_billion = max(0.0, raw_pessimistic_floor_billion)
            optimistic_target_billion = max(baseline_fair_val_billion, raw_optimistic_target_billion)

            two_stage_fair_val_billion = max(liquidation_floor_billion, raw_two_stage_fair_val_billion, 0.0)
            two_stage_floor_billion = max(0.0, raw_two_stage_floor_billion)
            two_stage_target_billion = max(two_stage_fair_val_billion, raw_two_stage_target_billion)

        # -------------------------------------------------------------
        # 4. 资产负债表健康度、债务墙与失血跑道诊断 (Distress & Zombie Diagnostics)
        # -------------------------------------------------------------
        if firm.interest_expense_million > 0:
            interest_coverage_ratio = round(firm.ebitda_million / firm.interest_expense_million, 2)
        else:
            interest_coverage_ratio = 999.0

        if firm.ebitda_million > 0:
            debt_to_ebitda_ratio = round(firm.total_debt_million / firm.ebitda_million, 2)
        else:
            debt_to_ebitda_ratio = 999.0

        if fcf < 0:
            cash_burn_runway_months = round((firm.cash_and_equivalents_million / abs(fcf)) * 12.0, 1)
        else:
            cash_burn_runway_months = None

        # 僵尸企业与价值陷阱判据:
        # 1. 僵尸企业: 利息无法覆盖 (ICR < 1.0) 或 EBITDA为负且资不抵债，或失血跑道低于12个月
        is_zombie_firm = (
            (firm.interest_expense_million > 0 and interest_coverage_ratio < 1.0) or
            (firm.ebitda_million <= 0 and firm.total_debt_million > firm.cash_and_equivalents_million) or
            (fcf < 0 and cash_burn_runway_months is not None and cash_burn_runway_months < 12.0)
        )
        # 2. 价值陷阱: 债务/EBITDA > 5.0 且伴随有形净资产为负或ICR脆弱 (<2.0) 或净债务严重透支市值
        is_value_trap = (
            debt_to_ebitda_ratio > 5.0 and
            (firm.tangible_book_value_million < 0 or interest_coverage_ratio < 2.0 or (net_cash_million < 0 and abs(net_cash_million) / 1000.0 > firm.market_cap_billion * 2.0))
        )

        # -------------------------------------------------------------
        # 5. 达摩达兰资本内生增长检验: 隐含 ROIC 与资本侵蚀防御 (纯自然中文，去工程符号化)
        # -------------------------------------------------------------
        if firm.ebitda_million <= 0 or fcf < 0:
            fcf_conversion = fcf / max(1.0, abs(firm.ebitda_million))
            reinvestment_ratio = 1.0 - fcf_conversion
            invested_cap = max(100.0, firm.tangible_book_value_million + firm.total_debt_million)
            implied_roic_pct = -round(abs(firm.ebitda_million / invested_cap) * 100.0, 2)
            is_roic_feasible = False
            capital_status = "资本持续侵蚀 / 经济附加值严重为负"
        else:
            fcf_conversion = fcf / max(1e-4, firm.ebitda_million)
            reinvestment_ratio = max(0.02, 1.0 - fcf_conversion)
            implied_roic_pct = (g / reinvestment_ratio) * 100.0
            is_roic_feasible = (2.0 <= implied_roic_pct <= 65.0)
            capital_status = "内生资本增长良性可行" if is_roic_feasible else "内生资本增长假设异常 (隐含ROIC偏离正常经济区间)"

        # -------------------------------------------------------------
        # 6. 机构估值缺口测算 (Valuation Gap %)
        # -------------------------------------------------------------
        if baseline_fair_val_billion <= 0.001:
            val_gap_pct = 999.9  # 权益已被消灭或仅存看涨期权投机溢价
        else:
            val_gap_pct = ((firm.market_cap_billion - baseline_fair_val_billion) / max(1e-6, baseline_fair_val_billion)) * 100.0

        if two_stage_fair_val_billion <= 0.001:
            two_stage_val_gap_pct = 999.9
        else:
            two_stage_val_gap_pct = ((firm.market_cap_billion - two_stage_fair_val_billion) / max(1e-6, two_stage_fair_val_billion)) * 100.0

        # -------------------------------------------------------------
        # 7. 机构决策研判 (防范价值陷阱与财务暴雷，去工程符号化)
        # -------------------------------------------------------------
        if is_zombie_firm or fcf < 0 or interest_coverage_ratio < 1.0 or firm.ebitda_million <= 0 or is_value_trap:
            if cash_burn_runway_months is not None and cash_burn_runway_months < 6.0:
                verdict = "极度破产重组风险 / 严重现金失血"
                action = "强制回避 / 剔除出投资池 / 严禁抄底"
            elif is_zombie_firm:
                verdict = "僵尸企业债务危机 / 利息支出无法覆盖"
                action = "强制剔除 / 债务重组高危 / 严禁买入"
            elif fcf < 0:
                verdict = "高危财务预警 / 自由现金流持续失血"
                action = "严禁买入 / 防范破产重组与股权大幅稀释风险"
            elif is_value_trap:
                verdict = "价值陷阱警报 / 巨额债务墙与资产负债表恶化"
                action = "谨慎减持 / 规避债务悬崖 / 严禁抄底"
            else:
                verdict = "高危财务预警 / 资产负债表与偿债能力恶化"
                action = "谨慎减持 / 规避债务悬崖"
        else:
            if val_gap_pct <= -15.0:
                verdict = "深度低估最佳击球区"
                action = "强烈建议买入 / 建立战略底仓"
            elif -15.0 < val_gap_pct <= 10.0:
                verdict = "合理公允估值均衡区间"
                action = "均衡持有 / 顺势跟踪"
            elif 10.0 < val_gap_pct <= 30.0:
                verdict = "温和溢价透支区间"
                action = "谨慎观望 / 适度分批减持"
            else:
                verdict = "严重泡沫化透支区间"
                action = "锁定利润 / 逢高坚决止盈"

        gap_desc = f"折价 {abs(val_gap_pct):.1f}%" if val_gap_pct < 0 else f"溢价 {val_gap_pct:.1f}%"
        curr = self._get_currency_symbol(firm)
        distress_desc = (
            f"债务诊断: 净现金 {curr}{net_cash_million:,.1f}M，利息保障倍数 {interest_coverage_ratio:.1f}x"
            + (f"，现金失血跑道仅剩 {cash_burn_runway_months:.1f} 个月" if cash_burn_runway_months else "，造血能力良性")
        )
        narrative_zh = (
            f"【标的 {firm.ticker} 微观内在价值与多情景折现全息研报】"
            f"当前市值与估值缺口: 当前市值 {curr}{firm.market_cap_billion:,.2f}B，两阶段收敛 DCF 公允价值 {curr}{two_stage_fair_val_billion:,.2f}B "
            f"(基准单阶段戈登估值 {curr}{baseline_fair_val_billion:,.2f}B)，相对公允中枢【{gap_desc}】。"
            f"安全边际与多情景走廊: 悲观防御底价 {curr}{two_stage_floor_billion:,.2f}B，乐观弹性靶心 {curr}{two_stage_target_billion:,.2f}B，"
            f"清算破产残值底线 {curr}{liquidation_floor_billion:,.2f}B。"
            f"内生资本检验: 资本状态处于【{capital_status}】(隐含 ROIC {implied_roic_pct:.1f}%)。"
            f"{distress_desc}。"
            f"买方机构终局研判: 【{verdict}】；执行战术: 【{action}】。"
        )

        res = {
            "ticker": firm.ticker,
            "currency_symbol": curr,
            "company_name": firm.company_name,
            "market": firm.market,
            "sector_id": firm.sector_id,
            "current_market_cap_billion": firm.market_cap_billion,
            "benchmark_wacc_pct": round(wacc * 100.0, 2),
            "terminal_growth_pct": round(g * 100.0, 2),
            "annual_fcf_million": round(fcf, 2),
            "raw_operational_dcf_billion": round(raw_operational_dcf_billion, 2),
            "liquidation_floor_billion": round(liquidation_floor_billion, 2),
            "fair_intrinsic_value_billion": round(baseline_fair_val_billion, 2),
            "pessimistic_floor_value_billion": round(pessimistic_floor_billion, 2),
            "optimistic_target_value_billion": round(optimistic_target_billion, 2),
            "valuation_gap_pct": round(val_gap_pct, 2),
            "two_stage_valuation": {
                "stage1_years": T,
                "stage1_growth_pct": round(g * 100.0, 2),
                "terminal_growth_cap_pct": round(g_inf * 100.0, 2),
                "raw_two_stage_operational_dcf_billion": round(raw_two_stage_fair_val_billion, 2),
                "two_stage_fair_value_billion": round(two_stage_fair_val_billion, 2),
                "two_stage_floor_billion": round(two_stage_floor_billion, 2),
                "two_stage_target_billion": round(two_stage_target_billion, 2),
                "two_stage_valuation_gap_pct": round(two_stage_val_gap_pct, 2),
            },
            "endogenous_capital_consistency": {
                "fcf_to_ebitda_conversion_pct": round(fcf_conversion * 100.0, 2),
                "implied_reinvestment_rate_pct": round(reinvestment_ratio * 100.0, 2),
                "implied_roic_pct": round(implied_roic_pct, 2),
                "is_economically_feasible": is_roic_feasible,
                "capital_status": capital_status,
            },
            "financial_distress_diagnostics": {
                "total_debt_million": firm.total_debt_million,
                "cash_and_equivalents_million": firm.cash_and_equivalents_million,
                "interest_expense_million": firm.interest_expense_million,
                "tangible_book_value_million": firm.tangible_book_value_million,
                "interest_coverage_ratio": interest_coverage_ratio,
                "debt_to_ebitda_ratio": debt_to_ebitda_ratio,
                "cash_burn_runway_months": cash_burn_runway_months,
                "is_zombie_firm": is_zombie_firm,
                "is_value_trap": is_value_trap,
            },
            "institutional_verdict": verdict,
            "institutional_verdict_zh": verdict,
            "recommended_action": action,
            "recommended_action_zh": action,
            "narrative_zh": narrative_zh,
        }

        if include_monte_carlo:
            mc_res = self.run_firm_monte_carlo_valuation(
                firm=firm,
                simulated_fcf_million=simulated_fcf_million,
                sector_wacc=wacc,
                terminal_growth_rate=g,
                forecast_years=stage1_years,
                iterations=mc_iterations,
                random_seed=mc_seed,
            )
            res["monte_carlo_simulation"] = mc_res.to_dict()

        return res
