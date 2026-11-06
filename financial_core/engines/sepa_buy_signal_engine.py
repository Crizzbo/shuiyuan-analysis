"""米奈尔维尼 SEPA 买入信号与精准价格时机引擎 (Minervini SEPA Timing & Buy Signal Engine).

遵循 Google Python 编程风格指南与《SPEC-07 买方时机决策与技术足迹分析引擎设计书》:
1. 建立 8 大趋势模板 (Trend Template) 硬性门禁与四大生命周期阶段状态机;
2. 建立 VCP (波动收缩形态) 递归收敛判定与技术足迹 (如 '8W 28/2 4T') 自动合成;
3. 建立价格边界解耦模型 (calculate_sepa_price_boundaries):
   - 刚性止损线 (Hard Stop-Loss)、建议精准止损 (Recommended Stop)、
   - 移动保本止损触发价 (Trailing Breakeven at 3R)、
   - 突破追高上限防线 (Extended Chase Limit at +5%)、
   - 目标盈亏比靶心 (Risk-Reward Target at 3:1);
4. 单一事实来源 (SSOT) 状态空间注册表 (SEPA_SIGNAL_STATE_REGISTRY):
   显式记载趋势阶段、VCP 收敛与买入信号状态的数值区间、商业本质直觉与操盘指令;
5. 纯相对导入，无逆向依赖，配置驱动，严禁任何价格常数硬编码。
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from .market_adaptive_params import SepaAdaptiveParams


# ==============================================================================
# 一、 强类型区间状态空间枚举 (State Enums)
# ==============================================================================

class TrendStageState(str, Enum):
    """股票生命周期四大阶段状态 (4 态空间)."""

    STAGE_1_CONSOLIDATION = "Stage_1_Consolidation"   # 第一阶段：忽略筑底横盘期
    STAGE_2_MARKUP = "Stage_2_Markup"                 # 第二阶段：主升突围推进期 (唯一准入阶段)
    STAGE_3_DISTRIBUTION = "Stage_3_Distribution"     # 第三阶段：高位震荡派发期
    STAGE_4_CAPITULATION = "Stage_4_Capitulation"     # 第四阶段：破位衰退投降期


class VcpContractionStatus(str, Enum):
    """VCP 波动收缩形态收敛阶段状态 (4 态空间)."""

    NO_CONTRACTION = "No_Contraction"                 # 未形成收敛：宽幅发散震荡
    LOOSE_SHAPING = "Loose_Shaping"                   # 初步收敛中：回撤幅度偏大 (>15%)
    CONTRACTING = "Contracting"                       # 标准收敛推进：已完成 2T~3T 振幅递减
    TIGHT_PIVOT_READY = "Tight_Pivot_Ready"           # 极度紧密收敛：地量抽干，具备枢轴点突破蓄势


class BuySignalTier(str, Enum):
    """最终买入信号决策分级 (5 态空间)."""

    OUT_OF_TREND = "Out_Of_Trend"                     # 趋势一票否决：未满足第二阶段 8 大硬指标
    WATCHLIST_FORMING = "Watchlist_Forming"           # 重点自选跟踪：在第二阶段但形态收敛未完成
    PIVOT_TRIGGERED = "Pivot_Triggered"               # 立即买入触发：放量突破枢轴买点，胜率赔率最佳
    EXTENDED_OVERBOUGHT = "Extended_Overbought"       # 突破后超买脱轨：已脱离枢轴点 5% 以上，严禁追高
    SQUAT_REVERSAL_WATCH = "Squat_Reversal_Watch"     # 突破后深蹲洗盘：价格轻微回落买点下方但守住止损线与均线，等待逆转恢复


# ==============================================================================
# 二、 单一事实来源状态元数据注册表 (SSOT)
# ==============================================================================

SEPA_SIGNAL_STATE_REGISTRY: Dict[str, Dict[str, Dict[str, Any]]] = {
    "trend_stage": {
        TrendStageState.STAGE_1_CONSOLIDATION.value: {
            "state_id": "TS_01",
            "state_name": "第一阶段忽略筑底期",
            "severity_level": 2,
            "business_intuition_zh": (
                "股价在 200 日线附近长时间横盘整理，机构资金尚未大规模入场，"
                "成交量低迷，死水微澜。"
            ),
            "action_directive_zh": (
                "绝不提前抄底！避免漫长的时间成本消耗，保持观望直至走出确立的上升趋势。"
            ),
        },
        TrendStageState.STAGE_2_MARKUP.value: {
            "state_id": "TS_02",
            "state_name": "第二阶段主升突围期",
            "severity_level": 1,
            "business_intuition_zh": (
                "低点不断抬高、高点不断创新高，长期均线拐头向上，机构吸筹推升，"
                "符合全部 8 项趋势模板硬指标。"
            ),
            "action_directive_zh": (
                "核心重点狙击池！唯一允许做多的主升浪阶段，在此阶段寻找 VCP 收缩与枢轴买点进场。"
            ),
        },
        TrendStageState.STAGE_3_DISTRIBUTION.value: {
            "state_id": "TS_03",
            "state_name": "第三阶段高位派发期",
            "severity_level": 4,
            "business_intuition_zh": (
                "日内与周度波动剧烈放大，成交量屡创巨量但价格滞涨，主力机构正在向散户快速派发出货。"
            ),
            "action_directive_zh": (
                "坚决禁止买入！已持仓者应分批果断止盈，并收紧移动止损保护既得利润。"
            ),
        },
        TrendStageState.STAGE_4_CAPITULATION.value: {
            "state_id": "TS_04",
            "state_name": "第四阶段破位衰退期",
            "severity_level": 5,
            "business_intuition_zh": (
                "均线呈空头排列向下倾斜，支撑位屡屡击穿，弱势资金不断割肉踩踏，处于长期下行通道。"
            ),
            "action_directive_zh": (
                "绝对红线禁区！严禁任何形式的抄底、补仓或摊平成本，反弹即是卖点。"
            ),
        },
    },
    "vcp_status": {
        VcpContractionStatus.NO_CONTRACTION.value: {
            "state_id": "VCP_01",
            "state_name": "宽幅发散未收敛",
            "severity_level": 4,
            "business_intuition_zh": "多空双方分歧巨大，价格大起大落，浮动筹码尚未被清洗沉淀。",
            "action_directive_zh": "不具备可操作性，等待形态自然整理与波动收紧。",
        },
        VcpContractionStatus.LOOSE_SHAPING.value: {
            "state_id": "VCP_02",
            "state_name": "初级宽幅收敛期",
            "severity_level": 3,
            "business_intuition_zh": (
                "价格开始尝试构筑基底，但回调深度依然偏大，解套盘与获利盘抛压仍未充分吸收。"
            ),
            "action_directive_zh": "列入观察池，继续等待第 2 次或第 3 次更浅深度的回撤收窄。",
        },
        VcpContractionStatus.CONTRACTING.value: {
            "state_id": "VCP_03",
            "state_name": "标准阶梯收敛期",
            "severity_level": 2,
            "business_intuition_zh": (
                "回撤幅度呈现标准对半递减，主力机构正在逐级消化供给，浮动筹码逐步被锁仓。"
            ),
            "action_directive_zh": (
                "进入一级准备状态，密切盯盘，锁定最后一次收缩的高点作为潜在枢轴买点。"
            ),
        },
        VcpContractionStatus.TIGHT_PIVOT_READY.value: {
            "state_id": "VCP_04",
            "state_name": "极度紧密地量临界点",
            "severity_level": 1,
            "business_intuition_zh": (
                "振幅收窄至极限（通常 ≤ 5%），成交量降至均量的一半以下出现极度地量，"
                "市面上可抛浮筹被彻底抽干！"
            ),
            "action_directive_zh": (
                "蓄势待发临界点！设置到价警报，一旦放量越过枢轴点即可瞬间开火买入。"
            ),
        },
    },
    "buy_signal": {
        BuySignalTier.OUT_OF_TREND.value: {
            "state_id": "SIG_01",
            "state_name": "趋势一票否决",
            "severity_level": 4,
            "business_intuition_zh": (
                "股票未处于第二阶段上升趋势中，违反趋势模板基本法，逆风交易胜率极低。"
            ),
            "action_directive_zh": "一票否决，移出交易计划，不执行买入动作。",
        },
        BuySignalTier.WATCHLIST_FORMING.value: {
            "state_id": "SIG_02",
            "state_name": "重点自选跟踪",
            "severity_level": 2,
            "business_intuition_zh": (
                "处于健康的第二阶段上升大趋势，正在经历基底整理，尚未出现阻力最小的击球点。"
            ),
            "action_directive_zh": (
                "保持耐心等待，绝不提前潜伏，让市场自行完成筹码换手与地量收敛。"
            ),
        },
        BuySignalTier.PIVOT_TRIGGERED.value: {
            "state_id": "SIG_03",
            "state_name": "枢轴买点立即触发",
            "severity_level": 1,
            "business_intuition_zh": (
                "第二阶段主升浪确立，VCP 经历多轮收敛吸收，地量抽干后主力大单放量突破最后的阻力线！"
            ),
            "action_directive_zh": (
                "果断击球买入！建立 30%~40% 试探性第一底仓，盘前强制挂好绝对止损单，浮盈前严禁加仓。"
            ),
        },
        BuySignalTier.EXTENDED_OVERBOUGHT.value: {
            "state_id": "SIG_04",
            "state_name": "突破后超买脱轨",
            "severity_level": 3,
            "business_intuition_zh": (
                "当前股价已脱离枢轴点超过 5%，追高将大幅恶化风险收益比，极易遭遇突破后的正常回踩洗盘。"
            ),
            "action_directive_zh": (
                "严禁追高！错过买点绝不心急，等待下一次缩量回踩 20 日/50 日线企稳或构筑新次级基底。"
            ),
        },
        BuySignalTier.SQUAT_REVERSAL_WATCH.value: {
            "state_id": "SIG_05",
            "state_name": "突破后深蹲洗盘观察",
            "severity_level": 2,
            "business_intuition_zh": (
                "放量尝试突破后受市场扰动轻微回踩买点下方，但坚决守在止损线和 20/50 日均线上方，"
                "且成交量显著萎缩，属于主力深蹲洗盘 (Squat)。"
            ),
            "action_directive_zh": (
                "【深蹲洗盘保护】给予 1~2 天耐心观察期，守住止损底线坚决不割肉！"
                "一旦成交量重新放大并逆转收复买点，可再次加仓。"
            ),
        },
    },
}


def get_sepa_state_metadata(domain_key: str, state_value: Union[str, Enum]) -> Dict[str, Any]:
    """统一查询 SEPA 状态元数据 (SSOT).

    Args:
        domain_key: 状态所属业务域 ('trend_stage', 'vcp_status', 'buy_signal').
        state_value: 具体的枚举值或字符串代号.

    Returns:
        包含 state_id, state_name, severity_level, business_intuition_zh,
        action_directive_zh 等全息字典.
    """
    raw_val = state_value.value if isinstance(state_value, Enum) else str(state_value)
    domain = SEPA_SIGNAL_STATE_REGISTRY.get(domain_key, {})
    meta = domain.get(raw_val)
    if meta:
        return {"domain_key": domain_key, "state_key": raw_val, **meta}
    return {
        "domain_key": domain_key,
        "state_key": raw_val,
        "state_id": "UNKNOWN",
        "state_name": "未收录状态",
        "severity_level": 0,
        "business_intuition_zh": "未定义状态",
        "action_directive_zh": "谨慎核对数据源",
    }


# ==============================================================================
# 三、 价格边界与输入契约 (Price Boundaries & Input Contracts)
# ==============================================================================

@dataclass(frozen=True)
class SepaPriceBoundaries:
    """价格解耦计算契约 (完全配置驱动，消除任何硬编码价格数字).

    Attributes:
        val_pivot_price: 枢轴买点价格基准 (美分级).
        val_stop_loss_price: 刚性最大不可逾越止损价 (美分级).
        val_recommended_stop_price: 建议常态精准止损价 (美分级).
        val_risk_unit_usd: 单股风险敞口 (R = pivot - stop_loss).
        val_breakeven_trigger_price: 移动保本止损触发价 (浮盈达 3R 时上调止损至买入成本价).
        val_extended_limit_price: 追高脱轨超买上限价 (突破点 + 5%).
        val_target_profit_price: 目标基准止盈靶心 (3:1 盈亏比对应目标价).
        pct_hard_stop_loss: 刚性硬止损百分比 (如 7.0%).
        pct_recommended_stop_loss: 推荐止损百分比 (如 5.0%).
        pct_current_to_pivot: 当前现价距枢轴买点溢价百分比.
        is_within_buy_range: 现价是否处于 [pivot_price, extended_limit_price] 黄金击球区间内.
        currency_symbol: 货币符号 ('$', '¥').
    """

    val_pivot_price: float
    val_stop_loss_price: float
    val_recommended_stop_price: float
    val_risk_unit_usd: float
    val_breakeven_trigger_price: float
    val_extended_limit_price: float
    val_target_profit_price: float
    pct_hard_stop_loss: float
    pct_recommended_stop_loss: float
    pct_current_to_pivot: float
    is_within_buy_range: bool
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方研报呈现字典."""
        curr = self.currency_symbol or "$"
        return {
            "pivot_price": f"{curr}{self.val_pivot_price:.2f}",
            "hard_stop_loss_price": f"{curr}{self.val_stop_loss_price:.2f}",
            "recommended_stop_price": f"{curr}{self.val_recommended_stop_price:.2f}",
            "risk_unit_usd": f"{curr}{self.val_risk_unit_usd:.2f}",
            "breakeven_trigger_price": f"{curr}{self.val_breakeven_trigger_price:.2f}",
            "extended_limit_price": f"{curr}{self.val_extended_limit_price:.2f}",
            "target_profit_price": f"{curr}{self.val_target_profit_price:.2f}",
            "hard_stop_loss_pct": f"{self.pct_hard_stop_loss:.2f}%",
            "recommended_stop_loss_pct": f"{self.pct_recommended_stop_loss:.2f}%",
            "current_to_pivot_pct": f"{self.pct_current_to_pivot:+.2f}%",
            "is_within_buy_range": self.is_within_buy_range,
            "currency_symbol": curr,
        }


