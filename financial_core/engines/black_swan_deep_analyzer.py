"""黑天鹅宏观巨震与组合资产全息深度分析引擎 (Black Swan Shock Deep Analyzer).

遵循 Google Python 编程风格指南与《SPEC-06 资产负债表健康度与信用风险规格书》:
专门针对突发黑天鹅、资本开支退潮、无差别流动性踩踏事件开发:
1. 宏观去杠杆与黑天鹅烈度全息研判 (Black Swan Macro Regime Assessment);
2. 大资金避险路径与跨资产迁徙追踪 (Capital Flight Path Tracking);
3. 组合多标的微观血肉穿透与脆弱度分类 (Portfolio Micro-Flesh Stress Profiling);
4. 物理垄断资产“流动性提款机 (ATM Effect)”错杀识别与不对称击球定价;
5. 结构化生成符合买方机构风控准则的战术应对兵法卡片 (Tactical Action Cards).
"""

# 1. Python 标准库
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple

# 2. 第三方数学与科学计算库
# (纯原生依赖，无外置第三方)

# 3. 内部核心库 (纯相对导入，符合 Google 风格与架构物理单向解耦铁律)
from .macro_elastic_margin_engine import MacroElasticMarginEngine, MacroLiquidityState
from .macro_shock_transmission_engine import (
    AssetMicroVulnerabilityType,
    MacroRegimeState,
    MacroShockInput,
    MacroShockTransmissionEngine,
)


@dataclass(frozen=True)
class HoldingAssetSpec:
    """用户持仓标的特征契约数据契约.

    Attributes:
        ticker: 标的代码.
        company_name_zh: 公司中文名称.
        current_price: 现价.
        market_session: 交易时段 (如 '盘前', '盘中', '盘后', '前收盘').
        beta: 相对基准市场 Beta 弹性.
        debt_to_equity: 产权比率 (负债/股东权益).
        base_wacc: 基础加权平均资本成本 WACC.
        months_cash_runway: 现金消耗跑道月数 (可选).
        top_5_customer_share: 前五大客户集中度占比 (可选).
        has_monopoly_moat: 是否具备垄断性物理护城河.
        core_investment_thesis: 核心投资逻辑与买入假设.
    """

    ticker: str
    company_name_zh: str
    current_price: float
    market_session: str
    beta: float
    debt_to_equity: float
    base_wacc: float
    months_cash_runway: Optional[float] = None
    top_5_customer_share: Optional[float] = None
    has_monopoly_moat: bool = False
    core_investment_thesis: str = ""


@dataclass(frozen=True)
class BlackSwanAnalysisResult:
    """黑天鹅深度分析报告综合实体数据契约.

    Attributes:
        as_of_date: 分析基准日.
        macro_regime: 宏观流动性状态标签.
        macro_severity_level: 宏观危机烈度等级 (1~5级).
        carry_trade_stress_score: 日元套息交易平仓压力得分.
        converged_correlation: 极端踩踏下收敛的市场相关性.
        required_elastic_margin_pct: 机构硬性弹性安全边际要求 %.
        capital_flight_destinations: 大资金避险路径与跨资产迁徙清单.
        holdings_diagnostics: 各持仓标的微观穿透诊断列表.
        tactical_playbook_summary: 顶层买方战术操盘兵法摘要.
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        macro_severity_level_zh: 烈度等级自然中文命名.
    """

    as_of_date: str
    macro_regime: str
    macro_severity_level: int
    carry_trade_stress_score: float
    converged_correlation: float
    required_elastic_margin_pct: float
    capital_flight_destinations: List[Dict[str, str]]
    holdings_diagnostics: List[Dict[str, Any]]
    tactical_playbook_summary: str
    narrative_zh: str = ""
    macro_severity_level_zh: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "as_of_date": self.as_of_date,
            "macro_regime": self.macro_regime,
            "macro_severity_level": self.macro_severity_level,
            "macro_severity_level_zh": (
                self.macro_severity_level_zh
                or f"{self.macro_severity_level} 级"
            ),
            "carry_trade_stress_score": self.carry_trade_stress_score,
            "converged_correlation": self.converged_correlation,
            "required_elastic_margin_pct": (
                f"{self.required_elastic_margin_pct:.1f}%"
            ),
            "capital_flight_destinations": self.capital_flight_destinations,
            "holdings_diagnostics": self.holdings_diagnostics,
            "tactical_playbook_summary": self.tactical_playbook_summary,
            "narrative_zh": (
                self.narrative_zh or self.tactical_playbook_summary
            ),
        }


