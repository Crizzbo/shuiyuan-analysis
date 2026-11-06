"""发布契约探针 unit。"""

import math
import json
from .common import check, require, ROOT


@check("F11", "finance", "P0", "finance_tools/valuation.py", "UT-08")
def reverse_dcf_roundtrip_and_unreachable_target(_):
    from finance_tools.valuation import multistage_dcf, reverse_dcf
    cash_flow, growth, years, discount, terminal, shares = 120, 0.17, 5, 0.11, 0.03, 30
    target = multistage_dcf(cash_flow, [growth] * years, discount, terminal, shares, "FCFF", 60)["value_per_share"]
    implied = reverse_dcf(target, cash_flow, years, discount, terminal, shares, "FCFF", 60)
    require(implied["status"] == "converged" and abs(implied["implied_growth"] - growth) < 1e-7,
            f"反向 DCF 未还原已知增长率 {implied}")
    unreachable = reverse_dcf(target * 10_000, cash_flow, years, discount, terminal, shares, "FCFF", 60)
    return require(unreachable["status"] == "outside_bounds" and unreachable["implied_growth"] is None,
                   f"不可达价格返回了伪增长率 {unreachable}")


@check("F12", "finance", "P0", "financial_core/engines/options_causal_analyzer.py", "UT-09")
def option_payoffs_and_kelly_match_independent_arithmetic(_):
    from financial_core.engines.options_causal_analyzer import OptionContractInput, OptionsCausalAnalyzer, UnderlyingScenarios
    contract = OptionContractInput("AUDIT", 100, "2026-10-16T14:00:00Z", "regular_trading", 110, "call", 30, 5)
    scenarios = UnderlyingScenarios(95, 0.10, 120, 0.30, 145, 0.60)
    result = OptionsCausalAnalyzer.analyze_option(contract, scenarios, current_time_iso="2026-10-16T14:01:00Z")
    payoffs = (result.bear_payoff_per_share, result.base_payoff_per_share, result.bull_payoff_per_share)
    require(result.break_even_price == 115 and result.time_value == 5 and payoffs == (-5, 5, 30),
            f"保本价或三态期权损益偏离独立基准 {result.break_even_price}, {payoffs}")
    return require(math.isclose(result.expected_profit_per_share, 19) and 0 <= result.quarter_kelly_capital_pct <= 2,
                   f"概率加权损益或四分之一凯利上限失守 {result.expected_profit_per_share}, {result.quarter_kelly_capital_pct}")


@check("F10", "finance", "P1", "financial_core/engines/sepa_buy_signal_engine.py", "UT-10")
def sepa_missing_volume_baseline_cannot_trigger_buy(_):
    from dataclasses import replace
    from financial_core.engines.sepa_buy_signal_engine import BuySignalTier, SepaBuySignalEngine, SepaInputFacts
    engine = SepaBuySignalEngine()
    facts = SepaInputFacts(ticker="AUDIT", val_current_price=103, val_ma_50=95, val_ma_150=90,
                           val_ma_200=80, val_ma_200_20d_ago=78, val_low_52w=60,
                           val_high_52w=105, num_rs_rank=92, val_pivot_price=100,
                           pct_recent_contractions=[28, 14, 6, 2.5], days_base_duration=56,
                           num_current_volume=2_000_000, num_avg_volume_50d=1_000_000,
                           num_dryup_volume_min=0)
    good = engine.evaluate_buy_signal(facts)
    require(good.status_buy_signal == BuySignalTier.PIVOT_TRIGGERED, "正向夹具未进入放量突破分支")
    try:
        bad = engine.evaluate_buy_signal(replace(facts, num_avg_volume_50d=0))
    except ValueError:
        return "缺失有效均量时阻断"
    return require(bad.status_buy_signal != BuySignalTier.PIVOT_TRIGGERED, "无有效均量仍触发买入信号")


@check("Q06", "quote", "P0", "financial_core/engines/quote_freshness_gateway.py", "UT-01")
def quote_rejects_illegal_price_and_implicit_zone(_):
    cases = [(value, "2026-10-16 10:00 EDT") for value in (0, -1, float("nan"), float("inf"))]
    cases.append((100, "2026-10-16 14:00"))
    accepted = []
    for price, timestamp in cases:
        try:
            if quote(timestamp, "2026-10-16T14:01:00Z", price=price).is_valid:
                accepted.append(f"{price}@{timestamp}")
        except ValueError:
            continue
    return require(not accepted, f"行情校验接受非法价格或无时区时间 {accepted}")


