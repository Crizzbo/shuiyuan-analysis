"""商业品质、真实所有者收益与行业特异性微观血肉引擎 (Business Quality & Domain Flesh Engine).

遵循 Google Python 编程风格指南与《SPEC-03 行业知识中枢与微观商业机器解构规格书》:
1. 巴菲特所有者收益 (Owner Earnings) 穿透器:
   - 严厉扣除维持现有竞争力必须的维护性资本开支 (Maintenance Capex) 与股权激励 (SBC);
2. 行业特异性微观血肉诊断器 (Domain-Specific Micro KPIs):
   - 白酒与消费品: 渠道周转天数/月数、批价出厂价倒挂、合同负债枯竭预警;
   - 硬科技与半导体: 存货周转天数 (DIO) 周期演变、大客户集中度依赖、研发资本化粉饰;
3. 真实提价权与经济护城河指数 (Pricing Power & Moat Robustness Score);
4. 单一事实来源 (SSOT) 状态空间注册表 (METRICS_STATE_REGISTRY):
   - 显式记载每一个区间状态变量的状态总数、数值闭区间、严重度等级、通俗商业直觉释义与投资应对行动指令.
"""

# 1. Python 标准库
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union

# 2. 第三方数学与科学计算库
# (纯原生标准库依赖，保持纯净计算引擎零外部重量级污染)

# 3. 内部核心库 (纯相对导入，符合 Google Python 规范与单向依赖铁律)
from .knowledge_repository import KnowledgeRepository


# ==============================================================================
# 一、 强类型区间状态变量枚举 (Range / State Enums)
# ==============================================================================


class EarningsQualityVerdict(str, Enum):
    """盈利质量评判状态 (3 态空间)."""

    HIGH_QUALITY = "High_Quality"  # 扎实高质量 (>= 85%)
    MODERATE = "Moderate"  # 中度健康 (65% ~ 85%)
    SEVERE_HAIRCUT = "Severe_Accounting_Haircut"  # 严重会计粉饰/缩水 (< 65%)


class ChannelInventoryStatus(str, Enum):
    """渠道社会库存健康状态 (3 态空间)."""

    HEALTHY_TURNOVER = "Healthy_Turnover"  # 健康周转态 (< 3.0 个月)
    ELEVATED_OVERHANG = "Elevated_Overhang"  # 轻度积压预警态 (3.0 ~ 4.0 个月)
    CRITICAL_CLOG = "Critical_Channel_Clog"  # 严重堰塞湖积压态 (>= 4.0 个月)


class PricingPowerVerdict(str, Enum):
    """真实终端提价权评判状态 (3 态空间)."""

    DOMINANT_PRICING_POWER = "Dominant_Pricing_Power"  # 统御级提价权 (>= 80 分)
    CONSTRAINED_BY_MARKET = "Constrained_By_Market"  # 市场博弈约束 (40 ~ 80 分)
    SEVERE_PRICE_DESTRUCTION = (
        "Severe_Price_Destruction"  # 价格严重倒挂与破坏 (< 40 分)
    )


class CustomerVulnerabilityStatus(str, Enum):
    """客户集中度风险状态 (2 态空间)."""

    DIVERSIFIED = "Diversified"  # 分散稳健 (前五大 <= 60%)
    HIGH_DEPENDENCY = "High_Dependency"  # 高度依赖单点脆弱 (前五大 > 60%)


class TechOperatingHealthStatus(str, Enum):
    """硬科技经营周期健康状态 (2 态空间)."""

    ROBUST = "Robust"  # 经营周期稳健
    FRAGILE_DOWNCYCLE = (
        "Fragile_Downcycle"  # 下行周期脆弱 (库存暴增且客户集中)
    )


# ==============================================================================
# 二、 区间状态变量单一事实来源元数据注册表 (METRICS_STATE_REGISTRY - SSOT)
# ==============================================================================

