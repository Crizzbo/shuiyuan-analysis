"""通用财务指标计算引擎与封装类 (Generic Financial Metrics Engine)

业务定位：
1. 将跨行业通用的财务指标（盈利能力、流动性、偿债能力、现金流、估值倍数）封装为面向对象的独立计算类；
2. 提供清晰的中文注解、输入合法性校验、除零异常安全防御及高精度格式化；
3. 输出具备审计凭据的结构化结果（保留计算公式、分子分母、规范化数值及显示文本）；
4. 作为基础底座，与各行业专有驱动指标（如银行 NIM、半导体利用率、航司客座率）形成解耦分层架构。
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class MetricResult:
    """指标计算审计结果对象。"""
    metric_id: str
    name_zh: str
    category_zh: str
    value: float
    display_value: str
    formula_zh: str
    numerator: float
    denominator: float
    unit: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name_zh": self.name_zh,
            "category_zh": self.category_zh,
            "value": self.value,
            "display_value": self.display_value,
            "formula_zh": self.formula_zh,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "unit": self.unit,
        }


class GenericFinancialMetrics:
    """通用财务指标计算与体检引擎。

    涵盖五大维度：
    1. 盈利能力 (Profitability): ROE, ROA, 毛利率, 营业利润率, 净利率;
    2. 流动性 (Liquidity): 流动比率, 速动比率, 现金比率;
    3. 资本结构与偿债 (Solvency): 资产负债率, 产权比率, 利息保障倍数;
    4. 现金流质量 (Cash Flow Quality): 自由现金流收益率, 净利润现金含量;
    5. 市场估值乘数 (Valuation Multiples): PE, PB, PS, EV/EBITDA。
    """

    @staticmethod
    def _validate_positive(val: float, name: str) -> float:
        if val is None or not math.isfinite(val) or val <= 0:
            raise ValueError(f"{name} 必须为大于0的正数，当前输入: {val}")
        return float(val)

    @staticmethod
    def _validate_finite(val: float, name: str) -> float:
        if val is None or not math.isfinite(val):
            raise ValueError(f"{name} 必须为有限数值，当前输入: {val}")
        return float(val)

    # ==========================================
    # 1. 盈利能力指标 (Profitability Metrics)
    # ==========================================

    @classmethod
    def roe(cls, net_income: float, equity: float) -> MetricResult:
        """净资产收益率 (ROE) = 净利润 / 所有者权益。"""
        num = cls._validate_finite(net_income, "净利润")
        den = cls._validate_positive(equity, "所有者权益")
        val = num / den
        return MetricResult(
            metric_id="roe",
            name_zh="净资产收益率 (ROE)",
            category_zh="盈利能力",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="净利润 / 所有者权益",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    @classmethod
    def roa(cls, net_income: float, total_assets: float) -> MetricResult:
        """总资产收益率 (ROA) = 净利润 / 总资产。"""
        num = cls._validate_finite(net_income, "净利润")
        den = cls._validate_positive(total_assets, "总资产")
        val = num / den
        return MetricResult(
            metric_id="roa",
            name_zh="总资产收益率 (ROA)",
            category_zh="盈利能力",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="净利润 / 总资产",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    @classmethod
    def gross_margin(cls, gross_profit: float, revenue: float) -> MetricResult:
        """毛利率 = 毛利润 / 营业收入。"""
        num = cls._validate_finite(gross_profit, "毛利润")
        den = cls._validate_positive(revenue, "营业收入")
        val = num / den
        return MetricResult(
            metric_id="gross_margin",
            name_zh="销售毛利率",
            category_zh="盈利能力",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="毛利润 / 营业收入",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    @classmethod
    def operating_margin(cls, operating_income: float, revenue: float) -> MetricResult:
        """营业利润率 = 营业利润 / 营业收入。"""
        num = cls._validate_finite(operating_income, "营业利润")
        den = cls._validate_positive(revenue, "营业收入")
        val = num / den
        return MetricResult(
            metric_id="operating_margin",
            name_zh="营业利润率",
            category_zh="盈利能力",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="营业利润 / 营业收入",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    @classmethod
    def net_margin(cls, net_income: float, revenue: float) -> MetricResult:
        """净利率 = 净利润 / 营业收入。"""
        num = cls._validate_finite(net_income, "净利润")
        den = cls._validate_positive(revenue, "营业收入")
        val = num / den
        return MetricResult(
            metric_id="net_margin",
            name_zh="销售净利率",
            category_zh="盈利能力",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="净利润 / 营业收入",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    # ==========================================
    # 2. 流动性与短期偿债指标 (Liquidity Metrics)
    # ==========================================

    @classmethod
    def current_ratio(cls, current_assets: float, current_liabilities: float) -> MetricResult:
        """流动比率 = 流动资产 / 流动负债。"""
        num = cls._validate_finite(current_assets, "流动资产")
        den = cls._validate_positive(current_liabilities, "流动负债")
        val = num / den
        return MetricResult(
            metric_id="current_ratio",
            name_zh="流动比率",
            category_zh="流动性与偿债",
            value=round(val, 4),
            display_value=f"{val:.2f}x",
            formula_zh="流动资产 / 流动负债",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    @classmethod
    def quick_ratio(cls, quick_assets: float, current_liabilities: float) -> MetricResult:
        """速动比率 = 速动资产 (货币资金+应收账款) / 流动负债。"""
        num = cls._validate_finite(quick_assets, "速动资产")
        den = cls._validate_positive(current_liabilities, "流动负债")
        val = num / den
        return MetricResult(
            metric_id="quick_ratio",
            name_zh="速动比率",
            category_zh="流动性与偿债",
            value=round(val, 4),
            display_value=f"{val:.2f}x",
            formula_zh="速动资产 / 流动负债",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    @classmethod
    def cash_ratio(cls, cash_and_equivalents: float, current_liabilities: float) -> MetricResult:
        """现金比率 = 现金及现金等价物 / 流动负债。"""
        num = cls._validate_finite(cash_and_equivalents, "现金及等价物")
        den = cls._validate_positive(current_liabilities, "流动负债")
        val = num / den
        return MetricResult(
            metric_id="cash_ratio",
            name_zh="现金比率",
            category_zh="流动性与偿债",
            value=round(val, 4),
            display_value=f"{val:.2f}x",
            formula_zh="现金及等价物 / 流动负债",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    # ==========================================
    # 3. 资本结构与长期偿债指标 (Solvency Metrics)
    # ==========================================

    @classmethod
    def debt_to_assets(cls, total_debt: float, total_assets: float) -> MetricResult:
        """资产负债率 = 总带息负债 / 总资产。"""
        num = cls._validate_finite(total_debt, "总负债")
        den = cls._validate_positive(total_assets, "总资产")
        val = num / den
        return MetricResult(
            metric_id="debt_to_assets",
            name_zh="资产负债率",
            category_zh="资本结构与偿债",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="总负债 / 总资产",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    @classmethod
    def debt_to_equity(cls, total_debt: float, equity: float) -> MetricResult:
        """产权比率 (D/E) = 总带息负债 / 所有者权益。"""
        num = cls._validate_finite(total_debt, "总带息负债")
        den = cls._validate_positive(equity, "所有者权益")
        val = num / den
        return MetricResult(
            metric_id="debt_to_equity",
            name_zh="产权比率 (Debt-to-Equity)",
            category_zh="资本结构与偿债",
            value=round(val, 4),
            display_value=f"{val:.2f}x",
            formula_zh="总带息负债 / 所有者权益",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    @classmethod
    def interest_coverage(cls, ebit: float, interest_expense: float) -> MetricResult:
        """利息保障倍数 = 息税前利润 (EBIT) / 利息费用。"""
        num = cls._validate_finite(ebit, "息税前利润 (EBIT)")
        den = cls._validate_positive(interest_expense, "利息费用")
        val = num / den
        return MetricResult(
            metric_id="interest_coverage",
            name_zh="利息保障倍数",
            category_zh="资本结构与偿债",
            value=round(val, 2),
            display_value=f"{val:.2f}x",
            formula_zh="EBIT / 利息费用",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    # ==========================================
    # 4. 现金流与收益质量 (Cash Flow Quality)
    # ==========================================

    @classmethod
    def fcf_yield(cls, free_cash_flow: float, market_cap: float) -> MetricResult:
        """自由现金流收益率 = 自由现金流 (FCF) / 总市值。"""
        num = cls._validate_finite(free_cash_flow, "自由现金流")
        den = cls._validate_positive(market_cap, "总市值")
        val = num / den
        return MetricResult(
            metric_id="fcf_yield",
            name_zh="自由现金流收益率 (FCF Yield)",
            category_zh="现金流质量",
            value=round(val, 6),
            display_value=f"{val * 100:.2f}%",
            formula_zh="自由现金流 / 总市值",
            numerator=num,
            denominator=den,
            unit="ratio",
        )

    @classmethod
    def operating_cash_flow_ratio(cls, operating_cash_flow: float, net_income: float) -> MetricResult:
        """净利润现金含量 = 经营活动现金净额 / 净利润。"""
        num = cls._validate_finite(operating_cash_flow, "经营现金流")
        den = cls._validate_positive(net_income, "净利润")
        val = num / den
        return MetricResult(
            metric_id="ocf_to_net_income",
            name_zh="净利润现金含量",
            category_zh="现金流质量",
            value=round(val, 4),
            display_value=f"{val:.2f}x",
            formula_zh="经营活动现金净额 / 净利润",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    # ==========================================
    # 5. 市场估值乘数 (Valuation Multiples)
    # ==========================================

    @classmethod
    def pe(cls, price: float, eps: float) -> MetricResult:
        """市盈率 (P/E) = 市价 / 每股收益 (EPS)。"""
        num = cls._validate_positive(price, "每股市价")
        den = cls._validate_positive(eps, "每股收益 (EPS)")
        val = num / den
        return MetricResult(
            metric_id="pe",
            name_zh="市盈率 (P/E)",
            category_zh="市场估值倍数",
            value=round(val, 2),
            display_value=f"{val:.2f}x",
            formula_zh="市价 / EPS",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    @classmethod
    def pb(cls, price: float, bps: float) -> MetricResult:
        """市净率 (P/B) = 市价 / 每股净资产 (BPS)。"""
        num = cls._validate_positive(price, "每股市价")
        den = cls._validate_positive(bps, "每股净资产 (BPS)")
        val = num / den
        return MetricResult(
            metric_id="pb",
            name_zh="市净率 (P/B)",
            category_zh="市场估值倍数",
            value=round(val, 2),
            display_value=f"{val:.2f}x",
            formula_zh="市价 / BPS",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    @classmethod
    def ps(cls, market_cap: float, revenue: float) -> MetricResult:
        """市销率 (P/S) = 总市值 / 营业收入。"""
        num = cls._validate_positive(market_cap, "总市值")
        den = cls._validate_positive(revenue, "营业收入")
        val = num / den
        return MetricResult(
            metric_id="ps",
            name_zh="市销率 (P/S)",
            category_zh="市场估值倍数",
            value=round(val, 2),
            display_value=f"{val:.2f}x",
            formula_zh="总市值 / 营业收入",
            numerator=num,
            denominator=den,
            unit="multiple",
        )

    # ==========================================
    # 6. 综合体检报告批处理 (Batch Profile Calculation)
    # ==========================================

    @classmethod
    def compute_health_profile(cls, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """消费结构化财务底表，一次性批量推导全套通用财务比率。

        支持字段（按需提供）：
        - net_income, equity, total_assets, revenue, gross_profit, operating_income
        - current_assets, current_liabilities, quick_assets, cash_and_equivalents
        - total_debt, interest_expense, free_cash_flow, market_cap, operating_cash_flow
        - price, eps, bps
        """
        results: Dict[str, Any] = {}
        errors: List[str] = []

        def safe_compute(key: str, func, *args):
            try:
                res = func(*args)
                results[key] = res.to_dict()
            except (ValueError, TypeError, KeyError) as e:
                errors.append(f"{key}: {str(e)}")

        d = raw_data
        # 盈利
        if "net_income" in d and "average_equity" in d:
            safe_compute("roe", cls.roe, d["net_income"], d["average_equity"])
        if "net_income" in d and "average_total_assets" in d:
            safe_compute("roa", cls.roa, d["net_income"], d["average_total_assets"])
        if "gross_profit" in d and "revenue" in d:
            safe_compute("gross_margin", cls.gross_margin, d["gross_profit"], d["revenue"])
        if "operating_income" in d and "revenue" in d:
            safe_compute("operating_margin", cls.operating_margin, d["operating_income"], d["revenue"])
        if "net_income" in d and "revenue" in d:
            safe_compute("net_margin", cls.net_margin, d["net_income"], d["revenue"])

        # 流动性
        if "current_assets" in d and "current_liabilities" in d:
            safe_compute("current_ratio", cls.current_ratio, d["current_assets"], d["current_liabilities"])
        if "quick_assets" in d and "current_liabilities" in d:
            safe_compute("quick_ratio", cls.quick_ratio, d["quick_assets"], d["current_liabilities"])
        if "cash_and_equivalents" in d and "current_liabilities" in d:
            safe_compute("cash_ratio", cls.cash_ratio, d["cash_and_equivalents"], d["current_liabilities"])

        # 偿债
        if "total_liabilities" in d and "total_assets" in d:
            safe_compute("debt_to_assets", cls.debt_to_assets, d["total_liabilities"], d["total_assets"])
        if "total_debt" in d and "equity" in d:
            safe_compute("debt_to_equity", cls.debt_to_equity, d["total_debt"], d["equity"])
        if "ebit" in d and "interest_expense" in d:
            safe_compute("interest_coverage", cls.interest_coverage, d["ebit"], d["interest_expense"])

        # 现金流
        if "free_cash_flow" in d and "market_cap" in d:
            safe_compute("fcf_yield", cls.fcf_yield, d["free_cash_flow"], d["market_cap"])
        if "operating_cash_flow" in d and "net_income" in d:
            safe_compute("ocf_to_net_income", cls.operating_cash_flow_ratio, d["operating_cash_flow"], d["net_income"])

        # 估值
        if "price" in d and "eps" in d:
            safe_compute("pe", cls.pe, d["price"], d["eps"])
        if "price" in d and "bps" in d:
            safe_compute("pb", cls.pb, d["price"], d["bps"])
        if "market_cap" in d and "revenue" in d:
            safe_compute("ps", cls.ps, d["market_cap"], d["revenue"])

        return {
            "computed_metrics_count": len(results),
            "metrics": results,
            "omitted_or_error_count": len(errors),
            "diagnostics": errors,
        }

    # ==========================================
    # 7. 宏观联动估值与敏感性分析 (Macro Integration)
    # ==========================================

    @classmethod
    def compute_macro_valuation_profile(
        cls,
        raw_data: Dict[str, Any],
        macro_context: Optional[Any] = None,
        beta: float = 1.0,
        growth_forecast: Optional[List[float]] = None,
        terminal_growth: float = 0.025,
    ) -> Dict[str, Any]:
        """将宏观经济基准（美债、汇率、通胀）注入微观财务分析，输出估值情景与敏感性画像。"""
        from financial_reporting.macro_valuation import MacroContext, MacroValuationEngine

        # 1. 基础财务指标体检
        health_profile = cls.compute_health_profile(raw_data)

        # 2. 宏观上下文接入（未显式传入则自动读取最新已核实快照）
        if macro_context is None:
            macro_context = MacroContext.load_latest()

        d = raw_data
        market_cap = d.get("market_cap", 0.0)
        total_debt = d.get("total_debt", 0.0)
        price = d.get("price", 0.0)
        shares = d.get("shares")
        if (shares is None or shares <= 0) and price > 0 and market_cap > 0:
            shares = market_cap / price

        # 3. 宏观敏感度画像
        sensitivity = MacroValuationEngine.macro_sensitivity_profile(d, macro_context)

        # 4. 若具备现金流与股本信息，推导三态宏观情景估值与买入区间
        scenario_res = None
        fcf = d.get("free_cash_flow") or d.get("operating_cash_flow")
        if fcf is not None and fcf > 0 and shares is not None and shares > 0 and market_cap > 0:
            growth_rates = growth_forecast or [0.12, 0.10, 0.08, 0.06, 0.05]
            net_debt = total_debt - d.get("cash_and_equivalents", 0.0)
            scenario_res = MacroValuationEngine.scenario_valuation(
                cash_flow=float(fcf),
                growth_rates=growth_rates,
                terminal_growth=terminal_growth,
                shares=float(shares),
                market_cap=float(market_cap),
                total_debt=float(total_debt),
                beta=beta,
                macro_context=macro_context,
                current_price=float(price) if price > 0 else None,
                net_debt=float(net_debt),
            )

        return {
            "health_profile": health_profile,
            "macro_context": macro_context.to_dict(),
            "macro_sensitivity": sensitivity,
            "macro_scenario_valuation": scenario_res,
        }