@check("Q07", "quote", "P0", "financial_core/engines/quote_freshness_gateway.py", "UT-04")
def stale_intraday_quote_is_not_current(_):
    result = quote("2026-10-16 10:00 EDT", "2026-10-16T21:00:00Z")
    return require(not (result.is_fresh_today and "盘中现价" in result.formatted_label),
                   f"进入盘后仍展示早间报价为盘中现价，状态 {result.session_status}")


@check("F09", "finance", "P1", "financial_core/engines/american_option_tree_engine.py", "UT-09")
def american_option_no_dividend_convergence(_):
    from financial_core.engines.american_option_tree_engine import AmericanOptionTreeEngine, AmericanOptionTreeInput
    engine = AmericanOptionTreeEngine()
    prices = [engine.price_crr_tree(AmericanOptionTreeInput(100, 100, 1, 0.03, 0.20, steps=n)) for n in (100, 300)]
    coarse, fine = (abs(row["american_price"] - row["european_price"]) for row in prices)
    return require(fine <= coarse + 0.01 and fine < 0.05 and 0 <= prices[-1]["american_price"] <= 100,
                   f"无股息美式看涨的欧式定价对照误差为 {coarse:.4f}、{fine:.4f}")


@check("L05", "ledger", "P0", "financial_core/engines/prediction_ledger.py", "UT-13")
def hash_covers_material_event_fields(_):
    from dataclasses import replace
    from financial_core.engines.prediction_ledger import PredictionLedger
    from .common import prediction
    snapshot = prediction()
    base = PredictionLedger._compute_hash("0" * 64, snapshot)
    fields = {"pessimistic_event": "不同的下行触发器", "optimistic_event": "不同的上行触发器",
              "tactical_action": "不同的交易行动"}
    unchanged = [name for name, value in fields.items()
                 if PredictionLedger._compute_hash("0" * 64, replace(snapshot, **{name: value})) == base]
    return require(not unchanged, f"以下字段变化未改变预测摘要 {unchanged}")


def quote(timestamp, now, market="US", price=100.0):
    from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway
    return QuoteFreshnessGateway.verify_quote(price, "USD" if market == "US" else "JPY", timestamp, market, now)


@check("F07", "finance", "P1", "financial_core/engines/monte_carlo_engine.py", "UT-10")
def monte_carlo_reproducibility(_):
    from financial_core.engines.monte_carlo_engine import MonteCarloDCFInput, MonteCarloValuationEngine
    engine = MonteCarloValuationEngine()
    inputs = MonteCarloDCFInput(base_cash_flow=100, current_price=100, shares_outstanding=10, net_debt=20)
    first = engine.run_monte_carlo_dcf("AUDIT", inputs, iterations=1000, random_seed=12)
    second = engine.run_monte_carlo_dcf("AUDIT", inputs, iterations=1000, random_seed=12)
    ordered = first.percentile_10 <= first.median_fair_value <= first.percentile_90
    return require(first.to_dict() == second.to_dict() and ordered, "固定种子无法复算或分位数次序异常")



@check("Q01", "quote", "P0", "financial_core/engines/quote_freshness_gateway.py", 'UT-01')
def future_quote(_):
    result = quote("2026-10-16 12:00 EDT", "2026-10-16T15:00:00Z")
    return require(not result.is_valid, f"未来行情核验结果 is_valid={result.is_valid}, session={result.session_status}")



@check("Q02", "quote", "P1", "financial_core/engines/quote_freshness_gateway.py", 'UT-03')
def tokyo_lunch(_):
    result = quote("2026-10-16 12:00 JST", "2026-10-16T03:01:00Z", "JP")
    return require(result.session_status != "regular_trading", f"东京午休报价状态为 {result.session_status}")



@check("Q03", "quote", "P1", "financial_core/engines/quote_freshness_gateway.py", 'UT-02')
def exchange_day(_):
    result = quote("2026-10-16 19:59 EDT", "2026-10-17T00:01:00Z")
    return require(result.is_valid and result.is_fresh_today and result.session_status == "after_hours",
                   f"纽约同一交易日跨 UTC 零点得到 {result.session_status}, fresh={result.is_fresh_today}")



