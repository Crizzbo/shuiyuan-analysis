"""法证级证据穿透手术刀引擎 (Forensic Accounting & Ground-Truth Surgical Scalpel).

遵循 Google Python 编程风格指南与《SPEC-04 六步研究法与官方财报三表契约规范》:
针对“手握公司法定证据却缺乏商业血肉、被表面财报粉饰欺骗”的痛点研发五大核心刀法:
1. 附注受限资金与借款契约剥离 (Restricted Cash & Debt Covenant Scalpel);
2. 存货结构毒性与积压滞销解剖 (Inventory Toxicity & Finished Goods Bloat);
3. 研发资本化虚增利润强行费用化 (R&D Capitalization Impairment);
4. 大客户单点脆弱性集中度风险折扣 (Customer Concentration Haircut);
5. 场外微观现实与渠道倒挂三角对撞 (Ground-Truth Reality Triangulation).
"""

# 1. Python 标准库
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ForensicInputData:
    """法证穿透输入证据底账数据契约.

    Attributes:
        ticker: 证券代码 (如 'NVDA', '7203.T').
        company_name: 公司全称或商业简称.
        reported_cash_and_equivalents: 财报主表汇报的现金及等价物总额.
        restricted_cash_in_notes: 附注中披露的保证金、质押款、托管资金 (受限不可动用).
        debt_covenant_minimum_cash: 银行或借贷协议规定的最低流动性红线 (跌破即违约).
        raw_materials: 原材料库存.
        work_in_process: 在制品库存.
        finished_goods: 产成品 / 库存商品.
        prior_finished_goods: 上期产成品库存.
        revenue_growth_pct: 营业收入同期增速 (例如 0.05 代表 5%).
        total_rd_spent: 当期总研发投入.
        capitalized_rd_amount: 计入无形资产/开发支出的研发资本化金额.
        reported_operating_income: 财报主表汇报的营业利润.
        reported_net_income: 财报主表汇报的净利润.
        top_customer_share: 第一大单一客户营收占比 (例如 0.35 代表 35%).
        top_3_customers_share: 前三大客户合计占比 (例如 0.60 代表 60%).
        top_customer_risk_flag: 是否存在自研替代、竞品采购或削减 CapEx 迹象.
        factory_quote: 官方出厂价/标称销售单价.
        real_market_wholesale_quote: 真实场外批发价/二手现货价.
        channel_contract_liabilities_drain_pct: 合同负债(预收款)单季下滑幅度 (例如 -25.0 代表 -25%).
        market: 交易市场 ('US', 'JP', 'CN'，默认自适应推导).
        currency_symbol: 显式货币符号 ('$', '¥').
    """

    ticker: str
    company_name: str
    reported_cash_and_equivalents: float
    restricted_cash_in_notes: float
    debt_covenant_minimum_cash: float
    raw_materials: float
    work_in_process: float
    finished_goods: float
    prior_finished_goods: float
    revenue_growth_pct: float
    total_rd_spent: float
    capitalized_rd_amount: float
    reported_operating_income: float
    reported_net_income: float
    top_customer_share: float = 0.0
    top_3_customers_share: float = 0.0
    top_customer_risk_flag: bool = False
    factory_quote: float = 0.0
    real_market_wholesale_quote: float = 0.0
    channel_contract_liabilities_drain_pct: float = 0.0
    market: Optional[str] = None
    currency_symbol: Optional[str] = None


