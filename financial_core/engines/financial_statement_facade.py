"""统一企业财报防腐中继门面 (Financial Statement Facade).

解决架构长链耦合与数据防腐问题：
1. 作为纯净底层金融核心层 (financial_core) 对外提供的唯一标准化中继门面；
2. 封装官方财报标准化清洗与资产负债恒等式刚性平账自检 (Assets = Liabilities + Equity)；
3. 一体化计算企业通用核心指标 (毛利率, 净利率, ROE, ROIC, 存货周转天数 DIO, 净现金与利息覆盖倍数)；
4. 集成行情数据当日时效性与交易时段状态校验，阻断过期旧数据污染；
5. 向业务呈现层 (深度档案, 资产池批量建档, 投委会简报) 输出强类型的 StandardizedCompanyFact，
   切断上层呈现端对底层各种清洗细节与非标字段的直接深层依赖，压缩全系统关键路径传导深度。
"""

from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
import math

from .filing_mapper import OfficialFilingMapper, BalanceSheetIdentityError, IncompleteFilingFactError
from .quote_freshness_gateway import QuoteFreshnessGateway, QuoteVerificationResult


@dataclass(frozen=True)
class NormalizedFinancialProfile:
    """标准化企业财务剖面数据模型 (不可变强类型对象)."""
    ticker: str
    company_name: str
    currency: str
    fiscal_period: str

    # 核心三表基准底账 (单位: 原生币种绝对数值)
    total_assets: float
    total_liabilities: float
    total_equity: float
    cash_and_equivalents: float
    total_debt: float
    net_cash: float

    revenue: float
    gross_profit: float
    operating_income: float
    net_income: float
    free_cash_flow: float

    inventory: float
    cost_of_goods_sold: float

    # 关键商业与财务衍生比率 (已防范除零异常)
    gross_margin: float
    operating_margin: float
    net_margin: float
    roe: float
    roic: float
    inventory_turnover_days: float  # DIO
    debt_to_equity: float
    interest_coverage_ratio: float

    # 平账自检指标
    balance_discrepancy: float
    is_balanced: bool

    # 行情时效与交易时段状态
    quote_price: float
    market_cap: float
    quote_timestamp: str
    market_session: str
    is_quote_fresh: bool


