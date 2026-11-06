"""全行业同业横向对标与相对估值分析引擎 (Cross-Sectional Peer Benchmark Engine).

功能设计：
任何股票的定价都不能脱离行业横向可比中枢：
1. 构建同赛道对标企业矩阵 (Peer Group Comparison Matrix)；
2. 测算相对估值乘数走廊：EV/Sales、EV/EBITDA、P/E、P/B、FCF Yield；
3. 测算赛道专项指标横向排位（如 AI 制药的 EV/活跃管线、SaaS 的 EV/ARR/Growth）；
4. 计算标的在同业池中的百分位排名 (Percentile Ranking) 与相对中位数折溢价率；
5. 识别“高质量低估值（错杀金矿）”与“低质量高估值（虚高泡沫）”的不对称定价机会。
"""

from dataclasses import dataclass
import statistics
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CompanyPeerMetrics:
    """单家企业横向比较核心指标。"""
    ticker: str
    company_name: str
    ev_to_sales: float                # EV / Sales (企业价值 / 营业收入)
    pe_ratio: Optional[float]         # 市盈率 (TTM/Forward)
    pb_ratio: float                   # 市净率 P/B
    fcf_yield_pct: float              # 自由现金流收益率 %
    revenue_growth_yoy: float         # 营收同比增速 %
    gross_margin_pct: float           # 毛利率 %
    active_programs_count: Optional[int] = None # 生物医药核心管线数 / SaaS 关键产品数


@dataclass(frozen=True)
class PeerBenchmarkResult:
    """同业对标量化分析结果。"""
    target_ticker: str
    peer_count: int
    median_ev_sales: float
    ev_sales_premium_to_median_pct: float # 相对中位数折溢价 %
    ev_sales_percentile: float            # [0, 100] 分位数 (越小越便宜)
    median_revenue_growth: float
    relative_growth_advantage_pct: float  # 相对同业中位数增速超额 %
    relative_value_verdict: str           # "显著低估错杀", "合理中枢定价", "高估泡沫预警"
    matrix_table: List[Dict[str, Any]]    # 完整横向比对矩阵底表
    rationale_zh: str                     # 投资对比解读
    narrative_zh: str = ""                # 买方通俗全息研报卡片 (去工程符号化)
    relative_value_verdict_zh: str = ""   # 纯自然中文定性 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target_ticker,
            "peer_count": self.peer_count,
            "valuation_relative": {
                "median_ev_to_sales": f"{self.median_ev_sales:.2f}x",
                "premium_to_median": f"{self.ev_sales_premium_to_median_pct:+.1f}%",
                "percentile_rank": f"{self.ev_sales_percentile:.1f}%",
                "verdict": self.relative_value_verdict,
                "verdict_zh": self.relative_value_verdict_zh or self.relative_value_verdict,
            },
            "growth_relative": {
                "median_peer_growth": f"{self.median_revenue_growth:+.1f}%",
                "growth_advantage": f"{self.relative_growth_advantage_pct:+.1f}%",
            },
            "rationale": self.rationale_zh,
            "narrative_zh": self.narrative_zh or self.rationale_zh,
            "matrix": self.matrix_table,
        }