@dataclass(frozen=True)
class ForensicDissectionResult:
    """手术刀解剖穿透结果数据契约.

    Attributes:
        ticker: 标的代码.
        unrestricted_liquid_cash: 真正能自由动用的硬流动性.
        covenant_safety_buffer: 距银行违约红线的真实安全垫 (若负则违约).
        cash_haircut_ratio_pct: 受限现金占账面现金比例 %.
        finished_goods_surge_pct: 产成品激增速度 %.
        inventory_toxicity_verdict: 存货健康度判定文字.
        suggested_inventory_impairment: 建议计提的存货跌价准备金额.
        true_operating_income: 强行费用化后的真实营业利润.
        operating_income_haircut_pct: 利润被粉饰的虚增挤出比例 %.
        valuation_concentration_haircut_pct: 终端估值集中度下折折扣 %.
        channel_inversion_active: 是否触发渠道批价倒挂.
        inversion_pct: 倒挂百分比 %.
        final_equity_value_haircut_pct: 综合法证穿透后建议估值总下折折扣 %.
        forensic_red_flags: 发现的硬核致命警报清单.
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        currency_symbol: 货币符号 ('$', '¥').
    """

    ticker: str
    unrestricted_liquid_cash: float
    covenant_safety_buffer: float
    cash_haircut_ratio_pct: float
    finished_goods_surge_pct: float
    inventory_toxicity_verdict: str
    suggested_inventory_impairment: float
    true_operating_income: float
    operating_income_haircut_pct: float
    valuation_concentration_haircut_pct: float
    channel_inversion_active: bool
    inversion_pct: float
    final_equity_value_haircut_pct: float
    forensic_red_flags: List[str]
    narrative_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "ticker": self.ticker,
            "currency_symbol": self.currency_symbol,
            "liquidity": {
                "unrestricted_liquid_cash": self.unrestricted_liquid_cash,
                "covenant_safety_buffer": self.covenant_safety_buffer,
                "cash_haircut_ratio_pct": f"{self.cash_haircut_ratio_pct:.2f}%",
            },
            "inventory": {
                "finished_goods_surge_pct": f"{self.finished_goods_surge_pct:.2f}%",
                "inventory_toxicity_verdict": self.inventory_toxicity_verdict,
                "suggested_inventory_impairment": self.suggested_inventory_impairment,
            },
            "operating_income_restated": {
                "true_operating_income": self.true_operating_income,
                "operating_income_haircut_pct": f"{self.operating_income_haircut_pct:.2f}%",
            },
            "concentration_and_channel": {
                "valuation_concentration_haircut_pct": (
                    f"{self.valuation_concentration_haircut_pct:.2f}%"
                ),
                "channel_inversion_active": self.channel_inversion_active,
                "inversion_pct": f"{self.inversion_pct:.2f}%",
            },
            "valuation_penalty": {
                "final_equity_value_haircut_pct": (
                    f"{self.final_equity_value_haircut_pct:.2f}%"
                ),
                "forensic_red_flags": self.forensic_red_flags,
            },
            "narrative_zh": self.narrative_zh,
        }


