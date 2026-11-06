"""[已归档] 商业品质、真实所有者收益与行业特异性微观血肉引擎历史版本 (Legacy V1).

归档时间: 2026-11-02
归档原因: 全盘命名体系重构与区间状态变量 (Range/State Variables) 规范化升级。
替换版本: financial_core/engines/business_quality_and_moat_engine.py (现代化 Enum + 状态注册表)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import math


@dataclass
class OwnerEarningsInput:
    """巴菲特所有者收益穿透输入."""
    reported_net_income: float       # GAAP 净利润
    depreciation_amortization: float # 折旧与摊销 (D&A)
    total_capex: float               # 总资本开支
    maintenance_capex_ratio: float   # 维持现有竞争地位必须的维护性开支占比 (通常 60%~85%)
    stock_based_compensation: float  # 员工股权激励费用 (SBC)
    working_capital_change: float    # 营运资本变动 (增加为正，占用现金)
    shares_outstanding: float        # 总股本


@dataclass
class LiquorConsumerFleshInput:
    """白酒与高端消费品特异性微观血肉输入."""
    factory_price: float             # 出厂价 (例如五粮液 1019 元)
    wholesale_market_price: float    # 真实市场一批价 (例如五粮液 930 元)
    current_contract_liabilities: float # 当期合同负债 (预收款)
    prior_contract_liabilities: float   # 上期合同负债
    channel_inventory_months: float     # 渠道社会库存周转月数 (行业健康线通常为 2~2.5 个月)
    gross_margin: float                 # 毛利率


@dataclass
class TechHardwareFleshInput:
    """硬科技与半导体微观血肉输入."""
    current_dio_days: float          # 当期存货周转天数 (Days Inventory Outstanding)
    prior_dio_days: float            # 上期存货周转天数
    top_5_customer_revenue_share: float # 前五大客户营收集中度 (例如 0.65 代表 65%)
    datacenter_or_core_segment_share: float # 核心主力业务增速与营收占比
    capitalized_rd_ratio: float      # 研发支出资本化比例 (超过 15% 警惕虚增利润)


class BusinessQualityAndMoatEngine:
    """商业品质与微观血肉中枢."""

    def __init__(self):
        self.version = "1.0.0"

    def compute_owner_earnings(self, params: OwnerEarningsInput) -> Dict[str, Any]:
        """巴菲特所有者收益计算: 剥离会计粉饰后的真实自由造血能力.

        Owner Earnings = Net Income + D&A - Maintenance Capex - SBC - Change in Working Capital
        """
        maintenance_capex = params.total_capex * params.maintenance_capex_ratio
        growth_capex = params.total_capex - maintenance_capex

        owner_earnings = (
            params.reported_net_income
            + params.depreciation_amortization
            - maintenance_capex
            - params.stock_based_compensation
            - params.working_capital_change
        )

        owner_earnings_per_share = owner_earnings / max(1.0, params.shares_outstanding)
        reported_eps = params.reported_net_income / max(1.0, params.shares_outstanding)

        # 盈利品质系数 (Quality of Earnings Ratio) = Owner Earnings / Reported Net Income
        quality_ratio = (owner_earnings / max(1.0, abs(params.reported_net_income))) if params.reported_net_income != 0 else 0.0

        is_earnings_diluted_or_fake = quality_ratio < 0.65

        return {
            "reported_net_income": round(params.reported_net_income, 2),
            "owner_earnings": round(owner_earnings, 2),
            "maintenance_capex": round(maintenance_capex, 2),
            "sbc_drag": round(params.stock_based_compensation, 2),
            "reported_eps": round(reported_eps, 4),
            "owner_earnings_per_share": round(owner_earnings_per_share, 4),
            "earnings_quality_ratio": round(quality_ratio, 4),
            "earnings_quality_verdict": "High_Quality" if quality_ratio >= 0.85 else ("Moderate" if quality_ratio >= 0.65 else "Severe_Accounting_Haircut"),
            "warning": "利润严重失真: 大量利润被维护性开支或股权激励吞噬" if is_earnings_diluted_or_fake else "盈利品质扎实",
        }

    def evaluate_liquor_flesh(self, params: LiquorConsumerFleshInput) -> Dict[str, Any]:
        """白酒微观血肉诊断: 批价倒挂与渠道堰塞湖预警."""
        # 1. 价格倒挂率 (Inversion Rate)
        price_spread = params.wholesale_market_price - params.factory_price
        is_inverted = price_spread < 0
        inversion_pct = (price_spread / params.factory_price) * 100.0

        # 2. 合同负债变动 (经销商打款意愿晴雨表)
        contract_liab_growth_pct = ((params.current_contract_liabilities - params.prior_contract_liabilities) / max(1.0, params.prior_contract_liabilities)) * 100.0
        dealers_reluctant_to_pay = contract_liab_growth_pct < -15.0

        # 3. 渠道库存风险等级
        # 正常库存 2~2.5 个月，超过 3.5 个月为严重积压堰塞湖
        if params.channel_inventory_months >= 4.0:
            inventory_risk = "Critical_Channel_Clog"
        elif params.channel_inventory_months >= 3.0:
            inventory_risk = "Elevated_Overhang"
        else:
            inventory_risk = "Healthy_Turnover"

        # 4. 真实提价权评分 (0 ~ 100)
        # 若倒挂且库存高，提价权归零
        if is_inverted and params.channel_inventory_months > 3.0:
            pricing_power_score = max(10.0, 30.0 + inversion_pct)
        elif not is_inverted:
            pricing_power_score = min(100.0, 70.0 + (price_spread / params.factory_price) * 100.0)
        else:
            pricing_power_score = 45.0

        return {
            "price_inversion_active": is_inverted,
            "inversion_spread_yuan": round(price_spread, 2),
            "inversion_ratio_pct": round(inversion_pct, 2),
            "contract_liabilities_growth_pct": round(contract_liab_growth_pct, 2),
            "dealers_confidence_drain": dealers_reluctant_to_pay,
            "channel_inventory_status": inventory_risk,
            "pricing_power_score": round(pricing_power_score, 1),
            "pricing_power_verdict": "Dominant_Pricing_Power" if pricing_power_score >= 80 else ("Constrained_By_Market" if pricing_power_score >= 40 else "Severe_Price_Destruction"),
        }

    def evaluate_tech_flesh(self, params: TechHardwareFleshInput) -> Dict[str, Any]:
        """硬科技微观血肉诊断: 存货周期见顶反噬与客户集中度风险."""
        # 1. 存货周转天数 (DIO) 周期演变: 连续跳升说明下游砍单
        dio_delta = params.current_dio_days - params.prior_dio_days
        dio_surge_warning = dio_delta > 15.0 or params.current_dio_days > 120.0

        # 2. 大客户依赖度风险
        high_concentration = params.top_5_customer_revenue_share > 0.60

        # 3. 研发资本化粉饰识别
        rd_capitalization_red_flag = params.capitalized_rd_ratio > 0.15

        return {
            "current_dio_days": round(params.current_dio_days, 1),
            "dio_change_days": round(dio_delta, 1),
            "inventory_cycle_warning": dio_surge_warning,
            "top_5_concentration_pct": round(params.top_5_customer_revenue_share * 100, 2),
            "customer_vulnerability": "High_Dependency" if high_concentration else "Diversified",
            "rd_capitalization_warning": rd_capitalization_red_flag,
            "tech_operating_health": "Fragile_Downcycle" if (dio_surge_warning and high_concentration) else "Robust",
        }