@check("Q05", "quote", "P0", "financial_core/engines/filing_mapper.py", 'UT-04')
def valuation_cannot_invent_quote(_):
    from financial_core.engines.filing_mapper import IncompleteFilingFactError, OfficialFilingMapper
    data = {"overview": {"ticker": "AUDIT", "market": "US"}, "raw_financials_table": {
        "revenue": 1000, "total_assets": 1000, "total_liabilities": 600, "equity": 400,
    }, "long_term_outlook": {"dcf_valuation_matrix": {"base_fair_value": "$200"}}}
    try:
        mapped = OfficialFilingMapper.map_dossier_to_company_input(data)
    except (IncompleteFilingFactError, ValueError):
        return "无观测行情时映射阻断"
    return require(not mapped.current_price and not mapped.quote_timestamp,
                   f"无行情输入时仍生成价格和时间戳 {mapped.quote_timestamp!r}")



@check("F01", "finance", "P0", "financial_reporting/data_collection_gateway.py", 'UT-06', 'UT-07')
def incomplete_filing(_):
    from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway
    from financial_core.engines.filing_mapper import IncompleteFilingFactError
    try:
        facts = UnifiedDataCollectionGateway.ingest_company_financials(
            "AUDIT", "US", {"revenue": 1000, "total_assets": 1000, "stockholders_equity": 300}
        )
    except IncompleteFilingFactError:
        return "缺失官方事实的底稿被阻断"
    missing = {"total_liabilities", "net_income", "operating_cash_flow", "inventory", "dio"}
    filled = sorted(field for field in missing if facts.get(field) is not None)
    return require(not filled and not facts.get("source_filing"),
                   f"缺失科目被补成 {filled}，来源标签为 {facts.get('source_filing')!r}")



@check("F02", "finance", "P0", "financial_core/engines/filing_mapper.py", 'UT-06')
def balance_rejects_nonfinite(_):
    from financial_core.engines.filing_mapper import BalanceSheetIdentityError, OfficialFilingMapper
    accepted = []
    for value in (float("nan"), float("inf"), float("-inf")):
        try:
            valid, *_ = OfficialFilingMapper.verify_balance_sheet_identity(100, value, 25)
        except (BalanceSheetIdentityError, ValueError):
            continue
        if valid:
            accepted.append(str(value))
    return require(not accepted, f"会计恒等式接受非有限值 {accepted}")



@check("F03", "finance", "P0", "financial_core/engines/filing_mapper.py", 'UT-05')
def debt_scale(_):
    from financial_core.engines.filing_mapper import OfficialFilingMapper
    common = {"market_price": 100, "quote_timestamp": "2026-10-16 16:00 EDT", "shares_outstanding": 100_000_000}
    amounts = {"reported_revenue": 100, "total_assets": 100, "total_liabilities": 50, "equity": 50, "total_debt": 40}
    millions = OfficialFilingMapper.map_to_company_input({
        "ticker": "AUDIT", "financial_unit": "usd_million", "facts": common | amounts,
    })
    dollars = OfficialFilingMapper.map_to_company_input({
        "ticker": "AUDIT", "financial_unit": "usd",
        "facts": common | {key: value * 1_000_000 for key, value in amounts.items()},
    })
    return require(millions.total_debt == dollars.total_debt == 40_000_000,
                   f"同一总债务按百万输入为 {millions.total_debt:g}，按元输入为 {dollars.total_debt:g}")



@check("F04", "finance", "P0", "finance_tools/valuation.py", 'UT-08')
def dcf_closed_form(_):
    from finance_tools.valuation import multistage_dcf
    results = [multistage_dcf(100, [0.0] * years, 0.10, 0.0, 10, "FCFF", 100)
               for years in (1, 5, 20)]
    values = [result["value_per_share"] for result in results]
    return require(all(math.isclose(value, 90, abs_tol=1e-8) for value in values),
                   f"永续不增长、扣净债务后的每股估值应为 90，结果 {values}",
                   "1、5、20 年预测期均复现闭式估值")



@check("F05", "finance", "P0", "finance_tools/valuation.py", 'UT-08')
def dcf_invalid_terminal(_):
    from finance_tools.valuation import multistage_dcf
    for growth in (0.10, 0.11, float("nan")):
        try:
            multistage_dcf(100, [0.03], 0.10, growth, 10, "FCFF", 0)
        except ValueError as error:
            require("terminal_growth" in str(error) or "永续增长" in str(error), f"DCF 因无关错误拒绝输入 {error}")
            continue
        raise AssertionError(f"DCF 接受非法永续增长率 {growth}")
    return "DCF 拒绝 g ≥ 折现率及非有限增长率"



