# -*- coding: utf-8 -*-
"""买方宏观市场状态机与自适应策略切换引擎 (market_regime_switching_engine.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，不依赖任何外层脚本、工具或报告模块；
2. 零前视偏差 (Strict Point-in-Time)：输入必须仅包含截至调仓截面 T 的已知大盘历史日线；
3. 状态机驱动自适应切换 (Dynamic Regime Switching)：
   - 牛市主升浪 (BULL_MOMENTUM) -> 激活模型 A (MOMENTUM_SEPA，最大化进攻弹性)；
   - 震荡中性期 (RANGE_BOUND_VALUE) -> 激活模型 B (MOAT_VALUE，寻找折价安全边际)；
   - 危机避险期 (CRISIS_DEFENSE) -> 激活模型 C (VAR_TAIL_RISK，绝对防守压死回撤)；
4. 动态输出切换判定、触发归因、适用策略模型及自适应止损止盈风控参数。
"""

from dataclasses import dataclass, asdict
from enum import Enum
import math
from typing import Any, Dict, List, Optional


class MarketRegime(str, Enum):
    """宏观市场状态枚举."""
    BULL_MOMENTUM = "BULL_MOMENTUM"          # 牛市多头主升浪
    RANGE_BOUND_VALUE = "RANGE_BOUND_VALUE"  # 宽幅震荡/中性估值筑底
    CRISIS_DEFENSE = "CRISIS_DEFENSE"        # 危机熊市/剧烈下行避险


@dataclass
class MarketRegimeVerdict:
    """宏观状态机判定结果明细."""
    as_of_date: str
    regime: MarketRegime
    benchmark_close: float
    ema20: float
    ema50: float
    ema200: float
    vol20_annualized: float
    selected_strategy_model: str
    stop_loss_pct: float
    trailing_stop_pct: float
    rationale_zh: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["regime"] = self.regime.value
        return d


