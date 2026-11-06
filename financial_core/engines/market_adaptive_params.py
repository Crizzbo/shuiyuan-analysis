"""金融核心层离线市场自适应参数注册中心 (Market-Adaptive Parameters Registry).

物理架构定界 (Layer 1: financial_core):
- 纯净底层数据契约与配置注册中心，零外层依赖;
- 纯相对导入与标准库依赖 (dataclasses, json, pathlib, typing);
- 承担黄金宏观去美元化溢价、跨资产宏观冲击踩踏幂律、微观三表增加值动态经营杠杆 (DOL) 的参数管理;
- 自带零 I/O 内存基准默认值，在无配置文件或测试隔离环境下 100% 安全降级回退。
"""

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Dict, Any, Optional

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class GoldValuationAdaptiveParams:
    """央行购金去美元化溢价与黄金 TIPS 定价自适应参数 (基于 WGC / IMF 离线披露)."""
    baseline_cb_tonnes: float = 500.0          # 常态化央行年化购金基准吨数 (超额部分视为去美元化增持)
    cb_tonnes_step: float = 500.0              # 溢价递增阶梯单位吨数
    cb_premium_step_pct: float = 0.15          # 每递增一个阶梯带来的结构性估值溢价 (默认 15%)
    cb_max_premium_cap: float = 0.30           # 央行溢价封顶上限 (默认 30%)
    tips_sensitivity: float = 8.5              # TIPS 真实利率弹性乘数
    tips_pivot_yield: float = 0.0150           # TIPS 零偏离基准中枢真实利率 (1.50%)
    tips_base_price: float = 2250.0            # TIPS 基准价格锚 ($2,250/oz)
    bear_floor_usd: float = 2150.0             # 悲观防线保底价格 ($2,150/oz)
    bull_multiplier: float = 1.20              # 乐观靶心扩张倍率 (1.20x)
    data_source: str = "World_Gold_Council_Official_Reserve_Statistics_IMF_IFS"


@dataclass
class MacroShockAdaptiveParams:
    """宏观冲击与跨市场压力扩散自适应参数 (基于美联储 H.4.1 / 美债收益率离线披露)."""
    stampede_power_exponent: float = 1.2       # 踩踏收敛非线性幂律指数 (默认 1.2)
    base_correlation: float = 0.40             # 正常市场跨资产基础相关系数 (默认 0.40)
    max_correlation: float = 0.95              # 极端危机时跨资产相关性收敛上限 (默认 0.95)
    debt_leverage_multiplier: float = 0.5      # 债务杠杆信用利差放大敏感系数 (默认 0.5)
    rf_benchmark_yield: float = 0.040          # 10年期美债中枢无风险利率基准 (默认 4.0%)
    rf_drift_passthrough: float = 0.6          # 美债基准偏离向个股 WACC 传导系数 (默认 0.6)
    liquidity_drain_base_billion: float = 50.0 # 联储流动性抽水基数 (默认 500 亿美元)
    liquidity_drain_spread_bps: float = 15.0   # 基础抽水引发的流动性利差加点 (默认 15 bps)
    carry_trade_spread_bps_max: float = 80.0   # 套息平仓极端流动性利差上限 (默认 80 bps)
    carry_trade_trigger_score: float = 50.0    # 触发套息平仓警报阈值分 (默认 50 分)
    vix_baseline: float = 15.0                 # VIX 恐慌基线
    vix_span: float = 25.0                     # VIX 恐慌区间跨度
    fx_jpy_threshold: float = 0.03             # 日元单日汇率异动极端阈值 (3.0%)
    valuation_terminal_g: float = 0.02         # 估值久期冲击假定增长率 (2.0%)
    data_source: str = "Federal_Reserve_H41_FRED_US_Treasury_Quarterly"


@dataclass
class FirmValueAddedAdaptiveParams:
    """企业微观增加值映射与经营杠杆自适应参数 (基于 BEA / SNA / SEC 10-K 披露)."""
    default_operating_leverage_dol: float = 1.05  # 默认经营杠杆放大倍率 (DOL)
    default_fcf_leverage: float = 1.10            # 默认自由现金流扩张杠杆
    default_wage_elasticity: float = 0.95         # 默认劳动报酬要素分配弹性
    default_tax_elasticity: float = 1.05          # 默认生产税与所得税要素分配弹性
    enable_dynamic_dol_estimation: bool = True    # 是否开启基于微观三表成本结构的动态 DOL 测算
    enforce_accounting_identity_closure: bool = True # 是否刚性执行分配法恒等式闭环平账
    sector_dol_map: Dict[str, float] = field(default_factory=lambda: {
        "TECH_SEMI": 1.30,
        "TECH_HARDWARE": 1.25,
        "SOFTWARE": 1.35,
        "LIQUOR_CONSUMER": 1.08,
        "HEALTH_CARE": 1.15,
        "ENERGY": 1.20,
        "UTILITIES": 1.02,
        "GENERAL": 1.05,
    })
    sector_fcf_leverage_map: Dict[str, float] = field(default_factory=lambda: {
        "TECH_SEMI": 1.25,
        "TECH_HARDWARE": 1.18,
        "SOFTWARE": 1.28,
        "LIQUOR_CONSUMER": 1.10,
        "HEALTH_CARE": 1.15,
        "ENERGY": 1.22,
        "UTILITIES": 1.05,
        "GENERAL": 1.10,
    })
    data_source: str = "BEA_SNA_IO_Official_Accounts_SEC_10K"


