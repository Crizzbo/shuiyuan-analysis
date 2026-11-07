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
    cash_and_equivalents: Optional[float]
    total_debt: Optional[float]
    net_cash: Optional[float]

    revenue: float
    gross_profit: Optional[float]
    operating_income: Optional[float]
    net_income: Optional[float]
    free_cash_flow: Optional[float]

    inventory: Optional[float]
    cost_of_goods_sold: Optional[float]

    # 关键商业与财务衍生比率 (已防范除零异常)
    gross_margin: Optional[float]
    operating_margin: Optional[float]
    net_margin: Optional[float]
    roe: Optional[float]
    roic: Optional[float]
    inventory_turnover_days: Optional[float]  # DIO
    debt_to_equity: Optional[float]
    interest_coverage_ratio: Optional[float]

    # 平账自检指标
    balance_discrepancy: float
    is_balanced: bool

    # 行情时效与交易时段状态
    quote_price: float
    market_cap: Optional[float]
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
    def _safe_divide(
        numerator: Optional[float], denominator: Optional[float], fallback: float = 0.0
    ) -> Optional[float]:
        """缺失输入保持缺失，已披露的零分母按调用方约定降级。"""
        if numerator is None or denominator is None:
            return None
        if not math.isfinite(numerator) or not math.isfinite(denominator):
            raise IncompleteFilingFactError("财务比率输入必须为有限数")
        if denominator <= 1e-9:
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

        # 所有非标数值统一经过 Mapper，缺失科目保留 None，非法内容立即拒绝。
        def _number(*names: str) -> Optional[float]:
            for name in names:
                value = OfficialFilingMapper.parse_optional_financial_number(
                    raw_filing_facts.get(name), name
                )
                if value is not None:
                    return value
            return None

        assets = _number("total_assets", "assets")
        liabilities = _number("total_liabilities", "liabilities")
        equity = _number("total_equity", "stockholders_equity", "equity", "shareholders_equity")
        if assets is None or assets <= 0:
            raise IncompleteFilingFactError(f"公司 {ticker} 缺失总资产核心科目，拒绝执行金融计算")
        if liabilities is None or equity is None:
            raise IncompleteFilingFactError(f"公司 {ticker} 缺失负债或权益，无法独立平账")
        balance_discrepancy = abs(assets - (liabilities + equity))
        discrepancy_ratio = balance_discrepancy / assets
        if discrepancy_ratio > OfficialFilingMapper.BALANCE_SHEET_TOLERANCE_RATIO:
            raise BalanceSheetIdentityError(
                f"公司 {ticker} 资产负债恒等式严重破损: 资产={assets:.2f}, "
                f"负债+权益={liabilities + equity:.2f}, 偏差={discrepancy_ratio:.3%}"
            )
        is_balanced = True

        revenue = _number("revenue", "operating_revenue")
        if revenue is None:
            raise IncompleteFilingFactError(f"公司 {ticker} 缺失营业收入")
        gross_profit = _number("gross_profit")
        cogs = _number("cogs", "cost_of_goods_sold")
        if gross_profit is None and cogs is not None:
            gross_profit = revenue - cogs
        if cogs is None and gross_profit is not None:
            cogs = revenue - gross_profit
        operating_income = _number("operating_income")
        net_income = _number("net_income")
        fcf = _number("free_cash_flow", "fcf")
        if fcf is None:
            operating_cash_flow = _number("operating_cash_flow", "reported_operating_cash_flow")
            capex = _number("capex", "reported_capex")
            if operating_cash_flow is not None and capex is not None:
                fcf = operating_cash_flow - abs(capex)

        cash = _number("cash_and_equivalents", "cash")
        total_debt = _number("total_debt", "debt")
        net_cash = cash - total_debt if cash is not None and total_debt is not None else None
        inventory = _number("inventory")
        gross_margin = self._safe_divide(gross_profit, revenue)
        operating_margin = self._safe_divide(operating_income, revenue)
        net_margin = self._safe_divide(net_income, revenue)
        roe = self._safe_divide(net_income, equity)
        roic = None
        tax_rate = _number("tax_rate")
        if tax_rate is not None and not 0 <= tax_rate <= 1:
            raise IncompleteFilingFactError("有效税率必须位于 0 与 1 之间")
        if operating_income is not None and tax_rate is not None and net_cash is not None:
            roic = self._safe_divide(operating_income * (1 - tax_rate), equity - net_cash)

        # 优先使用已披露平均存货，其次用同口径期初期末均值；期末存货单值不足以计算 DIO。
        average_inventory = _number("average_inventory")
        prior_inventory = _number("prior_inventory")
        if average_inventory is None and inventory is not None and prior_inventory is not None:
            average_inventory = (inventory + prior_inventory) / 2
        inventory_turnover_days = self._safe_divide(
            average_inventory * 365 if average_inventory is not None else None, cogs
        )
        debt_to_equity = self._safe_divide(total_debt, equity)
        interest_expense = _number("interest_expense")
        interest_coverage = self._safe_divide(operating_income, interest_expense)

        # 6. 行情新鲜度与时效门禁处理
        quote_price = 0.0
        market_cap = None
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
            shares_outstanding = _number("shares_outstanding")
            market_cap = OfficialFilingMapper.parse_optional_financial_number(
                raw_quote_data.get("market_cap"), "market_cap"
            )
            if market_cap is None and shares_outstanding is not None:
                market_cap = quote_price * shares_outstanding
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
                is_quote_fresh = verified.is_valid and verified.is_fresh_today
            else:
                market_session = "invalid_timestamp"

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