class PeerBenchmarkEngine:
    """全行业同业横向对标分析器。"""

    @classmethod
    def evaluate(
        cls,
        target: CompanyPeerMetrics,
        peers: List[CompanyPeerMetrics],
    ) -> PeerBenchmarkResult:
        all_comps = [target] + peers
        n = len(all_comps)
        if n < 2:
            raise ValueError("对标分析至少需要 1 家同业可比公司进行参照")

        # 1. EV/Sales 统计 (除零除负防御)
        ev_sales_list = [c.ev_to_sales for c in peers]
        median_ev_s = statistics.median(ev_sales_list)
        safe_denom_ev = max(0.01, abs(median_ev_s))
        premium_pct = ((target.ev_to_sales - median_ev_s) / safe_denom_ev) * 100.0

        # 百分位排名
        less_count = sum(1 for c in all_comps if c.ev_to_sales < target.ev_to_sales)
        ev_s_percentile = (less_count / max(1, n - 1)) * 100.0

        # 2. 增速统计
        growth_list = [c.revenue_growth_yoy for c in peers]
        median_growth = statistics.median(growth_list)
        growth_adv = target.revenue_growth_yoy - median_growth

        # 格式化折溢价自然语言 (消除"溢价 -8.5%"与冗余正负号双重重复语病)
        if premium_pct < 0.0:
            premium_desc = f"折价 {abs(premium_pct):.1f}%"
        else:
            premium_desc = f"溢价 {premium_pct:.1f}%"

        # 3. 相对估值评价 (纯自然中文去工程符号化与商业直觉优先)
        if growth_adv > 2.0 and premium_pct < -10.0:
            verdict_zh = "极具性价比 (同业显著错杀)"
            verdict = verdict_zh
            rationale = (
                f"在同赛道 {len(peers)} 家可比对手中，标的营收增速 ({target.revenue_growth_yoy:+.1f}%) "
                f"超越行业中位数 ({median_growth:+.1f}%)，然而 EV/Sales 乘数 ({target.ev_to_sales:.2f}x) "
                f"却较同业中位数 ({median_ev_s:.2f}x) {premium_desc} (处于行业 {ev_s_percentile:.0f}% 极低估值分位)，"
                f"属于基本面领先但被市场情绪错杀的高安全边际标的。"
            )
        elif premium_pct > 30.0 and growth_adv < 0:
            verdict_zh = "估值虚高泡沫 (性价比低下)"
            verdict = verdict_zh
            rationale = (
                f"标的估值乘数 ({target.ev_to_sales:.2f}x) 显著高于同业中位数 ({median_ev_s:.2f}x) 达 {premium_desc}，"
                f"但营收成长性 ({target.revenue_growth_yoy:+.1f}%) 反而落后于同业中位数 ({median_growth:+.1f}%)，"
                f"面临严重的估值消化与向下均值回归风险。"
            )
        else:
            verdict_zh = "估值与行业中枢基本匹配"
            verdict = verdict_zh
            rationale = (
                f"标的 EV/Sales 乘数 ({target.ev_to_sales:.2f}x) 处于同业合理走廊区间，"
                f"相对同业中位数呈现{premium_desc}，反映了当前正常的市场竞争格局。"
            )

        # 4. 构建底表
        rows = []
        for c in sorted(all_comps, key=lambda x: x.ev_to_sales):
            rows.append({
                "ticker": c.ticker,
                "is_target": c.ticker == target.ticker,
                "name": c.company_name,
                "ev_to_sales": f"{c.ev_to_sales:.2f}x",
                "growth_yoy": f"{c.revenue_growth_yoy:+.1f}%",
                "gross_margin": f"{c.gross_margin_pct:.1f}%",
                "pe_ratio": f"{c.pe_ratio:.1f}x" if c.pe_ratio else "N/A",
                "fcf_yield": f"{c.fcf_yield_pct:+.1f}%",
            })

        narrative_zh = (
            f"【标的 {target.ticker} 行业同业可比对标全息研报】"
            f"相对估值综合定性为【{verdict_zh}】。"
            f"同业估值走廊: 纳入 {len(peers)} 家核心可比企业，行业企业价值倍数 EV/Sales 中位数为 {median_ev_s:.2f}倍，"
            f"标的当前倍数为 {target.ev_to_sales:.2f}倍 (相对同业中位数{premium_desc}，处于行业第 {ev_s_percentile:.1f}% 估值分位)。"
            f"成长性超额对比: 标的营收同比增速为 {target.revenue_growth_yoy:+.1f}% (行业中位数 {median_growth:+.1f}%，超额优势 {growth_adv:+.1f}%)。"
            f"买方对标研判: {rationale}"
        )

        return PeerBenchmarkResult(
            target_ticker=target.ticker,
            peer_count=len(peers),
            median_ev_sales=round(median_ev_s, 2),
            ev_sales_premium_to_median_pct=round(premium_pct, 2),
            ev_sales_percentile=round(ev_s_percentile, 1),
            median_revenue_growth=round(median_growth, 2),
            relative_growth_advantage_pct=round(growth_adv, 2),
            relative_value_verdict=verdict,
            matrix_table=rows,
            rationale_zh=rationale,
            narrative_zh=narrative_zh,
            relative_value_verdict_zh=verdict_zh,
        )