class MarketRegimeSwitchingEngine:
    """买方宏观状态自适应切换引擎."""

    def __init__(
        self,
        vol_crisis_threshold: float = 0.28,    # 年化波动率高于 28% 视为高恐慌危机
        vol_calm_threshold: float = 0.22,      # 年化波动率低于 22% 视为健康牛市
        min_benchmark_bars: int = 200          # 必须有充足历史计算 EMA200
    ):
        if vol_crisis_threshold <= vol_calm_threshold:
            raise ValueError("vol_crisis_threshold 必须大于 vol_calm_threshold")
        if min_benchmark_bars < 50:
            raise ValueError("min_benchmark_bars 必须 >= 50")

        self.vol_crisis_threshold = vol_crisis_threshold
        self.vol_calm_threshold = vol_calm_threshold
        self.min_benchmark_bars = min_benchmark_bars

    def detect_regime(
        self,
        as_of_date: str,
        historical_benchmark_bars: List[Dict[str, Any]]
    ) -> MarketRegimeVerdict:
        """在历史任意点时 as_of_date 截面上提取大盘特征并判定宏观状态.

        Args:
            as_of_date: 评估基准日 (YYYY-MM-DD)，仅使用 <= 该日期的已发生数据
            historical_benchmark_bars: 大盘基准全部日线序列

        Returns:
            MarketRegimeVerdict: 宏观状态判定与自适应策略配置
        """
        if not historical_benchmark_bars:
            raise ValueError("大盘基准日线数据不能为空")

        # 1. 严格点时截断：仅看 <= as_of_date 的已实现数据
        pit_bars = [b for b in historical_benchmark_bars if str(b["date"]) <= as_of_date]
        if len(pit_bars) < self.min_benchmark_bars:
            # 历史数据长度不足，默认采用机构复合稳健模型
            curr_c = float(pit_bars[-1]["close"]) if pit_bars else 100.0
            return MarketRegimeVerdict(
                as_of_date=as_of_date,
                regime=MarketRegime.RANGE_BOUND_VALUE,
                benchmark_close=curr_c,
                ema20=curr_c,
                ema50=curr_c,
                ema200=curr_c,
                vol20_annualized=0.15,
                selected_strategy_model="FULL_QUANTAMENTAL",
                stop_loss_pct=-0.07,
                trailing_stop_pct=0.15,
                rationale_zh="基准数据不足 200 天，采用默认机构复合稳健配置"
            )

        closes = [float(b["close"]) for b in pit_bars]
        curr_c = closes[-1]

        # 2. 计算大盘均线指标 EMA20, EMA50, EMA200
        ema20 = self._calc_ema(closes, span=20)
        ema50 = self._calc_ema(closes, span=50)
        ema200 = self._calc_ema(closes, span=200)

        # 3. 计算 20 日历史年化波动率
        recent_20 = closes[-21:]
        log_rets = [math.log(recent_20[i] / recent_20[i-1]) for i in range(1, len(recent_20))]
        mean_ret = sum(log_rets) / len(log_rets)
        variance = sum((r - mean_ret) ** 2 for r in log_rets) / (len(log_rets) - 1) if len(log_rets) > 1 else 0.0
        vol20 = math.sqrt(variance * 252.0)

        # 4. 状态转移判别逻辑
        # 条件 1: 危机避险 (CRISIS_DEFENSE)
        # - 大盘跌破 200 日牛熊分界均线 (SPY < EMA200)；
        # - 或 20 日年化波动率剧烈飙升超过危机阈值 (Vol20 > 28%)。
        if (curr_c < ema200) or (vol20 > self.vol_crisis_threshold):
            reasons = []
            if curr_c < ema200:
                reasons.append(f"大盘跌破EMA200牛熊分界线(现价${curr_c:.2f} < EMA200 ${ema200:.2f})")
            if vol20 > self.vol_crisis_threshold:
                reasons.append(f"大盘20日年化波动率飙升达 {vol20*100.0:.1f}%(超过阈值{self.vol_crisis_threshold*100.0:.0f}%)")

            rationale = "【危机避险】" + " 且 ".join(reasons) + "，自适应切换至模型 C (动态尾部风控)，收缩仓位并执行 -5% 极紧止损！"
            return MarketRegimeVerdict(
                as_of_date=as_of_date,
                regime=MarketRegime.CRISIS_DEFENSE,
                benchmark_close=curr_c,
                ema20=round(ema20, 2),
                ema50=round(ema50, 2),
                ema200=round(ema200, 2),
                vol20_annualized=round(vol20, 4),
                selected_strategy_model="VAR_TAIL_RISK",
                stop_loss_pct=-0.05,
                trailing_stop_pct=0.10,
                rationale_zh=rationale
            )

        # 条件 2: 牛市主升浪进攻 (BULL_MOMENTUM)
        # - 均线呈现标准多头排列 (SPY > EMA50 且 EMA20 > EMA50)；
        # - 且波动率平稳温和 (Vol20 <= 22%)。
        if (curr_c > ema50) and (ema20 > ema50) and (vol20 <= self.vol_calm_threshold):
            rationale = f"【牛市主升】大盘站稳EMA50且均线多头排列，波动率维持温和({vol20*100.0:.1f}%)，自适应切换至模型 A (纯动量时机)，全速捕获主升浪红利！"
            return MarketRegimeVerdict(
                as_of_date=as_of_date,
                regime=MarketRegime.BULL_MOMENTUM,
                benchmark_close=curr_c,
                ema20=round(ema20, 2),
                ema50=round(ema50, 2),
                ema200=round(ema200, 2),
                vol20_annualized=round(vol20, 4),
                selected_strategy_model="MOMENTUM_SEPA",
                stop_loss_pct=-0.07,
                trailing_stop_pct=0.15,
                rationale_zh=rationale
            )

        # 条件 3: 震荡中性与估值筑底 (RANGE_BOUND_VALUE)
        # - 处于 EMA50 与 EMA200 之间，或波动率介于平静与危机之间
        rationale = f"【震荡中性】大盘处于震荡消化区间(现价${curr_c:.2f}处于EMA50与EMA200之间或波动率适中)，自适应切换至模型 B (护城河价值)，逢低吸筹均值回归！"
        return MarketRegimeVerdict(
            as_of_date=as_of_date,
            regime=MarketRegime.RANGE_BOUND_VALUE,
            benchmark_close=curr_c,
            ema20=round(ema20, 2),
            ema50=round(ema50, 2),
            ema200=round(ema200, 2),
            vol20_annualized=round(vol20, 4),
            selected_strategy_model="MOAT_VALUE",
            stop_loss_pct=-0.10,
            trailing_stop_pct=0.20,
            rationale_zh=rationale
        )

    @staticmethod
    def _calc_ema(prices: List[float], span: int) -> float:
        """纯标准库计算 EMA."""
        if not prices:
            return 0.0
        alpha = 2.0 / (span + 1.0)
        ema = prices[0]
        for p in prices[1:]:
            ema = alpha * p + (1.0 - alpha) * ema
        return ema
