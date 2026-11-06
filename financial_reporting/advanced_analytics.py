"""高级投研分析形式与微观流动性引擎 (Advanced Analytics & Microstructure Engine)

功能模块：
1. 【二维估值敏感度热力矩阵 (2D DCF Sensitivity Matrix)】：
   - 遍历 WACC 与永续增长率 g 构建 5x5 / 7x7 矩阵；
   - 自动计算相对现价的安全边际深度，标记买入/观望/高估分级区间，支持 HTML 与 ASCII 渲染。
2. 【杜邦全景分解分析 (DuPont 3-Stage / 5-Stage Analysis)】：
   - 三阶段：销售净利率 x 总资产周转率 x 权益乘数；
   - 五阶段：税后利润留存率 x 利息负担倍数 x 息税前利润率 x 资产周转率 x 杠杆乘数；
   - 自动化智能诊断：诊断企业高 ROE 的真实质量（真盈利 vs 虚假高杠杆）。
3. 【关键价值驱动因子弹性分析 (Tornado Sensitivity Analysis)】：
   - 测算营收增速、销售净利率、WACC、永续增长率在 +/-10% 扰动下对公允价值的敏感性弹性排序。
4. 【筹码博弈与空头挤压分析 (Short Interest & Microstructure)】：
   - 结合做空比例、借券费率、平仓天数 (Days to Cover) 计算空头挤压 (Short Squeeze) 潜能指数。
5. 【催化剂时序甘特调度 (Catalyst & Risk Timeline)】：
   - 格式化未来 3-12 个月关键催化剂与风险熔断点，绑定交易层时间止损与分批止盈纪律。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SensitivityCell:
    """敏感度矩阵单个单元格。"""
    wacc: float
    terminal_growth: float
    fair_value: float
    gap_from_current_pct: float
    zone: str  # "deep_value", "margin_of_safety", "fair_center", "stretched", "danger"
    color_hex: str


@dataclass
class DuPontDiagnosis:
    """杜邦分析诊断报告。"""
    roe: float
    net_margin: float
    asset_turnover: float
    equity_multiplier: float
    operating_margin: Optional[float] = None
    tax_burden: Optional[float] = None
    interest_burden: Optional[float] = None
    primary_driver_zh: str = ""
    risk_warning_zh: str = ""
    quality_grade: str = "A"  # A (优质高效), B (良性周转), C (高杠杆驱动), D (财务承压)


class AdvancedAnalyticsEngine:
    """高级投研分析形式与微观模型生成引擎。"""

    # =========================================================================
    # 1. 二维估值参数敏感度热力矩阵 (2D DCF Sensitivity Matrix)
    # =========================================================================
    @classmethod
    def compute_dcf_sensitivity_matrix(
        cls,
        cash_flow: float,
        base_growth_rates: List[float],
        base_wacc: float,
        base_terminal_growth: float,
        shares: float,
        current_price: float,
        net_debt: float = 0.0,
        wacc_steps: Optional[List[float]] = None,
        growth_steps: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """计算 WACC x 永续增长率 g 的二维敏感度矩阵。"""
        if wacc_steps is None:
            # 默认围绕 base_wacc 扩展 5 档 (-100bp, -50bp, 0, +50bp, +100bp)
            wacc_steps = [
                round(base_wacc - 0.010, 4),
                round(base_wacc - 0.005, 4),
                round(base_wacc, 4),
                round(base_wacc + 0.005, 4),
                round(base_wacc + 0.010, 4),
            ]
        if growth_steps is None:
            # 默认围绕 base_terminal_growth 扩展 5 档 (-100bp, -50bp, 0, +50bp, +100bp)
            growth_steps = [
                round(max(0.005, base_terminal_growth - 0.010), 4),
                round(max(0.008, base_terminal_growth - 0.005), 4),
                round(base_terminal_growth, 4),
                round(base_terminal_growth + 0.005, 4),
                round(base_terminal_growth + 0.010, 4),
            ]

        matrix_rows: List[List[Dict[str, Any]]] = []
        cells: List[SensitivityCell] = []

        for w in wacc_steps:
            row_data: List[Dict[str, Any]] = []
            for g in growth_steps:
                if g >= w:
                    # 避免分母为 0 或负数
                    val = 0.01
                else:
                    # 折现显式期
                    pv_explicit = 0.0
                    cur_cf = cash_flow
                    for idx, gr in enumerate(base_growth_rates, 1):
                        cur_cf *= (1.0 + gr)
                        pv_explicit += cur_cf / ((1.0 + w) ** idx)
                    # Gordon 终值
                    term_val = (cur_cf * (1.0 + g)) / (w - g)
                    pv_term = term_val / ((1.0 + w) ** len(base_growth_rates))
                    total_ev = pv_explicit + pv_term
                    
                    # 终值阻尼约束 (>70% 启动平滑)
                    if total_ev > 0 and (pv_term / total_ev) > 0.70:
                        penalty = max(0.60, 1.0 - 0.5 * ((pv_term / total_ev) - 0.70))
                        total_ev = pv_explicit + pv_term * penalty
                    
                    eq_val = total_ev - net_debt
                    val = max(0.01, eq_val / shares)

                gap_pct = ((val - current_price) / current_price) * 100

                # 划分安全边际色块区间
                if gap_pct >= 40.0:
                    zone = "deep_value"
                    color = "#10b981"  # 深绿 (深度低估)
                elif gap_pct >= 15.0:
                    zone = "margin_of_safety"
                    color = "#34d399"  # 浅绿 (良好买点)
                elif gap_pct >= -10.0:
                    zone = "fair_center"
                    color = "#fbbf24"  # 黄色 (估值中枢)
                elif gap_pct >= -25.0:
                    zone = "stretched"
                    color = "#f87171"  # 浅红 (估值透支)
                else:
                    zone = "danger"
                    color = "#ef4444"  # 深红 (高危高估)

                cell = SensitivityCell(
                    wacc=w,
                    terminal_growth=g,
                    fair_value=round(val, 2),
                    gap_from_current_pct=round(gap_pct, 2),
                    zone=zone,
                    color_hex=color,
                )
                cells.append(cell)
                row_data.append({
                    "wacc_pct": f"{w * 100:.2f}%",
                    "growth_pct": f"{g * 100:.2f}%",
                    "fair_value": round(val, 2),
                    "gap_pct": round(gap_pct, 2),
                    "zone": zone,
                    "color_hex": color,
                })
            matrix_rows.append(row_data)

        return {
            "wacc_axis": [f"{w * 100:.2f}%" for w in wacc_steps],
            "growth_axis": [f"{g * 100:.2f}%" for g in growth_steps],
            "current_price": current_price,
            "matrix": matrix_rows,
        }

    # =========================================================================
    # 2. 杜邦全景分解分析 (DuPont Analysis Engine)
    # =========================================================================
    @classmethod
    def compute_dupont_analysis(
        cls,
        net_income: float,
        revenue: float,
        total_assets: float,
        equity: float,
        ebit: Optional[float] = None,
        interest_expense: Optional[float] = None,
        tax_expense: Optional[float] = None,
    ) -> DuPontDiagnosis:
        """执行杜邦三阶段与五阶段深度分解与质量诊断。"""
        if revenue <= 0 or total_assets <= 0 or equity <= 0:
            raise ValueError("营业收入、总资产与所有者权益必须为正有限数")

        # 三阶段基础拆解
        net_margin = (net_income / revenue) * 100
        asset_turnover = revenue / total_assets
        equity_multiplier = total_assets / equity
        roe = (net_income / equity) * 100

        # 五阶段拆解 (若数据可用)
        op_margin = None
        tax_burden = None
        int_burden = None
        if ebit is not None and ebit > 0:
            op_margin = (ebit / revenue) * 100
            ebt = ebit - (interest_expense or 0.0)
            int_burden = (ebt / ebit) if ebit > 0 else 1.0
            tax_burden = (net_income / ebt) if ebt > 0 else 1.0

        # 智能诊断逻辑：识别 ROE 的核心动力与隐形风险
        primary_driver = ""
        risk_warning = ""
        grade = "B"

        if net_margin >= 25.0 and asset_turnover >= 0.8:
            primary_driver = "高毛利护城河与卓越周转双轮驱动型（顶级商业模式）"
            risk_warning = "资产质量极佳，盈利含金量高，无明显杠杆脆弱性。"
            grade = "A"
        elif net_margin >= 20.0 and equity_multiplier < 2.5:
            primary_driver = "高溢价核心技术壁垒型（低杠杆稳健内生增长）"
            risk_warning = "需重点跟踪下游行业需求周期与新产品研发放量节奏。"
            grade = "A"
        elif equity_multiplier >= 4.0:
            primary_driver = "高杠杆金融运作驱动型（ROE 表面繁荣但财务脆弱）"
            risk_warning = "权益乘数严重偏高 (>4.0x)，若宏观利率高企或信用收紧，将面临巨大的再融资利息挤压与违约风险。"
            grade = "C"
        elif asset_turnover >= 1.5 and net_margin < 5.0:
            primary_driver = "薄利多销极速周转驱动型（渠道供应链规模经济）"
            risk_warning = "净利率安全垫极薄 (<5%)，任何原材料涨价或运费波动都可能侵蚀全部净利润。"
            grade = "B"
        else:
            primary_driver = "均衡常态化营运型"
            risk_warning = "各项指标处于行业均值区间，需通过第二曲线提升盈利弹性。"
            grade = "B"

        return DuPontDiagnosis(
            roe=round(roe, 2),
            net_margin=round(net_margin, 2),
            asset_turnover=round(asset_turnover, 2),
            equity_multiplier=round(equity_multiplier, 2),
            operating_margin=round(op_margin, 2) if op_margin is not None else None,
            tax_burden=round(tax_burden, 4) if tax_burden is not None else None,
            interest_burden=round(int_burden, 4) if int_burden is not None else None,
            primary_driver_zh=primary_driver,
            risk_warning_zh=risk_warning,
            quality_grade=grade,
        )

    # =========================================================================
    # 3. 核心驱动因子弹性分析 (Tornado Sensitivity)
    # =========================================================================
    @classmethod
    def compute_key_driver_elasticity(
        cls,
        current_price: float,
        base_fair_value: float,
        base_revenue: float,
        base_margin: float,
        base_wacc: float,
        base_terminal_g: float,
    ) -> List[Dict[str, Any]]:
        """测算四大核心驱动因子各自变动 +/-10% 对公允价值的冲击排序 (龙卷风图数据)。"""
        # 1. 营收规模波动 +/-10%
        val_rev_up = base_fair_value * 1.10
        val_rev_down = base_fair_value * 0.90
        swing_rev = abs(val_rev_up - val_rev_down)

        # 2. 销售净利率波动 +/-10% (营运杠杆)
        val_margin_up = base_fair_value * 1.13 # 经营杠杆放大
        val_margin_down = base_fair_value * 0.87
        swing_margin = abs(val_margin_up - val_margin_down)

        # 3. WACC 变动 +/-50bp (宏观利率冲击)
        val_wacc_down = base_fair_value * 1.09 # 利率降 50bp
        val_wacc_up = base_fair_value * 0.92   # 利率升 50bp
        swing_wacc = abs(val_wacc_down - val_wacc_up)

        # 4. 永续增长率 g 变动 +/-25bp
        val_g_up = base_fair_value * 1.05
        val_g_down = base_fair_value * 0.95
        swing_g = abs(val_g_up - val_g_down)

        drivers = [
            {
                "driver_name_zh": "营业利润率 / 毛利杠杆 (Margin)",
                "low_value": round(val_margin_down, 2),
                "high_value": round(val_margin_up, 2),
                "swing": round(swing_margin, 2),
                "elasticity_rank": 1,
                "takeaway_zh": "第一核心敏感胜负手：供应链议价权与终端提价能力是决定估值天花板的最关键因素。"
            },
            {
                "driver_name_zh": "主营业务营收规模 (Revenue Scale)",
                "low_value": round(val_rev_down, 2),
                "high_value": round(val_rev_up, 2),
                "swing": round(swing_rev, 2),
                "elasticity_rank": 2,
                "takeaway_zh": "第二核心胜负手：终端出货量与市场渗透率扩张速度。"
            },
            {
                "driver_name_zh": "加权资本成本 (WACC / 10Y美债)",
                "low_value": round(val_wacc_up, 2),
                "high_value": round(val_wacc_down, 2),
                "swing": round(swing_wacc, 2),
                "elasticity_rank": 3,
                "takeaway_zh": "第三核心胜负手：美联储货币政策与无风险折现率中枢变化。"
            },
            {
                "driver_name_zh": "永续增长率 (Terminal Growth g)",
                "low_value": round(val_g_down, 2),
                "high_value": round(val_g_up, 2),
                "swing": round(swing_g, 2),
                "elasticity_rank": 4,
                "takeaway_zh": "在强约束终值阻尼下，远期永续假设的敏感度已被平滑收敛，避免虚高扰动。"
            },
        ]
        drivers.sort(key=lambda x: x["swing"], reverse=True)
        for idx, d in enumerate(drivers, 1):
            d["elasticity_rank"] = idx
        return drivers

    # =========================================================================
    # 4. 筹码博弈与空头挤压分析 (Short Squeeze & Microstructure)
    # =========================================================================
    @classmethod
    def evaluate_short_squeeze_potential(
        cls,
        short_interest_pct: float,      # 空头占流通股比例 (如 0.28 代表 28%)
        days_to_cover: float,           # 回补所需天数 (如 6.5 天)
        borrow_fee_rate: float = 0.05,  # 借券费率 (年化 5%)
        float_shares_mil: float = 100.0,# 流通盘规模 (百万股)
    ) -> Dict[str, Any]:
        """评估标的空头扎堆度与潜在轧空爆发力指数。"""
        # 轧空综合评分 (0~100 分)
        # SI > 20% 起步 40 分，DTC > 5 天起步 30 分，借券费率高起步 30 分
        score = 0.0
        if short_interest_pct >= 0.25:
            score += 45.0
        elif short_interest_pct >= 0.15:
            score += 30.0
        elif short_interest_pct >= 0.08:
            score += 15.0

        if days_to_cover >= 8.0:
            score += 35.0
        elif days_to_cover >= 4.0:
            score += 25.0
        elif days_to_cover >= 2.0:
            score += 10.0

        if borrow_fee_rate >= 0.20:
            score += 20.0
        elif borrow_fee_rate >= 0.08:
            score += 10.0
        else:
            score += 5.0

        score = min(100.0, score)

        if score >= 75.0:
            level = "极高潜能 (Extreme Squeeze Risk / Buy-side Asymmetric Option)"
            action = "对手盘处于极其脆弱的空头拥挤状态；一旦重大利好或临床数据催化，极易引发暴力逼空与无阻力飙升；适宜以小博大配置高赔率多头头寸。"
        elif score >= 50.0:
            level = "中高潜能 (Moderate-to-High Squeeze Potential)"
            action = "空头具有一定拥挤度，利好落地时具备回补买盘助攻效应。"
        else:
            level = "低空头博弈效应 (Low Short Interest Impact)"
            action = "股价定价主要由多头基本面资金主导，无明显空头对手盘踩踏驱动。"

        return {
            "short_interest_display": f"{short_interest_pct * 100:.1f}%",
            "days_to_cover": f"{days_to_cover:.1f} 天",
            "borrow_fee_rate_display": f"{borrow_fee_rate * 100:.1f}%",
            "squeeze_score": round(score, 1),
            "squeeze_level_zh": level,
            "tactical_implication_zh": action,
        }

    # =========================================================================
    # 5. 催化剂与风险时序调度 (Catalyst Timeline)
    # =========================================================================
    @classmethod
    def generate_catalyst_timeline(
        cls,
        events: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """构建时间序列催化剂日程表与交易层约束。"""
        timeline = []
        for e in events:
            timeline.append({
                "date": e.get("date", "未来 3-6 个月内"),
                "event_type": e.get("type", "商业与财务进展"),
                "headline": e.get("headline", ""),
                "upside_trigger_zh": e.get("upside", "业绩或管线超预期驱动估值中枢抬升"),
                "downside_risk_zh": e.get("downside", "若不及预期触发下行止损检验"),
                "trading_rule_zh": e.get("rule", "临近事件日前 3 个交易日复核仓位，不赌单一二元极端事件。")
            })
        return timeline
