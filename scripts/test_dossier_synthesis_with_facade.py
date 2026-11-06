#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/test_dossier_synthesis_with_facade.py

深度投研建档合成器 (AIDossierSynthesizer) 与图谱/防腐双门禁集成打样测试集 (Sampling POC)
涵盖三大代表性行业标的:
1. 科技半导体 (semiconductors) NVDA: 检验正常平账建档与 DIO、毛利率等全指标组装
2. 商业银行 (banks) JPM: 检验违规使用 EV/EBITDA 的知识图谱前置硬拦截与 DDM/PB 合规放行
3. 研发型生物科技 (biotech) VRTX: 检验静态 P/E 违规硬拦截与资产负债不平的防腐门面硬拦截
"""

import unittest
from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
from financial_core.engines.financial_statement_facade import BalanceSheetIdentityError


class TestDossierSynthesisWithFacade(unittest.TestCase):
    """深度档案合成器挂接双门禁端到端打样测试套件"""

    def test_sample_poc_01_semiconductors_nvda_success(self):
        """【POC-01: 半导体巨头 NVDA 合规平账与全息指标建档打样】"""
        fin_facts = {
            "total_assets": 65728.0,
            "total_liabilities": 22750.0,
            "total_equity": 42978.0,  # 22750 + 42978 = 65728 (100% 刚性平账)
            "cash_and_equivalents": 25980.0,
            "total_debt": 9700.0,
            "revenue": 60922.0,
            "gross_profit": 44301.0,
            "operating_income": 32972.0,
            "net_income": 29760.0,
            "cogs": 16621.0,
            "inventory": 5282.0,
            "free_cash_flow": 27021.0,
        }
        quote = {
            "current_price": 138.25,
            "fair_anchor": 150.0,
            "valuation_model": "DCF_Growth",
            "timestamp": "2026-11-05 10:30:00 EST",
        }
        ai_data = {
            "business_model": "无晶圆厂芯片设计与全栈 CUDA 算力生态",
            "stance": "BUY_VALUE_ZONE",
        }

        dossier = AIDossierSynthesizer.synthesize_dossier(
            ticker="NVDA",
            market="US",
            company_name="NVIDIA Corporation",
            industry_id="semiconductors",
            industry_name_zh="半导体设计与制造",
            financial_statements=fin_facts,
            market_quote=quote,
            ai_analysis=ai_data,
        )

        self.assertEqual(dossier["overview"]["ticker"], "NVDA")
        self.assertEqual(dossier["overview"]["industry_id"], "semiconductors")
        self.assertEqual(dossier["decision_summary"]["stance"], "估值洼地 (积极布局)")
        self.assertTrue(dossier["decision_summary"]["margin_of_safety_pct"] > 0)

    def test_sample_poc_02_banks_jpm_valuation_rejection_and_pass(self):
        """【POC-02: 商业银行 JPM 拦截 EV/EBITDA 与 PB-ROE/DDM 合规放行打样】"""
        fin_facts = {
            "total_assets": 3875000.0,
            "total_liabilities": 3550000.0,
            "total_equity": 325000.0,  # 3550000 + 325000 = 3875000 (平账)
            "revenue": 158104.0,
            "operating_income": 61642.0,
            "net_income": 49552.0,
        }

        # 1. 尝试对银行使用 EV/EBITDA 估值模型 -> 必须被知识图谱硬拦截
        illegal_quote = {
            "current_price": 215.0,
            "valuation_model": "EV/EBITDA",
        }
        with self.assertRaises(ValueError) as ctx:
            AIDossierSynthesizer.synthesize_dossier(
                ticker="JPM",
                market="US",
                company_name="JPMorgan Chase & Co.",
                industry_id="banks",
                industry_name_zh="银行",
                financial_statements=fin_facts,
                market_quote=illegal_quote,
            )
        self.assertIn("【知识图谱边界硬拦截】", str(ctx.exception))
        self.assertIn("严禁使用企业价值倍数", str(ctx.exception))
        self.assertIn("必须使用市净率 PB-ROE 或股息折现 DDM", str(ctx.exception))

        # 2. 纠正为银行合规估值模型 DDM / PB-ROE -> 成功放行
        legal_quote = {
            "current_price": 215.0,
            "valuation_model": "DDM_Gordon",
        }
        dossier = AIDossierSynthesizer.synthesize_dossier(
            ticker="JPM",
            market="US",
            company_name="JPMorgan Chase & Co.",
            industry_id="banks",
            industry_name_zh="银行",
            financial_statements=fin_facts,
            market_quote=legal_quote,
        )
        self.assertEqual(dossier["overview"]["ticker"], "JPM")

    def test_sample_poc_03_biotech_vrtx_rejection_and_imbalance_block(self):
        """【POC-03: 研发型生物科技 VRTX 静态市盈率拦截与资产负债不平拦截打样】"""
        # 1. 静态市盈率 P/E 违规拦截
        with self.assertRaises(ValueError) as ctx:
            AIDossierSynthesizer.synthesize_dossier(
                ticker="VRTX",
                market="US",
                company_name="Vertex Pharmaceuticals",
                industry_id="biotech",
                industry_name_zh="研发型生物科技",
                market_quote={"valuation_model": "P/E"},
            )
        self.assertIn("严禁直接使用静态市盈率", str(ctx.exception))
        self.assertIn("必须使用研发管线风险调整净现值 rNPV", str(ctx.exception))

        # 2. 财报平账破损硬拦截 (资产 1000 != 负债 400 + 权益 500, 偏差 100)
        imbalanced_facts = {
            "total_assets": 1000.0,
            "total_liabilities": 400.0,
            "total_equity": 500.0,
        }
        with self.assertRaises(BalanceSheetIdentityError) as ctx_bal:
            AIDossierSynthesizer.synthesize_dossier(
                ticker="VRTX",
                market="US",
                company_name="Vertex Pharmaceuticals",
                industry_id="biotech",
                industry_name_zh="研发型生物科技",
                financial_statements=imbalanced_facts,
                market_quote={"valuation_model": "rNPV_Pipeline"},
            )
        self.assertIn("资产负债恒等式严重破损", str(ctx_bal.exception))


if __name__ == "__main__":
    unittest.main()
