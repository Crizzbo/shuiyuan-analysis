"""官方财报底账标准化转换映射器 (Official Filing Ingestion Mapper).

遵循 Google Python 编程风格指南与《SPEC-04 六步研究法与官方财报三表契约规范》:
1. 从官方 10-K/Q (SEC) 与决算短信 (JPX EDINET) 结构化事实底账自动对齐、量纲缩放与数据标准化；
2. 执行前置 Stage 1 资产负债表平账自检 ($Total Assets = Total Liabilities + Stockholders' Equity$)；
3. 输出强类型双向契约 (SystemicCompanyInput 与 FirmFinancialFact)，打通从监管事实到底层计算引擎。
"""

# 1. Python 标准库
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

# 2. 内部核心库 (纯相对导入，解耦外层)
from ..pipeline import SystemicCompanyInput
from .firm_value_added_bridge_engine import FirmFinancialFact


class BalanceSheetIdentityError(ValueError):
    """官方财报底账资产负债表刚性恒等式破损异常 (偏差超出 ±0.1% 容差)."""
    pass


class IncompleteFilingFactError(ValueError):
    """缺少官方权威财报底账异常 (关键三表科目缺失，严禁生成虚假补数)."""
    pass


class OfficialFilingMapper:
    """官方财报底账解析与标准输入组装器 (Google Python Style Guide 架构设计)."""

    BALANCE_SHEET_TOLERANCE_RATIO: float = 0.0010  # 刚性 0.1% (0.0010) 平账容差

    UNIT_MULTIPLIERS: Dict[str, float] = {
        "usd": 1.0,
        "cny": 1.0,
        "jpy": 1.0,
        "usd_thousand": 1_000.0,
        "cny_thousand": 1_000.0,
        "jpy_thousand": 1_000.0,
        "usd_million": 1_000_000.0,
        "cny_million": 1_000_000.0,
        "jpy_million": 1_000_000.0,
        "cny_hundred_million": 100_000_000.0,  # 亿元
        "jpy_hundred_million": 100_000_000.0,  # 億円
        "usd_billion": 1_000_000_000.0,
        "jpy_billion": 1_000_000_000.0,
    }

    @classmethod
    def verify_balance_sheet_identity(
        cls,
        total_assets: float,
        total_liabilities: float,
        stockholders_equity: float,
    ) -> Tuple[bool, float, float]:
        """执行 ±0.1% 资产负债表刚性恒等式自检 (Assets = Liabilities + Equity).

        Args:
            total_assets: 总资产标量数值.
            total_liabilities: 总负债标量数值.
            stockholders_equity: 股东权益 (归母净资产) 标量数值.

        Returns:
            Tuple[bool, float, float]: (是否平衡通过, 绝对差异额, 相对偏差比率).

        Raises:
            BalanceSheetIdentityError: 当相对误差超过 0.1% 且绝对误差大于 1.0 时抛出.
        """
        for val in (total_assets, total_liabilities, stockholders_equity):
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise BalanceSheetIdentityError(f"会计科目存在非法非有限数值: {val}")
        if total_assets <= 0.0:
            return True, 0.0, 0.0
        diff = abs(total_assets - (total_liabilities + stockholders_equity))
        tolerance = max(1.0, total_assets * cls.BALANCE_SHEET_TOLERANCE_RATIO)
        rel_diff = diff / max(1.0, total_assets)
        if diff > tolerance:
            raise BalanceSheetIdentityError(
                f"官方财报底账资产负债表刚性恒等式严重破损: 总资产 ({total_assets:,.2f}) 与 "
                f"[负债 ({total_liabilities:,.2f}) + 股东权益 ({stockholders_equity:,.2f})] "
                f"差异达 {diff:,.2f} (相对偏差 {rel_diff * 100:.3f}%)，超出 0.1% 刚性容差限度!"
            )
        return True, diff, rel_diff

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> SystemicCompanyInput:
        """从 JSON 底账文件中加载并解析为 SystemicCompanyInput.

        Args:
            file_path: 目标 JSON 文件物理路径.

        Returns:
            SystemicCompanyInput 结构化企业事实输入模型.

        Raises:
            FileNotFoundError: 当指定路径文件不存在时抛出.
            ValueError: 当传入绝对路径时抛出 (安全约束硬拦截).
        """
        path_obj = Path(file_path) if isinstance(file_path, (str, Path)) else Path(str(file_path))
        if path_obj.is_absolute():
            raise ValueError(f"安全约束硬拦截：财报入口严禁使用绝对路径: {file_path}")

        p = path_obj.resolve()
        if not p.exists():
            raise FileNotFoundError(f"官方财报底账文件不存在: {p}")

        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.map_to_company_input(data)

    @classmethod
    def map_to_company_input(cls, raw: Dict[str, Any]) -> SystemicCompanyInput:
        """将原始结构化财报事实映射为标准 SystemicCompanyInput.

        Args:
            raw: 原始多源输入字典 (包含 facts、财务单位、量纲及附注).

        Returns:
            SystemicCompanyInput 标准化强类型契约.
        """
        # 1. 识别量纲乘数
        unit_str = str(raw.get("financial_unit", "usd")).lower().strip()
        scale = cls.UNIT_MULTIPLIERS.get(unit_str, 1.0)

        # 2. 提取或推断标的概况
        ticker = (
            raw.get("ticker", "UNKNOWN")
            .replace("NASDAQ:", "")
            .replace("NYSE:", "")
            .strip()
            .upper()
        )
        name = raw.get("company", raw.get("company_name", ticker))
        sector = raw.get("sector", "General")

        facts = raw.get("facts", raw)  # 兼容扁平结构与 facts 嵌套结构

        # 现价与对照基准价
        cur_p = cls.parse_optional_financial_number(
            facts.get("market_price", facts.get("current_price")), "market_price"
        )
        # 财报映射可独立于报价执行，未提供报价时保留空状态，由估值入口阻断。
        cur_p = cur_p if cur_p is not None else 0.0
        quote_ts = facts.get("quote_timestamp") or ""
        base_p = float(facts.get("baseline_reference_price", facts.get("high52", cur_p)))
        session = facts.get("market_session", "closed")

        # 3. 三表核心财务科目提取与单位缩放
        # 收入与利润
        rev = float(facts.get("revenue_2026", facts.get("reported_revenue", 0.0))) * scale
        op_inc = (
            float(facts.get("operating_income_2026", facts.get("reported_operating_income", 0.0)))
            * scale
        )
        net_inc = (
            float(facts.get("net_income_2026", facts.get("reported_net_income", 0.0)))
            * scale
        )

        # 现金流与资本开支
        cfo = float(facts.get("cfo_2026", facts.get("reported_operating_cash_flow", 0.0))) * scale
        capex = float(facts.get("capex_2026", facts.get("reported_capex", 0.0))) * scale
        sbc = float(facts.get("sbc_2026", facts.get("stock_based_compensation", 0.0))) * scale

        # 资产负债表三项与现金
        cash = float(facts.get("cash_2026", facts.get("reported_cash", 0.0))) * scale
        restricted_cash = float(facts.get("restricted_cash", 0.0)) * scale
        covenant_cash = float(facts.get("debt_covenant_min_cash", 0.0)) * scale

        # 负债
        cur_debt = float(facts.get("current_debt_2026", 0.0)) * scale
        long_debt = float(facts.get("long_debt_2026", 0.0)) * scale
        if "total_debt" in facts:
            total_debt = float(facts["total_debt"]) * scale
        else:
            total_debt = cur_debt + long_debt

        # 总资产、总负债与股东权益
        tot_assets = float(facts.get("total_assets_2026", facts.get("total_assets", 0.0))) * scale
        tot_liab = float(facts.get("total_liabilities_2026", facts.get("total_liabilities", 0.0))) * scale
        equity = (
            float(
                facts.get(
                    "stockholders_equity_2026",
                    facts.get("stockholders_equity", facts.get("equity", 0.0)),
                )
            )
            * scale
        )

        # 若提供了资产与权益但未提供负债，依会计恒等式补全
        if tot_assets > 0 and tot_liab == 0.0 and equity != 0.0:
            tot_liab = tot_assets - equity
        elif tot_assets == 0.0 and tot_liab > 0 and equity != 0.0:
            tot_assets = tot_liab + equity
        elif tot_assets > 0 and tot_liab > 0 and equity == 0.0:
            equity = tot_assets - tot_liab

        # 股本数量解析
        shares = cls._resolve_shares_outstanding(facts, unit_str)

        # 存货三级细分与附注提取 (原材料、在制品、产成品)
        raw_materials = (
            float(
                facts.get(
                    "raw_materials",
                    facts.get("InventoryRawMaterials", facts.get("原材料及び貯蔵品", 0.0)),
                )
            )
            * scale
        )
        work_in_process = (
            float(
                facts.get(
                    "work_in_process",
                    facts.get("InventoryWorkInProcess", facts.get("仕掛品", 0.0)),
                )
            )
            * scale
        )
        finished_goods = (
            float(
                facts.get(
                    "finished_goods",
                    facts.get(
                        "InventoryFinishedGoods",
                        facts.get("商品及び製品", facts.get("inventories_2026", 0.0)),
                    ),
                )
            )
            * scale
        )
        prior_finished = (
            float(facts.get("prior_finished_goods", facts.get("inventories_2025", finished_goods)))
            * scale
        )
        rev_growth = float(facts.get("revenue_growth_pct", 0.0))

        # 研发投入与资本化附注
        total_rd = (
            float(
                facts.get(
                    "total_rd_spent",
                    facts.get("ResearchAndDevelopmentExpense", facts.get("研究開発費", 0.0)),
                )
            )
            * scale
        )
        cap_rd = (
            float(
                facts.get(
                    "capitalized_rd_amount",
                    facts.get("CapitalizedComputerSoftwareGross", facts.get("開発費", 0.0)),
                )
            )
            * scale
        )

        # 客户集中度与商业微观变量
        top_cust = float(
            facts.get("top_customer_share", facts.get("largest_customer_revenue_share_2026", 0.10))
        )
        top_cust_risk = bool(facts.get("top_customer_risk_flag", False))
        factory_quote = float(facts.get("factory_quote", 0.0))
        wholesale_quote = float(
            facts.get("real_wholesale_quote", facts.get("wholesale_quote", 0.0))
        )
        liab_drain = float(facts.get("contract_liabilities_drain_pct", 0.0))
        cur_dio = float(facts.get("current_dio_days", facts.get("dio", 0.0)))
        prior_dio = float(facts.get("prior_dio_days", cur_dio))

        # 4. 资产负债表平账自检 (±0.1% 刚性容差)
        if tot_assets > 0:
            cls.verify_balance_sheet_identity(tot_assets, tot_liab, equity)

        return SystemicCompanyInput(
            ticker=ticker,
            company_name=name,
            sector=sector,
            quote_timestamp=quote_ts,
            market_session=session,
            current_price=cur_p,
            baseline_reference_price=base_p,
            reported_cash=cash,
            restricted_cash=restricted_cash,
            debt_covenant_min_cash=covenant_cash,
            total_debt=total_debt,
            total_assets=tot_assets,
            total_liabilities=tot_liab,
            stockholders_equity=equity,
            reported_operating_cash_flow=cfo,
            reported_capex=capex,
            maintenance_capex_ratio=float(facts.get("maintenance_capex_ratio", 0.70)),
            stock_based_compensation=sbc,
            reported_revenue=rev,
            reported_operating_income=op_inc,
            reported_net_income=net_inc,
            shares_outstanding=shares,
            raw_materials=raw_materials,
            work_in_process=work_in_process,
            finished_goods=finished_goods,
            prior_finished_goods=prior_finished,
            revenue_growth_pct=rev_growth,
            total_rd_spent=total_rd,
            capitalized_rd_amount=cap_rd,
            top_customer_share=top_cust,
            top_customer_risk_flag=top_cust_risk,
            factory_quote=factory_quote,
            real_wholesale_quote=wholesale_quote,
            contract_liabilities_drain_pct=liab_drain,
            current_dio_days=cur_dio,
            prior_dio_days=prior_dio,
            us_10y_yield=float(facts.get("us_10y_yield", 0.045)),
            usdjpy_rate=float(facts.get("usdjpy_rate", 150.0)),
            vix_index=float(facts.get("vix_index", 20.0)),
            company_beta=float(facts.get("company_beta", 1.2)),
            short_interest_shares=float(facts.get("short_interest_shares", 0.0)),
            free_float_shares=float(facts.get("free_float_shares", shares * 0.95)),
            cost_to_borrow_pct=float(facts.get("cost_to_borrow_pct", 1.0)),
            average_volume_30d=float(facts.get("average_volume_30d", 2_000_000.0)),
            option_target_strike=float(facts.get("option_target_strike", round(cur_p * 1.05, 0))),
            option_expiry_days=int(facts.get("option_expiry_days", 30)),
            option_implied_vol=float(facts.get("option_implied_vol", 0.35)),
        )

    @classmethod
    def parse_financial_number(cls, val: Any) -> float:
        """从各种格式的财务文本中提取标准浮点数值.

        支持典型案例:
        - "$750.0M (现金及国债...)" -> 750,000,000.0
        - "-$380.0M" -> -380,000,000.0
        - "($345.0M)" -> -345,000,000.0
        - "$1.2B" -> 1,200,000,000.0
        - "380.0M 股" -> 380,000,000.0
        - "5,600億円" -> 560,000,000,000.0
        - "890円" -> 890.0

        Args:
            val: 原始待解析对象 (字符串、整数、浮点数或 None).

        Returns:
            提取转换后的标准浮点数值 (解析失败时安全返回 0.0).
        """
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val) if not math.isnan(val) else 0.0

        s = str(val).strip()
        if not s or s.upper() in ["N/A", "NONE", "NULL", "-"]:
            return 0.0

        is_negative = cls._check_negative_sign(s)

        match = re.search(
            r"[-+−–—△▲]?\s*[\$¥￥]?\s*[-+−–—△▲]?\s*"
            r"([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*"
            r"(BILLION|MILLION|THOUSAND|万亿|万億|千亿|千億|百亿|百億|十亿|十億|"
            r"百万円|百万美元|百万|亿美元|亿日元|亿元|億円|亿|億|万|万円|[BMKbmk])?(?![A-Za-z])",
            s,
            re.IGNORECASE,
        )
        if not match:
            return 0.0

        num_str = match.group(1).replace(",", "")
        num = float(num_str)
        unit = (match.group(2) or "").upper()
        mult = cls._resolve_unit_multiplier(unit)

        val_final = num * mult
        return -val_final if is_negative else val_final

    @classmethod
    def parse_optional_financial_number(
        cls, value: Any, field_name: str
    ) -> Optional[float]:
        """保留未披露科目，拒绝把非法格式、布尔值或非有限数写入事实底账。"""
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            if text.upper() in {"", "N/A", "NONE", "NULL", "-", "—", "未披露", "缺失"}:
                return None
            if not re.search(r"[0-9]", text):
                raise IncompleteFilingFactError(f"财报科目 {field_name} 无法解析")
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise IncompleteFilingFactError(f"财报科目 {field_name} 必须为数值或数值文本")
        # 纯数值文本允许科学计数法，带币种和单位的文本继续复用现有解析器。
        if isinstance(value, str):
            try:
                number = float(value.strip().replace(",", ""))
            except ValueError:
                number = cls.parse_financial_number(value)
        else:
            number = cls.parse_financial_number(value)
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise IncompleteFilingFactError(f"财报科目 {field_name} 必须为有限数")
        if not math.isfinite(number):
            raise IncompleteFilingFactError(f"财报科目 {field_name} 必须为有限数")
        return number

    @classmethod
    def map_dossier_to_company_input(cls, dossier: Dict[str, Any]) -> SystemicCompanyInput:
        """将全息深度档案字典转换为可运算的 SystemicCompanyInput.

        Args:
            dossier: 包含 overview、raw_financials_table、financial_statement_deep_dive 的档案字典.

        Returns:
            SystemicCompanyInput 标准化强类型契约.

        Raises:
            IncompleteFilingFactError: 当缺少官方权威三表关键底账时抛出.
        """
        overview = dossier.get("overview", {})
        ticker = overview.get("ticker", "UNKNOWN").strip().upper()
        company_name = overview.get("company_name", ticker)
        market = overview.get("market", "US").strip().upper()
        sector = overview.get("industry_id", "General")

        raw_fin = dossier.get("raw_financials_table", {})
        def _required_fact(name: str, *aliases: str) -> float:
            for key in (name, *aliases):
                number = cls.parse_optional_financial_number(raw_fin.get(key), key)
                if number is not None:
                    return number
            raise IncompleteFilingFactError(f"公司 {ticker} 档案缺少财报科目 {name}")

        rev = _required_fact("revenue")
        op_inc = _required_fact("operating_income")
        net_inc = _required_fact("net_income")
        tot_assets = _required_fact("total_assets")
        tot_liab = _required_fact("total_liabilities")
        equity = _required_fact("equity", "stockholders_equity", "total_equity")
        cash = _required_fact("cash_and_equivalents")
        total_debt = _required_fact("total_debt")
        shares = _required_fact("shares", "shares_outstanding")
        if shares <= 0:
            raise IncompleteFilingFactError("公司档案必须提供有限正数股数，单位为股")
        capex = abs(_required_fact("capex", "reported_capex"))
        cfo = cls.parse_optional_financial_number(raw_fin.get("operating_cash_flow"), "operating_cash_flow")
        fcf = cls.parse_optional_financial_number(raw_fin.get("free_cash_flow"), "free_cash_flow")
        # 只允许用已披露、同口径科目做现金流恒等变换。
        if cfo is None:
            if fcf is None:
                raise IncompleteFilingFactError("公司档案缺少经营现金流与自由现金流")
            cfo = fcf + capex
        if fcf is None:
            fcf = cfo - capex

        restricted_cash = cls.parse_financial_number(
            raw_fin.get("restricted_cash", raw_fin.get("restricted_deposits", 0.0))
        )
        covenant_cash = cls.parse_financial_number(raw_fin.get("debt_covenant_min_cash", 0.0))
        raw_materials = cls.parse_financial_number(raw_fin.get("raw_materials", 0.0))
        work_in_process = cls.parse_financial_number(raw_fin.get("work_in_process", 0.0))
        finished_goods = cls.parse_financial_number(
            raw_fin.get("finished_goods", raw_fin.get("inventories", 0.0))
        )
        total_rd = cls.parse_financial_number(
            raw_fin.get("total_rd_spent", raw_fin.get("rd_expense", 0.0))
        )
        cap_rd = cls.parse_financial_number(raw_fin.get("capitalized_rd_amount", 0.0))

        deep_dive = dossier.get("financial_statement_deep_dive", {})
        # 从财报深度解读与附注中解构细分科目
        (
            raw_materials,
            work_in_process,
            finished_goods,
            restricted_cash,
            covenant_cash,
            total_rd,
            cap_rd,
        ) = cls._penetrate_deep_dive_metrics(
            deep_dive,
            raw_materials,
            work_in_process,
            finished_goods,
            restricted_cash,
            covenant_cash,
            total_rd,
            cap_rd,
        )

        # 从估值走廊或文本中提取现价与基准对照价
        cur_p, base_p = cls._extract_price_and_baseline(dossier, overview)
        facts_dict = dossier.get("facts", {})
        now_ts = (
            facts_dict.get("quote_timestamp")
            or overview.get("quote_timestamp")
            or raw_fin.get("quote_timestamp")
        )
        if cur_p <= 0.0 or not now_ts:
            raise IncompleteFilingFactError("公司档案缺少有效观测价格或原始行情时间戳")

        # 严格质量门禁：缺少权威财报底账即刻阻断
        if rev <= 0.0 or tot_assets <= 0.0:
            raise IncompleteFilingFactError(
                f"企业 {ticker} 缺少官方权威财报底账（营业收入={rev}, 总资产={tot_assets}），"
                "严禁无中生有推算虚假财务报表。"
            )

        # 资产负债表刚性平账自检 (±0.1% 刚性容差)
        cls.verify_balance_sheet_identity(tot_assets, tot_liab, equity)

        prior_finished = cls.parse_financial_number(
            raw_fin.get("prior_finished_goods", finished_goods)
        )

        supply_chain = dossier.get("supply_chain_analysis", {})
        top_cust, top_cust_risk = cls._extract_supply_chain_metrics(
            supply_chain, raw_fin
        )

        factory_quote = cls.parse_financial_number(raw_fin.get("factory_quote", 0.0))
        wholesale_quote = cls.parse_financial_number(
            raw_fin.get("real_wholesale_quote", raw_fin.get("wholesale_quote", 0.0))
        )
        liab_drain = float(raw_fin.get("contract_liabilities_drain_pct", 0.0))

        return SystemicCompanyInput(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            quote_timestamp=now_ts,
            market_session="closed",
            current_price=cur_p,
            baseline_reference_price=base_p,
            reported_cash=cash,
            restricted_cash=restricted_cash,
            debt_covenant_min_cash=covenant_cash,
            total_debt=total_debt,
            total_assets=tot_assets,
            total_liabilities=tot_liab,
            stockholders_equity=equity,
            reported_operating_cash_flow=cfo,
            reported_capex=capex,
            maintenance_capex_ratio=0.75,
            stock_based_compensation=0.0,
            reported_revenue=rev,
            reported_operating_income=op_inc,
            reported_net_income=net_inc,
            shares_outstanding=shares,
            raw_materials=raw_materials,
            work_in_process=work_in_process,
            finished_goods=finished_goods,
            prior_finished_goods=prior_finished,
            revenue_growth_pct=0.0,
            total_rd_spent=total_rd,
            capitalized_rd_amount=cap_rd,
            top_customer_share=top_cust,
            top_customer_risk_flag=top_cust_risk,
            factory_quote=factory_quote,
            real_wholesale_quote=wholesale_quote,
            contract_liabilities_drain_pct=liab_drain,
            us_10y_yield=0.044,
            usdjpy_rate=152.0,
            vix_index=20.0,
            company_beta=1.1,
            short_interest_shares=0.0,
            free_float_shares=shares * 0.90,
            cost_to_borrow_pct=2.0,
            average_volume_30d=max(100_000.0, shares * 0.01),
            option_target_strike=round(cur_p, 1),
            option_expiry_days=30,
            option_implied_vol=0.35,
        )

    @classmethod
    def map_to_firm_financial_fact(
        cls, raw: Dict[str, Any], normalize_currency: bool = True
    ) -> FirmFinancialFact:
        """将原始财报字典映射为标准的微观企业财务底账 FirmFinancialFact.

        Args:
            raw: 包含财报三表科目、概况与深度解读的原始字典.
            normalize_currency: 是否将日元 (JPY) 折算为世界宏观美元量纲 (默认 True).

        Returns:
            FirmFinancialFact 统一标准化百万量纲微观底账契约.
        """
        unit_str = str(raw.get("financial_unit", "usd")).lower().strip()
        scale = cls.UNIT_MULTIPLIERS.get(unit_str, 1.0)
        scale_to_mil = scale / 1_000_000.0

        raw_table = raw.get("raw_financials_table", {})
        overview = raw.get("overview", {})
        facts = dict(raw.get("facts", {}))
        if not facts:
            facts = dict(raw)
        if raw_table:
            for k, v in raw_table.items():
                if k not in facts:
                    facts[k] = v
        if overview:
            for k, v in overview.items():
                if k not in facts:
                    facts[k] = v

        ticker = (
            raw.get("ticker", facts.get("ticker", overview.get("ticker", "UNKNOWN")))
            .replace("NASDAQ:", "")
            .replace("NYSE:", "")
            .strip()
            .upper()
        )
        name = raw.get(
            "company",
            raw.get(
                "company_name",
                facts.get("company_name", facts.get("company", overview.get("company_name", ticker))),
            ),
        )
        market = raw.get("market", facts.get("market", overview.get("market", "US"))).strip().upper()
        sector_id = raw.get(
            "sector_id",
            facts.get(
                "sector_id",
                raw.get("sector", facts.get("sector", overview.get("industry_id", "General"))),
            ),
        )
        country_id = raw.get(
            "country_id",
            facts.get(
                "country_id",
                "US" if market == "US" else "JP" if market == "JP" else "ROW",
            ),
        )

        def get_mil(key_mil: str, *alt_raw_keys: str, default: float = 0.0) -> float:
            if key_mil in facts:
                val = facts[key_mil]
                return float(val) if isinstance(val, (int, float)) else cls.parse_financial_number(val)
            if key_mil in raw:
                val = raw[key_mil]
                return float(val) if isinstance(val, (int, float)) else cls.parse_financial_number(val)
            for k in alt_raw_keys:
                if k in facts:
                    val = cls.parse_financial_number(facts[k])
                    return float(val) * scale_to_mil
                if k in raw:
                    val = cls.parse_financial_number(raw[k])
                    return float(val) * scale_to_mil
            return default

        rev_mil = get_mil(
            "revenue_million",
            "revenue_2026",
            "reported_revenue",
            "revenue",
            "Revenues",
            "SalesRevenueNet",
            "売上高",
        )
        cogs_mil = get_mil(
            "cogs_million",
            "cogs",
            "CostOfGoodsAndServicesSold",
            "CostOfRevenue",
            "売上原価",
        )
        op_inc_mil = get_mil(
            "operating_income_million",
            "operating_income_2026",
            "reported_operating_income",
            "operating_income",
            "OperatingIncomeLoss",
            "営業利益",
        )
        op_exp_mil = get_mil(
            "operating_expenses_million",
            "operating_expenses",
            "OperatingExpenses",
            "販売費及び一般管理費",
        )
        wages_mil = get_mil(
            "wages_and_salaries_million",
            "wages",
            "LaborAndRelatedExpense",
            "人件費",
            "給料及び手当",
        )
        taxes_mil = get_mil(
            "taxes_paid_million",
            "income_tax",
            "IncomeTaxExpenseBenefit",
            "法人税等",
        )
        capex_mil = get_mil(
            "capex_million",
            "capex_2026",
            "reported_capex",
            "capex",
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "設備投資",
        )
        fcf_mil = get_mil(
            "annual_fcf_million",
            "fcf",
            "free_cash_flow",
        )
        ebitda_mil = get_mil("ebitda_million", "ebitda")

        # 勾稽兜底推算
        if cogs_mil == 0.0 and rev_mil > 0:
            cogs_mil = (
                rev_mil - op_inc_mil - op_exp_mil
                if op_exp_mil > 0
                else rev_mil * 0.60
            )
        if op_exp_mil == 0.0 and rev_mil > 0 and op_inc_mil > 0:
            op_exp_mil = max(0.0, rev_mil - cogs_mil - op_inc_mil)
        if wages_mil == 0.0 and op_exp_mil > 0:
            wages_mil = op_exp_mil * 0.40
        if ebitda_mil == 0.0:
            ebitda_mil = op_inc_mil + max(1.0, capex_mil * 0.85)
        if fcf_mil == 0.0:
            cfo_mil = get_mil(
                "operating_cash_flow_million",
                "cfo_2026",
                "reported_operating_cash_flow",
                "cfo",
                "NetCashProvidedByUsedInOperatingActivities",
                "営業活動によるキャッシュフロー",
            )
            fcf_mil = (
                cfo_mil - capex_mil
                if cfo_mil != 0.0
                else ebitda_mil - capex_mil - taxes_mil
            )

        # 市值
        mcap_bil = get_mil(
            "market_cap_billion",
            "market_cap",
            "MarketCapitalization",
            default=0.0,
        )
        if mcap_bil == 0.0:
            shares = cls._resolve_shares_outstanding(facts, unit_str)
            cur_p, _ = cls._extract_price_and_baseline(raw, overview)
            if cur_p > 0.0:
                p = cur_p
            else:
                p = cls.parse_financial_number(facts.get("market_price", facts.get("current_price")))
            mcap_bil = (shares * p) / 1_000_000_000.0

        # 股东权益
        raw_eq = facts.get(
            "stockholders_equity_2026",
            facts.get(
                "equity",
                facts.get("StockholdersEquity", facts.get("純資産", facts.get("equity_2026", 0.0))),
            ),
        )
        equity = (
            float(raw_eq)
            if isinstance(raw_eq, (int, float))
            else cls.parse_financial_number(raw_eq)
        ) * scale

        deep_dive_raw = raw.get("financial_statement_deep_dive", {})

        # 负债与现金
        tot_debt = cls._extract_total_debt(facts, deep_dive_raw, scale)
        tot_debt_mil = tot_debt / 1_000_000.0

        cash_val = cls._extract_cash_balance(facts, deep_dive_raw)
        cash_mil = (cash_val * scale) / 1_000_000.0

        interest_mil = get_mil(
            "interest_expense_million",
            "interest_expense",
            "InterestExpense",
            "支払利息",
        )
        tangible_bv_mil = get_mil("tangible_book_value_million", "tangible_book_value")
        if tangible_bv_mil == 0.0 and equity > 0:
            tangible_bv_mil = (equity * 0.80) / 1_000_000.0

        raw_dio = facts.get("inventory_turnover_days_dio", facts.get("dio", 65.0))
        dio = (
            float(raw_dio)
            if isinstance(raw_dio, (int, float))
            else cls.parse_financial_number(raw_dio)
        )
        if dio <= 0.0:
            dio = 65.0
        raw_foreign = facts.get("foreign_revenue_ratio", 0.50)
        foreign_ratio = (
            float(raw_foreign)
            if isinstance(raw_foreign, (int, float))
            else cls.parse_financial_number(raw_foreign)
        )
        raw_fx = facts.get("fx_sensitivity_elasticity", 0.85 if market == "JP" else 0.0)
        fx_elasticity = (
            float(raw_fx)
            if isinstance(raw_fx, (int, float))
            else cls.parse_financial_number(raw_fx)
        )

        # 币种汇率统一归一化
        is_jpy = (
            normalize_currency
            and (
                market == "JP"
                or country_id == "JP"
                or str(raw.get("currency", "")).upper() == "JPY"
            )
        )
        if is_jpy:
            usd_jpy = float(raw.get("usdjpy_rate", facts.get("usdjpy_rate", 150.0)))
            if usd_jpy <= 0.0:
                usd_jpy = 150.0
            rev_mil /= usd_jpy
            cogs_mil /= usd_jpy
            op_inc_mil /= usd_jpy
            op_exp_mil /= usd_jpy
            ebitda_mil /= usd_jpy
            wages_mil /= usd_jpy
            taxes_mil /= usd_jpy
            capex_mil /= usd_jpy
            fcf_mil /= usd_jpy
            mcap_bil /= usd_jpy
            tot_debt_mil /= usd_jpy
            cash_mil /= usd_jpy
            interest_mil /= usd_jpy
            tangible_bv_mil /= usd_jpy

        return FirmFinancialFact(
            ticker=ticker,
            company_name=name,
            market=market,
            sector_id=sector_id,
            revenue_million=round(rev_mil, 2),
            cogs_million=round(cogs_mil, 2),
            operating_expenses_million=round(op_exp_mil, 2),
            ebitda_million=round(ebitda_mil, 2),
            wages_and_salaries_million=round(wages_mil, 2),
            taxes_paid_million=round(taxes_mil, 2),
            capex_million=round(capex_mil, 2),
            annual_fcf_million=round(fcf_mil, 2),
            market_cap_billion=round(mcap_bil, 2),
            country_id=country_id,
            foreign_revenue_ratio=round(foreign_ratio, 4),
            fx_sensitivity_elasticity=round(fx_elasticity, 4),
            inventory_turnover_days_dio=round(dio, 1),
            total_debt_million=round(tot_debt_mil, 2),
            cash_and_equivalents_million=round(cash_mil, 2),
            interest_expense_million=round(interest_mil, 2),
            tangible_book_value_million=round(tangible_bv_mil, 2),
        )

    @classmethod
    def map_sec_edgar_filing(
        cls, filing_json: Dict[str, Any]
    ) -> Tuple[SystemicCompanyInput, FirmFinancialFact]:
        """将 SEC EDGAR (10-K / 10-Q) 官方财报结构化事实底账映射为标准双向契约模型.

        Args:
            filing_json: 包含 SEC 原生 XBRL 标签的字典.

        Returns:
            Tuple[SystemicCompanyInput, FirmFinancialFact]: 双向契约模型元组.
        """
        raw = dict(filing_json)
        raw["market"] = raw.get("market", "US")
        raw["currency"] = raw.get("currency", "USD")
        facts = dict(raw.get("facts", raw))

        # 对齐 SEC 官方 XBRL 核心科目与附注别名
        xbrl_alias_map = {
            "Revenues": "reported_revenue",
            "SalesRevenueNet": "reported_revenue",
            "RevenueFromContractWithCustomerExcludingAssessedTax": "reported_revenue",
            "OperatingIncomeLoss": "reported_operating_income",
            "NetIncomeLoss": "reported_net_income",
            "Assets": "total_assets",
            "Liabilities": "total_liabilities",
            "StockholdersEquity": "stockholders_equity",
            "NetCashProvidedByUsedInOperatingActivities": "reported_operating_cash_flow",
            "PaymentsToAcquirePropertyPlantAndEquipment": "reported_capex",
            "CashAndCashEquivalentsAtCarryingValue": "reported_cash",
            "CommonStockSharesOutstanding": "shares_outstanding",
            "InventoryRawMaterialsAndSupplies": "raw_materials",
            "InventoryRawMaterials": "raw_materials",
            "RawMaterials": "raw_materials",
            "InventoryWorkInProcessAndRawMaterials": "work_in_process",
            "InventoryWorkInProcess": "work_in_process",
            "WorkInProcess": "work_in_process",
            "InventoryFinishedGoods": "finished_goods",
            "FinishedGoods": "finished_goods",
            "ResearchAndDevelopmentExpense": "total_rd_spent",
            "ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost": "total_rd_spent",
            "CapitalizedComputerSoftwareGross": "capitalized_rd_amount",
            "CapitalizedDevelopmentCosts": "capitalized_rd_amount",
            "RestrictedCashAndCashEquivalentsAtCarryingValue": "restricted_cash",
            "RestrictedCashAndCashEquivalents": "restricted_cash",
            "CompensatingBalances": "debt_covenant_min_cash",
        }
        for xbrl_k, std_k in xbrl_alias_map.items():
            if xbrl_k in facts and std_k not in facts:
                facts[std_k] = facts[xbrl_k]

        raw["facts"] = facts
        company_input = cls.map_to_company_input(raw)
        financial_fact = cls.map_to_firm_financial_fact(raw)
        return company_input, financial_fact

    @classmethod
    def map_jpx_edinet_filing(
        cls, edinet_json: Dict[str, Any]
    ) -> Tuple[SystemicCompanyInput, FirmFinancialFact]:
        """将 JPX EDINET / TDnet 决算短信官方事实底账映射为标准双向契约模型.

        Args:
            edinet_json: 包含东证决算短信科目的字典.

        Returns:
            Tuple[SystemicCompanyInput, FirmFinancialFact]: 双向契约模型元组.
        """
        raw = dict(edinet_json)
        raw["market"] = raw.get("market", "JP")
        raw["currency"] = raw.get("currency", "JPY")
        facts = dict(raw.get("facts", raw))

        # 对齐日股决算短信核心科目与附注别名
        jpx_alias_map = {
            "売上高": "reported_revenue",
            "NetSales": "reported_revenue",
            "営業利益": "reported_operating_income",
            "OperatingIncome": "reported_operating_income",
            "経常利益": "operating_income",
            "当期純利益": "reported_net_income",
            "ProfitLossAttributableToOwnersOfParent": "reported_net_income",
            "総資産": "total_assets",
            "TotalAssets": "total_assets",
            "純資産": "stockholders_equity",
            "NetAssets": "stockholders_equity",
            "負債合計": "total_liabilities",
            "TotalLiabilities": "total_liabilities",
            "営業活動によるキャッシュフロー": "reported_operating_cash_flow",
            "CashFlowsFromOperatingActivities": "reported_operating_cash_flow",
            "設備投資": "reported_capex",
            "有形固定資産の取得による支出": "reported_capex",
            "CapitalExpenditures": "reported_capex",
            "現金及び預金": "reported_cash",
            "CashAndDeposits": "reported_cash",
            "発行済株式総数": "shares_outstanding",
            "SharesOutstanding": "shares_outstanding",
            "原材料及び貯蔵品": "raw_materials",
            "原材料": "raw_materials",
            "仕掛品": "work_in_process",
            "商品及び製品": "finished_goods",
            "製品": "finished_goods",
            "研究開発費": "total_rd_spent",
            "開発費": "capitalized_rd_amount",
            "担保預金": "restricted_cash",
            "拘束性預金": "restricted_cash",
        }
        for jpx_k, std_k in jpx_alias_map.items():
            if jpx_k in facts and std_k not in facts:
                facts[std_k] = facts[jpx_k]

        raw["facts"] = facts
        company_input = cls.map_to_company_input(raw)
        financial_fact = cls.map_to_firm_financial_fact(raw, normalize_currency=False)
        return company_input, financial_fact

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _check_negative_sign(s: str) -> bool:
        """检查财务文本是否表达负数 (私有辅助方法)."""
        s_clean = s.replace(" ", "")
        neg_indicators = ("-", "−", "–", "—", "△", "▲")
        if any(s_clean.startswith(ind) for ind in neg_indicators):
            return True
        if s.startswith("(-") or s.startswith("(−") or s.startswith("(△") or s.startswith("(▲"):
            return True
        if s.startswith("（-") or s.startswith("（−") or s.startswith("（△") or s.startswith("（▲"):
            return True
        if (s.startswith("(") and s.endswith(")")) or (s.startswith("（") and s.endswith("）")):
            return True
        if any(f"{ind}$" in s or f"{ind}¥" in s or f"{ind}￥" in s for ind in neg_indicators):
            return True
        if any(f"${ind}" in s or f"¥{ind}" in s or f"￥{ind}" in s for ind in neg_indicators):
            return True
        if any(ind in s for ind in ("△", "▲")):
            return True
        return False

    @staticmethod
    def _resolve_unit_multiplier(unit: str) -> float:
        """根据文本单位返回数值乘数 (私有辅助方法)."""
        if unit in ["B", "BILLION", "十亿", "十億", "亿美元"]:
            return 1_000_000_000.0
        if unit in ["百亿", "百億"]:
            return 10_000_000_000.0
        if unit in ["千亿", "千億"]:
            return 100_000_000_000.0
        if unit in ["万亿", "万億"]:
            return 1_000_000_000_000.0
        if unit in ["M", "MILLION", "百万", "百万美元", "百万円"]:
            return 1_000_000.0
        if unit in ["K", "THOUSAND", "千"]:
            return 1_000.0
        if unit in ["亿", "億", "亿元", "億円", "亿日元"]:
            return 100_000_000.0
        if unit in ["万", "万円"]:
            return 10_000.0
        return 1.0

    @classmethod
    def _resolve_shares_outstanding(
        cls, facts: Dict[str, Any], unit_str: str
    ) -> float:
        """推导或解析总流通股本数量 (私有辅助方法)."""
        raw_shares = facts.get(
            "shares_outstanding",
            facts.get("shares", facts.get("shares_diluted", facts.get("q4_diluted_shares_million", 0.0))),
        )
        shares = (
            float(raw_shares)
            if isinstance(raw_shares, (int, float))
            else cls.parse_financial_number(raw_shares)
        )
        if shares <= 0.0:
            raw_ni = facts.get(
                "net_income_2026",
                facts.get("net_income", facts.get("reported_net_income", 0.0)),
            )
            raw_eps = facts.get("eps", 0.0)
            val_ni = (
                float(raw_ni)
                if isinstance(raw_ni, (int, float))
                else cls.parse_financial_number(raw_ni)
            )
            val_eps = (
                float(raw_eps)
                if isinstance(raw_eps, (int, float))
                else cls.parse_financial_number(raw_eps)
            )
            if abs(val_eps) >= 0.01 and abs(val_ni) > 0.0:
                shares = abs(val_ni) / abs(val_eps)
                if shares < 100_000:
                    shares *= 1_000_000.0
            else:
                shares = 100_000_000.0
        elif "hundred_million" in unit_str and shares < 1000:
            shares *= 100_000_000.0
        elif "million" in str(facts.get("q4_diluted_shares_million", "")) or (
            shares < 100_000 and "shares_million" in str(facts)
        ):
            shares *= 1_000_000.0
        elif shares < 100_000:
            shares *= 1_000_000.0
        return shares

    @classmethod
    def _penetrate_deep_dive_metrics(
        cls,
        deep_dive: Dict[str, Any],
        raw_materials: float,
        work_in_process: float,
        finished_goods: float,
        restricted_cash: float,
        covenant_cash: float,
        total_rd: float,
        cap_rd: float,
    ) -> Tuple[float, float, float, float, float, float, float]:
        """从财报深度分析附注中穿透细分指标 (私有辅助方法)."""
        if "inventory_cycle_analysis" in deep_dive:
            inv_block = deep_dive["inventory_cycle_analysis"]
            inv_scale_str = (
                inv_block.get("inventory_scale", "")
                if isinstance(inv_block, dict)
                else str(inv_block)
            )
            if inv_scale_str:
                if raw_materials == 0.0:
                    m_rm = re.search(
                        r"(?:原材料|Raw\s*Materials?)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        inv_scale_str,
                        re.I,
                    )
                    if m_rm:
                        raw_materials = cls.parse_financial_number(m_rm.group(1))
                if work_in_process == 0.0:
                    m_wip = re.search(
                        r"(?:在制品|仕掛品|Work\s*In\s*Process)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        inv_scale_str,
                        re.I,
                    )
                    if m_wip:
                        work_in_process = cls.parse_financial_number(m_wip.group(1))
                if finished_goods == 0.0:
                    m_fg = re.search(
                        r"(?:产成品|商品及び製品|Finished\s*Goods?)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        inv_scale_str,
                        re.I,
                    )
                    if m_fg:
                        finished_goods = cls.parse_financial_number(m_fg.group(1))
                    else:
                        finished_goods = cls.parse_financial_number(inv_scale_str)

        if "cash_and_liquidity" in deep_dive:
            cash_block = deep_dive["cash_and_liquidity"]
            cash_str = (
                cash_block.get("total_cash_and_equivalents", "")
                if isinstance(cash_block, dict)
                else str(cash_block)
            )
            if cash_str:
                if restricted_cash == 0.0:
                    m_rc = re.search(
                        r"(?:受限|质押|拘束性|保证金|Restricted)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        cash_str,
                        re.I,
                    )
                    if m_rc:
                        restricted_cash = cls.parse_financial_number(m_rc.group(1))
                if covenant_cash == 0.0:
                    m_cov = re.search(
                        r"(?:契约|红线|最低流动|Covenant)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        cash_str,
                        re.I,
                    )
                    if m_cov:
                        covenant_cash = cls.parse_financial_number(m_cov.group(1))

        if "profitability_quality" in deep_dive:
            prof_raw = deep_dive.get("profitability_quality", "")
            prof_str = (
                prof_raw.get("profitability_quality", str(prof_raw))
                if isinstance(prof_raw, dict)
                else str(prof_raw)
            )
            if prof_str:
                if total_rd == 0.0:
                    m_rd = re.search(
                        r"(?:研发[^\$¥￥0-9]{0,8}(?:投入|费用|支出)|R&D\s*Expense)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        prof_str,
                        re.I,
                    )
                    if m_rd:
                        total_rd = cls.parse_financial_number(m_rd.group(1))
                if cap_rd == 0.0:
                    m_crd = re.search(
                        r"(?:资本化|Capitalized)[^\$¥￥0-9]*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)",
                        prof_str,
                        re.I,
                    )
                    if m_crd:
                        cap_rd = cls.parse_financial_number(m_crd.group(1))

        return (
            raw_materials,
            work_in_process,
            finished_goods,
            restricted_cash,
            covenant_cash,
            total_rd,
            cap_rd,
        )

    @classmethod
    def _extract_price_and_baseline(
        cls, dossier: Dict[str, Any], overview: Dict[str, Any]
    ) -> Tuple[float, float]:
        """提取现价与基准对照价格 (私有辅助方法)."""
        raw_facts = dossier.get("facts", {}) if isinstance(dossier, dict) else {}
        if not isinstance(raw_facts, dict):
            raw_facts = {}
        cur_p = cls.parse_financial_number(
            raw_facts.get(
                "current_price",
                raw_facts.get(
                    "market_price",
                    overview.get("current_price", overview.get("market_price", 0.0)),
                ),
            )
        )
        base_p = cur_p

        outlook = dossier.get("long_term_outlook", {}) if isinstance(dossier, dict) else {}
        dcf_matrix = outlook.get("dcf_valuation_matrix", {}) if isinstance(outlook, dict) else {}
        mos_str = dcf_matrix.get("margin_of_safety_buy_zone", "")

        price_match = re.search(
            r"现价\s*[\$¥￥]?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)",
            mos_str,
        )
        if price_match:
            cur_p = float(price_match.group(1).replace(",", ""))
            base_p = cur_p

        base_val_str = dcf_matrix.get("base_fair_value", "")
        m_base = re.search(
            r"[\$¥￥]?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)",
            base_val_str,
        )
        if m_base:
            base_p = float(m_base.group(1).replace(",", ""))

        if base_p <= 0.0:
            base_p = cur_p

        return cur_p, base_p

    @classmethod
    def _fallback_from_narrative(
        cls,
        overview: Dict[str, Any],
        deep_dive: Dict[str, Any],
        rev: float,
        fcf: float,
        cash: float,
        total_debt: float,
        finished_goods: float,
    ) -> Tuple[float, float, float, float, float]:
        """自适应从叙述性文本中回退提取核心财务底账 (私有辅助方法)."""
        if rev == 0.0:
            rev_text = overview.get("revenue_mix", "")
            m_rev = re.search(r"规模约\s*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)", rev_text)
            if m_rev:
                rev = cls.parse_financial_number(m_rev.group(1))
            elif rev_text:
                m_rev2 = re.search(r"([\$¥￥][0-9,]+(?:\.[0-9]+)?\s*[MBK]?)", rev_text)
                if m_rev2:
                    rev = cls.parse_financial_number(m_rev2.group(1))

        prof = deep_dive.get("profitability_quality", "")
        if fcf == 0.0 and prof:
            m_fcf = re.search(r"自由现金流约\s*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)", prof)
            if m_fcf:
                fcf = cls.parse_financial_number(m_fcf.group(1))

        if cash == 0.0 and "cash_and_liquidity" in deep_dive:
            cash_str = deep_dive["cash_and_liquidity"].get("total_cash_and_equivalents", "")
            cash = cls.parse_financial_number(cash_str)

        if total_debt == 0.0 and "debt_structure_and_solvency" in deep_dive:
            debt_str = deep_dive["debt_structure_and_solvency"].get("short_vs_long_term_debt", "")
            m_debt = re.search(r"负债约\s*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)", debt_str)
            total_debt = (
                cls.parse_financial_number(m_debt.group(1))
                if m_debt
                else cls.parse_financial_number(debt_str)
            )

        if finished_goods == 0.0 and "inventory_cycle_analysis" in deep_dive:
            inv_str = deep_dive["inventory_cycle_analysis"].get("inventory_scale", "")
            finished_goods = cls.parse_financial_number(inv_str)

        return rev, fcf, cash, total_debt, finished_goods

    @classmethod
    def _extract_supply_chain_metrics(
        cls, supply_chain: Dict[str, Any], raw_fin: Dict[str, Any]
    ) -> Tuple[float, bool]:
        """提取供应链单一最大客户占比与集中度风险 (私有辅助方法)."""
        top_cust = float(
            supply_chain.get("top_customer_share", raw_fin.get("top_customer_share", 0.15))
        )
        top_cust_risk = bool(supply_chain.get("top_customer_risk_flag", False))
        if top_cust == 0.15 and "top_customers_concentration" in supply_chain:
            cust_text = supply_chain.get("top_customers_concentration", "")
            m_cust = re.search(r"单一最大客户占比\s*([0-9\.]+)%", cust_text)
            if m_cust:
                top_cust = float(m_cust.group(1)) / 100.0
                top_cust_risk = top_cust >= 0.25
        return top_cust, top_cust_risk

    @classmethod
    def _extract_total_debt(
        cls, facts: Dict[str, Any], deep_dive_raw: Dict[str, Any], scale: float
    ) -> float:
        """提取总有息负债 (私有辅助方法)."""
        raw_cur_debt = facts.get("current_debt_2026", facts.get("ShortTermDebt", 0.0))
        cur_debt = (
            float(raw_cur_debt)
            if isinstance(raw_cur_debt, (int, float))
            else cls.parse_financial_number(raw_cur_debt)
        ) * scale
        raw_long_debt = facts.get("long_debt_2026", facts.get("LongTermDebtNoncurrent", 0.0))
        long_debt = (
            float(raw_long_debt)
            if isinstance(raw_long_debt, (int, float))
            else cls.parse_financial_number(raw_long_debt)
        ) * scale
        raw_tot_debt = facts.get("total_debt", (cur_debt + long_debt))
        tot_debt = (
            float(raw_tot_debt)
            if isinstance(raw_tot_debt, (int, float))
            else cls.parse_financial_number(raw_tot_debt)
        )
        if tot_debt == (cur_debt + long_debt) and tot_debt < 1e6 and scale > 1.0:
            tot_debt *= scale
        if tot_debt == 0.0 and "debt_structure_and_solvency" in deep_dive_raw:
            debt_str = deep_dive_raw["debt_structure_and_solvency"].get("short_vs_long_term_debt", "")
            m_debt = re.search(r"负债约\s*([\$¥￥]?[0-9,]+(?:\.[0-9]+)?\s*[MBK]?)", debt_str)
            tot_debt = (
                cls.parse_financial_number(m_debt.group(1))
                if m_debt
                else cls.parse_financial_number(debt_str)
            )
        return tot_debt

    @classmethod
    def _extract_cash_balance(
        cls, facts: Dict[str, Any], deep_dive_raw: Dict[str, Any]
    ) -> float:
        """提取现金及现金等价物总额 (私有辅助方法)."""
        raw_cash = facts.get(
            "cash_2026",
            facts.get(
                "reported_cash",
                facts.get(
                    "CashAndCashEquivalentsAtCarryingValue",
                    facts.get("現金及び預金", facts.get("cash_and_equivalents", 0.0)),
                ),
            ),
        )
        cash_val = (
            float(raw_cash)
            if isinstance(raw_cash, (int, float))
            else cls.parse_financial_number(raw_cash)
        )
        if cash_val == 0.0 and "cash_and_liquidity" in deep_dive_raw:
            cash_str = deep_dive_raw["cash_and_liquidity"].get("total_cash_and_equivalents", "")
            cash_val = cls.parse_financial_number(cash_str)
        return cash_val
