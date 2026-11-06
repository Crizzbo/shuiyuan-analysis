"""黄金与宏观贵金属大宗商品深度研究体系 (Gold & Macro Commodity Framework)

功能模块：
1. 【实际利率脱钩与重定价模型 (10Y TIPS Real Rate & Gold Valuation)】：
   - 传统模型：黄金价格与 10Y 美债实际利率 (TIPS) 强负相关；
   - 新常态脱钩模型：纳入主权去美元化 (De-dollarization) 与全球央行购金溢价项，定量求解公允定价中枢。
2. 【全球央行去美元化储备增持雷达 (Central Bank Reserve Dynamics)】：
   - 追踪主要央行 (中国央行 PBOC、印度央行 RBI、土耳其、波兰等) 净购金节奏与全球官方黄金储备占比。
3. 【期现货与跨市场实物溢价 (Physical vs Paper Gold Premium)】：
   - 监控上海黄金交易所 (SGE) 实物黄金较 COMEX 纸黄金期货的现货溢价率 (Basis Spread)。
4. 【特级金矿股营运杠杆与现金流弹性测算 (Gold Miners Operating Leverage)】：
   - 覆盖纽蒙特矿业 (NEM)、巴里克黄金 (GOLD)、阿格尼科鹰 (AEM)；
   - 结合综合全维持成本 (AISC, All-In Sustaining Costs) 测算金价每上涨 $100 对金矿股自由现金流与 EPS 的乘数放大效应。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

from financial_core.engines.cross_asset_engine import (
    CrossAssetValuationEngine,
    GoldValuationFact,
    GoldMinerLeverageFact,
)


@dataclass(frozen=True)
class GoldMacroContext:
    """黄金宏观定价环境快照。"""
    spot_gold_usd_oz: float = 2650.0       # 现货黄金价格 (美元/盎司)
    us_10y_nominal_yield: float = 0.0440   # 10Y 名义美债收益率 (4.40%)
    breakeven_inflation_10y: float = 0.0235# 10Y 通胀保值利差 (2.35%)
    dxy_index: float = 104.2               # 美元指数 DXY
    annual_central_bank_net_tonnes: float = 1050.0 # 全球央行过去 12 个月净购金吨数
    sge_shanghai_premium_usd_oz: float = 28.5      # 上海金对国际金价实物溢价 (美元/盎司)


@dataclass(frozen=True)
class GoldMinerProfile:
    """特级金矿龙头运营参数。"""
    ticker: str
    name_zh: str
    current_price: float
    aisc_per_oz: float          # 综合维持成本 AISC (美元/盎司)
    annual_production_koz: float# 年黄金产量 (千盎司)
    shares_mil: float           # 总股本 (百万股)
    net_debt_mil: float         # 净负债 (百万美元)


STANDARD_GOLD_MINERS: Dict[str, GoldMinerProfile] = {
    "NEM": GoldMinerProfile(
        ticker="NEM",
        name_zh="纽蒙特矿业 (Newmont Corporation)",
        current_price=53.20,
        aisc_per_oz=1440.0,
        annual_production_koz=6700.0,
        shares_mil=1150.0,
        net_debt_mil=5400.0,
    ),
    "GOLD": GoldMinerProfile(
        ticker="GOLD",
        name_zh="巴里克黄金 (Barrick Gold Corporation)",
        current_price=20.45,
        aisc_per_oz=1380.0,
        annual_production_koz=4100.0,
        shares_mil=1750.0,
        net_debt_mil=500.0,
    ),
    "AEM": GoldMinerProfile(
        ticker="AEM",
        name_zh="阿格尼科鹰矿业 (Agnico Eagle Mines Limited)",
        current_price=82.60,
        aisc_per_oz=1190.0,
        annual_production_koz=3450.0,
        shares_mil=495.0,
        net_debt_mil=1200.0,
    ),
    "PAAS": GoldMinerProfile(
        ticker="PAAS",
        name_zh="泛美白银与贵金属 (Pan American Silver Corp.)",
        current_price=22.80,
        aisc_per_oz=1350.0,
        annual_production_koz=900.0,
        shares_mil=365.0,
        net_debt_mil=450.0,
    ),
}


class CommodityGoldFramework:
    """黄金与贵金属大宗商品投研引擎。"""

    @classmethod
    def evaluate_gold_macro_valuation(
        cls,
        ctx: Optional[GoldMacroContext] = None,
    ) -> Dict[str, Any]:
        """评估现货黄金宏观公允估值与三态情景，底层委托至核心量化引擎。"""
        if ctx is None:
            ctx = GoldMacroContext()

        core_fact = CrossAssetValuationEngine.compute_gold_macro_valuation(
            spot_gold_usd=ctx.spot_gold_usd_oz,
            nominal_10y_yield=ctx.us_10y_nominal_yield,
            breakeven_10y=ctx.breakeven_inflation_10y,
            dxy_index=ctx.dxy_index,
            annual_cb_tonnes=ctx.annual_central_bank_net_tonnes,
            sge_premium_usd=ctx.sge_shanghai_premium_usd_oz,
        )

        return {
            "spot_gold_usd": f"${core_fact.spot_gold_usd:,.1f}/oz",
            "tips_10y_real_yield": f"{core_fact.tips_10y_real_yield_pct:.2f}%",
            "breakeven_inflation": f"{core_fact.breakeven_inflation_pct:.2f}%",
            "dxy_index": core_fact.dxy_index,
            "central_bank_net_tonnes": f"{core_fact.central_bank_net_tonnes:,.0f} 吨/年",
            "physical_premium_sge": f"+${core_fact.sge_physical_premium_usd:.2f}/oz (上海金实物溢价)",
            "valuation_models": {
                "traditional_real_yield_anchor": f"${core_fact.traditional_tips_anchor_usd:,.1f}",
                "central_bank_structural_premium": f"+${core_fact.central_bank_premium_usd:,.1f} (+{core_fact.central_bank_premium_pct:.1f}%)",
                "macro_fair_value_center": f"${core_fact.macro_fair_value_usd:,.1f}",
                "current_deviation_pct": f"{core_fact.deviation_pct:+.2f}%",
            },
            "scenarios": {
                "bear_case": f"${core_fact.bear_case_usd:,.1f} (高真实利率强压制)",
                "base_case": f"${core_fact.base_case_usd:,.1f} (央行结构性买盘中枢)",
                "bull_case": f"${core_fact.bull_case_usd:,.1f} (主权信用重定价主升浪)",
            },
            "strategic_verdict_zh": (
                "【战略底仓增配】黄金已由单纯的‘抗通胀/负真实利率工具’升级为‘全球央行去美元化资产负债表第一安全储备’。"
                "尽管短期美债真实利率处于 2.0%+ 历史高位，但金价依托央行刚性净买盘与亚洲实物溢价呈现坚韧抗跌格局，建议保留 5%~10% 作为非对称宏观对冲底仓。"
            )
        }

    @classmethod
    def evaluate_gold_miner_leverage(
        cls,
        miner_ticker: str,
        spot_gold_price: float = 2650.0,
    ) -> Dict[str, Any]:
        """计算特级金矿股相对现货金价的营运现金流放大倍数 (Operating Leverage)，底层委托至核心量化引擎。"""
        if miner_ticker not in STANDARD_GOLD_MINERS:
            raise ValueError(f"未登记的金矿股代码: {miner_ticker}，支持标的: {list(STANDARD_GOLD_MINERS.keys())}")
        m = STANDARD_GOLD_MINERS[miner_ticker]

        core_fact = CrossAssetValuationEngine.compute_gold_miner_leverage(
            ticker=m.ticker,
            current_price=m.current_price,
            aisc_per_oz=m.aisc_per_oz,
            annual_production_koz=m.annual_production_koz,
            shares_mil=m.shares_mil,
            net_debt_mil=m.net_debt_mil,
            spot_gold_price=spot_gold_price,
            valuation_multiple=12.0,
        )

        return {
            "ticker": m.ticker,
            "name_zh": m.name_zh,
            "current_share_price": f"${core_fact.current_price:.2f}",
            "aisc_cost_per_oz": f"${core_fact.aisc_per_oz:.0f}/oz",
            "cash_margin_per_oz": f"${core_fact.cash_margin_per_oz:.0f}/oz (现价利润空间)",
            "operating_leverage_multiplier": f"{core_fact.operating_leverage_multiplier:.2f}x (金价每涨1%，现金利润放大 {core_fact.operating_leverage_multiplier:.2f}%)",
            "annual_fcf_estimate": f"${core_fact.annual_fcf_mil:,.0f} 百万美元",
            "fcf_yield": f"{core_fact.fcf_yield_pct:.2f}%",
            "fair_target_price": f"${core_fact.fair_target_price:.2f}",
            "potential_upside": f"{core_fact.potential_upside_pct:+.2f}%",
            "tactical_view_zh": (
                f"{m.name_zh} 享有行业顶级的低成本优势 (AISC ${m.aisc_per_oz:.0f}/oz)；在当前金价平台下，自由现金流收益率高达 {core_fact.fcf_yield_pct:.1f}%，"
                f"具备典型的营运杠杆放大特性，是享受金价主升浪弹性超越现货黄金的绝佳买方配置工具。"
            )
        }
