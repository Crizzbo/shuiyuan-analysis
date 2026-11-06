"""商业模式微观量价拆解与单体经济量化引擎 (Unit Economics & rNPV Engine).

功能设计：
彻底废除“凭空假定一个整体增速 g”的粗暴估值做法：
1. 【生物制药与 AI 药物研发模型 (Pipeline rNPV)】：
   - 逐条拆解临床在研管线资产：临床阶段 (Phase 1/2/3)、临床成功概率 (POS)、适应症峰值销售、分成比例 (Royalty) 与排他专利年限；
   - 严格进行风险调整净现值 (rNPV) 逐年贴现与资产加总；
   - 健全金融有限责任下界与资不抵债边界防御，杜绝负数公允股价语病；
2. 【SaaS 与企业级云服务单体模型 (ARR / ARPU / NRR / LTV / CAC)】：
   - 拆解付费席位数、客单价 (ARPU)、净金额留存率 (NRR)、获客成本回收期 (CAC Payback) 与 LTV/CAC；
   - 测算 SaaS 销售效率魔力数字 (Magic Number) 并提供机构级健康度评级；
3. 【硬件终端与先进制造量价模型 (P × Q)】：
   - 拆解产品线出货台数 (Shipment Volume Q)、平均售价 (ASP P) 与 BOM 硬件成本，推导结构性毛利率。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PipelineAsset:
    """创新药/AI制药单条在研管线微观资产。"""
    asset_name: str                  # 如 "REC-994 (海绵状血管瘤 CCM)"
    phase: str                       # "Phase 1", "Phase 2", "Phase 3", "Filed", "Approved"
    pos: float                       # 临床与获批成功概率 (Phase 1: 0.10, Phase 2: 0.28, Phase 3: 0.58)
    peak_annual_sales: float         # 商业化峰值年销售额 (百万美元)
    royalty_take_rate: float         # 公司分成/许可比例 (如 0.15 代表 15% 销售分成)
    years_to_peak: int               # 距离峰值销售年限 (如 5 年)
    commercial_life_years: int = 10  # 专利保护与商业化高毛利持续年限
    indications_zh: str = ""         # 适应症描述


@dataclass(frozen=True)
class BiotechRNPVResult:
    """创新药管线 rNPV 估值与单股价值推导结果。"""
    ticker: str
    total_pipeline_rnpv: float       # 管线风险折现总价值 (百万美元/百万日元/百万元)
    net_cash: float                  # 账面净现金储备
    platform_technology_value: float # 专有算法/湿实验超算底层技术平台清算溢价
    total_firm_equity_value: float   # 权益总价值
    shares: float                    # 稀释总股本 (百万股)
    rnpv_fair_value_per_share: float # 基于 rNPV 的每股公允价值 (有限责任下界 >= 0.0)
    asset_breakdowns: List[Dict[str, Any]] # 各条管线明细估值
    deduction_notes_zh: str          # 推导演绎说明
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    currency_symbol: str = "$"       # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        curr = self.currency_symbol or "$"
        return {
            "ticker": self.ticker,
            "valuation_summary": {
                "pipeline_rnpv": f"{curr}{self.total_pipeline_rnpv:,.2f}M",
                "net_cash": f"{curr}{self.net_cash:,.2f}M",
                "platform_tech_value": f"{curr}{self.platform_technology_value:,.2f}M",
                "firm_equity_value": f"{curr}{self.total_firm_equity_value:,.2f}M",
                "shares": f"{self.shares:,.2f}M 股",
                "fair_value_per_share": f"{curr}{self.rnpv_fair_value_per_share:.2f}",
            },
            "pipeline_assets": self.asset_breakdowns,
            "deduction_rationale": self.deduction_notes_zh,
            "narrative_zh": self.narrative_zh or self.deduction_notes_zh,
        }


@dataclass(frozen=True)
class SaaSUnitEconomicsInput:
    """SaaS 与云服务微观单体经济指标输入。"""
    ticker: str
    arr_millions: float               # 当前年度经常性收入 ARR (百万单位)
    ending_customers_count: int       # 期末付费客户总数
    nrr_pct: float                    # 净金额留存率 Net Revenue Retention % (如 115.0 代表 115%)
    gross_margin_pct: float           # 订阅服务毛利率 % (如 75.0 代表 75%)
    cac_spend_millions: float         # 期间获客与销售市场支出 S&M (百万单位)
    new_customers_added: int          # 期间净增/新签约客户数
    net_new_arr_millions: float       # 期间净增 ARR (百万单位)
    market: Optional[str] = None      # 交易市场 ("US" / "JP" / "CN"，未指定时自适应推导)
    currency_symbol: Optional[str] = None # 显式指定货币符号 ("$", "¥")


@dataclass(frozen=True)
class SaaSUnitEconomicsResult:
    """SaaS 微观单体经济学诊断结果。"""
    ticker: str
    arpu_dollars: float               # 平均单客年收入 ARPU
    cac_per_customer_dollars: float   # 单个客户获取成本 CAC
    ltv_cac_ratio: float              # 客户生命周期价值与获客成本比值 LTV/CAC
    cac_payback_months: float         # 获客成本回收期 (月)
    magic_number: float               # SaaS 效率魔力指标 Net New ARR / S&M Spend
    health_grade: str                 # 单元经济学健康分级
    verdict_zh: str                   # 商业模型微观投资研判
    narrative_zh: str = ""            # 买方通俗全息研报卡片 (去工程符号化)
    health_grade_zh: str = ""         # 纯自然中文分级 (去工程符号化)
    currency_symbol: str = "$"        # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        curr = self.currency_symbol or "$"
        return {
            "ticker": self.ticker,
            "arpu": f"{curr}{self.arpu_dollars:,.0f} / 年",
            "cac": f"{curr}{self.cac_per_customer_dollars:,.0f}",
            "ltv_cac_ratio": f"{self.ltv_cac_ratio:.1f}x",
            "cac_payback_months": f"{self.cac_payback_months:.1f} 个月",
            "magic_number": f"{self.magic_number:.2f}",
            "health_grade": self.health_grade,
            "health_grade_zh": self.health_grade_zh or self.health_grade,
            "verdict": self.verdict_zh,
            "narrative_zh": self.narrative_zh or self.verdict_zh,
        }


class UnitEconomicsEngine:
    """商业模式微观驱动量化引擎。"""

    @classmethod
    def calculate_biotech_rnpv(
        cls,
        ticker: str,
        shares: float,
        net_cash: float,
        wacc: float,
        pipelines: List[PipelineAsset],
        platform_base_value: float = 300.0, # 底层 50PB 数据与自动化超算工厂平台估值
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> BiotechRNPVResult:
        """执行专业级创新药管线 rNPV (Risk-Adjusted Net Present Value) 折现测算。"""
        if not pipelines:
            raise ValueError("rNPV 测算至少需要输入一条在研管线")
        safe_shares = max(0.01, shares)
        safe_wacc = max(0.01, min(0.50, wacc))

        # 自适应推导市场与货币符号
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

        total_pipe_val = 0.0
        breakdowns = []

        for p in pipelines:
            # 测算单条管线：商业化期现金流
            # 年化分成收入 = 峰值销售 * 提成比例
            annual_cashflow = max(0.0, p.peak_annual_sales) * max(0.0, p.royalty_take_rate)

            # 贴现到上市首年 (折现期 = years_to_peak - 2)
            pv_cashflows = 0.0
            launch_years = max(1, p.years_to_peak - 2)
            safe_pos = max(0.0, min(1.0, p.pos))
            safe_life = max(1, p.commercial_life_years)

            for t in range(1, safe_life + 1):
                discount_period = launch_years + t
                pv_cashflows += annual_cashflow / ((1.0 + safe_wacc) ** discount_period)

            # 风险加权 POS
            rnpv_asset = pv_cashflows * safe_pos
            total_pipe_val += rnpv_asset

            breakdowns.append({
                "asset": p.asset_name,
                "phase": p.phase,
                "pos": f"{safe_pos * 100:.1f}%",
                "peak_sales": f"{curr_sym}{p.peak_annual_sales:,.0f}M",
                "royalty": f"{p.royalty_take_rate * 100:.1f}%",
                "discounted_unadjusted_pv": f"{curr_sym}{pv_cashflows:,.1f}M",
                "rnpv_contribution": f"{curr_sym}{rnpv_asset:,.1f}M",
                "per_share_contribution": f"{curr_sym}{rnpv_asset / safe_shares:.2f}",
            })

        total_firm_equity = total_pipe_val + net_cash + platform_base_value

        # 金融有限责任下界防御：股东价值绝无负数下界
        if total_firm_equity <= 0.0:
            fair_value_per_share = 0.0
            rationale = (
                f"基于 {len(pipelines)} 条核心在研管线的微观 rNPV 折现总值 ({curr_sym}{total_pipe_val:,.1f}M) 及平台价值 "
                f"({curr_sym}{platform_base_value:,.1f}M)，无法覆盖账面巨额净负债 ({curr_sym}{abs(net_cash):,.1f}M)；"
                f"在股东有限责任约束下，每股理论清算公允价值归零 ({curr_sym}0.00)，企业正面临实质性资不抵债与重组清盘风险。"
            )
        else:
            fair_value_per_share = total_firm_equity / safe_shares
            rationale = (
                f"基于 {len(pipelines)} 条核心研发管线的微观 rNPV 概率加权模型：管线折现总值 {curr_sym}{total_pipe_val:,.1f}M，"
                f"叠加账面手头净现金 {curr_sym}{net_cash:,.1f}M 以及专有超算数据平台价值 {curr_sym}{platform_base_value:,.1f}M，"
                f"折合总权益价值 {curr_sym}{total_firm_equity:,.1f}M；除以 {safe_shares:.1f}M 股，推导每股微观公允价值为 {curr_sym}{fair_value_per_share:.2f}。"
            )

        narrative_zh = (
            f"【标的 {ticker} 创新药管线 rNPV 估值全息研报】"
            f"微观管线加总价值: 覆盖 {len(pipelines)} 条核心在研管线，风险调整净现值 rNPV 合计 {curr_sym}{total_pipe_val:,.1f}M；"
            f"资产负债体魄: 账面净现金储备 {curr_sym}{net_cash:,.1f}M，专有算法与超算底层平台估值 {curr_sym}{platform_base_value:,.1f}M；"
            f"股东每股微观公允价值为 {curr_sym}{fair_value_per_share:.2f} (稀释总股本 {safe_shares:.1f}M 股)。"
            f"买方估值推导逻辑: {rationale}"
        )

        return BiotechRNPVResult(
            ticker=ticker,
            total_pipeline_rnpv=round(total_pipe_val, 2),
            net_cash=round(net_cash, 2),
            platform_technology_value=round(platform_base_value, 2),
            total_firm_equity_value=round(total_firm_equity, 2),
            shares=round(safe_shares, 2),
            rnpv_fair_value_per_share=round(fair_value_per_share, 2),
            asset_breakdowns=breakdowns,
            deduction_notes_zh=rationale,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def calculate_saas_unit_economics(
        cls,
        inp: SaaSUnitEconomicsInput,
    ) -> SaaSUnitEconomicsResult:
        """测算 SaaS / 企业级订阅制微观单体经济模型 (ARR, ARPU, NRR, CAC Payback, LTV/CAC)."""
        safe_cust = max(1, inp.ending_customers_count)
        # ARPU: ARR / 客户总数
        arpu = (inp.arr_millions * 1_000_000.0) / safe_cust

        # CAC: 获客投入 / 新增客户数
        safe_new_cust = max(1, inp.new_customers_added)
        cac = (inp.cac_spend_millions * 1_000_000.0) / safe_new_cust

        # 客户流失率测算: 基于 NRR 与常规留存假设 (Churn Rate 估算)
        # 若 NRR >= 100%, 净流失为负(负流失金矿)；客户基准毛利率加权
        gross_margin = max(0.10, min(0.95, inp.gross_margin_pct / 100.0))

        # 典型客户留存生命周期推导 (年)
        # 当 NRR >= 120% 时，客户流失极低，预估平均客户生命周期达 7-8 年；NRR 低于 90% 时约为 2-3 年
        if inp.nrr_pct >= 120.0:
            est_lifetime_years = 7.0
        elif inp.nrr_pct >= 105.0:
            est_lifetime_years = 5.0
        elif inp.nrr_pct >= 95.0:
            est_lifetime_years = 3.5
        else:
            est_lifetime_years = 2.0

        # LTV = ARPU * Gross Margin * Lifetime
        ltv = arpu * gross_margin * est_lifetime_years
        ltv_cac = ltv / max(1.0, cac)

        # CAC Payback (月数): CAC / (ARPU * Gross Margin / 12)
        annual_gross_profit_per_user = max(1.0, arpu * gross_margin)
        cac_payback_months = (cac / annual_gross_profit_per_user) * 12.0

        # Magic Number: (期间净增 ARR / 期间 S&M 支出)
        magic_number = inp.net_new_arr_millions / max(0.01, inp.cac_spend_millions)

        # 自适应推导市场与货币符号
        t_up = (inp.ticker or "").upper()
        m_up = (inp.market or "").upper()
        is_jp = m_up == "JP" or t_up.endswith(".T") or t_up.endswith(".JP") or (t_up.isdigit() and len(t_up) == 4)
        is_cn = m_up == "CN" or t_up.endswith(".SS") or t_up.endswith(".SZ") or (t_up.isdigit() and len(t_up) == 6)
        if inp.currency_symbol:
            curr_sym = inp.currency_symbol
        elif is_jp or is_cn:
            curr_sym = "¥"
        else:
            curr_sym = "$"

        # 单元经济学评级与投资研判 (纯自然中文去工程符号化与商业直觉优先)
        if ltv_cac >= 4.0 and cac_payback_months <= 15.0 and inp.nrr_pct >= 115.0:
            grade_zh = "优秀现金牛飞轮 (极高客户忠诚度与获客杠杆)"
            grade = grade_zh
            verdict = (
                f"单体经济学极度健康：LTV/CAC 达 {ltv_cac:.1f}x，CAC 回收期仅需 {cac_payback_months:.1f} 个月 "
                f"(显著优于行业 18 个月中位数)；NRR 净金额留存高达 {inp.nrr_pct:.1f}%，魔力数字 {magic_number:.2f}，"
                "表明投入销售费用能高效转化为确定性 ARR 扩张，属于典型的 SaaS 增长飞轮标的。"
            )
        elif ltv_cac >= 2.5 and cac_payback_months <= 24.0:
            grade_zh = "健康稳健扩张 (具备持续扩张潜力)"
            grade = grade_zh
            verdict = (
                f"商业模式稳健：LTV/CAC 为 {ltv_cac:.1f}x，CAC 回收期 {cac_payback_months:.1f} 个月，"
                f"NRR 为 {inp.nrr_pct:.1f}%，销售拓展保持合理回报，需进一步优化大客户留存与向上增购转化率。"
            )
        else:
            grade_zh = "烧钱失血警报 (获客成本过高或流失严重)"
            grade = grade_zh
            verdict = (
                f"微观单元经济学存在严重失血隐患：CAC 回收期长达 {cac_payback_months:.1f} 个月，"
                f"LTV/CAC 仅为 {ltv_cac:.1f}x；NRR ({inp.nrr_pct:.1f}%) 低于健康扩张阈值，"
                "盲目扩大销售团队与市场费用将带来沉重现金流消耗，面临价值毁灭风险。"
            )

        payback_term = (
            f"仅需 {cac_payback_months:.1f} 个月" if cac_payback_months <= 15.0
            else f"需 {cac_payback_months:.1f} 个月" if cac_payback_months <= 24.0
            else f"长达 {cac_payback_months:.1f} 个月"
        )
        narrative_zh = (
            f"【标的 {inp.ticker} SaaS 与云服务微观单体经济全息研报】"
            f"单体健康度评级为【{grade_zh}】。"
            f"客户获客与生命周期: 平均单客年收入 ARPU {curr_sym}{arpu:,.0f}，获客成本 CAC {curr_sym}{cac:,.0f}，"
            f"客户生命周期价值比 LTV/CAC 为 {ltv_cac:.1f}x，CAC 回收期{payback_term}。"
            f"增长飞轮动能: 净金额留存率 NRR 为 {inp.nrr_pct:.1f}%，销售拓展魔力数字 Magic Number 为 {magic_number:.2f}。"
            f"买方单元经济学研判: {verdict}"
        )

        return SaaSUnitEconomicsResult(
            ticker=inp.ticker,
            arpu_dollars=round(arpu, 2),
            cac_per_customer_dollars=round(cac, 2),
            ltv_cac_ratio=round(ltv_cac, 2),
            cac_payback_months=round(cac_payback_months, 1),
            magic_number=round(magic_number, 2),
            health_grade=grade,
            verdict_zh=verdict,
            narrative_zh=narrative_zh,
            health_grade_zh=grade_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def calculate_hardware_volume_price(
        cls,
        segments: List[Dict[str, Any]], # [{"segment": "iPhone", "volume_m": 230.0, "asp": 920.0, "bom_cost": 460.0}]
        shares: float,
        currency_symbol: str = "$",
    ) -> Dict[str, Any]:
        """硬件与消费科技 P × Q 量价拆解计算器。"""
        total_rev = 0.0
        total_gross_profit = 0.0
        details = []
        curr_sym = currency_symbol or "$"
        for s in segments:
            vol = max(0.0, float(s.get("volume_m", 0.0)))
            asp = max(0.0, float(s.get("asp", 0.0)))
            bom = max(0.0, float(s.get("bom_cost", asp * 0.6)))
            rev = vol * asp
            gp = vol * (asp - bom)
            margin = (gp / rev) * 100.0 if rev > 0 else 0.0
            total_rev += rev
            total_gross_profit += gp
            details.append({
                "segment": s.get("segment", "Unknown"),
                "volume": f"{vol:.1f}M 台",
                "asp": f"{curr_sym}{asp:.2f}",
                "revenue": f"{curr_sym}{rev:,.1f}M",
                "gross_margin": f"{margin:.1f}%",
            })
        blended_margin = (total_gross_profit / total_rev) * 100.0 if total_rev > 0 else 0.0
        narrative_zh = (
            f"【硬件终端与制造业务 P×Q 微观量价拆解研报】"
            f"拆解 {len(segments)} 条主力产品线，合计贡献营收 {curr_sym}{total_rev:,.1f}M，毛利 {curr_sym}{total_gross_profit:,.1f}M；"
            f"整体综合毛利率为 {blended_margin:.1f}%。"
        )
        return {
            "total_revenue": f"{curr_sym}{total_rev:,.1f}M",
            "total_gross_profit": f"{curr_sym}{total_gross_profit:,.1f}M",
            "blended_gross_margin": f"{blended_margin:.1f}%",
            "segments_breakdown": details,
            "narrative_zh": narrative_zh,
        }

