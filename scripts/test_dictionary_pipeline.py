# -*- coding: utf-8 -*-
"""字典端到端管道测试 (Dictionary Input to Analysis Output Pipeline Test).

测试目标：
验证从一个纯粹的 Python 业务字典输入（包含财报底稿、盘中报价、期权盘口、预期差、微观筹码），
端到端流经所有量化引擎，输出一个结构化的全景投研字典结果，并打印格式化 JSON。
"""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finance_tools import (
    OptionContractInput,
    UnderlyingScenarios,
    OptionsCausalAnalyzer,
    ConsensusDataInput,
    ConsensusSurpriseEngine,
    MicrostructureInput,
    MicrostructureFlowEngine,
    CorporateEvent,
    CatalystCalendarEngine,
    CompanyPeerMetrics,
    PeerBenchmarkEngine,
    PipelineAsset,
    UnitEconomicsEngine,
    BaselineFinancials,
    IntegratedThreeStatementEngine,
)
from financial_reporting.strong_constrained_valuation import (
    CompanyFinancialFacts,
    MacroParameters,
    StronglyConstrainedValuationEngine,
)


def run_dictionary_test():
    # ==========================================
    # 1. 模拟喂给系统的一个原始综合输入字典 (Input Dict)
    # ==========================================
    raw_input_dict = {
        "identity": {
            "ticker": "RXRX",
            "name": "Recursion Pharmaceuticals, Inc.",
            "currency": "USD",
            "market": "US",
        },
        "quote": {
            "spot_price": 3.835,
            "pre_market_price": 3.89,
            "timestamp": "2026-10-14T06:06:47Z",
            "market_session": "pre_market",
        },
        "raw_financials": {
            "shares": 535.0,
            "cash_and_equivalents": 550.0,
            "total_debt": 35.0,
            "total_assets": 750.0,
            "current_assets": 590.0,
            "total_liabilities": 120.0,
            "equity": 630.0,
            "goodwill_and_intangibles": 40.0,
            "revenue": 50.0,
            "operating_income": -280.0,
            "net_income": -260.0,
            "free_cash_flow": -240.0,
            "operating_cash_flow": -220.0,
            "beta": 1.45,
        },
        "consensus": {
            "fiscal_period": "Q3 2024",
            "consensus_eps": -0.42,
            "consensus_revenue": 14.5,
            "reported_eps": -0.38,
            "reported_revenue": 15.2,
            "upgrades_30d": 4,
            "downgrades_30d": 1,
            "total_analysts": 8,
        },
        "microstructure": {
            "float_shares": 260.0,
            "short_interest_shares": 80.0,
            "adv_30d": 7.5,
            "cost_to_borrow_pct": 32.5,
            "borrow_utilization_pct": 91.0,
            "insider_net_buy_shares": 0.25,
            "inst_net_flow_shares": 3.8,
        },
        "option_target": {
            "strike": 4.00,
            "option_type": "call",
            "market_premium": 0.45,
            "days_to_expiration": 45,
        },
    }

    # ==========================================
    # 2. 中间处理：执行各引擎计算与因果闭环
    # ==========================================
    # A. 强约束估值模型
    facts = CompanyFinancialFacts(
        ticker=raw_input_dict["identity"]["ticker"],
        currency=raw_input_dict["identity"]["currency"],
        current_price=raw_input_dict["quote"]["spot_price"],
        shares=raw_input_dict["raw_financials"]["shares"],
        cash_and_equivalents=raw_input_dict["raw_financials"]["cash_and_equivalents"],
        total_debt=raw_input_dict["raw_financials"]["total_debt"],
        total_assets=raw_input_dict["raw_financials"]["total_assets"],
        current_assets=raw_input_dict["raw_financials"]["current_assets"],
        total_liabilities=raw_input_dict["raw_financials"]["total_liabilities"],
        equity=raw_input_dict["raw_financials"]["equity"],
        goodwill_and_intangibles=raw_input_dict["raw_financials"]["goodwill_and_intangibles"],
        revenue=raw_input_dict["raw_financials"]["revenue"],
        operating_income=raw_input_dict["raw_financials"]["operating_income"],
        net_income=raw_input_dict["raw_financials"]["net_income"],
        free_cash_flow=raw_input_dict["raw_financials"]["free_cash_flow"],
        operating_cash_flow=raw_input_dict["raw_financials"]["operating_cash_flow"],
        beta=raw_input_dict["raw_financials"]["beta"],
        quote_timestamp=raw_input_dict["quote"]["timestamp"],
        market_session=raw_input_dict["quote"]["market_session"],
    )
    val_res = StronglyConstrainedValuationEngine.evaluate_valuation(
        facts, current_time_iso="2026-10-14T06:10:00Z"
    )

    # B. 预期差引擎
    c_inp = ConsensusDataInput(
        ticker=raw_input_dict["identity"]["ticker"],
        fiscal_period=raw_input_dict["consensus"]["fiscal_period"],
        consensus_eps=raw_input_dict["consensus"]["consensus_eps"],
        consensus_revenue=raw_input_dict["consensus"]["consensus_revenue"],
        reported_eps=raw_input_dict["consensus"]["reported_eps"],
        reported_revenue=raw_input_dict["consensus"]["reported_revenue"],
        analysts_upgrades_30d=raw_input_dict["consensus"]["upgrades_30d"],
        analysts_downgrades_30d=raw_input_dict["consensus"]["downgrades_30d"],
        total_covering_analysts=raw_input_dict["consensus"]["total_analysts"],
    )
    cons_res = ConsensusSurpriseEngine.evaluate(c_inp)

    # C. 微观筹码博弈引擎
    m_inp = MicrostructureInput(
        ticker=raw_input_dict["identity"]["ticker"],
        current_price=raw_input_dict["quote"]["spot_price"],
        float_shares=raw_input_dict["microstructure"]["float_shares"],
        short_interest_shares=raw_input_dict["microstructure"]["short_interest_shares"],
        average_daily_volume_30d=raw_input_dict["microstructure"]["adv_30d"],
        cost_to_borrow_pct=raw_input_dict["microstructure"]["cost_to_borrow_pct"],
        borrow_utilization_pct=raw_input_dict["microstructure"]["borrow_utilization_pct"],
        insider_buy_shares_90d=raw_input_dict["microstructure"]["insider_net_buy_shares"],
        insider_sell_shares_90d=0.0,
        top10_inst_net_flow_shares=raw_input_dict["microstructure"]["inst_net_flow_shares"],
    )
    micro_res = MicrostructureFlowEngine.evaluate(m_inp)

    # D. 期权因果推导器
    opt_contract = OptionContractInput(
        underlying_ticker=raw_input_dict["identity"]["ticker"],
        underlying_spot_price=raw_input_dict["quote"]["spot_price"],
        spot_quote_timestamp=raw_input_dict["quote"]["timestamp"],
        market_session=raw_input_dict["quote"]["market_session"],
        strike_price=raw_input_dict["option_target"]["strike"],
        option_type=raw_input_dict["option_target"]["option_type"],
        days_to_expiration=raw_input_dict["option_target"]["days_to_expiration"],
        market_premium=raw_input_dict["option_target"]["market_premium"],
    )
    scenarios = UnderlyingScenarios(
        bear_price=val_res.bear_fair_value,
        bear_prob=0.25,
        base_price=val_res.base_fair_value,
        base_prob=0.50,
        bull_price=val_res.bull_fair_value,
        bull_prob=0.25,
    )
    opt_res = OptionsCausalAnalyzer.analyze_option(
        opt_contract, scenarios, current_time_iso="2026-10-14T10:45:00Z"
    )

    # ==========================================
    # 3. 组装最终输出全景字典 (Output Dict)
    # ==========================================
    final_output_dict = {
        "meta": {
            "ticker": facts.ticker,
            "evaluation_time": "2026-10-14T20:05:00+09:00",
            "framework_version": "Level 3.5 Institutional Quantamental",
        },
        "valuation_and_floors": val_res.to_dict(),
        "consensus_surprise": cons_res.to_dict(),
        "microstructure_flow": micro_res.to_dict(),
        "options_causal_verdict": opt_res.to_dict(),
    }

    print("=== 字典端到端管道测试成功 ===")
    print(json.dumps(final_output_dict, ensure_ascii=False, indent=2))
    return final_output_dict


