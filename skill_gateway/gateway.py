"""Skill 交互网关中枢 (Skill Gateway & Adapter).

连接 AI Agent Skill 交互层与底层 Financial Core 金融分析核心的轻量化适配网关。
贯彻 2026-10-15 工程整改规范：
1. Task 02: 严禁正式模式静默回退演示样本，样本必须显式声明 allow_demo=True;
2. Task 05 & 06: 构建不可拆分的不可变 QuoteSnapshot 报价对象，核心计算与展示端完全同源;
3. Task 07: 拦截平账失败与非法输入，优雅输出阻断凭证卡;
4. 响应用户核心需求：程序负责数据输入和结构化展示，支持挂载 AI 归纳整理的投研日记 (ai_journal)。
"""

from typing import Dict, Any, Optional
from datetime import datetime

from financial_core.api import FinancialAnalysisSystem
from financial_core.contracts import FinancialAnalysisResult, AnalysisMode
from skill_gateway.freshness import QuoteFreshnessVerifier, QuoteSnapshot
from skill_gateway.card_formatter import DecisionCardFormatter


class SkillGateway:
    """Agent Skill 交互网关适配器."""

    def __init__(self):
        self.financial_system = FinancialAnalysisSystem()

    def handle_equity_analysis(
        self,
        ticker: str,
        company_input: Optional[Any] = None,
        market_session: Optional[str] = None,
        quote_timestamp: Optional[str] = None,
        current_price: Optional[float] = None,
        mode: str = "full_systemic",
        allow_demo: bool = False,
        ai_journal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理 Agent 发起的个股投研分析请求.
        
        Args:
            ticker: 股票代码 (如 RXRX, 000858, NVDA)
            company_input: 可选官方输入底账
            market_session: 交易时段 (如 regular_trading, pre_market, closed)
            quote_timestamp: 行情时间戳 (如 2026-10-15 15:55:00 EDT)
            current_price: 当前现价 (可选显式传入)
            mode: 分析模式
            allow_demo: 是否允许在缺失底账时使用测试演示样本 (默认 False)
            ai_journal: 可选的 AI 投研日记/定性归纳文本
        """
        # 1. 尝试对齐或解析标的基准底账
        inp = company_input
        if inp is None and allow_demo:
            inp = self.financial_system.get_preset_sample_input(ticker)
            if inp:
                setattr(inp, "_is_demo_sample", True)

        # 2. 提取行情参数并构建不可拆分的 QuoteSnapshot (Task 06)
        eff_session = market_session or (getattr(inp, "market_session", "closed") if inp else "closed")
        eff_ts = quote_timestamp or (getattr(inp, "quote_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) if inp else datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        eff_price = current_price or (getattr(inp, "current_price", 0.0) if inp else 0.0)

        # 3. 严格执行时区感知的新鲜度核验 (Task 05)
        quote_snapshot: QuoteSnapshot = QuoteFreshnessVerifier.verify_and_build_snapshot(
            ticker=ticker,
            price=eff_price,
            quote_timestamp_str=eff_ts,
            market_session=eff_session,
        )

        # 4. 路由调用底层纯金融分析核心
        analysis_mode = AnalysisMode(mode)
        try:
            fin_result: FinancialAnalysisResult = self.financial_system.analyze_equity(
                ticker=ticker,
                company_input=inp,
                mode=analysis_mode,
                allow_demo_sample=allow_demo,
            )
        except Exception as e:
            return {
                "status": "error",
                "message": f"底层金融分析引擎异常: {str(e)}",
            }

        # 5. 若传入了 AI 投研日记，挂载至决策卡片
        if ai_journal:
            fin_result.decision_card.ai_research_journal = ai_journal

        # 6. 格式化生成用户端 Markdown 决策卡片
        markdown_card = DecisionCardFormatter.render_decision_card(
            result=fin_result,
            quote=quote_snapshot,
        )

        return {
            "status": "success" if fin_result.execution_success else "blocked",
            "execution_status": fin_result.execution_status,
            "message": fin_result.block_reason or ("投研计算完成" if fin_result.execution_success else "计算阻断"),
            "ticker": ticker,
            "company_name": fin_result.company_name,
            "market": fin_result.market,
            "currency": fin_result.currency,
            "market_session": quote_snapshot.market_session,
            "quote_timestamp": quote_snapshot.as_of_local_time,
            "is_live_quote": quote_snapshot.is_live,
            "freshness_grade": quote_snapshot.freshness_grade,
            "display_badge": quote_snapshot.display_badge,
            "objective_signal": fin_result.decision_card.objective_signal,
            "is_demo_sample": fin_result.is_demo_sample,
            "markdown_card": markdown_card,
            "result_data": fin_result.to_dict(),
        }


# 全局单例网关
default_gateway = SkillGateway()