@dataclass
class SepaAdaptiveParams:
    """米奈尔维尼 SEPA 买入信号与风控自适应参数契约 (消除任何代码层硬编码)."""
    # 刚性风控与价格边界参数
    pct_max_hard_stop_loss: float = 0.07          # 最大刚性硬止损比例 (默认 7.0%)
    pct_recommended_stop_loss: float = 0.05       # 建议常态精准止损比例 (默认 5.0%)
    ratio_breakeven_trailing_r: float = 3.0       # 移动保本止损触发风险倍数 (浮盈达 3R 即 3倍初始风险时上提止损至保本)
    pct_extended_chase_limit: float = 0.05        # 突破后超买脱轨上限 (超过枢轴点 5.0% 严禁追高)
    ratio_target_risk_reward: float = 3.0         # 目标基准风险报酬比 (默认 3:1)

    # 趋势模板 (Trend Template) 门禁参数
    pct_min_gain_from_52w_low: float = 0.30       # 距离 52 周最低点最小涨幅 (默认 30.0%)
    pct_max_pullback_from_52w_high: float = 0.25  # 距离 52 周最高点最大回撤容忍度 (默认 25.0%)
    num_min_rs_rank: float = 70.0                 # 相对强度 (RS Rank) 最低门槛 (默认 70.0)

    # VCP 波动收缩与微观筹码参数
    pct_vcp_tight_threshold: float = 0.05         # 最终紧密收缩最大振幅 (默认 <= 5.0%)
    ratio_contraction_decay_max: float = 0.75     # 每次收敛振幅较前一次的最大比例 (默认 <= 75%, 理想在 50% 左右)
    ratio_volume_breakout_surge: float = 1.50     # 枢轴点放量突破成交量倍数 (默认 >= 1.50 倍 50日均量)
    ratio_dryup_volume_max: float = 0.50          # 收敛期间地量抽干成交量上限 (默认 <= 0.50 倍 50日均量)

    data_source: str = "Minervini_SEPA_Official_Trend_Template_Specification"


@dataclass
class MarketAdaptiveParamsRegistry:
    """市场自适应全局注册中心."""
    gold_params: GoldValuationAdaptiveParams = field(default_factory=GoldValuationAdaptiveParams)
    macro_shock_params: MacroShockAdaptiveParams = field(default_factory=MacroShockAdaptiveParams)
    firm_bridge_params: FirmValueAddedAdaptiveParams = field(default_factory=FirmValueAddedAdaptiveParams)
    sepa_params: SepaAdaptiveParams = field(default_factory=SepaAdaptiveParams)

    @classmethod
    def get_default(cls) -> "MarketAdaptiveParamsRegistry":
        """纯内存基准配置（零 I/O 依赖保证）."""
        return cls()

    @classmethod
    def load_from_json(cls, config_path: Optional[Path] = None) -> "MarketAdaptiveParamsRegistry":
        """从项目统一配置文件加载，支持容错与断言回退."""
        path = config_path or (ROOT / "config" / "market_adaptive_params.json")
        if not path.is_file():
            return cls.get_default()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            gold_data = data.get("gold_valuation", {})
            macro_data = data.get("macro_shock", {})
            firm_data = data.get("firm_value_added", {})
            sepa_data = data.get("sepa_signals", {})
            return cls(
                gold_params=GoldValuationAdaptiveParams(**{k: v for k, v in gold_data.items() if hasattr(GoldValuationAdaptiveParams, k)}),
                macro_shock_params=MacroShockAdaptiveParams(**{k: v for k, v in macro_data.items() if hasattr(MacroShockAdaptiveParams, k)}),
                firm_bridge_params=FirmValueAddedAdaptiveParams(**{k: v for k, v in firm_data.items() if hasattr(FirmValueAddedAdaptiveParams, k)}),
                sepa_params=SepaAdaptiveParams(**{k: v for k, v in sepa_data.items() if hasattr(SepaAdaptiveParams, k)}),
            )
        except Exception:
            return cls.get_default()