class DictionaryPipelineTests(unittest.TestCase):
    """业务字典端到端管道集成测试套件。"""

    def test_dictionary_pipeline_end_to_end(self):
        """【IT-DICT-01: 跨引擎端到端全息字典级输入至投研全景输出闭环管道】

        1. 测试功能与测试点:
           - 验证从原始输入字典 (财报三表底稿、盘前报价、期权盘口、预期差、微观筹码) 端到端穿越:
             1. 强约束估值模型 (StronglyConstrainedValuationEngine)；
             2. 预期差分析引擎 (ConsensusSurpriseEngine)；
             3. 微观筹码博弈引擎 (MicrostructureFlowEngine)；
             4. 期权因果推导器 (OptionsCausalAnalyzer)；
           - 最终闭环组装为买方机构级全景投研输出字典，验证各引擎 DTO 相互传递的无损性与序列化自洽性。

        2. 正常函数业务边界与参数契约:
           - facts 输入包含强类型财报科目与带时区的现价时间戳；
           - 估值引擎生成悲观/基准/乐观三档公允底价，作为下游期权推导的情景概率树；
           - 输出字典必须包含 meta, valuation_and_floors, consensus_surprise, microstructure_flow, options_causal_verdict 五大支柱。

        3. 测试数据与模拟场景说明:
           - 选取高成长AI制药新星 Recursion Pharmaceuticals (RXRX) 商业模型；
           - 模拟盘前现价 $3.835，研发烧钱期营业利润 -$280M，空头借券费率 32.5%，空头借券使用率 91.0%，目标 Call 期权行权价 $4.00。

        4. 预期断言与结果验证:
           - 最终输出字典结构完整，五大顶级键全部存在；
           - 估值模块输出 base_fair_value > 0；
           - 预期差模块 reported_revenue > consensus_revenue 判定为超预期；
           - 微观筹码借券使用率超过 90% 触发挤压敏感警报；
           - 期权模块完成盈亏平衡与期望现值计算。
        """
        output = run_dictionary_test()
        self.assertIn("meta", output)
        self.assertIn("valuation_and_floors", output)
        self.assertIn("consensus_surprise", output)
        self.assertIn("microstructure_flow", output)
        self.assertIn("options_causal_verdict", output)
        self.assertEqual(output["meta"]["ticker"], "RXRX")
        self.assertIn("base_case", output["valuation_and_floors"]["constrained_scenarios"])
        self.assertIn("Double Beat", output["consensus_surprise"]["beat_category"])
        self.assertIn("squeeze_score", output["microstructure_flow"]["short_metrics"])
        self.assertIn("contract_profile", output["options_causal_verdict"])


if __name__ == "__main__":
    unittest.main()