@check("F06", "finance", "P1", "financial_core/engines/volatility_surface_engine.py", 'UT-09')
def option_no_arbitrage(_):
    from financial_core.engines.volatility_surface_engine import VolatilitySurfaceGreeksEngine as Engine
    params = {"spot": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.03, "dividend_yield": 0}
    price = Engine.calculate_option_greeks(volatility=0.25, **params).theoretical_price
    iv = Engine.solve_implied_volatility(price, **params)
    require(iv is not None and math.isclose(iv, 0.25, abs_tol=0.001), f"合法期权价格反解波动率为 {iv}")
    result = Engine.solve_implied_volatility(101, **params)
    return require(result is None, f"违反无套利上界的报价仍得到隐含波动率 {result!r}",
                   "合法期权可反解波动率，违反无套利上界的报价被拒绝")



@check("X01", "multi_asset", "P1", "financial_core/engines/cross_asset_engine.py", 'UT-11')
def etf_overlap_math(_):
    from financial_core.engines.cross_asset_engine import CrossAssetValuationEngine as Engine
    a, b = {"AAA": 0.4, "BBB": 0.1}, {"AAA": 0.2, "CCC": 0.3}
    ab = Engine.compute_etf_overlap(a, b)
    ba = Engine.compute_etf_overlap(b, a)
    return require(ab.weighted_overlap_pct == ba.weighted_overlap_pct == 20
                   and ab.common_holdings_count == ba.common_holdings_count == 1,
                   f"预期双向重叠 20%、交集 1，得到 {ab.weighted_overlap_pct}% / {ba.weighted_overlap_pct}%")



@check("X02", "multi_asset", "P1", "financial_core/engines/cross_asset_engine.py", 'UT-11')
def etf_overlap_bounds(_):
    from financial_core.engines.cross_asset_engine import CrossAssetValuationEngine as Engine
    invalid = {"AAA": 0.8, "BBB": 0.8}
    try:
        result = Engine.compute_etf_overlap(invalid, invalid)
    except ValueError:
        return "ETF 持仓权重合计超过 100% 被拒绝"
    return require(0 <= result.weighted_overlap_pct <= 100, f"持仓重叠率超出 100%，结果 {result.weighted_overlap_pct}%")



@check("X03", "multi_asset", "P1", "financial_core/engines/cross_asset_engine.py", 'UT-11')
def gold_invalid_spot(_):
    from financial_core.engines.cross_asset_engine import CrossAssetValuationEngine as Engine
    accepted = []
    for spot in (0, -100, float("nan"), float("inf")):
        try:
            Engine.compute_gold_macro_valuation(spot_gold_usd=spot)
        except ValueError:
            continue
        accepted.append(str(spot))
    return require(not accepted, f"黄金估值接受非法现货输入 {accepted}")



@check("B05", "batch", "P1", "financial_core/engines/knowledge_graph_engine.py", 'UT-14')
def industry_legacy_alias(_):
    from financial_core.engines.knowledge_graph_engine import KnowledgeGraphEngine
    graph = KnowledgeGraphEngine()
    canonical = graph.resolve_industry_node_id("semiconductors")
    old = graph.resolve_industry_node_id("tech_semi")
    return require(bool(canonical) and canonical == old, f"semiconductors={canonical!r}，历史 tech_semi={old!r}")



@check("A02", "architecture", "P1", "financial_core/engines/filing_mapper.py", 'UT-12')
def absolute_filing_path(work):
    from financial_core.engines.filing_mapper import OfficialFilingMapper
    data = {"ticker": "AUDIT", "facts": {
        "reported_revenue": 100, "total_assets": 100, "total_liabilities": 50, "equity": 50,
        "market_price": 100, "quote_timestamp": "2026-10-16 16:00 EDT", "shares_outstanding": 100_000_000,
    }}
    path = work / "filing.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    OfficialFilingMapper.map_to_company_input(data)
    try:
        OfficialFilingMapper.load_from_file(path.resolve())
    except (ValueError, PermissionError):
        return "财报入口拒绝绝对本地引用"
    raise AssertionError("财报入口接受绝对本地引用")



@check("G01", "governance", "P0", "scripts/data_store.py", 'UT-12')
def source_catalog_boundary(work):
    from scripts.data_store import destination
    # 相对路径可落到审计临时目录，外部引用须在解析层拒绝。
    require(destination(work.relative_to(ROOT).as_posix()) == work, "合法相对目录无法解析")
    accepted = []
    for path in ("../outside", "%2e%2e/outside", "https://example.test/test", str(work)):
        try:
            destination(path)
        except ValueError:
            continue
        accepted.append(path)
    return require(not accepted, f"来源目录接受越界或绝对引用 {accepted}")
