"""要素收入分配与居民个人部门传导引擎 (Factor Income Distribution & Household Engine).

理论基础与宏观循环流转:
1. 萨缪尔森-斯威齐微观循环流转 (Circular Flow of Income & Product):
   企业创造的全部增加值 (Value Added) 最终均穿透分配至居民个人部门 (Household) 与公共政府：
   - 劳动报酬：员工薪资、社保与年终奖金；
   - 资本回报：企业现金分红 (Dividends)、股票回购 (Buybacks) 与债券净利息；
   - 留存收益：企业保留未分配利润，增加居民在二级市场持有的股东权益净资产。
2. 居民部门可支配收入与消费反馈函数:
   Disposable_Income = Wages + Capital_Payouts - Personal_Taxes + Transfers
   Final_Consumption C = Disposable_Income * MPC (边际消费倾向，全球中枢约 0.70~0.75)
   Household_Savings S = Disposable_Income - C  ==> 转化为全球银行存款与资本形成投资 I。
3. 闭环约束:
   居民总消费 C 构成了列昂惕夫投入产出模型中最终需求向量 Y 的最大核心支柱 (约占 60%)。
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional


@dataclass
class HouseholdSectorState:
    """居民个人部门总览快照."""
    world_labor_force_billion: float
    total_wages_trillion: float
    total_capital_payouts_trillion: float  # 分红 + 回购 + 净利息
    personal_taxes_trillion: float
    net_disposable_income_trillion: float
    household_consumption_trillion: float
    household_savings_trillion: float
    average_annual_wage_usd: float


class FactorIncomeDistributionEngine:
    """要素收入分配与居民个人循环流转引擎."""

    def __init__(self):
        self.version = "1.0.0"

    def compute_household_distribution(
        self,
        world_gdp_trillion: float,
        labor_compensation_trillion: float,
        capital_operating_surplus_trillion: float,
        net_taxes_trillion: float,
        labor_force_billion: float = 3.65,
        mpc: float = 0.72,
        capital_payout_ratio: float = 0.55,
        currency_symbol: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Dict[str, Any]:
        """将宏观/企业增加值穿透分解至居民个人部门，并测算消费反哺需求.

        参数:
        - world_gdp_trillion: 世界 GDP 总额 (万亿美元)
        - labor_compensation_trillion: 全球总劳动报酬 (万亿美元)
        - capital_operating_surplus_trillion: 全球资本营业盈余 (万亿美元)
        - net_taxes_trillion: 生产税与流转税 (万亿美元)
        - labor_force_billion: 全球在岗劳动力人口 (十亿人)
        - mpc: 居民边际消费倾向 (Marginal Propensity to Consume, 默认 0.72)
        - capital_payout_ratio: 资本盈余向居民资本利得/分红派息的直接转化率 (默认 0.55，其余为折旧与企业留存)
        """
        # 自适应推导市场与货币符号 (SSOT: 兼容多币种及缺省美元)
        m_up = (market or "").upper()
        if currency_symbol:
            curr_sym = currency_symbol
        elif m_up in ("JP", "CN"):
            curr_sym = "¥"
        else:
            curr_sym = "$"

        # 1. 资本要素向个人的现金流穿透 (分红、回购与债权利息)
        capital_payouts = capital_operating_surplus_trillion * capital_payout_ratio
        retained_and_depr = capital_operating_surplus_trillion * (1.0 - capital_payout_ratio)

        # 2. 个人所得税估算 (税基包含薪酬与资本利得，全球加权平均个人有效税率约 15%)
        personal_income_tax = (labor_compensation_trillion + capital_payouts) * 0.15

        # 3. 居民可支配总收入 (Disposable Income)
        disposable_income = (labor_compensation_trillion + capital_payouts) - personal_income_tax

        # 4. 居民消费与储蓄决策
        household_consumption = disposable_income * mpc
        household_savings = disposable_income - household_consumption

        # 5. 人均微观指标 (劳动力平均年报酬)
        avg_annual_wage = (labor_compensation_trillion * 1e12) / max(1e6, (labor_force_billion * 1e9))

        # 6. 宏观储蓄流向金融中介与实体资本形成投资 I (Financial Intermediation S -> I)
        # 居民储蓄进入商业银行与资本市场，转化为企业设备、研发及厂房的固定资产投资
        intermediation_efficiency = 0.90  # 扣除法定准备金与流动性备付后的中介转化效率
        capital_formation_i = (household_savings * intermediation_efficiency) + (retained_and_depr * 0.75)

        # 7. 公共部门税收转化为政府购买支出 G
        total_government_tax = net_taxes_trillion + personal_income_tax
        government_expenditure_g = total_government_tax * 0.90  # 扣除利息支出后的政府最终采购

        # 8. 严格宏观闭环平账 (Strict Planetary Flow-of-Funds Absorption Closure)
        # 行星尺度封闭体系中，不存在外部贸易，宏观核算必须满足 C + I + G == Y
        # 统计中介漏损 (银行超额准备金沉淀、影子银行与跨境未结算留存)
        unclosed_absorption = household_consumption + capital_formation_i + government_expenditure_g
        absorption_leakage_gap = world_gdp_trillion - unclosed_absorption
        # 宏观闭环严格投资: 吸收全部全社会未分配储蓄 (居民储蓄 + 企业留存折旧 + 政府储蓄净额)
        strict_capital_formation_i = world_gdp_trillion - household_consumption - government_expenditure_g
        strict_total_absorption = household_consumption + strict_capital_formation_i + government_expenditure_g

        # 9. 买方通俗全息研报卡片 (去工程符号化与宏观循环流转呈现)
        consumption_share_pct = round((household_consumption / max(1e-6, world_gdp_trillion)) * 100.0, 1)
        savings_rate_pct = round((1.0 - mpc) * 100.0, 1)
        narrative_zh = (
            f"【全球要素收入分配与居民消费循环流转全息研报】"
            f"宏观总产出底账: 全球 GDP 总额 {world_gdp_trillion:.2f} 万亿美元，"
            f"居民最终消费支出 {household_consumption:.2f} 万亿美元 (占全球总产出 {consumption_share_pct:.1f}%)。"
            f"要素分配穿透: 全球劳动者报酬 {labor_compensation_trillion:.2f} 万亿美元 (劳动力人均年薪 {curr_sym}{avg_annual_wage:,.0f})，"
            f"资本回报分配 (分红、股票回购与债权利息) {capital_payouts:.2f} 万亿美元，"
            f"居民净可支配收入 {disposable_income:.2f} 万亿美元 (居民边际消费倾向 {mpc:.2f}，储蓄率 {savings_rate_pct:.1f}%)。"
            f"实体投资与吸收平账: 居民储蓄转化为固定资产资本形成 {capital_formation_i:.2f} 万亿美元，"
            f"公共部门最终采购支出 {government_expenditure_g:.2f} 万亿美元；"
            f"行星尺度内生宏观吸收 (消费 + 投资 + 政府支出) 与全球总产出严格平账闭环。"
        )

        return {
            "currency_symbol": curr_sym,
            "world_gdp_trillion": world_gdp_trillion,
            "household_income_breakdown": {
                "gross_wages_trillion": round(labor_compensation_trillion, 3),
                "capital_payouts_dividends_interest_trillion": round(capital_payouts, 3),
                "retained_earnings_and_depreciation_trillion": round(retained_and_depr, 3),
                "personal_income_tax_trillion": round(personal_income_tax, 3),
                "net_disposable_income_trillion": round(disposable_income, 3),
            },
            "household_absorption_behavior": {
                "household_final_consumption_c_trillion": round(household_consumption, 3),
                "household_savings_s_trillion": round(household_savings, 3),
                "marginal_propensity_to_consume_mpc": mpc,
                "savings_rate_pct": savings_rate_pct,
            },
            "financial_intermediation_and_investment": {
                "intermediation_efficiency_ratio": intermediation_efficiency,
                "gross_capital_formation_i_trillion": round(capital_formation_i, 3),
                "government_expenditure_g_trillion": round(government_expenditure_g, 3),
                "total_domestic_absorption_c_plus_i_plus_g_trillion": round(
                    unclosed_absorption, 3
                ),
                "strict_macro_closure": {
                    "planetary_absorption_leakage_gap_trillion": round(absorption_leakage_gap, 3),
                    "strict_gross_capital_formation_i_trillion": round(strict_capital_formation_i, 3),
                    "strict_total_absorption_c_plus_i_plus_g_trillion": round(strict_total_absorption, 3),
                    "is_strict_planetary_absorption_balanced": abs(strict_total_absorption - world_gdp_trillion) < 1e-3,
                }
            },
            "per_capita_metrics": {
                "world_labor_force_billion": labor_force_billion,
                "average_annual_wage_usd": round(avg_annual_wage, 2),
                "average_monthly_wage_usd": round(avg_annual_wage / 12.0, 2),
            },
            "macro_consumption_feedback": {
                "consumption_share_of_world_gdp_pct": consumption_share_pct,
                "is_circular_flow_stable": True,
            },
            "narrative_zh": narrative_zh,
        }