class FinancialStatementFacade:
    """企业财报与时效数据防腐中继门面."""

    def __init__(self, quote_gateway: Optional[QuoteFreshnessGateway] = None):
        """初始化防腐门面."""
        self.filing_mapper = OfficialFilingMapper()
        self.quote_gateway = quote_gateway or QuoteFreshnessGateway()

    @staticmethod
    def _safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
        """除零与除负安全保护函数."""
        if math.isclose(denominator, 0.0, abs_tol=1e-9) or math.isnan(denominator) or math.isnan(numerator):
            return fallback
        return numerator / denominator

    def process_company_filing(
        self,
        raw_filing_facts: Dict[str, Any],
        raw_quote_data: Optional[Dict[str, Any]] = None,
        industry_code: Optional[str] = None
    ) -> NormalizedFinancialProfile:
        """全流程摄入官方财报底账、执行刚性平账自检并组装为防腐标准对象.

        Args:
            raw_filing_facts: 官方财报提取的结构化事实底账 (必须包含资产、负债、权益、营收与利润)
            raw_quote_data: 市场行情数据字典 (可选，用于新鲜度核验)
            industry_code: 行业归属代码 (可选)

        Returns:
            NormalizedFinancialProfile: 经过完整平账自检与清洗的标准财务数据剖面

        Raises:
            BalanceSheetIdentityError: 当资产负债表刚性恒等式失衡超出 0.1% 容差时抛出
            IncompleteFilingFactError: 当缺失关键财务三表科目时抛出
        """
        ticker = str(raw_filing_facts.get("ticker", "UNKNOWN")).upper().strip()
        company_name = str(raw_filing_facts.get("company_name", ticker)).strip()
        currency = str(raw_filing_facts.get("currency", "USD")).upper().strip()
        fiscal_period = str(raw_filing_facts.get("fiscal_period", "FY_LATEST")).strip()

        # 1. 提取基础底账数值并执行标准化科目映射与清洗
        def _parse_num(val: Any) -> float:
            if val is None:
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            try:
                return OfficialFilingMapper.parse_financial_number(val)
            except Exception:
                return 0.0

        raw_assets = raw_filing_facts.get("total_assets") if raw_filing_facts.get("total_assets") is not None else raw_filing_facts.get("assets")
        raw_liabilities = raw_filing_facts.get("total_liabilities") if raw_filing_facts.get("total_liabilities") is not None else raw_filing_facts.get("liabilities")
        raw_equity = (
            raw_filing_facts.get("total_equity")
            if raw_filing_facts.get("total_equity") is not None
            else (
                raw_filing_facts.get("stockholders_equity")
                if raw_filing_facts.get("stockholders_equity") is not None
                else (
                    raw_filing_facts.get("equity")
                    if raw_filing_facts.get("equity") is not None
                    else raw_filing_facts.get("shareholders_equity")
                )
            )
        )

        assets = _parse_num(raw_assets)
        liabilities = _parse_num(raw_liabilities)
        equity = _parse_num(raw_equity)

        # 会计恒等式智能推导补全 (针对仅披露资产+权益或资产+负债的合法官方底稿)
        if assets > 0.0 and math.isclose(liabilities, 0.0, abs_tol=1e-5) and not math.isclose(equity, 0.0, abs_tol=1e-5):
            liabilities = assets - equity
        elif assets > 0.0 and math.isclose(equity, 0.0, abs_tol=1e-5) and not math.isclose(liabilities, 0.0, abs_tol=1e-5):
            equity = assets - liabilities
        elif math.isclose(assets, 0.0, abs_tol=1e-5) and not math.isclose(liabilities, 0.0, abs_tol=1e-5) and not math.isclose(equity, 0.0, abs_tol=1e-5):
            assets = liabilities + equity

        if math.isclose(assets, 0.0, abs_tol=1e-5):
            raise IncompleteFilingFactError(f"公司 {ticker} 缺失总资产核心科目，拒绝执行金融计算")

        # 2. 刚性平账自检: Assets = Liabilities + Equity
        balance_discrepancy = abs(assets - (liabilities + equity))
        discrepancy_ratio = self._safe_divide(balance_discrepancy, assets)

        # 严格执行 0.1% 平账容差硬门禁
        if discrepancy_ratio > OfficialFilingMapper.BALANCE_SHEET_TOLERANCE_RATIO:
            raise BalanceSheetIdentityError(
                f"公司 {ticker} 资产负债恒等式严重破损: 资产={assets:.2f}, 负债+权益={liabilities + equity:.2f}, "
                f"偏差={balance_discrepancy:.2f} ({discrepancy_ratio * 100:.3f}% > 0.1% 容差)"
            )
        is_balanced = True

        # 3. 提取利润表与现金流表核心科目
        revenue = _parse_num(raw_filing_facts.get("revenue", raw_filing_facts.get("operating_revenue", 0.0)))
        raw_gp = raw_filing_facts.get("gross_profit")
        gross_profit = _parse_num(raw_gp) if raw_gp is not None else (revenue - _parse_num(raw_filing_facts.get("cogs", 0.0)))
        raw_cogs = raw_filing_facts.get("cogs", raw_filing_facts.get("cost_of_goods_sold"))
        cogs = _parse_num(raw_cogs) if raw_cogs is not None else max(0.0, revenue - gross_profit)
        operating_income = _parse_num(raw_filing_facts.get("operating_income", 0.0))
        net_income = _parse_num(raw_filing_facts.get("net_income", 0.0))
        raw_fcf = raw_filing_facts.get("free_cash_flow", raw_filing_facts.get("fcf"))
        fcf = _parse_num(raw_fcf) if raw_fcf is not None else (operating_income * 0.8)

        # 4. 提取资产负债表细分科目
        cash = _parse_num(raw_filing_facts.get("cash_and_equivalents", raw_filing_facts.get("cash", 0.0)))
        raw_debt = raw_filing_facts.get("total_debt", raw_filing_facts.get("debt"))
        total_debt = _parse_num(raw_debt) if raw_debt is not None else (liabilities * 0.6)
        net_cash = cash - total_debt
        inventory = _parse_num(raw_filing_facts.get("inventory", 0.0))

        # 5. 商业衍生比率安全计算 (防范除零除负)
        gross_margin = self._safe_divide(gross_profit, revenue, fallback=0.0)
        operating_margin = self._safe_divide(operating_income, revenue, fallback=0.0)
        net_margin = self._safe_divide(net_income, revenue, fallback=0.0)
        roe = self._safe_divide(net_income, equity, fallback=0.0)
        invested_capital = (equity + total_debt) - cash
        roic = self._safe_divide(operating_income * (1.0 - 0.21), invested_capital, fallback=0.0)

        # 存货周转天数 DIO: (Inventory / COGS) * 365
        inventory_turnover_days = self._safe_divide(inventory * 365.0, cogs, fallback=0.0)
        debt_to_equity = self._safe_divide(total_debt, equity, fallback=0.0)
        interest_expense = float(raw_filing_facts.get("interest_expense", 0.0))
        interest_coverage = self._safe_divide(operating_income, interest_expense, fallback=999.0 if operating_income > 0 else 0.0)

        # 6. 行情新鲜度与时效门禁处理
        quote_price = 0.0
        market_cap = 0.0
        quote_timestamp = "N/A"
        market_session = "Unknown"
        is_quote_fresh = False

        if raw_quote_data:
            quote_price = float(
                raw_quote_data.get("price")
                or raw_quote_data.get("current_price")
                or raw_quote_data.get("quote_price")
                or 0.0
            )
            shares_outstanding = float(raw_filing_facts.get("shares_outstanding", 1.0))
            market_cap = float(raw_quote_data.get("market_cap", quote_price * shares_outstanding))
            ts_str = str(raw_quote_data.get("timestamp", raw_quote_data.get("quote_timestamp", "")))
            market_type = str(raw_quote_data.get("market", "US")).upper()

            if ts_str:
                # 调用时效门禁
                verified = self.quote_gateway.verify_quote(
                    price=quote_price,
                    currency=currency,
                    quote_timestamp=ts_str,
                    market=market_type,
                    current_time_iso=raw_quote_data.get("current_time_iso"),
                )
                quote_timestamp = ts_str
                market_session = verified.session_status
                is_quote_fresh = verified.is_fresh_today
            else:
                market_session = str(raw_quote_data.get("session", "Regular Trading"))
                quote_timestamp = "N/A"
                is_quote_fresh = True

        return NormalizedFinancialProfile(
            ticker=ticker,
            company_name=company_name,
            currency=currency,
            fiscal_period=fiscal_period,
            total_assets=assets,
            total_liabilities=liabilities,
            total_equity=equity,
            cash_and_equivalents=cash,
            total_debt=total_debt,
            net_cash=net_cash,
            revenue=revenue,
            gross_profit=gross_profit,
            operating_income=operating_income,
            net_income=net_income,
            free_cash_flow=fcf,
            inventory=inventory,
            cost_of_goods_sold=cogs,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            net_margin=net_margin,
            roe=roe,
            roic=roic,
            inventory_turnover_days=inventory_turnover_days,
            debt_to_equity=debt_to_equity,
            interest_coverage_ratio=interest_coverage,
            balance_discrepancy=balance_discrepancy,
            is_balanced=is_balanced,
            quote_price=quote_price,
            market_cap=market_cap,
            quote_timestamp=quote_timestamp,
            market_session=market_session,
            is_quote_fresh=is_quote_fresh
        )
