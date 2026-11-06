"""测试 AI 智能投研与多情景推演代理 (AIResearchAgent & AIEngineAdapter)."""

import json
from pathlib import Path
import unittest

from financial_reporting.ai_research_agent import (
    AIResearchAgent,
    AIEngineAdapter,
    EMOJI_PATTERN,
)

ROOT = Path(__file__).resolve().parents[1]


class TestAIResearchAgent(unittest.TestCase):
    """测试 AI 投研代理的核心清洗、参数化与推演能力."""

    def test_clean_text_no_emoji(self):
        """【UT-AI-01: 物理过滤所有Emoji表情与花哨装饰符】

        1. 测试功能与测试点:
           - 验证 AIResearchAgent.clean_text_no_emoji 函数对文本中所有 Emoji 表情符和特殊装饰符的物理级清除。
           - 严格执行机构买方报告规范，彻底剔除火箭、盾牌、图表、五角星等非专业符号，同时完好保留中文文字与标点。

        2. 正常函数业务边界与参数契约:
           - 输入为任意包含非标 Emoji 字符的原始字符串。
           - 输出为纯净自然文本。

        3. 测试数据与模拟场景说明:
           - 原始测试文本: "苹果公司 🚀 极具护城河 🛡️，未来预期大幅上涨 📈！ ⭐⭐⭐"。

        4. 预期断言与结果验证:
           - 断言火箭、盾牌、图表、五角星均不在输出文本中。
           - 断言 '苹果公司'、'极具护城河' 等核心字句完全无损保留。
        """
        raw_text = "苹果公司 🚀 极具护城河 🛡️，未来预期大幅上涨 📈！ ⭐⭐⭐"
        cleaned = AIResearchAgent.clean_text_no_emoji(raw_text)
        self.assertNotIn("🚀", cleaned)
        self.assertNotIn("🛡", cleaned)
        self.assertNotIn("📈", cleaned)
        self.assertNotIn("⭐", cleaned)
        self.assertIn("苹果公司", cleaned)
        self.assertIn("极具护城河", cleaned)

    def test_sanitize_ai_response_recursive(self):
        """【UT-AI-02: 嵌套字典与列表的递归Emoji清洗与净化】

        1. 测试功能与测试点:
           - 验证 AIResearchAgent.sanitize_ai_response 对复杂深度嵌套 JSON 结构的递归净化。
           - 遍历 dict 键值、嵌套子字典、字符串列表，逐层递归剥离所有 Emoji，保持非字符串数据类型原样不变。

        2. 正常函数业务边界与参数契约:
           - 接收 Dict[str, Any] 或 List[Any]，返回清洗后的同构结构。

        3. 测试数据与模拟场景说明:
           - 包含字典键值中带表情 '投资备忘录 💡'，列表项中带 '现金流充裕 💰'、'高分红 🎁'，以及数值 9.5。

        4. 预期断言与结果验证:
           - 标题清洗为 '投资备忘录'。
           - 列表元素清洗为 ['现金流充裕', '研发壁垒高'] 与 ['核心资产', '高分红']。
           - 浮点数值 9.5 保留不变。
        """
        dirty_dict = {
            "title": "投资备忘录 💡",
            "details": {
                "pros": ["现金流充裕 💰", "研发壁垒高 🔬"],
                "score": 9.5,
            },
            "tags": ["核心资产 🔥", "高分红 🎁"],
        }
        sanitized = AIResearchAgent.sanitize_ai_response(dirty_dict)
        self.assertEqual(sanitized["title"], "投资备忘录")
        self.assertEqual(sanitized["details"]["pros"], ["现金流充裕", "研发壁垒高"])
        self.assertEqual(sanitized["tags"], ["核心资产", "高分红"])

    def test_build_research_prompt(self):
        """【UT-AI-03: 买方分析师提示词装配规范与零表情符约束】

        1. 测试功能与测试点:
           - 验证 AIResearchAgent.build_research_prompt 提示词组装器。
           - 显式植入买方机构合规约束 ('绝对严禁使用任何表情符号')，并动态挂载标的代码、中文名称与官方审计财报底账。

        2. 正常函数业务边界与参数契约:
           - ticker, market, company_name, industry_name 均为非空字符串，audited_facts 包含财报科目。

        3. 测试数据与模拟场景说明:
           - NVDA 美股标的，行业 '前沿半导体与算力芯片'，审计事实包含营收 60922 与净利润 29760。

        4. 预期断言与结果验证:
           - 提示词文本必须显式包含 '绝对严禁使用任何表情符号'。
           - 必须包含标的代码 'NVDA'、中文名 '英伟达' 以及财报数值 '60922.0'。
        """
        prompt = AIResearchAgent.build_research_prompt(
            ticker="NVDA",
            market="US",
            company_name="英伟达 (NVIDIA Corp)",
            industry_name="前沿半导体与算力芯片",
            audited_facts={"revenue": 60922.0, "net_income": 29760.0},
        )
        self.assertIn("绝对严禁使用任何表情符号", prompt)
        self.assertIn("NVDA", prompt)
        self.assertIn("英伟达", prompt)
        self.assertIn("60922.0", prompt)

    def test_parameterize_qualitative_factors(self):
        """【UT-AI-04: AI定性分析参数化映射(护城河WACC贴现与供应链风险乘数)】

        1. 测试功能与测试点:
           - 验证 AIResearchAgent.parameterize_qualitative_factors 将定性研判参数化注入核心金融引擎。
           - 护城河得分转化: 高于中枢 (5.0) 减少贴现率 (负利差基点)，低于中枢增加风险溢价。
           - 供应链风险评级转化: LOW -> 乘数 1.0x，CRITICAL -> 惩罚乘数 1.40x。

        2. 正常函数业务边界与参数契约:
           - 输入包含 qualitative_scores 的分析字典。

        3. 测试数据与模拟场景说明:
           - 场景 1: 强护城河 (得分 9.0, 供应链风险 LOW)。
           - 场景 2: 弱护城河 (得分 4.0, 供应链风险 CRITICAL)。

        4. 预期断言与结果验证:
           - 场景 1 断言 wacc_spread_bps < 0.0，乘数 == 1.0。
           - 场景 2 断言 wacc_spread_bps > 0.0，乘数 == 1.40。
        """
        high_moat_analysis = {
            "qualitative_scores": {
                "moat_score": 9.0,
                "supply_chain_risk_level": "LOW",
            }
        }
        params = AIResearchAgent.parameterize_qualitative_factors(high_moat_analysis)
        self.assertEqual(params["moat_score"], 9.0)
        # 护城河得分 9.0 分高于中枢 5.0 分，带来贴现率扣减 (负值)
        self.assertLess(params["wacc_spread_bps"], 0.0)
        self.assertEqual(params["supply_chain_risk_multiplier"], 1.0)

        high_risk_analysis = {
            "qualitative_scores": {
                "moat_score": 4.0,
                "supply_chain_risk_level": "CRITICAL",
            }
        }
        risk_params = AIResearchAgent.parameterize_qualitative_factors(high_risk_analysis)
        self.assertGreater(risk_params["wacc_spread_bps"], 0.0)  # 弱护城河增加贴现罚息
        self.assertEqual(risk_params["supply_chain_risk_multiplier"], 1.40)  # 致命风险加乘 1.40x

    def test_synthesize_three_state_scenario_cards(self):
        """【UT-AI-05: 多情景三态推演卡片生成(悲观底/中性公允/乐观靶心与战术纪律)】

        1. 测试功能与测试点:
           - 验证 AIResearchAgent.synthesize_three_state_scenario_cards 生成买方多情景决策卡。
           - 严格覆盖三态价格走廊 (悲观底价、中性基准公允价、乐观靶心价格) 与买方战术操作纪律。
           - 催化剂与风险熔断触发事件结构化注入。

        2. 正常函数业务边界与参数契约:
           - quote 包含 4 大价格字段，ai_analysis 包含催化剂与风险项。

        3. 测试数据与模拟场景说明:
           - 现价 100，悲观底 70，公允 120，乐观 160。供应链风险乘数 1.10。

        4. 预期断言与结果验证:
           - 决策卡包含 pessimistic_floor, neutral_fair, optimistic_target, tactical_discipline。
           - 断言悲观价格 <= 70.0，公允价格 == 120.0，乐观靶心 == 160.0。
           - 乐观触发事件中准确包含 '新架构芯片放量'。
        """
        quote = {
            "current_price": 100.0,
            "pessimistic_floor": 70.0,
            "fair_anchor": 120.0,
            "optimistic_target": 160.0,
        }
        ai_analysis = {
            "catalysts": ["新架构芯片放量"],
            "kill_switch_risks": ["代工厂地缘风险"],
            "tactical_action": "底仓配置 20%，跌破 80 加仓。",
        }
        params = {"supply_chain_risk_multiplier": 1.10}

        cards = AIResearchAgent.synthesize_three_state_scenario_cards(quote, ai_analysis, params)
        self.assertIn("pessimistic_floor", cards)
        self.assertIn("neutral_fair", cards)
        self.assertIn("optimistic_target", cards)
        self.assertIn("tactical_discipline", cards)

        # 验证数值及逻辑
        self.assertLessEqual(cards["pessimistic_floor"]["price"], 70.0)
        self.assertEqual(cards["neutral_fair"]["price"], 120.0)
        self.assertEqual(cards["optimistic_target"]["price"], 160.0)
        self.assertIn("新架构芯片放量", cards["optimistic_target"]["trigger_events"])

    def test_ai_engine_adapter_verified_replay(self):
        """【IT-AI-06: 已核验批次数据无损回放(AAPL)与零Emoji合规验签】

        1. 测试功能与测试点:
           - 验证 AIEngineAdapter.get_analysis 在离线回放模式下从已核验批次数据中提取分析。
           - 保证业务模式、护城河分析、供应链分析字段齐全。
           - 全文严格正则扫描，验证 100% 物理消除所有 Emoji。

        2. 正常函数业务边界与参数契约:
           - ticker="AAPL", live_mode=False。

        3. 测试数据与模拟场景说明:
           - 检索苹果公司 (Apple Inc.) 深度档案。

        4. 预期断言与结果验证:
           - 包含 business_model, moat_analysis, supply_chain_analysis。
           - EMOJI_PATTERN 正则扫描匹配结果为 None。
        """
        analysis = AIEngineAdapter.get_analysis(
            ticker="AAPL",
            market="US",
            company_name="苹果 (Apple Inc.)",
            industry_name="消费电子",
            audited_facts={"revenue": 391035.0},
            live_mode=False,
        )
        self.assertIn("business_model", analysis)
        self.assertIn("moat_analysis", analysis)
        self.assertIn("supply_chain_analysis", analysis)
        # 确保无表情符号
        text_str = json.dumps(analysis, ensure_ascii=False)
        self.assertIsNone(EMOJI_PATTERN.search(text_str))

    def test_ai_engine_adapter_deterministic_fallback(self):
        """【IT-AI-07: 未建档新公司确定性回退研报生成与契约自洽性】

        1. 测试功能与测试点:
           - 验证当遇到全新且未建档标的时，AIEngineAdapter 自动启动确定性业务骨架回退生成。
           - 拒绝崩溃或调用外部未授权生成 API，基于审计财报自动生成审慎评级与结构化研报。

        2. 正常函数业务边界与参数契约:
           - ticker="UNKNOWN_NEWCO", live_mode=False。

        3. 测试数据与模拟场景说明:
           - 模拟新兴科技公司，营收 5000 万，营业利润 1000 万。

        4. 预期断言与结果验证:
           - 商业模式描述中包含 '新兴科技'。
           - 评级为 '审慎增持'。
           - 全文正则扫描无 Emoji 违规。
        """
        analysis = AIEngineAdapter.get_analysis(
            ticker="UNKNOWN_NEWCO",
            market="US",
            company_name="新兴科技",
            industry_name="通用软件",
            audited_facts={"revenue": 5000.0, "operating_income": 1000.0},
            live_mode=False,
        )
        self.assertIn("新兴科技", analysis["business_model"])
        self.assertEqual(analysis["rating"], "审慎增持")
        text_str = json.dumps(analysis, ensure_ascii=False)
        self.assertIsNone(EMOJI_PATTERN.search(text_str))

    def test_synthesize_from_raw_pipeline_end_to_end(self):
        """【FT-AI-08: 原始输入一键合成完整合规深度档案端到端全链路】

        1. 测试功能与测试点:
           - 验证 AIDossierSynthesizer.synthesize_from_raw_pipeline 端到端合成管线。
           - 严格对接 schemas/deep_dossier.schema.json (Schema 2.0.0)。
           - 输出完整包含概览、护城河、供应链、决策总结与情景决策卡，并满足零 Emoji 规范。

        2. 正常函数业务边界与参数契约:
           - 输入 raw_facts 与 raw_quote，输出标准深度档案字典。

        3. 测试数据与模拟场景说明:
           - 标的 TEST_CO，营收 10 亿，资产 40 亿，负债 25 亿，权益 15 亿 (平账)，现价 150 美元。

        4. 预期断言与结果验证:
           - schema_version == '2.0.0'。
           - 包含 overview, moat_analysis, supply_chain_analysis, decision_summary。
           - scenario_cards 包含 pessimistic_floor。
           - 全文 EMOJI_PATTERN 匹配结果为 None。
        """
        from financial_reporting.ai_dossier_synthesizer import AIDossierSynthesizer
        raw_facts = {
            "revenue": 100000.0,
            "net_income": 20000.0,
            "operating_cash_flow": 28000.0,
            "total_assets": 400000.0,
            "total_liabilities": 250000.0,
            "stockholders_equity": 150000.0,
        }
        raw_quote = {
            "current_price": 150.0,
            "quote_timestamp": "2026-10-17T12:00:00Z",
        }
        dossier = AIDossierSynthesizer.synthesize_from_raw_pipeline(
            ticker="TEST_CO",
            market="US",
            company_name="测试卓越科技",
            industry_id="software",
            industry_name_zh="云软件与企业级服务",
            raw_facts=raw_facts,
            raw_quote=raw_quote,
            report_date="2026-10-17",
        )
        self.assertEqual(dossier["schema_version"], "2.0.0")
        self.assertIn("overview", dossier)
        self.assertIn("moat_analysis", dossier)
        self.assertIn("supply_chain_analysis", dossier)
        self.assertIn("decision_summary", dossier)
        self.assertEqual(dossier["overview"]["ticker"], "TEST_CO")
        dec = dossier["decision_summary"]
        self.assertIn("scenario_cards", dec)
        self.assertIn("pessimistic_floor", dec["scenario_cards"])
        text_str = json.dumps(dossier, ensure_ascii=False)
        self.assertIsNone(EMOJI_PATTERN.search(text_str))


if __name__ == "__main__":
    unittest.main()
