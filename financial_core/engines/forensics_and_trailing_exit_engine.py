# -*- coding: utf-8 -*-
"""攻防护航工具：Beneish M-Score 八维财务防造假排雷与吊灯移动止盈棘轮系统 (forensics_and_trailing_exit_engine.py).

遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，纯数学与统计推导；
2. Beneish M-Score 八维法务会计财务舞弊排雷模型：
   - DSRI (应收账款周转天数指数)、GMI (毛利率恶化指数)、AQI (资产质量指数)、SGI (营收增长指数)；
   - DEPI (折旧率放缓指数)、SGAI (销管费用指数)、LVGI (杠杆扩张指数)、TATA (应计利润占比)；
   - 综合 M 分数与概率映射: M > -1.78 触发财务操纵一票否决；
3. Chandelier Exit 吊灯移动止盈系统 (买方浮盈锁定器)：
   - 基于 HighestHigh(22) - k * ATR(22) 构建动态移动离场基准；
   - 单向棘轮机制 (One-Way Ratchet Effect)：止盈线只升不降，锁定利润，回撤击穿即刻平仓；
4. 全面防御除零除负与缺失项平滑。
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BeneishMetrics:
    """Beneish 八维单项财务指标契约."""
    dsri: float   # 应收账款指数
    gmi: float    # 毛利率指数
    aqi: float    # 资产质量指数
    sgi: float    # 营业收入增长率指数
    depi: float   # 折旧率指数
    sgai: float   # 销售管理费用指数
    lvgi: float   # 资产负债率/杠杆指数
    tata: float   # 总应计利润与总资产之比

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeneishScoreResult:
    """Beneish 舞弊排雷研判契约."""
    m_score: float                # 综合 M 分数
    manipulation_probability_pct: float # 操纵概率百分比
    risk_rating: str              # "CLEAN" (安全), "WATCH" (观察), "MANIPULATOR_ALERT" (高危造假)
    is_manipulation_suspect: bool # 是否触发造假一票否决 (M > -1.78)
    metrics: BeneishMetrics
    flagged_dimensions: List[str] # 异常爆表科目清单

    def to_dict(self) -> Dict[str, Any]:
        return {
            "m_score": self.m_score,
            "manipulation_probability_pct": self.manipulation_probability_pct,
            "risk_rating": self.risk_rating,
            "is_manipulation_suspect": self.is_manipulation_suspect,
            "metrics": self.metrics.to_dict(),
            "flagged_dimensions": self.flagged_dimensions,
        }


@dataclass
class ChandelierExitResult:
    """吊灯移动止盈状态契约."""
    ticker: str
    as_of_date: str
    current_price: float
    highest_high_period: float    # 周期内最高点
    atr_period: float             # 周期 ATR
    raw_chandelier_exit: float    # 原始吊灯位 (HH - k * ATR)
    ratchet_stop_price: float     # 棘轮锁定止盈价 (只升不降)
    is_triggered: bool            # 是否击穿止盈离场线
    profit_cushion_pct: float     # 当前价格距离止盈线的缓冲垫垫厚度百分比
    action_verdict: str           # "HOLD_RIDE_TREND" (持仓守利), "TAKE_PROFIT_EXIT" (击穿止盈)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ForensicsAndTrailingExitEngine:
    """攻防护航中枢：Beneish 财务排雷与吊灯移动止盈引擎."""

    # Beneish 官方标准权重参数 (1999)
    BENEISH_INTERCEPT = -4.84
    W_DSRI = 0.920
    W_GMI = 0.528
    W_AQI = 0.404
    W_SGI = 0.892
    W_DEPI = 0.115
    W_SGAI = -0.172
    W_TATA = 4.037
    W_LVGI = 0.0327
    CRITICAL_M_THRESHOLD = -1.78

    def __init__(
        self,
        chandelier_period: int = 22,    # 吊灯追溯周期 (通常为 22 个交易日，约 1 个月)
        chandelier_atr_mult: float = 3.0, # ATR 乘数 (通常 2.5~3.0)
    ):
        self.chandelier_period = chandelier_period
        self.chandelier_atr_mult = chandelier_atr_mult

    def compute_beneish_m_score(
        self,
        # 当期 (Period t) 核心财报科目 (金额口径一致)
        curr_sales: float,
        curr_cogs: float,
        curr_receivables: float,
        curr_current_assets: float,
        curr_ppe_net: float,
        curr_securities: float,
        curr_total_assets: float,
        curr_depreciation: float,
        curr_sga: float,
        curr_long_term_debt: float,
        curr_current_liabilities: float,
        curr_net_income: float,
        curr_cfo: float,
        # 基期 (Period t-1) 对应科目
        prev_sales: float,
        prev_cogs: float,
        prev_receivables: float,
        prev_current_assets: float,
        prev_ppe_net: float,
        prev_securities: float,
        prev_total_assets: float,
        prev_depreciation: float,
        prev_sga: float,
        prev_long_term_debt: float,
        prev_current_liabilities: float,
    ) -> BeneishScoreResult:
        """纯数学解析计算 Beneish M-Score 八维指标与财务舞弊概率."""
        # 1. DSRI = (Rec_t / Sales_t) / (Rec_{t-1} / Sales_{t-1})
        dsr_t = curr_receivables / max(curr_sales, 1e-4)
        dsr_prev = prev_receivables / max(prev_sales, 1e-4)
        dsri = dsr_t / max(dsr_prev, 1e-4)

        # 2. GMI = [(Sales_{t-1} - COGS_{t-1}) / Sales_{t-1}] / [(Sales_t - COGS_t) / Sales_t]
        gm_prev = (prev_sales - prev_cogs) / max(prev_sales, 1e-4)
        gm_t = (curr_sales - curr_cogs) / max(curr_sales, 1e-4)
        gmi = gm_prev / max(gm_t, 1e-4) if gm_t > 0 else 1.5

        # 3. AQI = [1 - (CA_t + PPE_t + Sec_t) / TA_t] / [1 - (CA_{t-1} + PPE_{t-1} + Sec_{t-1}) / TA_{t-1}]
        non_hard_t = max(curr_total_assets - (curr_current_assets + curr_ppe_net + curr_securities), 0.0)
        aq_t = non_hard_t / max(curr_total_assets, 1e-4)
        non_hard_prev = max(prev_total_assets - (prev_current_assets + prev_ppe_net + prev_securities), 0.0)
        aq_prev = non_hard_prev / max(prev_total_assets, 1e-4)
        aqi = (1.0 + aq_t) / max(1.0 + aq_prev, 1e-4)

        # 4. SGI = Sales_t / Sales_{t-1}
        sgi = curr_sales / max(prev_sales, 1e-4)

        # 5. DEPI = [Depr_{t-1} / (PPE_{t-1} + Depr_{t-1})] / [Depr_t / (PPE_t + Depr_t)]
        dep_rate_prev = prev_depreciation / max(prev_ppe_net + prev_depreciation, 1e-4)
        dep_rate_t = curr_depreciation / max(curr_ppe_net + curr_depreciation, 1e-4)
        depi = dep_rate_prev / max(dep_rate_t, 1e-4)

        # 6. SGAI = (SGA_t / Sales_t) / (SGA_{t-1} / Sales_{t-1})
        sga_t = curr_sga / max(curr_sales, 1e-4)
        sga_prev = prev_sga / max(prev_sales, 1e-4)
        sgai = sga_t / max(sga_prev, 1e-4)

        # 7. LVGI = [(LTD_t + CL_t) / TA_t] / [(LTD_{t-1} + CL_{t-1}) / TA_{t-1}]
        lev_t = (curr_long_term_debt + curr_current_liabilities) / max(curr_total_assets, 1e-4)
        lev_prev = (prev_long_term_debt + prev_current_liabilities) / max(prev_total_assets, 1e-4)
        lvgi = lev_t / max(lev_prev, 1e-4)

        # 8. TATA = (NetIncome_t - CFO_t) / TA_t
        tata = (curr_net_income - curr_cfo) / max(curr_total_assets, 1e-4)

        # 截断异常值防止极端数值失真
        def _clamp(v: float, low: float = 0.0, high: float = 10.0) -> float:
            return max(low, min(high, v))

        dsri_c = _clamp(dsri)
        gmi_c = _clamp(gmi)
        aqi_c = _clamp(aqi)
        sgi_c = _clamp(sgi)
        depi_c = _clamp(depi)
        sgai_c = _clamp(sgai)
        lvgi_c = _clamp(lvgi)
        tata_c = max(-2.0, min(2.0, tata))

        # 线性求和
        m_score = (
            self.BENEISH_INTERCEPT
            + self.W_DSRI * dsri_c
            + self.W_GMI * gmi_c
            + self.W_AQI * aqi_c
            + self.W_SGI * sgi_c
            + self.W_DEPI * depi_c
            + self.W_SGAI * sgai_c
            + self.W_TATA * tata_c
            + self.W_LVGI * lvgi_c
        )

        # 标准正态累积分布函数映射出概率 (Probit CDF)
        # 简化标准近似: P = 1 / (1 + exp(-0.07056 * M^3 - 1.5976 * M))
        z = m_score - self.CRITICAL_M_THRESHOLD
        prob = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, 1.2 * z))))
        prob_pct = round(prob * 100.0, 2)

        # 标记异常爆表维度
        flagged = []
        if dsri_c > 1.4:
            flagged.append("应收账款增速异常远超营业收入(DSRI)")
        if gmi_c > 1.3:
            flagged.append("毛利率严重恶化提示粉饰报表动机(GMI)")
        if aqi_c > 1.3:
            flagged.append("非流动资产比例膨胀疑似成本资本化递延(AQI)")
        if depi_c > 1.2:
            flagged.append("固定资产折旧率放缓虚增当期利润(DEPI)")
        if tata_c > 0.10:
            flagged.append("净利润与经营现金流深度背离(应计利润过高TATA)")

        is_suspect = m_score > self.CRITICAL_M_THRESHOLD
        if is_suspect:
            rating = "MANIPULATOR_ALERT"
        elif m_score > -2.00:
            rating = "WATCH"
        else:
            rating = "CLEAN"

        metrics = BeneishMetrics(
            dsri=round(dsri_c, 3),
            gmi=round(gmi_c, 3),
            aqi=round(aqi_c, 3),
            sgi=round(sgi_c, 3),
            depi=round(depi_c, 3),
            sgai=round(sgai_c, 3),
            lvgi=round(lvgi_c, 3),
            tata=round(tata_c, 3),
        )

        return BeneishScoreResult(
            m_score=round(m_score, 3),
            manipulation_probability_pct=prob_pct,
            risk_rating=rating,
            is_manipulation_suspect=is_suspect,
            metrics=metrics,
            flagged_dimensions=flagged,
        )

    def compute_chandelier_exit(
        self,
        ticker: str,
        as_of_date: str,
        high_series: List[float],
        low_series: List[float],
        close_series: List[float],
        prior_ratchet_stop: Optional[float] = None, # 前一日棘轮止盈位 (只升不降记忆)
    ) -> ChandelierExitResult:
        """计算吊灯移动止盈 (Chandelier Exit) 并应用单向棘轮机制."""
        P = self.chandelier_period
        if len(close_series) < P or len(high_series) < P or len(low_series) < P:
            raise ValueError(f"吊灯止盈计算需要至少 {P} 个交易日价位时序")

        current_close = close_series[-1]
        highest_high = max(high_series[-P:])

        # 计算真实波幅 ATR(P)
        tr_list = []
        for i in range(len(close_series) - P, len(close_series)):
            h = high_series[i]
            l = low_series[i]
            prev_c = close_series[i - 1] if i > 0 else close_series[i]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)

        atr = sum(tr_list) / len(tr_list)

        raw_chandelier = highest_high - self.chandelier_atr_mult * atr

        # 单向棘轮机制 (Ratchet Effect): 止盈价只能向上抬高锁利，绝不允许向下回撤
        if prior_ratchet_stop is not None and prior_ratchet_stop > 0.0:
            ratchet_stop = max(prior_ratchet_stop, raw_chandelier)
        else:
            ratchet_stop = raw_chandelier

        is_triggered = current_close < ratchet_stop
        cushion_pct = ((current_close - ratchet_stop) / max(current_close, 1e-6)) * 100.0

        if is_triggered:
            action = "TAKE_PROFIT_EXIT"
        else:
            action = "HOLD_RIDE_TREND"

        return ChandelierExitResult(
            ticker=ticker,
            as_of_date=as_of_date,
            current_price=round(current_close, 2),
            highest_high_period=round(highest_high, 2),
            atr_period=round(atr, 2),
            raw_chandelier_exit=round(raw_chandelier, 2),
            ratchet_stop_price=round(ratchet_stop, 2),
            is_triggered=is_triggered,
            profit_cushion_pct=round(cushion_pct, 2),
            action_verdict=action,
        )
