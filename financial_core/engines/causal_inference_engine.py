"""买方量化因果推导网络与商业大白话事实生成引擎 (Quantitative Causal Inference Engine).

物理架构定界 (Layer 1: financial_core):
- 纯净底层量化推导中枢，零外层依赖;
- 纯相对导入与标准库依赖 (dataclasses, typing);
- 承担将全流水线各量化工序的客观指标（存货DIO、批零倒挂、合同负债、现金跑道、
  微观加价率、前沿距离、空头逼仓、期权Gamma、宏观WACC加压）构建成严格因果拓扑链条;
- 严格遵循自然语言汇报规范：杜绝生硬数学公式或空洞模板，以通俗自然的商业投资语言输出。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .industry_causal_registry import IndustryCausalStrategyRegistry


@dataclass
class CausalInferenceResult:
    """因果推导综合结果数据结构."""
    primary_catalysts: List[str]            # 核心催化事实清单 (通俗商业投资大白话)
    key_risks: List[str]                    # 核心破位与警示事实清单 (通俗商业投资大白话)
    top_optimistic_trigger: str             # 达成乐观靶心的主导催化路径总结
    top_pessimistic_trigger: str            # 跌穿悲观底价的主导风险路径总结
    causal_confidence_score: float = 1.0    # 因果证据链完备度评分 (0.0 ~ 1.0)
    narrative_zh: str = ""                  # 买方通俗全息研报卡片 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_catalysts": self.primary_catalysts,
            "key_risks": self.key_risks,
            "top_optimistic_trigger": self.top_optimistic_trigger,
            "top_pessimistic_trigger": self.top_pessimistic_trigger,
            "causal_confidence_score": round(self.causal_confidence_score, 2),
            "narrative_zh": self.narrative_zh,
        }


class QuantitativeCausalInferenceEngine:
    """买方量化因果推导中枢."""

    def __init__(self):
        self.version = "1.1.0"
        self.industry_registry = IndustryCausalStrategyRegistry()

    def infer_catalysts_and_risks(
        self,
        company_info: Dict[str, Any],
        forensic_result: Dict[str, Any],
        macro_shock_result: Dict[str, Any],
        valuation_result: Dict[str, Any],
        microstructure_result: Dict[str, Any],
        micro_founded_macro_result: Optional[Dict[str, Any]] = None,
        attribution_result: Optional[Dict[str, Any]] = None,
    ) -> CausalInferenceResult:
        """从全流水线各量化工序输出构建因果推导网络."""
        catalysts: List[str] = []
        risks: List[str] = []

        ticker = company_info.get("ticker", "")
        sector = company_info.get("sector", "")
        industry = company_info.get("industry", sector)
        cur_p = company_info.get("current_price", 0.0)

        # -------------------------------------------------------------
        # 维度 0: 41 细分行业专属因果策略路由 (高特异性买方商业事实)
        # -------------------------------------------------------------
        merged_metrics = dict(company_info)
        if micro_founded_macro_result:
            merged_metrics["micro_markup_ratio"] = micro_founded_macro_result.get("micro_markup_ratio", 1.0)
            merged_metrics["distance_to_technology_frontier"] = micro_founded_macro_result.get("distance_to_technology_frontier", 1.0)
        merged_metrics["hard_runway_months"] = valuation_result.get("hard_runway_months", 999.0)

        ind_facts = self.industry_registry.evaluate_industry_causal_facts(
            industry_id=industry,
            company_metrics=merged_metrics,
            forensic_findings=forensic_result,
            macro_shock_data=macro_shock_result,
        )
        for cat in ind_facts.industry_catalysts:
            if cat not in catalysts:
                catalysts.append(cat)
        for rk in ind_facts.industry_risks:
            if rk not in risks:
                risks.append(rk)

        # -------------------------------------------------------------
        # 维度 1: 行业微观商业血肉与渠道库存 (特异性高优先级事实)
        # -------------------------------------------------------------
        factory_quote = company_info.get("factory_quote", 0.0)
        wholesale_quote = company_info.get("real_wholesale_quote", 0.0)
        liabilities_drain = company_info.get("contract_liabilities_drain_pct", 0.0)
        inv_verdict = forensic_result.get("inventory_verdict", "良性周转")

        # 白酒/高端消费品批零倒挂与经销商打款意愿
        if factory_quote > 0.0 and wholesale_quote > 0.0:
            if wholesale_quote < factory_quote:
                discount_pct = (factory_quote - wholesale_quote) / factory_quote * 100.0
                risks.append(
                    f"【渠道批零倒挂断裂】真实批发价低于出厂价（倒挂 {discount_pct:.1f}%），"
                    f"渠道商无利可图出现抛货减仓；若厂家被迫调整出厂价或加大返点补贴，将直接冲击中枢利润率。"
                )
            else:
                premium_pct = (wholesale_quote - factory_quote) / factory_quote * 100.0
                catalysts.append(
                    f"【渠道顺价销售健康】真实批发价高于出厂价（顺价空间达 +{premium_pct:.1f}%），"
                    f"渠道利润空间丰厚、经销商打款意愿饱满，核心品牌护城河与自发提价空间扎实。"
                )

        if liabilities_drain < -15.0:
            risks.append(
                f"【渠道蓄水池大幅干涸】合同负债出现剧烈净流出（环比缩减 {abs(liabilities_drain):.1f}%），"
                f"反映下游经销商压货或订货意愿急剧冷却，后续数个季度营收与现金回笼将直接承压。"
            )

        # 存货毒性与去库存周期
        if "异常积压" in inv_verdict or "滞销" in inv_verdict:
            risks.append(
                "【库存滞销与跌价减值冲击】库房产成品库存增速严重脱离终端销售实际消化速度，"
                "渠道存在严重积压滞销征兆；后续降价清仓或计提存货跌价准备将直接吞噬利润。"
            )
        elif inv_verdict == "良性周转" and company_info.get("current_dio_days", 0.0) <= 90.0:
            dio = company_info.get("current_dio_days", 60.0)
            catalysts.append(
                f"【库存健康与营运资本回流】存货周转天数稳定在 {dio:.0f} 天优良水位，"
                f"未见异常压库包袱；终端需求一旦温和回暖，营运资金将快速转为高流动性真实现金流。"
            )

        # -------------------------------------------------------------
        # 维度 2: 现金跑道与造血能力 (买方底线思维)
        # -------------------------------------------------------------
        runway_months = valuation_result.get("hard_runway_months", 999.0)
        runway_desc = valuation_result.get("hard_runway_desc", "")
        unrestricted_cash = forensic_result.get("unrestricted_cash", 0.0)
        covenant_min_cash = company_info.get("debt_covenant_min_cash", 0.0)

        if runway_months < 12.0 or (covenant_min_cash > 0.0 and unrestricted_cash <= covenant_min_cash):
            risks.append(
                f"【现金跑道告急与股权稀释红线】扣除受限质押与债务红线后，不受限现金储备仅够维持 {runway_months:.1f} 个月现金跑道支出；"
                f"企业迫近债务重组边缘，若短期无法扭亏，极可能在低位折价定增股权，导致老股东权益严重稀释。"
            )
        elif "持续净流入" in runway_desc:
            catalysts.append(
                "【内生造血充沛免除稀释】企业具备成熟且持续的自由现金流净流入造血能力，"
                "完全实现内生自给自足，彻底免除外部定增抽水与债务再融资风险。"
            )

        # -------------------------------------------------------------
        # 维度 3: 垄断定价权与技术前沿 (微观基础宏观模型)
        # -------------------------------------------------------------
        if micro_founded_macro_result:
            hall_tier = micro_founded_macro_result.get("pricing_power_tier", "")
            markup = micro_founded_macro_result.get("micro_markup_ratio", 1.0)
            dtf = micro_founded_macro_result.get("distance_to_technology_frontier", 1.0)

            if "强定价权" in hall_tier or markup >= 1.15:
                catalysts.append(
                    f"【定价权护城河抗成本通胀】微观加价率达 {markup:.2f}（具备超额定价壁垒），"
                    f"在供应链成本与要素价格上涨周期，能平稳将通胀压力转嫁至下游终端，维系中枢利润率稳定。"
                )
            elif "受挤压" in hall_tier or markup < 0.95:
                risks.append(
                    f"【产业链议价地位受挤压】微观加价率仅为 {markup:.2f}，处于成本转嫁弱势地位，"
                    f"上游涨价或下游压价极易挤压毛利空间，缺乏防御护城河。"
                )

            if dtf <= 0.20:
                catalysts.append(
                    f"【紧贴全球创新技术前沿】与全球前沿技术距离仅 {dtf:.2f}（处于领跑梯队），"
                    f"高强度研发有效转化为技术专利与先发垄断壁垒，锁定未来超额投资回报。"
                )

        # -------------------------------------------------------------
        # 维度 4: 筹码博弈与衍生品 Greeks 因果 (做市商与空头踩踏)
        # -------------------------------------------------------------
        squeeze_score = microstructure_result.get("squeeze_score", 0.0)
        borrow_cost = company_info.get("cost_to_borrow_pct", 0.0)
        gamma_drag = attribution_result.get("gamma_drag_impact", 0.0) if attribution_result else 0.0

        if squeeze_score >= 55.0 or borrow_cost >= 6.0:
            borrow_desc = f"，融券借券成本高达 {borrow_cost:.1f}%" if borrow_cost > 0.0 else ""
            catalysts.append(
                f"【空头筹码高度拥挤逼仓】场内融券卖空持仓高度集中（空头挤压评分 {squeeze_score:.1f}{borrow_desc}）；"
                f"空头止损防线薄弱，基本面边际改善极易诱发空头集中踩踏式回补，推动股价向乐观靶心快速冲刺。"
            )

        if gamma_drag < -3.0:
            risks.append(
                "【期权做市商顺势助跌踩踏】期权持仓呈现空头集中特征，做市商处于负 Gamma 敏感区域；"
                "股价一旦破位下行，做市商动态对冲程序将被动顺势抛售股票，引发加速破位超跌。"
            )

        # -------------------------------------------------------------
        # 维度 5: 宏观折现率加压与大客户集中度
        # -------------------------------------------------------------
        shocked_wacc = macro_shock_result.get("shocked_wacc_pct", 9.0)
        haircut = macro_shock_result.get("valuation_haircut_pct", 0.0)
        top_cust_share = company_info.get("top_customer_share", 0.0)

        if top_cust_share >= 30.0 or company_info.get("top_customer_risk_flag", False):
            share_desc = f"超 {top_cust_share:.1f}%" if top_cust_share > 0.0 else "高比例"
            risks.append(
                f"【单一客户集中度过高】最大客户贡献了{share_desc}营收；"
                f"一旦核心客户削减采购配额、调整供应链或切入自研，公司将面临断崖式滑坡与产能闲置亏损。"
            )

        if haircut >= 15.0 or shocked_wacc >= 10.0:
            risks.append(
                f"【宏观资金面趋紧压制估值】宏观无风险利率偏高致使综合折现成本升至 {shocked_wacc:.1f}%，"
                f"推高负债端利息负担并压制公允估值锚点下折 {haircut:.1f}%，构成跌穿悲观底价的核心宏观外因。"
            )

        # -------------------------------------------------------------
        # 保底防御：确保任何合法输入至少产出 1-3 条通俗专业事实，杜绝空列表
        # -------------------------------------------------------------
        if not catalysts:
            mos = valuation_result.get("margin_of_safety_pct", 0.0)
            if mos > 15.0:
                catalysts.append(
                    f"【估值折价提供厚实安全垫】当前市场报价显著低于企业内在公允价值（折价空间达 {mos:.1f}%），"
                    f"资产价格已充分计入悲观预期，长期均值回归动力充沛。"
                )
            else:
                catalysts.append(
                    "【内生复合增长平稳释放】企业依赖现有业务基本盘与稳健的再投资回报率，"
                    "通过逐年经营现金流的内生累积驱动内在价值向公允中枢平稳修复。"
                )

        if not risks:
            red_flags = forensic_result.get("red_flags", [])
            if red_flags:
                risks.append(
                    f"【财报法证审计检出瑕疵】法证手术刀检出 {len(red_flags)} 项审计异常，"
                    f"包括部分非经常性损益或资本化支出，需防范后续财务挤水分后的估值重估风险。"
                )
            else:
                risks.append(
                    "【宏观中枢与行业周期性波动】当前微观质地优良，主要风险集中于宏观经济周期回落"
                    "引发的终端需求放缓及行业估值乘数中枢跟随大盘下移。"
                )

        top_opt = catalysts[0] if catalysts else "基本面内生现金流稳健增长驱动估值修复。"
        top_pes = risks[0] if risks else "宏观流动性紧缩与行业周期回落压制估值中枢。"

        confidence = 1.0 if len(catalysts) >= 2 and len(risks) >= 2 else 0.85

        # 构建买方通俗全息研报卡片 (去工程符号化)
        cat_highlights = "；".join([c.replace("【", "").replace("】", ": ") for c in catalysts[:3]])
        risk_highlights = "；".join([r.replace("【", "").replace("】", ": ") for r in risks[:3]])
        narrative_zh = (
            f"【标的 {ticker or '公司'} 量化因果推导与情景触发全息研报】"
            f"因果推断置信度【{round(confidence * 100.0, 1)}%】(证据链完备度评分 {confidence:.2f})。"
            f"主导催化与乐观靶心路径: {top_opt} "
            f"底线防御与悲观底价破位风险: {top_pes} "
            f"核心催化清单 (前{min(3, len(catalysts))}项): {cat_highlights}。 "
            f"核心警示清单 (前{min(3, len(risks))}项): {risk_highlights}。"
        )

        return CausalInferenceResult(
            primary_catalysts=catalysts,
            key_risks=risks,
            top_optimistic_trigger=top_opt,
            top_pessimistic_trigger=top_pes,
            causal_confidence_score=confidence,
            narrative_zh=narrative_zh,
        )
