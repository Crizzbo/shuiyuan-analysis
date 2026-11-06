"""细分行业买方结构化知识库契约单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖 Schema 契约完备性、半导体标杆样本解析、未迁移行业稳健兜底回退、
单例缓存一致性以及向下兼容中继门面 SSOT 等价性断言。
"""

from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.industry_knowledge_manager import (
    IndustryKnowledgeProfile,
    IndustryKnowledgeManager,
)
from finance_tools.industry_knowledge_manager import (
    IndustryKnowledgeProfile as FacadeIndustryKnowledgeProfile,
    IndustryKnowledgeManager as FacadeIndustryKnowledgeManager,
)


class TestIndustryKnowledgeContract(unittest.TestCase):
    """行业结构化知识库契约测试."""

    def setUp(self):
        self.mgr = IndustryKnowledgeManager()
        self.facade_mgr = FacadeIndustryKnowledgeManager()

    def test_ut_ind_01_schema_contract_compliance(self):
        """【UT-IND-01: 细分行业知识库 Schema 结构契约完整性断言】

        一、测试功能与测试点:
            验证 `schemas/industry_knowledge.schema.json` 契约定义完备，
            且标杆打样样例 `data/industry_knowledge/semiconductors.json`
            包含 meta, economic_structure, financial_guardrails, supply_chain_dynamics,
            causal_scenarios 与 forensic_audit_rules 六大核心顶层字段，
            所有必填子属性皆存在且类型合规。

        二、正常函数业务边界与参数契约:
            - Schema 文件必须有效存在并可被 JSON 解析。
            - semiconductors.json 必须符合六大顶层契约。

        三、测试数据与模拟场景说明:
            测试前沿半导体打样 POC 数据结构。

        四、预期断言与结果验证:
            断言六大顶层键皆存在于 semiconductors.json 中。
            断言 meta 中包含 industry_id == "semiconductors"。
        """
        schema_path = ROOT / "schemas" / "industry_knowledge.schema.json"
        sample_path = ROOT / "data" / "industry_knowledge" / "semiconductors.json"

        self.assertTrue(schema_path.exists(), "Schema 契约文件必须存在")
        self.assertTrue(sample_path.exists(), "半导体标杆打样数据必须存在")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
        with open(sample_path, "r", encoding="utf-8") as f:
            sample_data = json.load(f)

        required_sections = schema_data.get("required", [])
        for section in required_sections:
            self.assertIn(section, sample_data, f"标杆打样必须包含顶层字段: {section}")

        self.assertEqual(sample_data["meta"]["industry_id"], "semiconductors")
        self.assertEqual(sample_data["meta"]["sector_id"], "information_technology")

    def test_ut_ind_02_semiconductors_profile_parsing(self):
        """【UT-IND-02: 半导体标杆知识档案强类型解析与金融门禁阈值断言】

        一、测试功能与测试点:
            验证 IndustryKnowledgeManager 能将 semiconductors.json 精确解析为
            强类型 `IndustryKnowledgeProfile` 对象，且数值边界符合半导体行业特征:
            1. 存货周转天数警戒线 dio_warning_days == 160.0 天;
            2. 研发资本化率上限 rd_capitalization_max_allowed == 0.05 (5%);
            3. 大客户集中度红线 top_customer_concentration_redline == 0.25 (25%);
            4. 典型加价率 typical_markup_ratio == 1.35。

        二、正常函数业务边界与参数契约:
            - 输入 industry_id="semiconductors"。
            - 输出 IndustryKnowledgeProfile 实例。

        三、测试数据与模拟场景说明:
            加载半导体行业买方投研知识库。

        四、预期断言与结果验证:
            断言各金融门禁数值与配置文件完全一致，无精度丢失。
        """
        profile = self.mgr.get_profile("semiconductors")

        self.assertIsInstance(profile, IndustryKnowledgeProfile)
        self.assertEqual(profile.industry_id, "semiconductors")
        self.assertEqual(profile.industry_name_zh, "前沿半导体与芯片硬件")
        self.assertEqual(profile.dio_healthy_days, 95.0)
        self.assertEqual(profile.dio_warning_days, 160.0)
        self.assertEqual(profile.rd_capitalization_max_allowed, 0.05)
        self.assertEqual(profile.top_customer_concentration_redline, 0.25)
        self.assertEqual(profile.typical_markup_ratio, 1.35)
        self.assertEqual(profile.operating_leverage_exposure, "极高经营杠杆")

    def test_ut_ind_03_fallback_mechanism_for_unmigrated_industries(self):
        """【UT-IND-03: 未迁移行业基于 Taxonomy Bridge 优雅兜底防崩溃断言】

        一、测试功能与测试点:
            验证系统韧性与防劣变兜底逻辑：当请求尚未独立编写 JSON 的细分行业（例如 "oil_gas"）时，
            管理器严禁抛出 FileNotFoundError 或崩溃中断，而是平滑自适应回退到
            `IndustryTaxonomyBridge` 契约，自动填充完备的默认经济与因果字段。

        二、正常函数业务边界与参数契约:
            - 输入尚未生成 JSON 的行业 ID: "oil_gas"。
            - 能够正常返回合法的 IndustryKnowledgeProfile 实例。

        三、测试数据与模拟场景说明:
            模拟在分批次迁移过程中，部分行业仍处于老版契约阶段的混合调用场景。

        四、预期断言与结果验证:
            断言 profile 不为空。
            断言 profile.industry_id == "oil_gas"。
            断言 profile.typical_cogs_ratio == 0.55 (来自 TaxonomyBridge 预设)。
        """
        profile = self.mgr.get_profile("oil_gas")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.industry_id, "oil_gas")
        self.assertEqual(profile.industry_name_zh, "油气勘探与生产")
        self.assertEqual(profile.typical_cogs_ratio, 0.55)
        self.assertEqual(profile.typical_markup_ratio, 1.18)
        self.assertTrue(len(profile.leading_bull_triggers) > 0)
        self.assertTrue(len(profile.leading_bear_defenses) > 0)

    def test_ut_ind_04_singleton_and_cache_integrity(self):
        """【UT-IND-04: 单例模式内存缓存只读预热与加载清单断言】

        一、测试功能与测试点:
            验证 IndustryKnowledgeManager 遵循全局单例模式，第二次获取实例与第一次完全相同，
            且在启动时已成功预热加载包含 "semiconductors" 在内的行业配置。

        二、正常函数业务边界与参数契约:
            - 多次调用 IndustryKnowledgeManager() 返回相同实例引用。

        三、测试数据与模拟场景说明:
            并发或多模块复用加载器场景。

        四、预期断言与结果验证:
            断言 mgr1 is mgr2。
            断言 list_loaded_industries() 包含 "semiconductors"。
        """
        mgr1 = IndustryKnowledgeManager()
        mgr2 = IndustryKnowledgeManager()

        self.assertIs(mgr1, mgr2)
        loaded = mgr1.list_loaded_industries()
        self.assertIn("semiconductors", loaded)

    def test_ut_ind_05_facade_and_core_ssot_equivalence(self):
        """【UT-IND-05: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.industry_knowledge_manager` 门面与底层核心
            `financial_core.engines.industry_knowledge_manager` 功能和产出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同 industry_id。

        三、测试数据与模拟场景说明:
            新旧路径兼容性验证。

        四、预期断言与结果验证:
            断言门面取出的 profile 属性与核心取出的完全一致。
        """
        p_core = self.mgr.get_profile("semiconductors")
        p_facade = self.facade_mgr.get_profile("semiconductors")

        self.assertEqual(p_core.industry_id, p_facade.industry_id)
        self.assertEqual(p_core.dio_warning_days, p_facade.dio_warning_days)
        self.assertEqual(p_core.leading_bull_triggers, p_facade.leading_bull_triggers)
        self.assertEqual(p_core.red_flag_rules, p_facade.red_flag_rules)

    def test_ut_ind_06_buyer_causal_triggers_integrity(self):
        """【UT-IND-06: 半导体买方因果推导靶心与底线大白话文本高锐度断言】

        一、测试功能与测试点:
            验证标杆打样中的买方因果推导事实清单具备商业真实血肉与大白话直觉，
            杜绝泛泛而谈的模板废话。

        二、正常函数业务边界与参数契约:
            - profile.leading_bull_triggers 包含先进制程或云厂商算力集群事实。
            - profile.leading_bear_defenses 包含 CapEx 削减或库存积压跌价事实。

        三、测试数据与模拟场景说明:
            验证买方全息研报文本事实来源的锐度。

        四、预期断言与结果验证:
            断言乐观触发器包含 "先进制程" 或 "算力集群"。
            断言悲观防线包含 "CapEx" 或 "巨额跌价准备"。
        """
        profile = self.mgr.get_profile("semiconductors")

        bull_text = " ".join(profile.leading_bull_triggers)
        bear_text = " ".join(profile.leading_bear_defenses)
        forensic_text = " ".join(profile.red_flag_rules)

        self.assertTrue(any(k in bull_text for k in ["先进制程", "算力集群", "产能利用率"]))
        self.assertTrue(any(k in bear_text for k in ["CapEx", "跌价准备", "出口管制"]))
        self.assertTrue(any(k in forensic_text for k in ["渠道塞货", "资本化", "单一大客户"]))


if __name__ == "__main__":
    unittest.main()