METRICS_STATE_REGISTRY: Dict[str, Dict[str, Dict[str, Any]]] = {
    "earnings_quality": {
        EarningsQualityVerdict.HIGH_QUALITY.value: {
            "state_id": "EQ_01",
            "state_name": "高质量盈利",
            "numerical_interval": "[0.85, +inf) 比率",
            "severity_level": 1,
            "business_intuition_zh": (
                "账面利润与真实自由现金高度匹配，维护性开支和股权激励稀释极低，"
                "真金白银造血能力出众。"
            ),
            "action_directive_zh": (
                "维持正常或积极买点评估，无需对财报利润施加保守折让剪刀差。"
            ),
        },
        EarningsQualityVerdict.MODERATE.value: {
            "state_id": "EQ_02",
            "state_name": "中度健康盈利",
            "numerical_interval": "[0.65, 0.85) 比率",
            "severity_level": 2,
            "business_intuition_zh": (
                "利润大部分转化为真实造血，但存在一定的厂房设备维护或常规股权激励摩擦。"
            ),
            "action_directive_zh": (
                "建议在基准 DCF 模型中对自由现金流设置 10% 的安全扣减垫。"
            ),
        },
        EarningsQualityVerdict.SEVERE_HAIRCUT.value: {
            "state_id": "EQ_03",
            "state_name": "严重会计粉饰与虚假繁荣",
            "numerical_interval": "(-inf, 0.65) 比率",
            "severity_level": 5,
            "business_intuition_zh": (
                "虚胖！大量纸面净利润被巨额维护性资本开支吞噬，或被管理层疯狂发放股票期权自我侵吞，"
                "造血严重贫血。"
            ),
            "action_directive_zh": (
                "立即触发财务警报！DCF 模型强制按所有者收益而非净利润折现，"
                "或下调买入击球区 20% 以上。"
            ),
        },
    },
    "channel_inventory": {
        ChannelInventoryStatus.HEALTHY_TURNOVER.value: {
            "state_id": "CI_01",
            "state_name": "渠道周转健康",
            "numerical_interval": "[0.0, 3.0) 个月",
            "severity_level": 1,
            "business_intuition_zh": (
                "社会渠道动销顺畅，终端消费开瓶率良好，经销商库容充裕，出厂价与批发价支撑强劲。"
            ),
            "action_directive_zh": (
                "标的具备较强定价护城河，维持顺周期成长或红利建仓跟踪。"
            ),
        },
        ChannelInventoryStatus.ELEVATED_OVERHANG.value: {
            "state_id": "CI_02",
            "state_name": "社会库存轻度积压",
            "numerical_interval": "[3.0, 4.0) 个月",
            "severity_level": 3,
            "business_intuition_zh": (
                "渠道出现轻度压货，经销商资金回笼出现滞纳感，部分批价出现小幅贴水摩擦。"
            ),
            "action_directive_zh": (
                "暂缓左侧追高，密切排查下期合同负债与预收款流向，估值增加 10%"
                " 安全边际。"
            ),
        },
        ChannelInventoryStatus.CRITICAL_CLOG.value: {
            "state_id": "CI_03",
            "state_name": "渠道严重堰塞湖积压",
            "numerical_interval": "[4.0, +inf) 个月",
            "severity_level": 5,
            "business_intuition_zh": (
                "渠道全面形成堰塞湖淤积！经销商为保现金流亏本甩货，一批价大幅跌破出厂价，"
                "价格体系濒临崩塌。"
            ),
            "action_directive_zh": (
                "一票否决红线！坚决避开‘估值看起来便宜但渠道正在雪崩’的价值陷阱，"
                "等待渠道去库存彻底完成。"
            ),
        },
    },
    "pricing_power": {
        PricingPowerVerdict.DOMINANT_PRICING_POWER.value: {
            "state_id": "PP_01",
            "state_name": "统御级提价权",
            "numerical_interval": "[80.0, 100.0] 分",
            "severity_level": 1,
            "business_intuition_zh": (
                "产品具备独占性品牌或技术特许权，顺畅将通胀与成本向下游完全转移，提价不损销量。"
            ),
            "action_directive_zh": (
                "长期核心底仓配置，可给予买方估值溢价与更高的仓位容忍度。"
            ),
        },
        PricingPowerVerdict.CONSTRAINED_BY_MARKET.value: {
            "state_id": "PP_02",
            "state_name": "市场博弈约束",
            "numerical_interval": "[40.0, 80.0) 分",
            "severity_level": 2,
            "business_intuition_zh": (
                "具备一定品牌辨识度，但面对竞品压力无法随意提价，受制于大盘消费景气度。"
            ),
            "action_directive_zh": "严守公允内在价值锚点，拒绝在乐观靶心溢价追高。",
        },
        PricingPowerVerdict.SEVERE_PRICE_DESTRUCTION.value: {
            "state_id": "PP_03",
            "state_name": "价格严重倒挂与破坏",
            "numerical_interval": "(-inf, 40.0) 分",
            "severity_level": 5,
            "business_intuition_zh": (
                "护城河失效，大打价格战，批价已失守出厂防线，毛利空间遭到系统性挤压。"
            ),
            "action_directive_zh": (
                "剔除出高确信度买入池，估值走廊全面滑入悲观底线防御区。"
            ),
        },
    },
    "customer_vulnerability": {
        CustomerVulnerabilityStatus.DIVERSIFIED.value: {
            "state_id": "CV_01",
            "state_name": "客户群体多元分散",
            "numerical_interval": "[0.0, 60.0%] 占比",
            "severity_level": 1,
            "business_intuition_zh": (
                "下游客户广泛分散，任何单一客户砍单均不会引发灾难性系统停摆。"
            ),
            "action_directive_zh": "企业经营安全垫扎实，现金流波动率低。",
        },
        CustomerVulnerabilityStatus.HIGH_DEPENDENCY.value: {
            "state_id": "CV_02",
            "state_name": "大客户高度依赖单点脆弱",
            "numerical_interval": "(60.0%, 100.0%] 占比",
            "severity_level": 4,
            "business_intuition_zh": (
                "营收高度寄生于少数一两个超级大客户，议价能力弱，"
                "极易因客户自研替代或砍单导致业绩断崖。"
            ),
            "action_directive_zh": (
                "强制计提 15%"
                " 客户集中度折价，建立大客户资本开支与供应链变动高频雷达。"
            ),
        },
    },
    "tech_operating_health": {
        TechOperatingHealthStatus.ROBUST.value: {
            "state_id": "TO_01",
            "state_name": "科技经营周期稳健",
            "numerical_interval": "正常存货与客户分散组合",
            "severity_level": 1,
            "business_intuition_zh": (
                "存货周转天数稳定或受控，下游需求与订单可见度高，研发投入真实转化为竞争力。"
            ),
            "action_directive_zh": (
                "保持科技成长股正常攻防配置，重点追踪主力产品商业化进展。"
            ),
        },
        TechOperatingHealthStatus.FRAGILE_DOWNCYCLE.value: {
            "state_id": "TO_02",
            "state_name": "下行周期双重脆弱",
            "numerical_interval": "DIO突增 (>15天/120天) 且 客户集中度 (>60%)",
            "severity_level": 5,
            "business_intuition_zh": (
                "下游大客户已开始砍单削减订单，存货在库房急速积压变质，"
                "即将面临毁灭性的存货跌价减值风暴。"
            ),
            "action_directive_zh": (
                "立刻防守！等待存货跌价充分计提、存货天数见顶回落的右侧企稳信号再行建仓。"
            ),
        },
    },
}