class BlackSwanDeepAnalyzer:
    """黑天鹅宏观巨震与组合资产全息深度分析调度器 (Google Python Style Guide 架构设计)."""

    def __init__(self):
        """初始化黑天鹅分析引擎."""
        self.version: str = "2.0.0"
        self.shock_engine = MacroShockTransmissionEngine()

    def analyze_event(
        self,
        macro_state: MacroLiquidityState,
        usdjpy_daily_change_pct: float,
        fed_liquidity_drain_billion: float,
        holdings: List[HoldingAssetSpec],
        as_of_date: str = "2026-11-03",
    ) -> BlackSwanAnalysisResult:
        """执行黑天鹅深度事件穿透分析.

        Args:
            macro_state: 宏观流动性基准状态实体.
            usdjpy_daily_change_pct: 美元兑日元汇率单日变动幅度 %.
            fed_liquidity_drain_billion: 美联储流动性单周回笼规模 (十亿美元).
            holdings: 组合持仓特征对象列表.
            as_of_date: 分析基准日期字符串.

        Returns:
            BlackSwanAnalysisResult 包含宏观评级、避险流向、各标的脆弱度诊断与战术兵法的结果对象.
        """
        # 1. 评估宏观弹性安全边际与纯宏观基准冲击
        elastic_res = MacroElasticMarginEngine.evaluate_elastic_margin(
            state=macro_state,
            base_margin_pct=20.0,
            is_tier0_quality=True,
        )

        base_macro_input = MacroShockInput(
            us_10y_yield=macro_state.term_spread_10y_2y_bps / 10000.0 + 0.040,
            usdjpy_rate=152.0,
            vix_index=macro_state.vix_index,
            usdjpy_daily_change_pct=usdjpy_daily_change_pct,
            fed_liquidity_drain_billion=fed_liquidity_drain_billion,
            company_beta=1.0,
            company_debt_to_equity=0.5,
            base_wacc=0.08,
        )
        base_shock_out = self.shock_engine.evaluate_macro_shock(base_macro_input)
        macro_carry_stress = base_shock_out["carry_trade_stress_score"]
        macro_converged_corr = base_shock_out["converged_market_correlation"]

        # 2. 结构化大资金避险路径
        capital_flight_destinations = self._build_capital_flight_destinations()

        # 3. 逐一穿透诊断持仓标的
        diagnostics = [
            self._diagnose_single_holding(
                h=h,
                macro_state=macro_state,
                usdjpy_daily_change_pct=usdjpy_daily_change_pct,
                fed_liquidity_drain_billion=fed_liquidity_drain_billion,
            )
            for h in holdings
        ]

        # 4. 提炼顶层买方战术操盘兵法
        tactical_summary = self._synthesize_tactical_playbook(
            diagnostics=diagnostics,
            regime_label=elastic_res.regime_label,
        )

        severity_lvl = (
            5
            if elastic_res.stress_score >= 0.75
            else (3 if elastic_res.stress_score >= 0.50 else 2)
        )

        # 5. 生成买方通俗自然语言研报卡片
        narrative_zh = self._render_narrative(
            regime_label=elastic_res.regime_label,
            severity_lvl=severity_lvl,
            macro_carry_stress=macro_carry_stress,
            macro_converged_corr=macro_converged_corr,
            elastic_margin_pct=elastic_res.elastic_margin_pct,
            tactical_summary=tactical_summary,
        )

        return BlackSwanAnalysisResult(
            as_of_date=as_of_date,
            macro_regime=elastic_res.regime_label,
            macro_severity_level=severity_lvl,
            carry_trade_stress_score=round(macro_carry_stress, 2),
            converged_correlation=round(macro_converged_corr, 4),
            required_elastic_margin_pct=elastic_res.elastic_margin_pct,
            capital_flight_destinations=capital_flight_destinations,
            holdings_diagnostics=diagnostics,
            tactical_playbook_summary=tactical_summary,
            narrative_zh=narrative_zh,
            macro_severity_level_zh=f"{severity_lvl} 级",
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _build_capital_flight_destinations() -> List[Dict[str, str]]:
        """定义大资金避险迁徙路径 (私有辅助方法)."""
        return [
            {
                "category": "无风险超短债与高息现金工具",
                "instrument": "USD 超短国债 / 货币市场基金 (MMF)",
                "rationale": (
                    "美债收益率突破 4.2%，大机构锁定 4.5% 无风险利息，"
                    "拒绝在高位承担权益资产下行风险。"
                ),
                "allocation_stance": (
                    "超配/压舱石 (建议现金水位提升至 40%~60%)"
                ),
            },
            {
                "category": "抗通胀硬通货与去美元化资产",
                "instrument": "实物黄金 (GLD) / 低成本金矿股 (NEM)",
                "rationale": (
                    "主权央行持续增持黄金储备，对冲地缘冲突溢价与法币信用稀释。"
                ),
                "allocation_stance": "底仓标配 (维持 10%~15% 战略抗跌仓位)",
            },
            {
                "category": "低估值高造血实体现金牛",
                "instrument": "低成本页岩油 (EOG) / 防务军工 (LMT)",
                "rationale": (
                    "市盈率仅 10~13 倍，拥有极高自由现金流分红与回购，"
                    "在手刚性积压订单锁定未来数年收益。"
                ),
                "allocation_stance": "结构防守 (逐步替代纯远期梦想成长股)",
            },
        ]

    def _diagnose_single_holding(
        self,
        h: HoldingAssetSpec,
        macro_state: MacroLiquidityState,
        usdjpy_daily_change_pct: float,
        fed_liquidity_drain_billion: float,
    ) -> Dict[str, Any]:
        """穿透诊断单只持仓标的 (私有辅助方法)."""
        shock_in = MacroShockInput(
            us_10y_yield=macro_state.term_spread_10y_2y_bps / 10000.0 + 0.040,
            usdjpy_rate=152.0,
            vix_index=macro_state.vix_index,
            usdjpy_daily_change_pct=usdjpy_daily_change_pct,
            fed_liquidity_drain_billion=fed_liquidity_drain_billion,
            company_beta=h.beta,
            company_debt_to_equity=h.debt_to_equity,
            base_wacc=h.base_wacc,
            months_cash_runway=h.months_cash_runway,
            top_5_customer_share=h.top_5_customer_share,
            has_monopoly_moat=h.has_monopoly_moat,
        )
        shock_out = self.shock_engine.evaluate_macro_shock(shock_in)

        micro_meta = shock_out.get("micro_vulnerability_metadata", {})
        micro_name_zh = micro_meta.get("state_name", "财务均衡稳健型")
        lev_tier = shock_out.get("leverage_vulnerability_tier", "Low")
        lev_tier_zh = (
            "高杠杆危急"
            if lev_tier == "High"
            else ("中杠杆警惕" if lev_tier == "Medium" else "低杠杆安全")
        )

        return {
            "ticker": h.ticker,
            "company_name_zh": h.company_name_zh,
            "current_price": h.current_price,
            "market_session": h.market_session,
            "shocked_wacc_pct": shock_out["shocked_wacc_pct"],
            "valuation_haircut_pct": shock_out["valuation_haircut_pct"],
            "micro_vulnerability_type": shock_out["micro_vulnerability_type"],
            "micro_vulnerability_name_zh": micro_name_zh,
            "leverage_vulnerability_tier": lev_tier,
            "leverage_vulnerability_tier_zh": lev_tier_zh,
            "debt_to_equity": h.debt_to_equity,
            "is_atm_liquidity_victim": shock_out["is_atm_liquidity_victim"],
            "tactical_directive_zh": shock_out["tactical_directive_zh"],
            "core_thesis": h.core_investment_thesis,
        }

    @staticmethod
    def _synthesize_tactical_playbook(
        diagnostics: List[Dict[str, Any]], regime_label: str
    ) -> str:
        """动态提炼买方操盘战术兵法 (私有辅助方法)."""
        atm_victims = [
            d["ticker"]
            for d in diagnostics
            if d.get("is_atm_liquidity_victim")
        ]
        customer_risks = [
            d["ticker"]
            for d in diagnostics
            if d.get("micro_vulnerability_type")
            == AssetMicroVulnerabilityType.CAPEX_CYCLICAL_CONCENTRATED.value
            or "CONCENTRATED" in str(d.get("micro_vulnerability_type")).upper()
        ]
        runway_risks = [
            d["ticker"]
            for d in diagnostics
            if d.get("micro_vulnerability_type")
            == AssetMicroVulnerabilityType.CASH_BURN_LONG_DURATION.value
            or "CASH_BURN" in str(d.get("micro_vulnerability_type")).upper()
        ]
        high_debt_risks = [
            d["ticker"]
            for d in diagnostics
            if d.get("leverage_vulnerability_tier") == "High"
            or d.get("debt_to_equity", 0.0) >= 1.5
        ]

        tactical_directives: List[str] = []
        if atm_victims:
            tactical_directives.append(
                f"优质护城河/流动性提款机错杀标的（{', '.join(atm_victims)}）"
                "守住核心价值底线，拒绝恐慌低位割肉，耐心等待情绪反转；"
            )
        if customer_risks:
            tactical_directives.append(
                f"下游大客户高集中度标的（{', '.join(customer_risks)}）"
                "防范订单砍单反噬，严禁左侧盲目追高；"
            )
        if runway_risks:
            tactical_directives.append(
                f"现金跑道紧缩/长久期无造血标的（{', '.join(runway_risks)}）"
                "逢反弹果断控仓，防范久期杀估值风险；"
            )
        if high_debt_risks:
            tactical_directives.append(
                f"高负债/再融资承压标的（{', '.join(high_debt_risks)}）"
                "警惕利率走阔挤压利润，收紧风控止损；"
            )

        if not tactical_directives:
            holdings_directive_str = (
                "持仓整体财务稳健、资产负债表与现金造血能力优异，"
                "可安心按计划持有穿越风暴。"
            )
        else:
            holdings_directive_str = "针对当前持仓：" + "".join(
                tactical_directives
            )

        return (
            f"【宏观黑天鹅防守反击策略】当前市场处于 {regime_label}，"
            "跨资产踩踏收敛度高。大资金正全面从‘高估值未盈利题材’撤退至‘高息现金与低估值实体’。"
            f"{holdings_directive_str}"
        )

    @staticmethod
    def _render_narrative(
        regime_label: str,
        severity_lvl: int,
        macro_carry_stress: float,
        macro_converged_corr: float,
        elastic_margin_pct: float,
        tactical_summary: str,
    ) -> str:
        """渲染买方通俗自然语言研报卡片 (私有辅助方法)."""
        return (
            f"【宏观黑天鹅巨震与持仓微观穿透全息研报】"
            f"宏观流动性烈度: 当前处于【{regime_label}】(综合烈度评级为【{severity_lvl} 级】)，"
            f"日元套息平仓压力度 {macro_carry_stress:.1f}分，极端踩踏相关性收敛至 {macro_converged_corr:.2f}，"
            f"买方硬性弹性安全边际要求上浮至 {elastic_margin_pct:.1f}%。"
            f"大资金避险迁徙路径: 超配超短美债与现金管理工具，底仓持有黄金硬通货对冲法币稀释，"
            "结构防守低估值高造血实体现金牛。"
            f"操盘战术兵法指令: {tactical_summary}"
        )
