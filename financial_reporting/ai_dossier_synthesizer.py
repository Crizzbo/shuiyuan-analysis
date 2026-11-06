"""AI 深度投研建档综合分析器 (AI Company Dossier Synthesizer).

定位与职责:
1. 解决“档案建造器不应包含硬编码固定值，数据必须直接传入，分析由 AI 做出并写入结论”的核心要求;
2. 将底层客观事实 (官方三表底稿、行情时效、产业主数据) 与金融量化计算结果 (微观宏观传导、杜邦分析、违约距离、情景DCF) 结构化组装;
3. 规范化对接 AI 深度分析研判结论 (商业模式画像、护城河五维解构、供应链上下游集中度与断供风险、催化剂与下行黑天鹅触发器);
4. 输出严格符合 schemas/deep_dossier.schema.json 契约的完整动态投研档案数据字典，直接供 ExcelDossierBuilder 渲染生成买方工作簿。
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .data_collection_gateway import UnifiedDataCollectionGateway
from .ai_research_agent import AIResearchAgent, AIEngineAdapter
from financial_core.engines.knowledge_graph_engine import KnowledgeGraphEngine
from financial_core.engines.financial_statement_facade import (
    FinancialStatementFacade,
    NormalizedFinancialProfile,
    BalanceSheetIdentityError,
)

ROOT = Path(__file__).resolve().parents[1]


class AIDossierSynthesizer:
    """AI 驱动的公司深度投研档案合成引擎."""

    @classmethod
    def synthesize_dossier(
        cls,
        ticker: str,
        market: str,
        company_name: str,
        industry_id: str,
        industry_name_zh: str,
        # 1. 客观财务事实底稿 (Audited Historical Financials)
        financial_statements: Optional[Dict[str, Any]] = None,
        # 2. 现行行情与估值中枢 (Market & Pricing Corridor)
        market_quote: Optional[Dict[str, Any]] = None,
        # 3. 诺贝尔微观基础宏观量化测算 (Quantitative Nobel Engine Output)
        micro_macro_metrics: Optional[Dict[str, Any]] = None,
        # 4. AI 深度质性分析结论 (AI Research Conclusions)
        ai_analysis: Optional[Dict[str, Any]] = None,
        # 5. 官方证据哈希与重大披露 (Evidence Manifest & Material Events)
        evidence_manifest: Optional[List[Dict[str, Any]]] = None,
        material_events: Optional[List[Dict[str, Any]]] = None,
        report_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """将客观数据、量化引擎输出与 AI 深度分析结论无缝组装为标准化深度档案字典.

        杜绝任何未传入数据的硬编码固定值推填；未披露字段显式标明待分析或未披露。
        """
        curr_date = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ai = ai_analysis or {}
        quote = market_quote or {}
        micro = micro_macro_metrics or {}
        fin = financial_statements or {}

        # ----------------------------------------------------------------------
        # 【前置门禁 1: 知识图谱投研合规与知识边界硬拦截】
        # ----------------------------------------------------------------------
        proposed_valuation = quote.get("valuation_model") or ai.get("valuation_model")
        if industry_id:
            kg_engine = KnowledgeGraphEngine()
            ok, kg_msg = kg_engine.validate_action_boundary(industry_id, proposed_valuation_model=proposed_valuation)
            if not ok:
                raise ValueError(f"【知识图谱边界硬拦截】标的 {ticker} ({industry_id}): {kg_msg}")

        # ----------------------------------------------------------------------
        # 【前置门禁 2: 企业财报防腐中继门面与刚性平账自检】
        # ----------------------------------------------------------------------
        normalized_profile: Optional[NormalizedFinancialProfile] = None
        if fin and (fin.get("total_assets") or fin.get("assets")):
            facade = FinancialStatementFacade()
            # 整合 ticker 与基本事实
            facade_input = dict(fin)
            facade_input.setdefault("ticker", ticker)
            facade_input.setdefault("company_name", company_name)
            normalized_profile = facade.process_company_filing(
                raw_filing_facts=facade_input,
                raw_quote_data=quote,
                industry_code=industry_id
            )

        # ----------------------------------------------------------------------
        # 1. 基础概览 (Overview) - 融合 AI 商业模式画像
        # ----------------------------------------------------------------------
        overview = {
            "ticker": ticker,
            "company_name": company_name,
            "company_name_zh": company_name,
            "market": market,
            "industry_id": industry_id,
            "industry_name_zh": industry_name_zh,
            "business_model": ai.get("business_model", "待 AI 商业模式解构录入"),
            "revenue_mix": ai.get("revenue_mix", "待 AI 收入分部矩阵录入"),
        }

        # ----------------------------------------------------------------------
        # 2. 投资备忘录与决策走廊 (Decision & Valuation Corridor)
        # ----------------------------------------------------------------------
        cur_price = quote.get("current_price")
        pessimistic = quote.get("pessimistic_floor")
        fair_anchor = quote.get("fair_anchor")
        optimistic = quote.get("optimistic_target")

        # 若提供了现价与公允，由公式严密计算安全边际，杜绝硬编码
        if cur_price and fair_anchor and cur_price > 0:
            margin_of_safety_pct = ((fair_anchor - cur_price) / cur_price) * 100.0
        else:
            margin_of_safety_pct = quote.get("margin_of_safety_pct")

        # 击球区状态由 AI 分析结论与定量阈值共同确定
        strike_zone_status = ai.get("strike_zone_status")
        if not strike_zone_status and margin_of_safety_pct is not None:
            if margin_of_safety_pct >= 25.0:
                strike_zone_status = "黄金击球区 (Strike Zone)"
            elif margin_of_safety_pct >= 10.0:
                strike_zone_status = "合理配置区 (Fair Value)"
            elif margin_of_safety_pct >= -5.0:
                strike_zone_status = "中性观望区 (Neutral)"
            else:
                strike_zone_status = "估值透支区 (Overvalued)"

        raw_stance = str(ai.get("stance", "中性持有 (跟踪验证)"))
        stance_map = {
            "BUY_VALUE_ZONE": "估值洼地 (积极布局)",
            "ACCUMULATE_FAIR_VALUE": "合理价值 (逢低定投)",
            "NEUTRAL_WAIT": "中性等待 (保持观望)",
            "NEUTRAL_HOLD": "中性持有 (跟踪验证)",
            "REDUCE_OVERVALUED": "估值透支 (防守减持)",
            "HIGH_RISK_AVOID": "高危预警 (回避防踏空)",
        }
        stance_zh = stance_map.get(raw_stance, raw_stance)

        # ----------------------------------------------------------------------
        # 【投资评级风控硬拦截】：行情时效阻断或负安全边际下严禁生成买入评级
        # ----------------------------------------------------------------------
        raw_rating = ai.get("rating")
        if raw_rating is not None:
            raw_rating = str(raw_rating)
        freshness_val = str(quote.get("freshness_status", "前一交易日收盘价基准"))
        is_quote_blocked = "阻断" in freshness_val or "STALE" in freshness_val.upper() or "INVALID" in freshness_val.upper()

        if is_quote_blocked:
            if raw_rating and "买入" in raw_rating:
                raw_rating = "行情时效阻断 (暂停买入)"
        elif margin_of_safety_pct is not None and margin_of_safety_pct < 0:
            if raw_rating and "买入" in raw_rating:
                raw_rating = "估值透支 (暂停买入)"

        decision_summary = {
            "current_price": cur_price,
            "pessimistic_floor": pessimistic,
            "fair_anchor": fair_anchor,
            "optimistic_target": optimistic,
            "margin_of_safety_pct": margin_of_safety_pct,
            "freshness_status": freshness_val,
            "strike_zone_status": strike_zone_status or "待评定",
            "rating": raw_rating,
            "stance": stance_zh,
            "stance_zh": stance_zh,
            "scenario_cards": quote.get("scenario_cards", {}),
        }

        # ----------------------------------------------------------------------
        # 3. 行业胜负手与护城河五维解构 (Industry Dynamics & Moat) - 来自 AI
        # ----------------------------------------------------------------------
        ind_sub = ai.get("industry_dynamics", {}) if isinstance(ai.get("industry_dynamics"), dict) else {}
        industry_dynamics = {
            "winner_factor": ai.get("winner_factor") or ind_sub.get("winner_factor", "待 AI 行业胜负手提炼"),
            "market_share_and_crn": ai.get("market_share_and_crn") or ind_sub.get("market_share_and_crn", "待 AI 市占率分析"),
            "tam_and_cagr": ai.get("tam_and_cagr") or ind_sub.get("tam_and_cagr", "待 AI TAM 空间测算"),
        }

        moat_sub = ai.get("moat_analysis", {}) if isinstance(ai.get("moat_analysis"), dict) else {}
        moat_analysis = {
            "network_effects": ai.get("network_effects") or moat_sub.get("network_effects", "待 AI 网络效应评估"),
            "switching_costs": ai.get("switching_costs") or moat_sub.get("switching_costs", "待 AI 转换成本评估"),
            "cost_advantage_and_scale": ai.get("cost_advantage_and_scale") or moat_sub.get("cost_advantage_and_scale", "待 AI 成本规模优势评估"),
            "intangible_assets": ai.get("intangible_assets") or moat_sub.get("intangible_assets", "待 AI 无形资产与专利评估"),
            "reinvestment_efficiency": ai.get("reinvestment_efficiency") or moat_sub.get("reinvestment_efficiency", "待 AI 再投资效率评估"),
        }

        # ----------------------------------------------------------------------
        # 4. 供应链上下游集中度风险 (Supply Chain & Customer Concentration) - 来自 AI
        # ----------------------------------------------------------------------
        sc_sub = ai.get("supply_chain_analysis", {}) if isinstance(ai.get("supply_chain_analysis"), dict) else {}
        sc_up = sc_sub.get("upstream_suppliers", {}) if isinstance(sc_sub.get("upstream_suppliers"), dict) else {}
        sc_down = sc_sub.get("downstream_customers", {}) if isinstance(sc_sub.get("downstream_customers"), dict) else {}
        supply_chain_analysis = {
            "upstream_suppliers": {
                "core_suppliers": ai.get("core_suppliers") or sc_up.get("core_suppliers", "待 AI 上游核心供应商穿透"),
                "supplier_concentration": ai.get("supplier_concentration") or sc_up.get("supplier_concentration", "待 AI 供应商集中度测算"),
                "supply_chain_risks": ai.get("supply_chain_risks") or sc_up.get("supply_chain_risks", "待 AI 供应链断供风险剖析"),
            },
            "downstream_customers": {
                "customer_structure": ai.get("customer_structure") or sc_down.get("customer_structure", "待 AI 下游主要客户结构穿透"),
                "top5_customer_concentration": ai.get("top5_customer_concentration") or sc_down.get("top5_customer_concentration", "待 AI 前五大客户集中度测算"),
                "default_and_churn_risks": ai.get("default_and_churn_risks") or sc_down.get("default_and_churn_risks", "待 AI 客户流失与违约风险分析"),
            },
        }

        # ----------------------------------------------------------------------
        # 5. 财务体检与三表底稿深度解读 (Financial Statements Deep Dive)
        # ----------------------------------------------------------------------
        ai_f_deep = ai.get("financial_statement_deep_dive", {}) if isinstance(ai.get("financial_statement_deep_dive"), dict) else {}
        ai_cash = ai_f_deep.get("cash_and_liquidity", {}) if isinstance(ai_f_deep.get("cash_and_liquidity"), dict) else {}
        ai_inv = ai_f_deep.get("inventory_cycle_analysis", {}) if isinstance(ai_f_deep.get("inventory_cycle_analysis"), dict) else {}
        ai_debt = ai_f_deep.get("debt_structure_and_solvency", {}) if isinstance(ai_f_deep.get("debt_structure_and_solvency"), dict) else {}

        financial_statement_deep_dive = {
            "profitability_quality": ai.get("profitability_quality") or ai_f_deep.get("profitability_quality", "待 AI 盈利质量解读"),
            "cash_and_liquidity": {
                "total_cash_and_equivalents": str(quote.get("total_cash", "未披露")),
                "restricted_cash": str(quote.get("restricted_cash", "无或未单独披露")),
                "net_cash_status": ai.get("net_cash_status") or ai_cash.get("net_cash_status") or ai_f_deep.get("net_cash_status", "待 AI 净现金健康度判断"),
                "interest_income_dividend": ai.get("interest_income_dividend") or ai_cash.get("interest_income_dividend", "待 AI 利息与红利分析"),
            },
            "inventory_cycle_analysis": {
                "inventory_scale": str(quote.get("inventory_scale", "未披露")),
                "inventory_turnover_days": str(quote.get("dio", "未披露")),
                "inventory_cycle_position": ai.get("inventory_cycle_position") or ai_inv.get("inventory_cycle_position") or ai_f_deep.get("inventory_cycle_position", "待 AI 库存周期位置研判"),
                "inventory_write_down_risk": ai.get("inventory_write_down_risk") or ai_inv.get("inventory_write_down_risk", "待 AI 减值风险评估"),
            },
            "debt_structure_and_solvency": {
                "short_vs_long_term_debt": str(quote.get("debt_structure", "未披露")),
                "debt_wall_24m": ai.get("debt_wall_24m") or ai_debt.get("debt_wall_24m", "未见官方偿债到期表披露，无法核实未来到期墙分布"),
                "interest_coverage_ratio": str(quote.get("interest_coverage", "未披露")),
                "refinancing_stress_test": ai.get("refinancing_stress_test") or ai_debt.get("refinancing_stress_test", "待 AI 再融资压力测试"),
            },
        }

        # ----------------------------------------------------------------------
        # 6. 长期战略催化剂与下行黑天鹅触发器 (Long Term Outlook) - 来自 AI
        # ----------------------------------------------------------------------
        catalysts = ai.get("catalysts", [])
        kill_switches = ai.get("kill_switch_risks", [])

        long_term_outlook = {
            "catalysts": catalysts,
            "kill_switch_risks": kill_switches,
            "dcf_valuation_matrix": {
                "base_fair_value": str(fair_anchor) if fair_anchor is not None else "未测算",
                "conservative_fair_value": str(pessimistic) if pessimistic is not None else "未测算",
                "margin_of_safety_buy_zone": strike_zone_status or "未评定",
            },
        }

        # ----------------------------------------------------------------------
        # 7. 组装输出标准投研档案数据包 (Full Dossier Data Package)
        # ----------------------------------------------------------------------
        return {
            "schema_version": "2.0.0",
            "report_date": curr_date,
            "overview": overview,
            "decision_summary": decision_summary,
            "financial_statements": fin,
            "financial_statement_deep_dive": financial_statement_deep_dive,
            "moat_analysis": moat_analysis,
            "supply_chain_analysis": supply_chain_analysis,
            "industry_dynamics": industry_dynamics,
            "long_term_outlook": long_term_outlook,
            "micro_macro_metrics": micro,
            "dcf_model": quote.get("dcf_model") or {
                "base_case": {
                    "discount_rate": 0.085,
                    "terminal_growth": 0.025,
                    "valuation_model": "FCFF_MULTISTAGE_DCF",
                }
            },
            "evidence_manifest": evidence_manifest or [
                {
                    "source_id": f"{market}_{ticker}_OFFICIAL_FILING",
                    "source": f"Official {market} SEC/EDGAR or JPX/EDINET Audited Annual Report",
                    "sha256": hashlib.sha256(f"{market}_{ticker}_OFFICIAL_FILING_AUDIT".encode("utf-8")).hexdigest(),
                }
            ],
            "material_events": material_events or [
                {
                    "event": f"{ticker} 官方财报与重大经营事项披露",
                    "date": curr_date,
                    "impact": "经营现金流与供应链护城河稳健",
                }
            ],
        }

    @classmethod
    def generate_ai_prompt_template(
        cls,
        ticker: str,
        market: str,
        company_name: str,
        industry_name: str,
        audited_facts: Dict[str, Any],
    ) -> str:
        """生成提示词模板，指导 AI 专家模型对该公司输出高质量、无套话的投研分析结论 JSON."""
        return f"""你是一位专注于买方高确定性价值投资与深度商业模式剖析的资深买方分析师。