@dataclass(frozen=True)
class SepaInputFacts:
    """SEPA 输入数据契约 (全息时效价量与微观财务事实).

    Attributes:
        ticker: 标的代码 (如 'NVDA', '7203.T').
        val_current_price: 最新核验现价.
        val_ma_50: 50 日移动平均线.
        val_ma_150: 150 日移动平均线.
        val_ma_200: 200 日移动平均线.
        val_ma_200_20d_ago: 20 个交易日前的 200 日线 (用于断言倾斜斜率).
        val_low_52w: 52 周最低价.
        val_high_52w: 52 周最高价.
        num_rs_rank: 相对强度评分 (0~100).
        val_pivot_price: 枢轴点价格 (最后一次收敛高点).
        pct_recent_contractions: 历次回撤幅度序列 (如 [28.0, 14.0, 6.0, 2.5]).
        days_base_duration: 基底整理持续总天数.
        num_current_volume: 今日当前成交量.
        num_avg_volume_50d: 50 日日均成交量.
        num_dryup_volume_min: 收敛整理期间最低单日成交量.
        is_eps_accelerating_3q: 连续 3 季度每股收益加速 (默认 True).
        is_sales_accelerating_3q: 连续 3 季度销售营收加速 (默认 True).
        has_positive_surprise: 业绩公布超分析师预期 (默认 True).
        market: 交易市场 ('US', 'JP', 'CN'，未指定时自适应推导).
        currency_symbol: 显式货币符号 (未指定时自适应推导).
    """

    ticker: str
    val_current_price: float
    val_ma_50: float
    val_ma_150: float
    val_ma_200: float
    val_ma_200_20d_ago: float
    val_low_52w: float
    val_high_52w: float
    num_rs_rank: float
    val_pivot_price: float

    # VCP 与成交量微观穿透
    pct_recent_contractions: List[float]
    days_base_duration: int
    num_current_volume: float
    num_avg_volume_50d: float
    num_dryup_volume_min: float

    # 基本面动能 (默认通过)
    is_eps_accelerating_3q: bool = True
    is_sales_accelerating_3q: bool = True
    has_positive_surprise: bool = True
    market: Optional[str] = None
    currency_symbol: Optional[str] = None


