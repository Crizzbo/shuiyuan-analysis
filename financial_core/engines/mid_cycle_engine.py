"""周期性企业跨周期正常化估值引擎 (Mid-Cycle Normalization & Shiller CAPE Valuation Engine)

设计目标与理论基础：
为买方机构构建对冲“周期顶点虚假高利润陷阱”与“周期谷底非理性错杀”的跨周期正常化估值体系：
1. 【跨周期正常化现金流 (Normalized Mid-Cycle FCF)】：
   - 提取企业过去完整经济周期 (7~10 年) 的历史资产周转率中枢 ATO_mid 与历史营业利润率中枢 Margin_mid；
   - 基于现有重资产规模重构中周期营收能力：Rev_norm = Total_Assets * ATO_mid；
   - 正常化经营利润与自由现金流：
     EBIT_norm = Rev_norm * Margin_mid
     NOPAT_norm = EBIT_norm * (1 - t)
     FCF_mid = NOPAT_norm - (Rev_norm * CapexRatio_mid)
   - 杜绝航运、半导体、大宗商品、汽车制造等重周期行业在繁荣顶点用假低 PE 诱多、在萧条谷底因巨亏不敢建仓的通病。
2. 【席勒周期调整市盈率 (Shiller CAPE)】：
   - 计算过去 10 年剔除通胀扰动后的实际平均净利润 E_real_bar；
   - Shiller CAPE = Current_Market_Cap / E_real_bar
   - 走廊对标：识别当前股价相对 10 年真实盈利中枢的溢价/折价倍率。
3. 【周期所处阶段智能识别 (Cycle Phase Classifier)】：
   - 谷底复苏 (TROUGH_RECOVERY)：利润率处于历史底部 (<P20)，营收增速回正，确认左侧高赔率反转点；
   - 中周期稳健 (MID_CYCLE_EXPANSION)：利润率处于中枢合理走廊 (P40~P65)，主升浪；
   - 繁荣见顶 (PEAK_OVERHEAT)：利润率超过历史 P85 极值，警惕“假低 PE、高景气拐点”；
   - 晚周期收缩 (LATE_CYCLE_CONTRACTION)：利润率与需求同步下滑，右侧坚决回避。
4. 【中周期内在价值与情景估值公允锚点】：
   - 结合中周期 FCF 贴现模型，输出不受短期景气噪点扭曲的真实内在锚点。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


CYCLE_PHASE_METADATA: Dict[str, Dict[str, str]] = {
    "TROUGH_RECOVERY": {
        "state_name_zh": "谷底反转与修复期",
        "strategic_stance_zh": "逆向积极建仓 (左侧高赔率反转点)",
        "business_intuition_zh": "利润率处于历史底部 20% 分位数，但营收下滑趋缓或已企稳回升；市场普遍沉浸在悲观预期中，是逆向建仓布局高赔率资产的黄金窗口。",
    },
    "MID_CYCLE_EXPANSION": {
        "state_name_zh": "中周期稳健扩张期",
        "strategic_stance_zh": "顺风主升浪健康运行 (结合护城河与公允锚点做多)",
        "business_intuition_zh": "利润率处于历史中枢稳健区间，行业供需平衡良好，可结合公司护城河与中周期公允锚点逢低做多。",
    },
    "PEAK_OVERHEAT": {
        "state_name_zh": "周期见顶与过热期",
        "strategic_stance_zh": "警惕假低 PE 见顶陷阱 (逢高获利了结)",
        "business_intuition_zh": "当前利润率处于历史极端高位 (>80% 分位数)，名义 PE 虽显便宜但本质是周期顶点盈利被极度透支；严禁盲目追高，建议逢高止盈锁定利润。",
    },
    "LATE_CYCLE_CONTRACTION": {
        "state_name_zh": "晚周期利润收缩期",
        "strategic_stance_zh": "右侧下行通道坚决回避 (空仓观望)",
        "business_intuition_zh": "营收显著负增长且利润率大幅被挤压，行业产能过剩或去库存压力严峻，基本面底尚未清晰，建议保持空仓观望。",
    },
}


@dataclass
class MidCycleFCFResult:
    """跨周期正常化现金流计算拆解."""
    history_years_count: int              # 回溯历史财报年数 (通常 7~10 年)
    median_asset_turnover: float          # 历史资产周转率中枢
    median_operating_margin: float        # 历史息税前营业利润率中枢 EBIT Margin %
    median_capex_to_revenue: float        # 历史资本开支占收入比例中枢 Capex %
    normalized_mid_cycle_revenue: float   # 现有资产规模下的正常化中周期营收
    normalized_mid_cycle_ebit: float      # 正常化中周期 EBIT
    normalized_mid_cycle_nopat: float     # 正常化中周期税后净营业利润 NOPAT
    normalized_mid_cycle_capex: float     # 中周期总资本开支 (Gross Capex)
    normalized_mid_cycle_fcf: float       # 正常化中周期自由现金流 FCF (NOPAT + D&A - Capex)
    normalized_mid_cycle_dna: float = 0.0 # 正常化折旧与摊销中枢 D&A
    normalized_net_capex: float = 0.0     # 正常化净资本开支 Net Capex (Capex - D&A)
    currency_symbol: str = "$"            # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        curr = self.currency_symbol or "$"
        return {
            "history_years_count": self.history_years_count,
            "median_asset_turnover": f"{self.median_asset_turnover:.2f}x",
            "median_operating_margin": f"{self.median_operating_margin * 100:.1f}%",
            "median_capex_to_revenue": f"{self.median_capex_to_revenue * 100:.1f}%",
            "normalized_revenue": f"{curr}{self.normalized_mid_cycle_revenue:,.1f}M",
            "normalized_ebit": f"{curr}{self.normalized_mid_cycle_ebit:,.1f}M",
            "normalized_nopat": f"{curr}{self.normalized_mid_cycle_nopat:,.1f}M",
            "normalized_capex": f"{curr}{self.normalized_mid_cycle_capex:,.1f}M",
            "normalized_fcf": f"{curr}{self.normalized_mid_cycle_fcf:,.1f}M",
            "normalized_dna": f"{curr}{self.normalized_mid_cycle_dna:,.1f}M",
            "normalized_net_capex": f"{curr}{self.normalized_net_capex:,.1f}M",
            "currency_symbol": curr,
        }


@dataclass
class ShillerCAPEResult:
    """席勒周期调整市盈率指标结果."""
    current_price: float
    shiller_real_eps_10y: float           # 10 年平均真实每股收益
    shiller_cape_ratio: float             # 席勒 CAPE 倍数
    historical_benchmark_cape: float      # 行业历史 CAPE 基准中枢 (通常 16~22 倍)
    cape_premium_discount_pct: float      # 相对历史中枢溢价/折价 %
    cape_valuation_tier_zh: str           # CAPE 估值分级评价
    currency_symbol: str = "$"            # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        curr = self.currency_symbol or "$"
        disp_cape = "亏损不可比" if self.shiller_cape_ratio >= 900.0 else f"{self.shiller_cape_ratio:.1f}x"
        return {
            "current_price": f"{curr}{self.current_price:.2f}",
            "shiller_real_eps_10y": f"{curr}{self.shiller_real_eps_10y:.2f}",
            "shiller_cape": disp_cape,
            "benchmark_cape": f"{self.historical_benchmark_cape:.1f}x",
            "premium_discount_pct": f"{self.cape_premium_discount_pct:+.1f}%",
            "valuation_tier_zh": self.cape_valuation_tier_zh,
            "currency_symbol": curr,
        }


@dataclass
class CyclePhaseResult:
    """企业当前周期所处阶段与买方决策导向."""
    current_operating_margin: float       # 当前最新利润率 %
    margin_percentile_in_history: float   # 当前利润率在历史周期中的分位数 (0~100%)
    cycle_phase_code: str                 # TROUGH_RECOVERY, MID_CYCLE_EXPANSION, PEAK_OVERHEAT, LATE_CYCLE_CONTRACTION
    cycle_phase_name_zh: str              # 周期阶段中文名称
    buy_side_strategic_verdict_zh: str    # 买方机构战略决策研判
    strategic_stance_zh: str = ""         # 买方战略立场
    business_intuition_zh: str = ""       # 商业投资直觉

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_operating_margin": f"{self.current_operating_margin * 100:.1f}%",
            "margin_percentile": f"{self.margin_percentile_in_history:.1f}%",
            "cycle_phase_code": self.cycle_phase_code,
            "cycle_phase_name_zh": self.cycle_phase_name_zh,
            "strategic_stance_zh": self.strategic_stance_zh,
            "strategic_verdict_zh": self.buy_side_strategic_verdict_zh,
        }


@dataclass
class MidCycleValuationResult:
    """跨周期正常化估值全景输出."""
    ticker: str
    current_price: float
    fcf_normalization: MidCycleFCFResult
    shiller_cape: ShillerCAPEResult
    cycle_phase: CyclePhaseResult
    mid_cycle_fair_value: float           # 跨周期正常化公允内在价值
    implied_upside_downside_pct: float    # 相对现价潜在修复/回调空间 %
    valuation_summary_zh: str             # 机构级跨周期研报总结
    narrative_zh: str = ""                # 买方通俗全息研报卡片 (去工程符号化)
    currency_symbol: str = "$"            # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        curr = self.currency_symbol or "$"
        return {
            "ticker": self.ticker,
            "current_price": f"{curr}{self.current_price:.2f}",
            "mid_cycle_fair_value": f"{curr}{self.mid_cycle_fair_value:.2f}",
            "implied_upside_downside_pct": f"{self.implied_upside_downside_pct:+.1f}%",
            "fcf_normalization": self.fcf_normalization.to_dict(),
            "shiller_cape": self.shiller_cape.to_dict(),
            "cycle_phase": self.cycle_phase.to_dict(),
            "valuation_summary_zh": self.valuation_summary_zh,
            "narrative_zh": self.narrative_zh or self.valuation_summary_zh,
            "currency_symbol": curr,
        }


class MidCycleNormalizationEngine:
    """跨周期正常化与周期调整估值引擎."""

    @classmethod
    def normalize_cycle_fcf(
        cls,
        history_revenues: List[float],
        history_operating_incomes: List[float],
        history_capex: List[float],
        current_total_assets: float,
        tax_rate: float = 0.21,
        history_dna: Optional[List[float]] = None,
        maintenance_capex_ratio: float = 0.75,
        currency_symbol: str = "$",
    ) -> MidCycleFCFResult:
        """基于企业过去完整历史周期表现，估算现有资产底账下的跨周期正常化自由现金流.

        遵循买方会计恒等式：
        FCFF = NOPAT + D&A - Capex - ΔNWC = NOPAT - (Capex - D&A)
        避免在扣除 Capex 时遗漏 D&A 加回导致固定资产更新成本被双重扣除。
        """
        N = len(history_revenues)
        if N < 3 or len(history_operating_incomes) != N or len(history_capex) != N:
            raise ValueError(f"跨周期正常化至少需要 3 期以上的完整历史序列 (当前提供 {N} 期)")

        revs = np.array(history_revenues, dtype=float)
        ebits = np.array(history_operating_incomes, dtype=float)
        capex = np.abs(np.array(history_capex, dtype=float))

        # 1. 营业利润率序列 Margin = EBIT / Revenue (过滤收入 <= 0 的异常年份)
        valid_mask = revs > 1e-4
        if np.sum(valid_mask) < 2:
            raise ValueError("有效正向营业收入历史样本不足")

        valid_revs = revs[valid_mask]
        valid_ebits = ebits[valid_mask]
        valid_capex = capex[valid_mask]

        margins = valid_ebits / valid_revs
        capex_ratios = valid_capex / valid_revs

        # 2. 中枢统计量 (采用稳健中位数规避极值扭曲)
        median_margin = float(np.median(margins))
        median_capex_ratio = float(np.median(capex_ratios))

        # 3. 资产周转率中枢 ATO = Revenue / Total Assets
        # 若无历年总资产序列，以历史平均营收对标当前资产规模折算，下限约束 0.15，上限约束 3.0
        implied_ato = float(np.median(valid_revs)) / max(1.0, current_total_assets)
        bounded_ato = max(0.15, min(3.0, implied_ato))

        # 4. 正常化中周期各项关键指标重构
        norm_rev = current_total_assets * bounded_ato
        norm_ebit = norm_rev * median_margin
        norm_nopat = norm_ebit * (1.0 - tax_rate)
        norm_capex = norm_rev * median_capex_ratio

        # 5. 折旧与摊销 (D&A) 与净资本开支 (Net Capex)
        # 会计恒等式：FCF = NOPAT + D&A - Capex = NOPAT - (Capex - D&A)
        if history_dna is not None and len(history_dna) == N:
            valid_dna = np.abs(np.array(history_dna, dtype=float))[valid_mask]
            dna_ratios = valid_dna / valid_revs
            median_dna_ratio = float(np.median(dna_ratios))
            norm_dna = norm_rev * median_dna_ratio
        else:
            # 默认中周期稳态下维持性资本开支对标折旧摊销 D&A
            norm_dna = norm_capex * min(1.0, max(0.0, maintenance_capex_ratio))

        norm_net_capex = max(0.0, norm_capex - norm_dna)
        norm_fcf = norm_nopat - norm_net_capex

        return MidCycleFCFResult(
            history_years_count=N,
            median_asset_turnover=round(bounded_ato, 4),
            median_operating_margin=round(median_margin, 4),
            median_capex_to_revenue=round(median_capex_ratio, 4),
            normalized_mid_cycle_revenue=round(norm_rev, 2),
            normalized_mid_cycle_ebit=round(norm_ebit, 2),
            normalized_mid_cycle_nopat=round(norm_nopat, 2),
            normalized_mid_cycle_capex=round(norm_capex, 2),
            normalized_mid_cycle_fcf=round(norm_fcf, 2),
            normalized_mid_cycle_dna=round(norm_dna, 2),
            normalized_net_capex=round(norm_net_capex, 2),
            currency_symbol=currency_symbol,
        )

    @classmethod
    def compute_shiller_cape(
        cls,
        current_price: float,
        shares_outstanding: float,
        history_net_incomes: List[float],
        cpi_inflation_multipliers: Optional[List[float]] = None,
        historical_benchmark_cape: float = 18.0,
        currency_symbol: str = "$",
    ) -> ShillerCAPEResult:
        """计算席勒周期调整市盈率 (Shiller CAPE) 与历史基准溢折价度."""
        N = len(history_net_incomes)
        if N < 3:
            raise ValueError("计算 Shiller CAPE 至少需要 3 年以上历史净利润数据")
        shares = max(0.001, shares_outstanding)

        incomes = np.array(history_net_incomes, dtype=float)
        if cpi_inflation_multipliers and len(cpi_inflation_multipliers) == N:
            cpi_adj = np.array(cpi_inflation_multipliers, dtype=float)
            real_incomes = incomes * cpi_adj
        else:
            real_incomes = incomes

        # 10 年平均真实净利润 (或现有全部历史年数平均)
        avg_real_net_income = float(np.mean(real_incomes))
        real_eps = avg_real_net_income / shares

        if real_eps <= 0:
            # 极端长期亏损标的
            cape_ratio = 999.0
            premium_pct = 999.0
            tier = "【长期基本面亏损】周期平均真实净利润为负，无法形成有意义的 CAPE 估值锚点。"
        else:
            cape_ratio = current_price / real_eps
            safe_bench_cape = max(0.1, historical_benchmark_cape)
            premium_pct = (cape_ratio - safe_bench_cape) / safe_bench_cape * 100.0
            disp_term = "折价" if premium_pct < 0 else "溢价"

            if cape_ratio < safe_bench_cape * 0.70:
                tier = f"【极度深度折价】当前 Shiller CAPE ({cape_ratio:.1f}x) 较行业历史中枢 ({safe_bench_cape:.1f}x) 折价高达 {abs(premium_pct):.1f}%，具备绝佳周期安全边际。"
            elif cape_ratio <= safe_bench_cape * 1.15:
                tier = f"【中周期公允合理】当前 Shiller CAPE ({cape_ratio:.1f}x) 贴近历史中枢走廊 ({safe_bench_cape:.1f}x)，{disp_term} {abs(premium_pct):.1f}%。"
            else:
                tier = f"【周期高估透支】当前 Shiller CAPE ({cape_ratio:.1f}x) 大幅超越历史中枢 ({safe_bench_cape:.1f}x)，溢价高达 {premium_pct:.1f}%，需警惕周期回归杀估值风险。"

        return ShillerCAPEResult(
            current_price=round(current_price, 2),
            shiller_real_eps_10y=round(real_eps, 4),
            shiller_cape_ratio=round(cape_ratio, 2),
            historical_benchmark_cape=round(historical_benchmark_cape, 2),
            cape_premium_discount_pct=round(premium_pct, 2),
            cape_valuation_tier_zh=tier,
            currency_symbol=currency_symbol,
        )

    @classmethod
    def detect_cycle_phase(
        cls,
        current_operating_margin: float,
        history_operating_margins: List[float],
        current_revenue_growth: float,
        industry_median_margin: float = 0.15,
    ) -> CyclePhaseResult:
        """判定企业当前处于周期的具体阶段 (谷底复苏 / 中周期稳健 / 见顶过热 / 晚周期收缩)."""
        margins = np.array(history_operating_margins, dtype=float)
        cur_m = float(current_operating_margin)

        # 计算当前利润率在历史序列中的分位数
        pct = float(np.sum(margins <= cur_m) / len(margins) * 100.0)

        if pct <= 20.0 and current_revenue_growth > -0.05:
            phase_code = "TROUGH_RECOVERY"
            phase_name = "谷底反转与修复期 (Trough / Early Recovery)"
            verdict = "【买方极佳左侧击球点】利润率处于历史底部 20% 分位数，但营收下滑趋缓或已企稳回升；市场普遍沉浸在悲观预期中，是逆向建仓布局高赔率资产的黄金窗口。"
        elif pct >= 80.0:
            phase_code = "PEAK_OVERHEAT"
            phase_name = "周期见顶与过热期 (Peak / Overheat)"
            verdict = "【警惕假低 PE 见顶陷阱】当前利润率处于历史极端高位 (>80% 分位数)，名义 PE 虽显便宜但本质是周期顶点盈利被极度透支；严禁盲目追高，建议逢高止盈锁定利润。"
        elif current_revenue_growth < -0.05 and cur_m < industry_median_margin:
            phase_code = "LATE_CYCLE_CONTRACTION"
            phase_name = "晚周期利润收缩期 (Late-Cycle Contraction)"
            verdict = "【右侧下行通道回避】营收显著负增长且利润率大幅被挤压，行业产能过剩或去库存压力严峻，基本面底尚未清晰，建议保持空仓观望。"
        else:
            phase_code = "MID_CYCLE_EXPANSION"
            phase_name = "中周期稳健扩张期 (Mid-Cycle Expansion)"
            verdict = "【顺风主升浪健康运行】利润率处于历史中枢稳健区间，行业供需平衡良好，可结合公司护城河与中周期公允锚点逢低做多。"

        meta = CYCLE_PHASE_METADATA.get(phase_code, {
            "state_name_zh": phase_name,
            "strategic_stance_zh": "中性跟踪",
            "business_intuition_zh": verdict,
        })

        return CyclePhaseResult(
            current_operating_margin=round(cur_m, 4),
            margin_percentile_in_history=round(pct, 1),
            cycle_phase_code=phase_code,
            cycle_phase_name_zh=phase_name,
            buy_side_strategic_verdict_zh=verdict,
            strategic_stance_zh=meta.get("strategic_stance_zh", ""),
            business_intuition_zh=meta.get("business_intuition_zh", ""),
        )

    @classmethod
    def evaluate_mid_cycle_valuation(
        cls,
        ticker: str,
        current_price: float,
        shares_outstanding: float,
        total_debt: float,
        cash_and_equivalents: float,
        history_revenues: List[float],
        history_operating_incomes: List[float],
        history_capex: List[float],
        history_net_incomes: List[float],
        current_total_assets: float,
        current_revenue_growth: float = 0.05,
        wacc: float = 0.09,
        terminal_growth: float = 0.02,
        historical_benchmark_cape: float = 18.0,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> MidCycleValuationResult:
        """执行端到端跨周期正常化估值，输出不受景气波动的公允内在价值锚点."""
        # 自适应推导市场与货币符号 (SSOT: 兼容美股、日股、A股多币种)
        t_up = (ticker or "").upper()
        m_up = (market or "").upper()
        is_jp = m_up == "JP" or t_up.endswith(".T") or t_up.endswith(".JP") or (t_up.isdigit() and len(t_up) == 4)
        is_cn = m_up == "CN" or t_up.endswith(".SS") or t_up.endswith(".SZ") or (t_up.isdigit() and len(t_up) == 6)
        if currency_symbol:
            curr_sym = currency_symbol
        elif is_jp or is_cn:
            curr_sym = "¥"
        else:
            curr_sym = "$"

        # 1. 正常化 FCF
        fcf_norm = cls.normalize_cycle_fcf(
            history_revenues=history_revenues,
            history_operating_incomes=history_operating_incomes,
            history_capex=history_capex,
            current_total_assets=current_total_assets,
            currency_symbol=curr_sym,
        )

        # 2. Shiller CAPE
        shiller = cls.compute_shiller_cape(
            current_price=current_price,
            shares_outstanding=shares_outstanding,
            history_net_incomes=history_net_incomes,
            historical_benchmark_cape=historical_benchmark_cape,
            currency_symbol=curr_sym,
        )

        # 3. 周期阶段识别
        latest_ebit = history_operating_incomes[-1]
        latest_rev = max(1.0, history_revenues[-1])
        cur_margin = latest_ebit / latest_rev
        hist_margins = [ebit / max(1.0, rev) for ebit, rev in zip(history_operating_incomes, history_revenues)]
        cycle_phase = cls.detect_cycle_phase(
            current_operating_margin=cur_margin,
            history_operating_margins=hist_margins,
            current_revenue_growth=current_revenue_growth,
            industry_median_margin=fcf_norm.median_operating_margin,
        )

        # 4. 中周期 FCF 贴现模型推导公允企业价值 EV
        # 假设中周期正常化现金流以名义永续增长率 terminal_growth 稳定成长
        # EV = FCF_mid * (1 + g) / (WACC - g)
        r_spread = max(0.02, wacc - terminal_growth)
        norm_fcf = fcf_norm.normalized_mid_cycle_fcf

        if norm_fcf > 0:
            ev_mid = norm_fcf * (1.0 + terminal_growth) / r_spread
            net_debt = total_debt - cash_and_equivalents
            equity_val = max(0.01, ev_mid - net_debt)
            fair_p = equity_val / max(0.001, shares_outstanding)
        else:
            # 若中周期 FCF 为负，以 Shiller CAPE 锚定公允价
            fair_p = max(0.01, shiller.shiller_real_eps_10y * historical_benchmark_cape)

        # 股价除零与负数防御，避免崩溃
        safe_price = max(0.01, current_price)
        upside_downside_pct = (fair_p - current_price) / safe_price * 100.0

        # 去工程符号化：若 Shiller CAPE 为内部哨兵值 999.0x，转为自然商业语义
        if shiller.shiller_cape_ratio >= 900.0:
            cape_desc = "亏损不可比 (10年平均真实 EPS 为负)"
        else:
            cape_desc = f"{shiller.shiller_cape_ratio:.1f}x"

        # 若中周期 FCF 与 10年盈利双负，补充公允价触及残值保护下界的商业定性
        if norm_fcf <= 0 and shiller.shiller_real_eps_10y <= 0:
            solvency_note = "【特别风险警示】企业中周期现金流与10年平均利润双双为负，缺乏自我造血与再投资能力，公允估值被动触及最低残值保护下界；"
        else:
            solvency_note = ""

        # 自然语言空间与溢折价描述 (消弭双重负号语病)
        if upside_downside_pct < 0:
            space_desc = f"潜在回调 {abs(upside_downside_pct):.1f}% (相对现价空间 {upside_downside_pct:+.1f}%)"
        else:
            space_desc = f"潜在修复空间 {upside_downside_pct:+.1f}%"

        summary = (
            f"【{ticker} 跨周期正常化估值研报】"
            f"企业当前处于【{cycle_phase.cycle_phase_name_zh}】；"
            f"{solvency_note}"
            f"基于过去 {fcf_norm.history_years_count} 年完整周期中枢，现有资产正常化年均产生 FCF {curr_sym}{fcf_norm.normalized_mid_cycle_fcf:,.1f}M；"
            f"跨周期内在公允价值为 {curr_sym}{fair_p:.2f} (现价 {curr_sym}{current_price:.2f}，{space_desc})；"
            f"Shiller CAPE 为 {cape_desc}。{cycle_phase.buy_side_strategic_verdict_zh}"
        )

        narrative_zh = (
            f"【标的 {ticker} 跨周期正常化估值全息研报】"
            f"周期所处阶段: 企业当前处于【{cycle_phase.cycle_phase_name_zh}】(利润率处于历史 {cycle_phase.margin_percentile_in_history:.1f}% 分位)。"
            f"跨周期造血中枢: 基于 {fcf_norm.history_years_count} 年周期中枢，资产周转率中位数 {fcf_norm.median_asset_turnover:.2f}x，"
            f"营业利润率中枢 {fcf_norm.median_operating_margin * 100:.1f}%，现有资产年化正常化 FCF 为 {curr_sym}{fcf_norm.normalized_mid_cycle_fcf:,.1f}M。"
            f"估值走廊与公允锚点: 10年期 Shiller CAPE 席勒市盈率为 {cape_desc}；"
            f"中周期内在公允价值为 {curr_sym}{fair_p:.2f} (对比现价 {curr_sym}{current_price:.2f}，{space_desc})。"
            f"买方战略研判: {cycle_phase.buy_side_strategic_verdict_zh}"
        )

        return MidCycleValuationResult(
            ticker=ticker,
            current_price=round(current_price, 2),
            fcf_normalization=fcf_norm,
            shiller_cape=shiller,
            cycle_phase=cycle_phase,
            mid_cycle_fair_value=round(fair_p, 2),
            implied_upside_downside_pct=round(upside_downside_pct, 2),
            valuation_summary_zh=summary,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )


# 向下兼容别名与单一事实来源 (SSOT)
MidCycleValuationEngine = MidCycleNormalizationEngine

__all__ = [
    "MidCycleFCFResult",
    "ShillerCAPEResult",
    "CyclePhaseResult",
    "MidCycleValuationResult",
    "MidCycleNormalizationEngine",
    "MidCycleValuationEngine",
]