def get_metric_state_metadata(
    domain_key: str, state_value: Union[str, Enum]
) -> Dict[str, Any]:
    """统一查询区间状态变量的元数据 (单一事实来源查询器).

    Args:
        domain_key: 状态所属业务域 ('earnings_quality', 'channel_inventory',
            'pricing_power', 'customer_vulnerability',
            'tech_operating_health').
        state_value: 具体的枚举值或字符串代号.

    Returns:
        包含 state_id, state_name, numerical_interval, severity_level,
        business_intuition_zh, action_directive_zh 等全息字典.
    """
    raw_val = (
        state_value.value if isinstance(state_value, Enum) else str(state_value)
    )
    domain = METRICS_STATE_REGISTRY.get(domain_key, {})
    meta = domain.get(raw_val)
    if meta:
        return {
            "domain_key": domain_key,
            "state_key": raw_val,
            **meta,
        }
    return {
        "domain_key": domain_key,
        "state_key": raw_val,
        "state_id": "UNKNOWN",
        "state_name": "未收录状态",
        "numerical_interval": "未定义",
        "severity_level": 0,
        "business_intuition_zh": "未在标准状态注册表中登记的自定义状态。",
        "action_directive_zh": "谨慎核对数据源。",
    }


# ==============================================================================
# 三、 规范化输入数据契约 (Dataclass Inputs)
# ==============================================================================