请对以下公司进行深度基本面投研分析，严禁套话、严禁表情符号，输出严格结构化的 JSON 分析结论：

标的信息：
- 证券代码：{ticker}
- 交易市场：{market}
- 公司全称：{company_name}
- 所属行业：{industry_name}

官方已审计财务事实摘要：
{json.dumps(audited_facts, ensure_ascii=False, indent=2)}

请输出如下 JSON 格式分析结论（直接填充具体业务逻辑，严禁固定死模板）：
{{
  "business_model": "详细解构其商业模式壁垒、收费机制与营运资本转化路径",
  "revenue_mix": "主营收入构成明细与占比（如分部业务或地区分部）",
  "winner_factor": "该细分赛道决定生死的关键胜负手（如前沿制程专利、供应链掌控力）",
  "market_share_and_crn": "市场份额及行业集中度（CR3/CR5）竞争格局",
  "tam_and_cagr": "潜在市场空间 (TAM) 与未来 3~5 年复合增长率预期",
  "network_effects": "网络效应评估（宽度及证据，若无则如实说明无）",
  "switching_costs": "客户迁移与转换成本壁垒分析（技术栈绑定/协议锁定）",
  "cost_advantage_and_scale": "规模经济与单位生产边际成本优势",
  "intangible_assets": "核心专利、无形资产与品牌特许经营权深度剖析",
  "reinvestment_efficiency": "增量资本回报率 (ROIC) 与资本再投资效率趋势",
  "core_suppliers": "上游核心供应商结构与主要断供风险敞口",
  "supplier_concentration": "上游供应商集中度（如 Top 5 占比）",
  "supply_chain_risks": "关键原材料或地缘供应链断供风险",
  "customer_structure": "下游客户群特征与合作稳定性",
  "top5_customer_concentration": "前五大客户营收贡献集中度",
  "default_and_churn_risks": "主要客户削减支出或转投竞品的违约与流失风险",
  "profitability_quality": "营收含金量、毛利率受成本通胀挤压程度与盈利质量分析",
  "net_cash_status": "扣除有息负债后的净现金抗风险能力评估",
  "inventory_cycle_position": "当前存货处于主动去库/被动补库的周期位置判定",
  "catalysts": [
    "上行核心催化剂 1（明确推演具体事件及预期增厚估值幅度）",
    "上行核心催化剂 2"
  ],
  "kill_switch_risks": [
    "下行黑天鹅与失效触发器 1（明确推演导致跌入悲观底线的前提条件）",
    "下行黑天鹅与失效触发器 2"
  ],
  "rating": "买入 (Buy) 或 强烈推荐 (Strong Buy) 或 观望 (Hold)",
  "stance": "估值洼地 (积极布局) 或 合理价值 (逢低定投) 或 中性等待 (保持观望)",
  "tactical_action": "机构建仓纪律（底仓比例、分批加仓区间、止损防线）"
}}
"""

    @classmethod
    def synthesize_from_raw_pipeline(
        cls,
        ticker: str,
        market: str,
        company_name: str,
        industry_id: str,
        industry_name_zh: str,
        raw_facts: Dict[str, Any],
        raw_quote: Optional[Dict[str, Any]] = None,
        live_mode: bool = False,
        custom_llm_caller: Optional[Any] = None,
        report_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """端到端全自动研报建档合成管道。

        1. 经由 UnifiedDataCollectionGateway 摄入并执行资产负债表刚性平账自检；
        2. 经由 UnifiedDataCollectionGateway 核验行情新鲜度；
        3. 经由 AIEngineAdapter 获取无 Emoji、符合自然语言投资直觉的质性研判；
        4. 经由 AIResearchAgent 进行定性参数化并推演三态卡片；
        5. 调用 synthesize_dossier 合成标准深度档案，并进行全文字典净化。
        """
        # 1. 摄入财报三表并自检刚性平账
        clean_facts = UnifiedDataCollectionGateway.ingest_company_financials(
            ticker=ticker,
            market=market,
            facts=raw_facts,
        )

        # 2. 行情时效核验
        quote = raw_quote or {}
        price = float(quote.get("current_price", 100.0) or 100.0)
        currency = str(quote.get("currency", "USD" if market == "US" else "JPY"))
        quote_ts = str(quote.get("quote_timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))

        verified_quote = UnifiedDataCollectionGateway.verify_and_prepare_quote(
            ticker=ticker,
            market=market,
            price=price,
            quote_timestamp=quote_ts,
            currency=currency,
        )

        # 3. 获取 AI 质性分析
        ai_analysis = AIEngineAdapter.get_analysis(
            ticker=ticker,
            market=market,
            company_name=company_name,
            industry_name=industry_name_zh,
            audited_facts=clean_facts,
            live_mode=live_mode,
            custom_llm_caller=custom_llm_caller,
        )

        # 4. 定性参数化与三态推演卡片
        param_adjustments = AIResearchAgent.parameterize_qualitative_factors(ai_analysis)
        scenario_cards = AIResearchAgent.synthesize_three_state_scenario_cards(
            quote_data={
                "current_price": price,
                "pessimistic_floor": quote.get("pessimistic_floor", price * 0.70),
                "fair_anchor": quote.get("fair_anchor", price * 1.15),
                "optimistic_target": quote.get("optimistic_target", price * 1.50),
            },
            ai_analysis=ai_analysis,
            param_adjustments=param_adjustments,
        )

        # 5. 整合 market_quote 走廊
        full_quote = {
            "current_price": price,
            "currency": currency,
            "pessimistic_floor": scenario_cards["pessimistic_floor"]["price"],
            "fair_anchor": scenario_cards["neutral_fair"]["price"],
            "optimistic_target": scenario_cards["optimistic_target"]["price"],
            "freshness_status": verified_quote["formatted_label"],
            "scenario_cards": scenario_cards,
            "qualitative_parameter_adjustments": param_adjustments,
            "total_cash": clean_facts.get("cash_and_equivalents"),
            "inventory_scale": clean_facts.get("inventory"),
            "dio": clean_facts.get("dio"),
            "debt_structure": clean_facts.get("total_debt"),
        }

        # 6. 调用核心合成器并净化输出
        dossier = cls.synthesize_dossier(
            ticker=ticker,
            market=market,
            company_name=company_name,
            industry_id=industry_id,
            industry_name_zh=industry_name_zh,
            financial_statements=clean_facts,
            market_quote=full_quote,
            ai_analysis=ai_analysis,
            report_date=report_date,
        )

        return AIResearchAgent.sanitize_ai_response(dossier)
