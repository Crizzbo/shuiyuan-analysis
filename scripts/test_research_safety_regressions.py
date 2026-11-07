"""财务缺失值、行情传播和研究输出的合成回归，所有文件写入隔离目录。"""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from finance_tools.market_quote_verifier import MarketQuoteVerifier, QuoteVerificationError
from financial_core.engines.filing_mapper import (
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
    OfficialFilingMapper,
)
from financial_core.engines.financial_statement_facade import FinancialStatementFacade
from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway
from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
from financial_reporting.ai_research_agent import AIResearchAgent
from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway
from scripts.test_support.fixtures import freeze_quote_clock


ROOT = Path(__file__).resolve().parents[1]


class ResearchSafetyRegressionTests(unittest.TestCase):
    """用独立合成输入覆盖原发布探针未覆盖的缺失值和真实零值分支。"""

    def setUp(self):
        self.facts = {
            "revenue": 800, "total_assets": 1000, "total_liabilities": 600,
            "equity": 400, "operating_income": 100, "net_income": 60,
        }

    def test_missing_optional_metrics_stay_missing(self):
        profile = FinancialStatementFacade().process_company_filing(self.facts)
        for name in ("free_cash_flow", "total_debt", "net_cash", "roic",
                     "inventory_turnover_days", "interest_coverage_ratio"):
            with self.subTest(name=name):
                self.assertIsNone(getattr(profile, name))
        normalized = UnifiedDataCollectionGateway.ingest_company_financials(
            "SYNTHETIC", "US", self.facts
        )
        self.assertIsNone(normalized["operating_cash_flow"])
        self.assertIsNone(normalized["fiscal_year"])

    def test_missing_balance_component_is_rejected(self):
        facts = dict(self.facts)
        del facts["total_liabilities"]
        for entry in (FinancialStatementFacade().process_company_filing,
                      lambda data: UnifiedDataCollectionGateway.ingest_company_financials("SYNTHETIC", "US", data)):
            with self.subTest(entry=entry):
                with self.assertRaises(IncompleteFilingFactError):
                    entry(facts)

    def test_disclosed_zero_liability_is_not_reconstructed(self):
        facts = dict(self.facts, total_liabilities=0)
        for entry in (FinancialStatementFacade().process_company_filing,
                      lambda data: UnifiedDataCollectionGateway.ingest_company_financials("SYNTHETIC", "US", data)):
            with self.subTest(entry=entry):
                with self.assertRaises(BalanceSheetIdentityError):
                    entry(facts)
        facts["equity"] = 1000
        profile = FinancialStatementFacade().process_company_filing(facts)
        self.assertEqual(profile.total_liabilities, 0)

    def test_disclosed_zero_revenue_is_not_missing(self):
        facts = dict(self.facts, revenue=0)
        result = UnifiedDataCollectionGateway.ingest_company_financials("SYNTHETIC", "US", facts)
        self.assertEqual(result["revenue"], 0)

    def test_invalid_numbers_are_rejected(self):
        for value in (float("nan"), float("inf"), True, "unknown", "1e999"):
            with self.subTest(value=value):
                with self.assertRaises(IncompleteFilingFactError):
                    FinancialStatementFacade().process_company_filing(dict(self.facts, total_assets=value))
        self.assertEqual(OfficialFilingMapper.parse_optional_financial_number("1e3", "assets"), 1000)

    def test_cash_flow_identity_uses_disclosed_operands(self):
        profile = FinancialStatementFacade().process_company_filing(
            dict(self.facts, operating_cash_flow=90, capex=-20)
        )
        self.assertEqual(profile.free_cash_flow, 70)
        self.assertIsNone(FinancialStatementFacade().process_company_filing(
            dict(self.facts, operating_cash_flow=90)
        ).free_cash_flow)

    def test_inventory_days_need_average_inventory(self):
        facts = dict(self.facts, inventory=30, cogs=365)
        self.assertIsNone(FinancialStatementFacade().process_company_filing(facts).inventory_turnover_days)
        profile = FinancialStatementFacade().process_company_filing(dict(facts, prior_inventory=10))
        self.assertEqual(profile.inventory_turnover_days, 20)

    def test_missing_quote_timestamp_is_not_fresh(self):
        profile = FinancialStatementFacade().process_company_filing(
            self.facts, {"price": 100, "session": "regular_trading"}
        )
        self.assertFalse(profile.is_quote_fresh)
        self.assertEqual(profile.market_session, "invalid_timestamp")
        self.assertIsNone(profile.market_cap)

    def test_exchange_date_and_session_transition(self):
        result = QuoteFreshnessGateway.verify_quote(
            100, "USD", "2026-10-16 19:59 EDT", "US", "2026-10-17T00:01:00Z"
        )
        self.assertTrue(result.is_fresh_today)
        self.assertEqual(result.session_status, "after_hours")
        for timestamp, now in (
            ("2026-10-16 08:00 EDT", "2026-10-16T14:00:00Z"),
            ("2026-10-16 10:00 EDT", "2026-10-16T21:00:00Z"),
        ):
            with self.subTest(timestamp=timestamp):
                result = QuoteFreshnessGateway.verify_quote(100, "USD", timestamp, "US", now)
                self.assertFalse(result.is_fresh_today)
                self.assertEqual(result.session_status, "previous_close_baseline")

    def test_archive_preserves_stale_and_missing_timestamp_status(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            reader = MarketQuoteVerifier(Path(directory))
            path = reader.raw_dir / "synthetic.json"
            for timestamp in ("2026-10-10T14:00:00Z", ""):
                with self.subTest(timestamp=timestamp):
                    path.write_text(json.dumps({"quotes": {"SYNTHETIC": {
                        "current_price": 100, "timestamp_iso": timestamp,
                    }}}), encoding="utf-8")
                    result = reader.get_latest_quote("SYNTHETIC", as_of_iso="2026-10-16T14:01:00Z")
                    self.assertFalse(result.is_valid)
                    self.assertFalse(result.is_fresh_today)
                    self.assertEqual(result.timestamp_iso, timestamp)
            with self.assertRaises(QuoteVerificationError):
                reader.archive_verified_quote("SYNTHETIC", "合成公司", 100)

    def test_complete_synthetic_dossiers_map_for_both_markets(self):
        for market, ticker in (("US", "SYNTHETIC"), ("JP", "9999")):
            with self.subTest(market=market):
                dossier = {
                    "overview": {"ticker": ticker, "market": market,
                                 "current_price": 100, "quote_timestamp": "2026-10-16T14:00:00Z"},
                    "raw_financials_table": dict(self.facts, cash_and_equivalents=120,
                                                total_debt=50, shares=10, capex=20,
                                                operating_cash_flow=90),
                }
                result = OfficialFilingMapper.map_dossier_to_company_input(dossier)
                self.assertEqual(result.current_price, 100)
                self.assertEqual(result.shares_outstanding, 10)
                self.assertEqual(result.reported_operating_cash_flow, 90)
                self.assertEqual(result.reported_capex, 20)
                missing = deepcopy(dossier)
                del missing["raw_financials_table"]["capex"]
                with self.assertRaises(IncompleteFilingFactError):
                    OfficialFilingMapper.map_dossier_to_company_input(missing)
                missing = deepcopy(dossier)
                del missing["overview"]["current_price"]
                missing["long_term_outlook"] = {"dcf_valuation_matrix": {"base_fair_value": "$200"}}
                with self.assertRaises(IncompleteFilingFactError):
                    OfficialFilingMapper.map_dossier_to_company_input(missing)

    def test_output_does_not_forge_evidence_events_or_dcf(self):
        dossier = AIDossierSynthesizer.synthesize_dossier("SYNTHETIC", "US", "合成公司", "", "")
        self.assertEqual(dossier["evidence_manifest"], [])
        self.assertEqual(dossier["material_events"], [])
        self.assertEqual(dossier["dcf_model"], {})

    def test_raw_pipeline_rejects_missing_quote_and_valuation_inputs(self):
        freeze_quote_clock(self)
        valid_quote = {
            "current_price": 100, "quote_timestamp": "2026-10-16T14:00:00Z",
            "pessimistic_floor": 70, "fair_anchor": 110, "optimistic_target": 130,
        }
        invalid_quotes = [None, {"current_price": 100}]
        for field in ("quote_timestamp", "pessimistic_floor", "fair_anchor", "optimistic_target"):
            missing = dict(valid_quote)
            del missing[field]
            invalid_quotes.append(missing)
        invalid_quotes.append(dict(valid_quote, quote_timestamp="2026-10-01T14:00:00Z"))
        for quote in invalid_quotes:
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                AIDossierSynthesizer.synthesize_from_raw_pipeline(
                    "SYNTHETIC", "US", "合成公司", "", "", self.facts, raw_quote=quote
                )

    def test_uncalibrated_scores_do_not_adjust_valuation_by_default(self):
        for analysis in ({"moat_analysis": {"network_effects": "强而深"}},
                         {"qualitative_scores": {"moat_score": 9, "supply_chain_risk_level": "HIGH"}}):
            with self.subTest(analysis=analysis):
                result = AIResearchAgent.parameterize_qualitative_factors(analysis)
                self.assertEqual(result["wacc_spread_decimal"], 0)
                self.assertEqual(result["supply_chain_risk_multiplier"], 1)
                self.assertEqual(result["growth_decay_factor"], 1)
                self.assertIn("disabled", result["calibration_status"])

    def test_scenario_cards_reject_missing_values_and_invalid_multiplier(self):
        quote = {"current_price": 100, "pessimistic_floor": 70, "fair_anchor": 110, "optimistic_target": 130}
        for key in quote:
            missing = dict(quote)
            del missing[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                AIResearchAgent.synthesize_three_state_scenario_cards(missing, {}, {})
        for multiplier in (0, -1, float("nan")):
            with self.subTest(multiplier=multiplier), self.assertRaises(ValueError):
                AIResearchAgent.synthesize_three_state_scenario_cards(
                    quote, {}, {"supply_chain_risk_multiplier": multiplier}
                )


if __name__ == "__main__":
    unittest.main()