@dataclass(frozen=True)
class OwnerEarningsInput:
    """巴菲特所有者收益穿透输入契约 (兼容自解释与旧版字段).

    Attributes:
        reported_net_income: GAAP/IFRS 报告净利润 (基础货币单位).
        depreciation_amortization: 折旧与摊销 (D&A).
        total_capex: 当期总资本开支.
        maintenance_capex_ratio: 维持现有竞争地位必须的维护性开支占比 (通常 60%~85%).
        stock_based_compensation: 员工股权激励费用 (SBC).
        working_capital_change: 营运资本变动 (增加为正，占用现金).
        shares_outstanding: 总股本 (股).
        currency_unit: 货币单位 (例如 '元', '美元', '日元' 等).
    """

    reported_net_income: float
    depreciation_amortization: float
    total_capex: float
    maintenance_capex_ratio: float
    stock_based_compensation: float
    working_capital_change: float
    shares_outstanding: float
    currency_unit: str = "元"


@dataclass(frozen=True)
class LiquorConsumerFleshInput:
    """白酒与高端消费品特异性微观血肉输入契约.

    Attributes:
        factory_price: 核心单品出厂价 (如五粮液 1019 元).
        wholesale_market_price: 真实市场一批价 (如五粮液 930 元).
        current_contract_liabilities: 当期合同负债 (预收款).
        prior_contract_liabilities: 上期合同负债.
        channel_inventory_months: 渠道社会库存周转月数 (行业健康线通常为 2~2.5 个月).
        gross_margin: 产品销售毛利率 (例如 0.75 代表 75%).
        currency_unit: 货币单位 (例如 '元', '日元' 等).
    """

    factory_price: float
    wholesale_market_price: float
    current_contract_liabilities: float
    prior_contract_liabilities: float
    channel_inventory_months: float
    gross_margin: float
    currency_unit: str = "元"


@dataclass(frozen=True)
class TechHardwareFleshInput:
    """硬科技与半导体微观血肉输入契约.

    Attributes:
        current_dio_days: 当期存货周转天数 (Days Inventory Outstanding).
        prior_dio_days: 上期存货周转天数.
        top_5_customer_revenue_share: 前五大客户营收集中度 (例如 0.65 代表 65%).
        datacenter_or_core_segment_share: 核心主力业务增速与营收占比.
        capitalized_rd_ratio: 研发支出资本化比例 (超过 15% 警惕虚增利润).
    """

    current_dio_days: float
    prior_dio_days: float
    top_5_customer_revenue_share: float
    datacenter_or_core_segment_share: float
    capitalized_rd_ratio: float


# ==============================================================================
# 四、 核心商业品质与微观血肉计算引擎 (Engine Implementation)
# ==============================================================================