class ForensicSurgicalScalpel:
    """法证级证据穿透手术刀中枢 (Google Python Style Guide 架构设计)."""

    def __init__(self):
        """初始化法证穿透手术刀引擎."""
        self.version: str = "1.0.0"

    def dissect(self, data: ForensicInputData) -> ForensicDissectionResult:
        """执行全套五式手术刀穿透解剖.

        Args:
            data: ForensicInputData 强类型输入事实底账.

        Returns:
            ForensicDissectionResult 包含真实流动性、存货毒性、真实利润及估值惩罚的穿透结果.
        """
        red_flags: List[str] = []
        haircut_accumulated_pct: float = 0.0

        curr_sym = self._resolve_currency_symbol(data)

        # 1. 第一刀: 附注受限资金与借款契约剥离
        unrestricted_cash, covenant_buffer, cash_haircut_pct = (
            self._dissect_cash_and_covenant(
                data=data,
                curr_sym=curr_sym,
                red_flags=red_flags,
            )
        )
        if covenant_buffer < 0:
            haircut_accumulated_pct += 25.0
        elif covenant_buffer < unrestricted_cash * 0.20:
            haircut_accumulated_pct += 8.0

        # 2. 第二刀: 存货结构毒性与积压滞销解剖
        finished_goods_growth, inventory_verdict, suggested_impairment = (
            self._dissect_inventory_toxicity(
                data=data,
                red_flags=red_flags,
            )
        )
        growth_spread = finished_goods_growth - (data.revenue_growth_pct * 100.0)
        total_inv = (
            max(0.0, data.raw_materials)
            + max(0.0, data.work_in_process)
            + max(0.0, data.finished_goods)
        )
        if growth_spread > 20.0 and data.finished_goods > 0:
            haircut_accumulated_pct += 10.0
        elif total_inv > 0 and (data.finished_goods / total_inv) > 0.60:
            haircut_accumulated_pct += 5.0

        # 3. 第三刀: 研发资本化虚增利润强行费用化
        true_op_income, op_haircut_pct = self._dissect_rd_capitalization(
            data=data,
            red_flags=red_flags,
        )
        cap_ratio = (
            (data.capitalized_rd_amount / max(1.0, data.total_rd_spent))
            if data.total_rd_spent > 0
            else 0.0
        )
        if cap_ratio > 0.12:
            haircut_accumulated_pct += min(15.0, op_haircut_pct * 0.5)

        # 4. 第四刀: 大客户单点脆弱性集中度折扣
        concentration_haircut = self._dissect_customer_concentration(
            data=data,
            red_flags=red_flags,
        )
        haircut_accumulated_pct += concentration_haircut

        # 5. 第五刀: 场外微观现实与渠道倒挂三角对撞
        channel_inversion, inversion_pct = self._dissect_channel_inversion(
            data=data,
            red_flags=red_flags,
        )
        if channel_inversion:
            haircut_accumulated_pct += min(15.0, abs(inversion_pct))
        if data.channel_contract_liabilities_drain_pct < -20.0:
            haircut_accumulated_pct += 8.0

        # 封顶总估值下折折扣 60%
        final_haircut = min(60.0, haircut_accumulated_pct)

        narrative_zh = self._render_narrative(
            data=data,
            curr_sym=curr_sym,
            final_haircut=final_haircut,
            unrestricted_cash=unrestricted_cash,
            cash_haircut_pct=cash_haircut_pct,
            covenant_buffer=covenant_buffer,
            inventory_verdict=inventory_verdict,
            finished_goods_growth=finished_goods_growth,
            suggested_impairment=suggested_impairment,
            true_op_income=true_op_income,
            op_haircut_pct=op_haircut_pct,
            concentration_haircut=concentration_haircut,
            channel_inversion=channel_inversion,
            inversion_pct=inversion_pct,
            red_flags=red_flags,
        )

        return ForensicDissectionResult(
            ticker=data.ticker,
            unrestricted_liquid_cash=round(unrestricted_cash, 2),
            covenant_safety_buffer=round(covenant_buffer, 2),
            cash_haircut_ratio_pct=round(cash_haircut_pct, 2),
            finished_goods_surge_pct=round(finished_goods_growth, 2),
            inventory_toxicity_verdict=inventory_verdict,
            suggested_inventory_impairment=round(suggested_impairment, 2),
            true_operating_income=round(true_op_income, 2),
            operating_income_haircut_pct=round(op_haircut_pct, 2),
            valuation_concentration_haircut_pct=round(concentration_haircut, 2),
            channel_inversion_active=channel_inversion,
            inversion_pct=round(inversion_pct, 2),
            final_equity_value_haircut_pct=round(final_haircut, 2),
            forensic_red_flags=red_flags,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _resolve_currency_symbol(data: ForensicInputData) -> str:
        """根据证券代码和市场推导货币符号 (私有辅助方法)."""
        t_up = (data.ticker or "").upper()
        m_up = (data.market or "").upper()
        is_jp = (
            m_up == "JP"
            or t_up.endswith(".T")
            or t_up.endswith(".JP")
            or (t_up.isdigit() and len(t_up) == 4)
        )
        is_cn = (
            m_up == "CN"
            or t_up.endswith(".SS")
            or t_up.endswith(".SZ")
            or (t_up.isdigit() and len(t_up) == 6)
        )
        if data.currency_symbol:
            return data.currency_symbol
        if is_jp or is_cn:
            return "¥"
        return "$"

    @staticmethod
    def _dissect_cash_and_covenant(
        data: ForensicInputData, curr_sym: str, red_flags: List[str]
    ) -> Tuple[float, float, float]:
        """剖析附注受限资金与借款契约安全垫 (私有辅助方法)."""
        safe_cash = max(0.01, data.reported_cash_and_equivalents)
        safe_restricted = max(0.0, data.restricted_cash_in_notes)
        unrestricted_cash = max(0.0, data.reported_cash_and_equivalents - safe_restricted)
        covenant_buffer = unrestricted_cash - max(0.0, data.debt_covenant_minimum_cash)
        cash_haircut_pct = (safe_restricted / safe_cash) * 100.0

        if cash_haircut_pct > 15.0:
            red_flags.append(
                f"受限资金占比高达 {cash_haircut_pct:.1f}%，账面现金存在严重流动性虚胖"
            )

        if covenant_buffer < 0:
            red_flags.append(
                f"【致命债务违约风险】真实可动用流动资金 {curr_sym}{unrestricted_cash:,.0f} "
                f"已击穿借贷契约底线 {curr_sym}{data.debt_covenant_minimum_cash:,.0f}"
            )
        elif covenant_buffer < unrestricted_cash * 0.20:
            red_flags.append(
                f"偿债流动性逼近警戒线，契约安全垫仅剩 {curr_sym}{covenant_buffer:,.0f}"
            )

        return unrestricted_cash, covenant_buffer, cash_haircut_pct

    @staticmethod
    def _dissect_inventory_toxicity(
        data: ForensicInputData, red_flags: List[str]
    ) -> Tuple[float, str, float]:
        """剖析存货结构毒性与积压滞销 (私有辅助方法)."""
        total_inv = (
            max(0.0, data.raw_materials)
            + max(0.0, data.work_in_process)
            + max(0.0, data.finished_goods)
        )
        finished_goods_growth = 0.0
        if data.prior_finished_goods > 0:
            finished_goods_growth = (
                (data.finished_goods - data.prior_finished_goods)
                / data.prior_finished_goods
            ) * 100.0

        growth_spread = finished_goods_growth - (data.revenue_growth_pct * 100.0)
        suggested_impairment = 0.0

        if growth_spread > 20.0 and data.finished_goods > 0:
            inventory_verdict = "严重积压塞货 (产成品异常飙升，滞销减值高危)"
            excess_growth_ratio = min(0.50, growth_spread / 100.0)
            suggested_impairment = data.finished_goods * excess_growth_ratio * 0.30
            red_flags.append(
                f"产成品库存飙升 {finished_goods_growth:.1f}%，远超营收增速 "
                f"{data.revenue_growth_pct*100:.1f}%，存在渠道塞货滞销"
            )
        elif total_inv > 0 and (data.finished_goods / total_inv) > 0.60:
            inventory_verdict = "产成品偏高 (库存结构承压，需警惕去库节奏)"
            suggested_impairment = data.finished_goods * 0.05
        else:
            inventory_verdict = "健康良性周转 (产销平衡，无存货减值隐患)"

        return finished_goods_growth, inventory_verdict, suggested_impairment

    @staticmethod
    def _dissect_rd_capitalization(
        data: ForensicInputData, red_flags: List[str]
    ) -> Tuple[float, float]:
        """剖析研发资本化虚增利润并强行费用化 (私有辅助方法)."""
        cap_ratio = (
            (data.capitalized_rd_amount / max(1.0, data.total_rd_spent))
            if data.total_rd_spent > 0
            else 0.0
        )
        true_op_income = data.reported_operating_income - data.capitalized_rd_amount
        denom_op = max(1.0, abs(data.reported_operating_income))
        op_haircut_pct = (data.capitalized_rd_amount / denom_op) * 100.0

        if cap_ratio > 0.12:
            if data.reported_operating_income <= 0.0:
                red_flags.append(
                    f"管理层将 {cap_ratio*100:.1f}% 研发支出资本化，企图掩盖实质性亏损 "
                    f"(真实营业亏损扩大至 {true_op_income:,.1f})"
                )
            else:
                red_flags.append(
                    f"管理层将 {cap_ratio*100:.1f}% 研发支出资本化，真实营业利润虚增了 "
                    f"{op_haircut_pct:.1f}%"
                )

        return true_op_income, op_haircut_pct

    @staticmethod
    def _dissect_customer_concentration(
        data: ForensicInputData, red_flags: List[str]
    ) -> float:
        """测算大客户单点脆弱性集中度折扣 (私有辅助方法)."""
        concentration_haircut = 0.0
        if data.top_customer_share > 0.30:
            base_concentration_penalty = (data.top_customer_share - 0.25) * 40.0
            if data.top_customer_risk_flag:
                base_concentration_penalty *= 2.0
                red_flags.append(
                    f"【高危单点依赖】第一大客户占比高达 {data.top_customer_share*100:.1f}% "
                    "且出现替代/砍单风险敞口"
                )
            else:
                red_flags.append(
                    f"第一大客户依赖度达 {data.top_customer_share*100:.1f}%，议价权处于劣势"
                )
            concentration_haircut = min(25.0, base_concentration_penalty)
        return concentration_haircut

    @staticmethod
    def _dissect_channel_inversion(
        data: ForensicInputData, red_flags: List[str]
    ) -> Tuple[bool, float]:
        """剖析场外微观现实与渠道批价倒挂 (私有辅助方法)."""
        channel_inversion = False
        inversion_pct = 0.0
        if data.factory_quote > 0 and data.real_market_wholesale_quote > 0:
            spread = data.real_market_wholesale_quote - data.factory_quote
            inversion_pct = (spread / data.factory_quote) * 100.0
            if spread < 0:
                channel_inversion = True
                red_flags.append(
                    f"【渠道批价倒挂】真实批发价 ({data.real_market_wholesale_quote}) "
                    f"低于出厂价 ({data.factory_quote})，倒挂幅度 {abs(inversion_pct):.1f}%"
                )

        if data.channel_contract_liabilities_drain_pct < -20.0:
            red_flags.append(
                f"合同负债骤降 {abs(data.channel_contract_liabilities_drain_pct):.1f}%，"
                "渠道经销商打款意愿瓦解"
            )

        return channel_inversion, inversion_pct

    @staticmethod
    def _render_narrative(
        data: ForensicInputData,
        curr_sym: str,
        final_haircut: float,
        unrestricted_cash: float,
        cash_haircut_pct: float,
        covenant_buffer: float,
        inventory_verdict: str,
        finished_goods_growth: float,
        suggested_impairment: float,
        true_op_income: float,
        op_haircut_pct: float,
        concentration_haircut: float,
        channel_inversion: bool,
        inversion_pct: float,
        red_flags: List[str],
    ) -> str:
        """生成买方通俗自然语言研报卡片 (私有辅助方法)."""
        red_flags_clause = (
            "；".join(red_flags)
            if red_flags
            else "未发现高危法务财务异常，各分项指标真实健康"
        )
        inversion_clause = (
            f"批价出现倒挂 (折价 {abs(inversion_pct):.1f}%)"
            if channel_inversion
            else "批价与渠道顺价健康"
        )
        return (
            f"【标的 {data.ticker} 法证级财务造假与微观血肉手术刀研报】"
            f"综合法证估值总下折惩罚: 建议扣减 -{final_haircut:.1f}% DCF 估值折扣。"
            f"硬流动性穿透: 真实可动用自由现金 {curr_sym}{unrestricted_cash:,.1f} "
            f"(受限资金扣减率 {cash_haircut_pct:.1f}%)，"
            f"银行契约违约安全垫为 {curr_sym}{covenant_buffer:,.1f}。"
            f"存货塞货诊断: 处于【{inventory_verdict}】(产成品增速 {finished_goods_growth:.1f}%)，"
            f"建议计提跌价准备 {curr_sym}{suggested_impairment:,.1f}。"
            f"利润真实性挤出: 剔除研发资本化粉饰后，真实营业利润为 {curr_sym}{true_op_income:,.1f} "
            f"(会计粉饰虚增率 {op_haircut_pct:.1f}%)。"
            f"集中度与场外倒挂: 核心大客户集中度扣减 -{concentration_haircut:.1f}%，"
            f"渠道现实对撞显示【{inversion_clause}】。"
            f"法务核心警报清单: {red_flags_clause}。"
        )