@dataclass(frozen=True)
class SepaBuySignalResult:
    """SEPA 买入信号与风控决策输出全息契约.

    Attributes:
        ticker: 标的代码.
        val_current_price: 最新基准现价.
        status_trend_stage: 趋势生命周期阶段代号.
        status_vcp_contraction: VCP 收缩状态代号.
        status_buy_signal: 顶层买入决策代号.
        is_trend_template_passed: 8 大趋势模板是否全票通过.
        trend_criteria_checks: 8 项指标具体核验布尔字典.
        technical_footprint_code: 米奈尔维尼经典记号 (例如: '8W 28/2 4T').
        cnt_contractions: 回撤收敛总轮数 T.
        is_volume_dryup_confirmed: 浮动筹码是否证实抽干.
        is_breakout_volume_confirmed: 突破成交量是否达标放量.
        is_squat_holding: 是否处于突破后深蹲回踩蓄势保护期 (Squat).
        price_boundaries: 价格边界契约对象.
        directive_action_zh: 投资决策建议指令.
        meta_trend_stage: 趋势阶段状态元数据.
        meta_vcp_status: VCP 状态元数据.
        meta_buy_signal: 买入信号状态元数据.
        narrative_zh: 买方通俗商业直觉全息研报卡片.
        status_trend_stage_zh: 趋势生命周期通俗中文语义.
        status_vcp_contraction_zh: VCP 收缩形态通俗中文语义.
        status_buy_signal_zh: 最终信号决策通俗中文语义.
        currency_symbol: 货币符号 ('$', '¥').
    """

    ticker: str
    val_current_price: float
    status_trend_stage: str
    status_vcp_contraction: str
    status_buy_signal: str
    is_trend_template_passed: bool
    trend_criteria_checks: Dict[str, bool]
    technical_footprint_code: str
    cnt_contractions: int
    is_volume_dryup_confirmed: bool
    is_breakout_volume_confirmed: bool
    is_squat_holding: bool
    price_boundaries: SepaPriceBoundaries
    directive_action_zh: str
    meta_trend_stage: Dict[str, Any]
    meta_vcp_status: Dict[str, Any]
    meta_buy_signal: Dict[str, Any]
    narrative_zh: str = ""
    status_trend_stage_zh: str = ""
    status_vcp_contraction_zh: str = ""
    status_buy_signal_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化输出契约."""
        curr = self.currency_symbol or "$"
        return {
            "ticker": self.ticker,
            "current_price": f"{curr}{self.val_current_price:.2f}",
            "trend_stage": self.status_trend_stage,
            "trend_stage_zh": self.status_trend_stage_zh or self.status_trend_stage,
            "vcp_contraction": self.status_vcp_contraction,
            "vcp_contraction_zh": self.status_vcp_contraction_zh or self.status_vcp_contraction,
            "buy_signal": self.status_buy_signal,
            "buy_signal_zh": self.status_buy_signal_zh or self.status_buy_signal,
            "technical_footprint": self.technical_footprint_code,
            "contractions_count": self.cnt_contractions,
            "is_volume_dryup": self.is_volume_dryup_confirmed,
            "is_breakout_volume": self.is_breakout_volume_confirmed,
            "is_squat_holding": self.is_squat_holding,
            "price_boundaries": self.price_boundaries.to_dict(),
            "directive_action": self.directive_action_zh,
            "narrative_zh": self.narrative_zh,
            "currency_symbol": curr,
        }


# ==============================================================================
# 四、 核心引擎实现 (SepaBuySignalEngine)
# ==============================================================================

class SepaBuySignalEngine:
    """米奈尔维尼 SEPA 买方时机与买入信号引擎 (Google Python Style Guide 架构设计)."""

    def __init__(self, adaptive_params: Optional[SepaAdaptiveParams] = None) -> None:
        """初始化 SEPA 买入信号引擎.

        Args:
            adaptive_params: 市场自适应参数配置对象 (留空则使用默认基准配置).
        """
        self.version = "1.0.0"
        self.adaptive_params = adaptive_params or SepaAdaptiveParams()

    def calculate_sepa_price_boundaries(
        self,
        val_pivot_price: float,
        val_current_price: float,
        params: Optional[SepaAdaptiveParams] = None,
        currency_symbol: str = "$",
    ) -> SepaPriceBoundaries:
        """纯数学计算：基于自适应配置计算解耦的价格边界与风控防线.

        Args:
            val_pivot_price: 枢轴买点价格基准 (美分级).
            val_current_price: 当前股票最新核验报价.
            params: 专属参数配置 (留空则采用引擎默认自适应参数).
            currency_symbol: 货币符号 ('$', '¥').

        Returns:
            SepaPriceBoundaries 结构化价格防线对象.

        Raises:
            ValueError: 当枢轴价格 <= 0 或现价 < 0 时抛出 (金融数学与有限责任防御).
        """
        if val_pivot_price <= 0.0:
            raise ValueError(
                f"【金融数学防御】枢轴买点价格必须大于0，收到非法值: {val_pivot_price}"
            )
        if val_current_price < 0.0:
            raise ValueError(
                f"【有限责任下界】当前股价不可为负，收到非法值: {val_current_price}"
            )

        cfg = params or self.adaptive_params

        # 1. 刚性与建议止损价
        val_stop_loss_price = round(val_pivot_price * (1.0 - cfg.pct_max_hard_stop_loss), 2)
        val_recommended_stop_price = round(
            val_pivot_price * (1.0 - cfg.pct_recommended_stop_loss), 2
        )

        # 2. 单股基准风险敞口 R (设置 0.01 下界防御，杜绝 R=0 导致盈亏比靶心失效)
        val_risk_unit_usd = max(0.01, round(val_pivot_price - val_stop_loss_price, 2))

        # 3. 移动保本止损触发价 (浮盈达 3R 时触发)
        val_breakeven_trigger_price = round(
            val_pivot_price + cfg.ratio_breakeven_trailing_r * val_risk_unit_usd, 2
        )

        # 4. 追高脱轨超买上限价 (突破点 + 5%)
        val_extended_limit_price = round(
            val_pivot_price * (1.0 + cfg.pct_extended_chase_limit), 2
        )

        # 5. 目标止盈靶心 (3:1 盈亏比)
        val_target_profit_price = round(
            val_pivot_price + cfg.ratio_target_risk_reward * val_risk_unit_usd, 2
        )

        # 6. 当前溢价与击球区间核验
        pct_current_to_pivot = round(
            ((val_current_price - val_pivot_price) / max(0.01, val_pivot_price)) * 100.0, 2
        )
        is_within_buy_range = val_pivot_price <= val_current_price <= val_extended_limit_price

        return SepaPriceBoundaries(
            val_pivot_price=round(val_pivot_price, 2),
            val_stop_loss_price=val_stop_loss_price,
            val_recommended_stop_price=val_recommended_stop_price,
            val_risk_unit_usd=val_risk_unit_usd,
            val_breakeven_trigger_price=val_breakeven_trigger_price,
            val_extended_limit_price=val_extended_limit_price,
            val_target_profit_price=val_target_profit_price,
            pct_hard_stop_loss=round(cfg.pct_max_hard_stop_loss * 100.0, 2),
            pct_recommended_stop_loss=round(cfg.pct_recommended_stop_loss * 100.0, 2),
            pct_current_to_pivot=pct_current_to_pivot,
            is_within_buy_range=is_within_buy_range,
            currency_symbol=currency_symbol,
        )

    def diagnose_trend_stage(
        self,
        facts: SepaInputFacts,
        params: Optional[SepaAdaptiveParams] = None,
    ) -> Dict[str, Any]:
        """诊断股票生命周期阶段并核验 8 大趋势模板硬指标 (全票否决制).

        Args:
            facts: SEPA 全息输入事实数据契约.
            params: 专属参数配置 (留空则采用引擎默认自适应参数).

        Returns:
            包含 'trend_stage', 'is_trend_template_passed', 'checks', 'metadata' 的字典.
        """
        cfg = params or self.adaptive_params
        checks = self._check_trend_template_criteria(facts, cfg)
        is_all_passed = all(checks.values())
        stage_state = self._classify_trend_stage(facts, is_all_passed)

        return {
            "trend_stage": stage_state,
            "is_trend_template_passed": is_all_passed,
            "checks": checks,
            "metadata": get_sepa_state_metadata("trend_stage", stage_state),
        }

    def diagnose_vcp_pattern(
        self,
        facts: SepaInputFacts,
        params: Optional[SepaAdaptiveParams] = None,
    ) -> Dict[str, Any]:
        """诊断 VCP 波动收缩形态与筹码地量抽干 (生成经典技术足迹).

        Args:
            facts: SEPA 全息输入事实数据契约.
            params: 专属参数配置 (留空则采用引擎默认自适应参数).

        Returns:
            包含 'vcp_status', 'footprint_code', 'cnt_contractions',
            'is_volume_dryup_confirmed', 'metadata' 的字典.
        """
        cfg = params or self.adaptive_params
        # 清洗收缩序列：取绝对值并设置微小正数下界，杜绝负数怪异足迹 (如 -5% 回调)
        contractions = [max(0.1, abs(c)) for c in facts.pct_recent_contractions]
        cnt_contractions = len(contractions)

        if cnt_contractions == 0:
            status = VcpContractionStatus.NO_CONTRACTION
            footprint = "0W 0/0 0T"
            is_dryup = False
        else:
            footprint = self._build_vcp_footprint(facts, contractions, cnt_contractions)

            # 检查收缩递减性
            is_decaying = True
            for i in range(1, cnt_contractions):
                if contractions[i] > (contractions[i - 1] * cfg.ratio_contraction_decay_max):
                    is_decaying = False
                    break

            # 检查地量抽干 (增加日均成交量防除零除负防御)
            safe_avg_vol = max(1.0, facts.num_avg_volume_50d)
            is_dryup = (
                facts.num_dryup_volume_min > 0.0
                and facts.num_dryup_volume_min <= (safe_avg_vol * cfg.ratio_dryup_volume_max)
            )

            # 最终收缩紧致度
            final_depth = round(contractions[-1], 1)
            is_tight = final_depth <= (cfg.pct_vcp_tight_threshold * 100.0)

            if cnt_contractions >= 2 and is_decaying and is_tight and is_dryup:
                status = VcpContractionStatus.TIGHT_PIVOT_READY
            elif cnt_contractions >= 2 and is_decaying:
                status = VcpContractionStatus.CONTRACTING
            elif contractions[0] > 15.0:
                status = VcpContractionStatus.LOOSE_SHAPING
            else:
                status = VcpContractionStatus.NO_CONTRACTION

        return {
            "vcp_status": status,
            "footprint_code": footprint,
            "cnt_contractions": cnt_contractions,
            "is_volume_dryup_confirmed": is_dryup,
            "metadata": get_sepa_state_metadata("vcp_status", status),
        }

    def evaluate_buy_signal(
        self,
        facts: SepaInputFacts,
        params: Optional[SepaAdaptiveParams] = None,
    ) -> SepaBuySignalResult:
        """顶层研判：综合趋势、VCP、价格边界与成交量突破，输出买入决策全息卡片.

        Args:
            facts: SEPA 全息输入事实数据契约.
            params: 专属参数配置 (留空则采用引擎默认自适应参数).

        Returns:
            SepaBuySignalResult 包含趋势、形态、买点、风控防线与研报卡片的全息输出对象.
        """
        cfg = params or self.adaptive_params
        curr_sym = self._resolve_currency_symbol(facts)

        # 1. 价格边界解耦计算
        boundaries = self.calculate_sepa_price_boundaries(
            val_pivot_price=facts.val_pivot_price,
            val_current_price=facts.val_current_price,
            params=cfg,
            currency_symbol=curr_sym,
        )

        # 2. 趋势模板诊断
        trend_diag = self.diagnose_trend_stage(facts, params=cfg)
        is_stage_2 = trend_diag["trend_stage"] == TrendStageState.STAGE_2_MARKUP

        # 3. VCP 收缩诊断
        vcp_diag = self.diagnose_vcp_pattern(facts, params=cfg)

        # 4. 成交量放量突破断言 (除零除负防御)
        safe_avg_vol = max(1.0, facts.num_avg_volume_50d)
        is_breakout_volume = (
            facts.num_current_volume >= (safe_avg_vol * cfg.ratio_volume_breakout_surge)
        )

        # 5. 买入信号状态机推演
        signal_tier, is_squat = self._determine_buy_signal_tier(
            facts=facts,
            boundaries=boundaries,
            is_stage_2=is_stage_2,
            vcp_status=vcp_diag["vcp_status"],
            is_breakout_volume=is_breakout_volume,
            safe_avg_vol=safe_avg_vol,
        )

        signal_meta = get_sepa_state_metadata("buy_signal", signal_tier)

        # 6. 生成买方通俗商业直觉全息研报卡片
        stage_name_zh = trend_diag["metadata"].get("state_name", "趋势观察期")
        vcp_name_zh = vcp_diag["metadata"].get("state_name", "形态构筑中")
        signal_name_zh = signal_meta.get("state_name", "信号跟踪")

        narrative_zh = self._format_timing_narrative(
            facts=facts,
            boundaries=boundaries,
            vcp_diag=vcp_diag,
            signal_tier=signal_tier,
            signal_meta=signal_meta,
            stage_name_zh=stage_name_zh,
            vcp_name_zh=vcp_name_zh,
            signal_name_zh=signal_name_zh,
            curr_sym=curr_sym,
        )

        return SepaBuySignalResult(
            ticker=facts.ticker,
            val_current_price=round(facts.val_current_price, 2),
            status_trend_stage=trend_diag["trend_stage"].value,
            status_vcp_contraction=vcp_diag["vcp_status"].value,
            status_buy_signal=signal_tier.value,
            is_trend_template_passed=trend_diag["is_trend_template_passed"],
            trend_criteria_checks=trend_diag["checks"],
            technical_footprint_code=vcp_diag["footprint_code"],
            cnt_contractions=vcp_diag["cnt_contractions"],
            is_volume_dryup_confirmed=vcp_diag["is_volume_dryup_confirmed"],
            is_breakout_volume_confirmed=is_breakout_volume,
            is_squat_holding=is_squat,
            price_boundaries=boundaries,
            directive_action_zh=signal_meta.get("action_directive_zh", ""),
            meta_trend_stage=trend_diag["metadata"],
            meta_vcp_status=vcp_diag["metadata"],
            meta_buy_signal=signal_meta,
            narrative_zh=narrative_zh,
            status_trend_stage_zh=stage_name_zh,
            status_vcp_contraction_zh=vcp_name_zh,
            status_buy_signal_zh=signal_name_zh,
            currency_symbol=curr_sym,
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helper Methods, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _resolve_currency_symbol(facts: SepaInputFacts) -> str:
        """根据标的代码和市场推断货币符号 (私有辅助方法)."""
        t_up = (facts.ticker or "").upper()
        m_up = (facts.market or "").upper()
        is_jp = (
            m_up == "JP"
            or t_up.endswith(".T")
            or t_up.endswith(".JP")
            or (t_up.isdigit() and len(t_up) == 4)
        )
        is_cn = (
            m_up == "CN"
            or t_up.endswith(".SS")
            or t_up.endswith(".SZ")
            or (t_up.isdigit() and len(t_up) == 6)
        )
        if facts.currency_symbol:
            return facts.currency_symbol
        if is_jp or is_cn:
            return "¥"
        return "$"

    @staticmethod
    def _check_trend_template_criteria(
        facts: SepaInputFacts, cfg: SepaAdaptiveParams
    ) -> Dict[str, bool]:
        """核查 8 项趋势模板硬性标准 (私有辅助方法)."""
        check_1 = (facts.val_current_price > facts.val_ma_150) and (
            facts.val_current_price > facts.val_ma_200
        )
        check_2 = facts.val_ma_150 > facts.val_ma_200
        check_3 = facts.val_ma_200 > facts.val_ma_200_20d_ago
        check_4 = (facts.val_ma_50 > facts.val_ma_150) and (
            facts.val_ma_50 > facts.val_ma_200
        )
        check_5 = facts.val_current_price > facts.val_ma_50
        pct_gain_from_low = (facts.val_current_price - facts.val_low_52w) / max(
            0.01, facts.val_low_52w
        )
        check_6 = pct_gain_from_low >= cfg.pct_min_gain_from_52w_low
        pct_pullback_from_high = (facts.val_high_52w - facts.val_current_price) / max(
            0.01, facts.val_high_52w
        )
        check_7 = pct_pullback_from_high <= cfg.pct_max_pullback_from_52w_high
        check_8 = facts.num_rs_rank >= cfg.num_min_rs_rank

        return {
            "1_price_above_150d_and_200d": check_1,
            "2_150d_above_200d": check_2,
            "3_200d_trending_up_1month": check_3,
            "4_50d_above_150d_and_200d": check_4,
            "5_price_above_50d": check_5,
            "6_price_up_at_least_30pct_from_52w_low": check_6,
            "7_price_within_25pct_of_52w_high": check_7,
            "8_rs_rank_above_threshold": check_8,
        }

    @staticmethod
    def _classify_trend_stage(facts: SepaInputFacts, is_all_passed: bool) -> TrendStageState:
        """根据均线系统与硬指标判定生命周期阶段 (私有辅助方法)."""
        if is_all_passed:
            return TrendStageState.STAGE_2_MARKUP
        if facts.val_current_price < facts.val_ma_200 and facts.val_ma_50 < facts.val_ma_200:
            return TrendStageState.STAGE_4_CAPITULATION
        if (
            facts.val_current_price < facts.val_ma_50
            and facts.val_ma_200 <= facts.val_ma_200_20d_ago
        ):
            return TrendStageState.STAGE_3_DISTRIBUTION
        return TrendStageState.STAGE_1_CONSOLIDATION

    @staticmethod
    def _build_vcp_footprint(
        facts: SepaInputFacts, contractions: List[float], cnt: int
    ) -> str:
        """合成米奈尔维尼经典记号如 '8W 28/2 4T' (私有辅助方法)."""
        weeks_duration = max(1, round(facts.days_base_duration / 7.0))
        max_depth = round(contractions[0], 0)
        final_depth = round(contractions[-1], 1)
        return f"{weeks_duration}W {int(max_depth)}/{final_depth} {cnt}T"

    @staticmethod
    def _determine_buy_signal_tier(
        facts: SepaInputFacts,
        boundaries: SepaPriceBoundaries,
        is_stage_2: bool,
        vcp_status: VcpContractionStatus,
        is_breakout_volume: bool,
        safe_avg_vol: float,
    ) -> Tuple[BuySignalTier, bool]:
        """买入信号决策状态机判定 (私有辅助方法)."""
        if not is_stage_2:
            return BuySignalTier.OUT_OF_TREND, False

        if facts.val_current_price > boundaries.val_extended_limit_price:
            return BuySignalTier.EXTENDED_OVERBOUGHT, False

        valid_vcp_statuses = (
            VcpContractionStatus.TIGHT_PIVOT_READY,
            VcpContractionStatus.CONTRACTING,
        )
        if (
            boundaries.is_within_buy_range
            and facts.val_current_price >= facts.val_pivot_price
            and is_breakout_volume
            and vcp_status in valid_vcp_statuses
        ):
            return BuySignalTier.PIVOT_TRIGGERED, False

        if (
            is_stage_2
            and (boundaries.val_stop_loss_price <= facts.val_current_price < facts.val_pivot_price)
            and (facts.val_current_price >= facts.val_ma_50)
            and (facts.num_current_volume <= safe_avg_vol * 1.20)
            and vcp_status in valid_vcp_statuses
        ):
            return BuySignalTier.SQUAT_REVERSAL_WATCH, True

        return BuySignalTier.WATCHLIST_FORMING, False

    @staticmethod
    def _format_timing_narrative(
        facts: SepaInputFacts,
        boundaries: SepaPriceBoundaries,
        vcp_diag: Dict[str, Any],
        signal_tier: BuySignalTier,
        signal_meta: Dict[str, Any],
        stage_name_zh: str,
        vcp_name_zh: str,
        signal_name_zh: str,
        curr_sym: str,
    ) -> str:
        """格式化买方商业直觉全息研报卡片文字 (私有辅助方法)."""
        if signal_tier == BuySignalTier.PIVOT_TRIGGERED:
            timing_zh = (
                f"当前现价 {curr_sym}{facts.val_current_price:.2f} 处于枢轴买点 "
                f"{curr_sym}{boundaries.val_pivot_price:.2f} 至追高上限 "
                f"{curr_sym}{boundaries.val_extended_limit_price:.2f} 的黄金击球区间内，"
                f"放量突破得到确证！"
            )
            risk_control_zh = (
                f"风控红线：刚性止损线为 {curr_sym}{boundaries.val_stop_loss_price:.2f} "
                f"(单股风险敞口 {curr_sym}{boundaries.val_risk_unit_usd:.2f})；"
                f"3R 移动保本触发价为 {curr_sym}{boundaries.val_breakeven_trigger_price:.2f}；"
                f"目标止盈靶心指向 {curr_sym}{boundaries.val_target_profit_price:.2f} (盈亏比 3:1)。"
            )
        elif signal_tier == BuySignalTier.EXTENDED_OVERBOUGHT:
            timing_zh = (
                f"当前现价 {curr_sym}{facts.val_current_price:.2f} 已脱离枢轴点超过 5% "
                f"(追高上限 {curr_sym}{boundaries.val_extended_limit_price:.2f})，"
                f"处于严重超买脱轨状态，严禁在当前价位盲目追高！"
            )
            risk_control_zh = "建议保持耐心，等待缩量回踩 20/50 日均线企稳后再行寻机建仓。"
        elif signal_tier == BuySignalTier.SQUAT_REVERSAL_WATCH:
            timing_zh = (
                f"股价突破后受大盘扰动轻微回踩买点下方至 {curr_sym}{facts.val_current_price:.2f}，"
                f"但仍显著高于 50日均线 {curr_sym}{facts.val_ma_50:.2f} 与刚性止损线 "
                f"{curr_sym}{boundaries.val_stop_loss_price:.2f}，且成交量缩量，属于典型主力深蹲洗盘。"
            )
            risk_control_zh = "操盘指令：坚决守住止损底线不割肉，一旦成交量重新放大收复买点即可恢复仓位。"
        else:
            timing_zh = (
                f"标的处于【{stage_name_zh}】，形态属于【{vcp_name_zh}】"
                f"(足迹 {vcp_diag['footprint_code']})，"
                f"距离理想枢轴买点 {curr_sym}{boundaries.val_pivot_price:.2f} 尚需时间整理沉淀。"
            )
            risk_control_zh = f"建议指令：{signal_meta.get('action_directive_zh', '')}"

        return (
            f"【标的 {facts.ticker} SEPA 精准时机研判】生命周期所处【{stage_name_zh}】，"
            f"VCP 收敛形态呈【{vcp_name_zh}】(技术足迹: {vcp_diag['footprint_code']})，"
            f"顶层买入信号判定为【{signal_name_zh}】。{timing_zh} {risk_control_zh}"
        )