class BusinessQualityAndMoatEngine:
    """商业品质、护城河与微观血肉计算中枢 (Google Python Style Guide 架构设计)."""

    def __init__(self) -> None:
        """初始化商业品质中枢引擎."""
        self.version: str = "2.0.0"

    def calculate_buffett_owner_earnings(
        self, params: OwnerEarningsInput
    ) -> Dict[str, Any]:
        """巴菲特所有者收益计算: 剥离会计粉饰后的真实自由造血能力.

        Owner Earnings = Net Income + D&A - Maintenance Capex - SBC - Change in
        Working Capital

        Args:
            params: OwnerEarningsInput 结构化输入事实对象.

        Returns:
            包含账面利润、维护性开支、真实所有者收益、每股收益、品质系数、
            评级枚举与研报叙述卡片的全息字典.
        """
        num_maintenance_capex = (
            params.total_capex * params.maintenance_capex_ratio
        )
        num_owner_earnings = (
            params.reported_net_income
            + params.depreciation_amortization
            - num_maintenance_capex
            - params.stock_based_compensation
            - params.working_capital_change
        )

        safe_shares = max(0.01, params.shares_outstanding)
        num_owner_earnings_per_share = num_owner_earnings / safe_shares
        num_reported_eps = params.reported_net_income / safe_shares

        denom_net_income = max(0.01, abs(params.reported_net_income))
        ratio_quality = (
            (num_owner_earnings / denom_net_income)
            if params.reported_net_income != 0
            else 0.0
        )

        state_enum, warning_text = self._evaluate_earnings_quality(
            reported_net_income=params.reported_net_income,
            num_owner_earnings=num_owner_earnings,
            ratio_quality=ratio_quality,
        )
        meta = get_metric_state_metadata("earnings_quality", state_enum)
        c_unit = getattr(params, "currency_unit", "元") or "元"

        narrative_zh = (
            f"【巴菲特所有者收益与真实造血品质研报】"
            f"盈利质量综合评级属于【{meta['state_name']}】(造血匹配度"
            f" {ratio_quality*100:.1f}%)。"
            f"穿透核算: 账面净利润 {params.reported_net_income:,.0f} {c_unit}，"
            f"扣除维护性资本开支 {num_maintenance_capex:,.0f} {c_unit}、"
            f"股权激励稀释 {params.stock_based_compensation:,.0f} {c_unit}及营运资本占用后，"
            f"真实所有者收益为 {num_owner_earnings:,.0f} {c_unit} "
            f"(每股所有者收益 {num_owner_earnings_per_share:.2f} {c_unit})。"
            f"商业直觉研判: {meta['business_intuition_zh']} "
            f"买方行动指令: {meta['action_directive_zh']}"
        )

        return {
            "reported_net_income": round(params.reported_net_income, 2),
            "owner_earnings": round(num_owner_earnings, 2),
            "maintenance_capex": round(num_maintenance_capex, 2),
            "sbc_drag": round(params.stock_based_compensation, 2),
            "reported_eps": round(num_reported_eps, 4),
            "owner_earnings_per_share": round(num_owner_earnings_per_share, 4),
            "earnings_quality_ratio": round(ratio_quality, 4),
            "earnings_quality_verdict": state_enum.value,
            "earnings_quality_verdict_zh": meta["state_name"],
            "earnings_quality_enum": state_enum,
            "state_metadata": meta,
            "warning": warning_text,
            "narrative_zh": narrative_zh,
        }

    compute_owner_earnings = calculate_buffett_owner_earnings

    def diagnose_liquor_channel_flesh(
        self, params: LiquorConsumerFleshInput
    ) -> Dict[str, Any]:
        """白酒微观血肉诊断: 批价倒挂与渠道堰塞湖预警.

        Args:
            params: LiquorConsumerFleshInput 消费品特异性微观输入对象.

        Returns:
            包含批价倒挂幅度、合同负债变动、渠道库存状态、提价权评分与全息研报卡片的字典.
        """
        safe_factory_price = max(0.01, float(params.factory_price))

        val_price_spread = params.wholesale_market_price - safe_factory_price
        is_inverted = val_price_spread < 0
        pct_inversion = (val_price_spread / safe_factory_price) * 100.0

        safe_prior_contract = max(0.01, params.prior_contract_liabilities)
        pct_contract_liab_growth = (
            (
                params.current_contract_liabilities
                - params.prior_contract_liabilities
            )
            / safe_prior_contract
        ) * 100.0
        has_dealers_confidence_drain = pct_contract_liab_growth < -15.0

        if params.channel_inventory_months >= 4.0:
            status_inventory = ChannelInventoryStatus.CRITICAL_CLOG
        elif params.channel_inventory_months >= 3.0:
            status_inventory = ChannelInventoryStatus.ELEVATED_OVERHANG
        else:
            status_inventory = ChannelInventoryStatus.HEALTHY_TURNOVER

        meta_inventory = get_metric_state_metadata(
            "channel_inventory", status_inventory
        )

        val_pricing_power_score, verdict_pricing = (
            self._evaluate_liquor_pricing_power(
                is_inverted=is_inverted,
                pct_inversion=pct_inversion,
                val_price_spread=val_price_spread,
                safe_factory_price=safe_factory_price,
                channel_inventory_months=params.channel_inventory_months,
            )
        )
        meta_pricing = get_metric_state_metadata(
            "pricing_power", verdict_pricing
        )
        c_unit = getattr(params, "currency_unit", "元") or "元"

        inversion_desc = (
            f"批价倒挂 {abs(val_price_spread):.1f} {c_unit} (倒挂幅度"
            f" {abs(pct_inversion):.1f}%)"
            if is_inverted
            else f"批价顺价溢价 +{val_price_spread:.1f} {c_unit}"
        )
        drain_desc = (
            "经销商打款信心出现明显动摇枯竭"
            if has_dealers_confidence_drain
            else "经销商打款意愿平稳"
        )
        narrative_zh = (
            f"【渠道批价与微观血肉诊断全息研报】"
            f"真实提价权定性为【{meta_pricing['state_name']}】"
            f"(提价权得分 {val_pricing_power_score:.1f}/100)；"
            f"社会渠道库存处于【{meta_inventory['state_name']}】"
            f"(周转月数 {params.channel_inventory_months:.1f} 个月)。"
            f"价格倒挂状态: {inversion_desc}。"
            f"打款信心风向: 合同负债变动 {pct_contract_liab_growth:+.1f}%"
            f" ({drain_desc})。"
            f"商业直觉研判: {meta_pricing['business_intuition_zh']} "
            f"买方行动指令: {meta_pricing['action_directive_zh']}"
        )

        return {
            "price_inversion_active": is_inverted,
            "inversion_spread_yuan": round(val_price_spread, 2),
            "inversion_ratio_pct": round(pct_inversion, 2),
            "contract_liabilities_growth_pct": round(
                pct_contract_liab_growth, 2
            ),
            "dealers_confidence_drain": has_dealers_confidence_drain,
            "channel_inventory_status": status_inventory.value,
            "channel_inventory_status_zh": meta_inventory["state_name"],
            "channel_inventory_enum": status_inventory,
            "channel_inventory_metadata": meta_inventory,
            "pricing_power_score": round(val_pricing_power_score, 1),
            "pricing_power_verdict": verdict_pricing.value,
            "pricing_power_verdict_zh": meta_pricing["state_name"],
            "pricing_power_enum": verdict_pricing,
            "pricing_power_metadata": meta_pricing,
            "narrative_zh": narrative_zh,
        }

    evaluate_liquor_flesh = diagnose_liquor_channel_flesh

    def diagnose_tech_inventory_cycle_and_moat(
        self, params: TechHardwareFleshInput
    ) -> Dict[str, Any]:
        """硬科技微观血肉诊断: 存货周期见顶反噬与客户集中度风险.

        Args:
            params: TechHardwareFleshInput 硬科技特异性微观输入对象.

        Returns:
            包含存货周转天数跳变、客户集中度状态、研发资本化预警与全息研报卡片的字典.
        """
        days_dio_delta = params.current_dio_days - params.prior_dio_days
        has_dio_surge_warning = (
            days_dio_delta > 15.0 or params.current_dio_days > 120.0
        )

        if params.top_5_customer_revenue_share > 0.60:
            status_customer = CustomerVulnerabilityStatus.HIGH_DEPENDENCY
        else:
            status_customer = CustomerVulnerabilityStatus.DIVERSIFIED
        meta_customer = get_metric_state_metadata(
            "customer_vulnerability", status_customer
        )

        has_rd_capitalization_red_flag = params.capitalized_rd_ratio > 0.15

        if has_dio_surge_warning and (
            status_customer == CustomerVulnerabilityStatus.HIGH_DEPENDENCY
        ):
            status_health = TechOperatingHealthStatus.FRAGILE_DOWNCYCLE
        else:
            status_health = TechOperatingHealthStatus.ROBUST
        meta_health = get_metric_state_metadata(
            "tech_operating_health", status_health
        )

        dio_warning_desc = (
            "触发库存积压高危警报" if has_dio_surge_warning else "存货节奏良性受控"
        )
        rd_desc = (
            "存在通过开发支出虚增利润倾向"
            if has_rd_capitalization_red_flag
            else "研发支出费用化扎实"
        )
        narrative_zh = (
            f"【硬科技存货周期与客户护城河全息研报】"
            f"科技经营周期综合评级为【{meta_health['state_name']}】；"
            f"客户集中度结构属于【{meta_customer['state_name']}】"
            f"(前五大客户营收占比"
            f" {params.top_5_customer_revenue_share*100:.1f}%)。"
            f"存货周转天数 (DIO): 当前 {params.current_dio_days:.1f} 天 "
            f"(较上期变动 {days_dio_delta:+.1f} 天，{dio_warning_desc})。"
            f"研发资本化审计: 研发支出资本化比例"
            f" {params.capitalized_rd_ratio*100:.1f}% ({rd_desc})。"
            f"商业直觉研判: {meta_health['business_intuition_zh']} "
            f"买方行动指令: {meta_health['action_directive_zh']}"
        )

        return {
            "current_dio_days": round(params.current_dio_days, 1),
            "dio_change_days": round(days_dio_delta, 1),
            "inventory_cycle_warning": has_dio_surge_warning,
            "top_5_concentration_pct": round(
                params.top_5_customer_revenue_share * 100, 2
            ),
            "customer_vulnerability": status_customer.value,
            "customer_vulnerability_zh": meta_customer["state_name"],
            "customer_vulnerability_enum": status_customer,
            "customer_vulnerability_metadata": meta_customer,
            "rd_capitalization_warning": has_rd_capitalization_red_flag,
            "tech_operating_health": status_health.value,
            "tech_operating_health_zh": meta_health["state_name"],
            "tech_operating_health_enum": status_health,
            "tech_operating_health_metadata": meta_health,
            "narrative_zh": narrative_zh,
        }

    evaluate_tech_flesh = diagnose_tech_inventory_cycle_and_moat

    def diagnose_business_model_and_moat(
        self,
        ticker: str,
        business_model_id: str,
        reported_metrics: Optional[Dict[str, float]] = None,
        currency_unit: str = "元",
    ) -> Dict[str, Any]:
        """商业模式法定指标契约与买方护城河全息诊断 (配置驱动 SSOT).

        Args:
            ticker: 证券代码 (如 'BLK', 'AAPL').
            business_model_id: 商业模式法定 ID (如 'asset_management_fee').
            reported_metrics: 实际上报或已计算的指标数值字典.
            currency_unit: 货币单位字符串 (默认 '元').

        Returns:
            包含模型中文名、指标覆盖率、缺失列表、研报叙述卡片等全息字典.
        """
        repo = KnowledgeRepository.get_instance()
        model_profile = repo.get_business_model(business_model_id)
        metrics_dict = reported_metrics or {}

        if not model_profile:
            return {
                "ticker": ticker,
                "business_model_id": business_model_id,
                "is_registered_model": False,
                "model_name_zh": "未定义商业模式",
                "required_metrics": [],
                "metric_coverage_pct": 0.0,
                "missing_metrics": [],
                "narrative_zh": (
                    f"【标的 {ticker} 商业模式诊断】未在知识库底账中检索到模式 "
                    f"'{business_model_id}'，无法执行法定契约核验。"
                ),
            }

        required_metrics_profiles = repo.get_metrics_for_business_model(
            business_model_id
        )
        total_required = len(model_profile.metric_ids)
        covered_count = 0
        missing_list: List[str] = []
        metrics_evaluation: List[Dict[str, Any]] = []

        for m in required_metrics_profiles:
            mid = m.metric_id
            if mid in metrics_dict and metrics_dict[mid] is not None:
                covered_count += 1
                val = metrics_dict[mid]
                metrics_evaluation.append({
                    "metric_id": mid,
                    "metric_name": m.name,
                    "unit": m.unit,
                    "reported_value": val,
                    "is_available": True,
                })
            else:
                missing_list.append(mid)
                metrics_evaluation.append({
                    "metric_id": mid,
                    "metric_name": m.name,
                    "unit": m.unit,
                    "reported_value": None,
                    "is_available": False,
                })

        coverage_pct = round((covered_count / max(1, total_required)) * 100.0, 1)

        if coverage_pct >= 100.0:
            readiness_zh = "法定指标完备齐备 (可执行高精度商业模式穿透)"
        elif coverage_pct >= 50.0:
            readiness_zh = "核心指标部分覆盖 (需关注缺项指标补充)"
        else:
            readiness_zh = "指标披露严重缺失 (数据底账不足以支持深度穿透)"

        narrative_zh = (
            f"【标的 {ticker} 商业模式与护城河全息诊断研报】"
            f"主营商业模式定性【{model_profile.name}】({model_profile.model_id})。"
            f"法定指标契约就绪度: {readiness_zh} (指标覆盖率 {coverage_pct:.1f}%，"
            f"齐备 {covered_count}/{total_required} 项)。"
            f"买方深度投研底账: 该模式已在知识库中建立买方深度研究专篇"
            f" ({model_profile.profile_path})，"
            "涵盖该商业形态在竞争博弈中的规模壁垒、转换成本及定价权演化规律。"
        )

        return {
            "ticker": ticker,
            "business_model_id": model_profile.model_id,
            "model_name_zh": model_profile.name,
            "is_registered_model": True,
            "required_metric_ids": list(model_profile.metric_ids),
            "metric_coverage_pct": coverage_pct,
            "covered_metric_count": covered_count,
            "total_required_metric_count": total_required,
            "missing_metric_ids": missing_list,
            "metrics_evaluation": metrics_evaluation,
            "has_deep_research_markdown": model_profile.has_deep_research_markdown,
            "profile_path": model_profile.profile_path,
            "narrative_zh": narrative_zh,
        }

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helper Methods, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _evaluate_earnings_quality(
        reported_net_income: float,
        num_owner_earnings: float,
        ratio_quality: float,
    ) -> Tuple[EarningsQualityVerdict, str]:
        """评判巴菲特所有者收益质量等级 (私有辅助方法)."""
        is_earnings_diluted_or_fake = ratio_quality < 0.65
        if ratio_quality >= 0.85:
            state_enum = EarningsQualityVerdict.HIGH_QUALITY
        elif ratio_quality >= 0.65:
            state_enum = EarningsQualityVerdict.MODERATE
        else:
            state_enum = EarningsQualityVerdict.SEVERE_HAIRCUT

        if reported_net_income <= 0 and num_owner_earnings < 0:
            warning_text = "账面亏损且真实所有者现金流失血持续恶化"
        elif is_earnings_diluted_or_fake:
            warning_text = "利润严重失真: 大量利润被维护性开支或股权激励吞噬"
        else:
            warning_text = "盈利品质扎实"

        return state_enum, warning_text

    @staticmethod
    def _evaluate_liquor_pricing_power(
        is_inverted: bool,
        pct_inversion: float,
        val_price_spread: float,
        safe_factory_price: float,
        channel_inventory_months: float,
    ) -> Tuple[float, PricingPowerVerdict]:
        """评判消费品终端提价权得分与定性级别 (私有辅助方法)."""
        if is_inverted:
            inventory_drag = 15.0 if channel_inventory_months > 3.0 else 0.0
            score = max(
                5.0, min(50.0, 45.0 + (pct_inversion * 0.5) - inventory_drag)
            )
        else:
            score = min(
                100.0, 70.0 + (val_price_spread / safe_factory_price) * 100.0
            )

        if score >= 80.0:
            verdict = PricingPowerVerdict.DOMINANT_PRICING_POWER
        elif score >= 40.0:
            verdict = PricingPowerVerdict.CONSTRAINED_BY_MARKET
        else:
            verdict = PricingPowerVerdict.SEVERE_PRICE_DESTRUCTION

        return score, verdict
