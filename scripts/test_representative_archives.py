"""验证41行业档案的事实血缘、覆盖及未放行行动，防止以目录数量掩盖缺口。"""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_knowledge_structure import local_file

class RepresentativeArchivesTests(unittest.TestCase):
    """41行业代表企业档案事实血缘、覆盖完备度与研究放行边界回归测试类。"""

    def test_coverage_fact_lineage_and_missing_boundaries(self):
        """【FT-REPARCH-01: 41行业代表企业13个版本档案事实血缘/无偏覆盖与未放行边界回归断言】

        1. 测试功能与测试点:
           - 验证 41 行业代表企业档案在 13 批历史演进版本（representatives-20261012 至 representatives-20261012m）中的事实血缘追踪与完整性。
           - 验证标的集合与规划底账 config/google-finance-industry-plan.json 100% 集合恒等对齐。
           - 验证事实求和与底层观测快照条数完全守恒。
           - 验证未放行行动边界防线：
             * investment_stance 必须为 None（严禁未获授权给出投资立场）；
             * position_fraction 必须为 None（严禁未审验分配仓位权重）；
             * valuation_status 必须为 'not_assessed'；
             * research_status 必须为 'evidence_partial' 或 'evidence_missing'；
             * 档案画像必须包含警示声明：“文档不等于完成深度分析”。
           - 验证财务事实与观测快照属性（value, unit, scope, period_start, period_end, source_ref, locator, component）1:1 严格一致，来源物理文件切实存在。

        2. 正常函数业务边界与参数契约:
           - 读取版本目录下的 index.json 与 observation_snapshot_path。
           - 企业数量严格等于 41。

        3. 测试数据与模拟场景说明:
           - 13 批代表企业已归档版本数据。

        4. 预期断言与结果验证:
           - companies_count == 41。
           - 集合恒等、字段一致、立场为空、断言物理文件存在。
        """
        read = lambda p: json.loads((ROOT / p).read_text(encoding="utf8"))
        plan = read("config/google-finance-industry-plan.json")
        for version_dir in (
            "representatives-20261012",
            "representatives-20261012b",
            "representatives-20261012c",
            "representatives-20261012d",
            "representatives-20261012e",
            "representatives-20261012f",
            "representatives-20261012g",
            "representatives-20261012h",
            "representatives-20261012i",
            "representatives-20261012j",
            "representatives-20261012k",
            "representatives-20261012l",
            "representatives-20261012m",
        ):
            with self.subTest(version=version_dir):
                index = read(f"knowledge/companies/{version_dir}/index.json")
                source = read(index["observation_snapshot_path"])
                byid = {o["observation_id"]: o for o in source["observations"]}
                self.assertEqual(index["companies_count"], 41)
                self.assertEqual(
                    {(c["industry_id"], c["ticker"]) for c in index["companies"]},
                    {(c["industry_id"], c["ticker"]) for c in plan["securities"]},
                )
                self.assertEqual(sum(len(c["facts"]) for c in index["companies"]), len(source["observations"]))
                for c in index["companies"]:
                    self.assertIsNone(c["investment_stance"])
                    self.assertIsNone(c["position_fraction"])
                    self.assertEqual(c["valuation_status"], "not_assessed")
                    self.assertEqual(c["research_status"], "evidence_partial" if c["facts"] else "evidence_missing")
                    profile = local_file(ROOT, c["profile_path"]).read_text(encoding="utf8")
                    self.assertIn(c["ticker"], profile)
                    self.assertIn("文档不等于完成深度分析", profile)
                    for fact in c["facts"]:
                        observed = byid[fact["observation_id"]]
                        self.assertEqual(observed["industry_id"], c["industry_id"])
                        self.assertEqual(observed["entity_id"], c["market"] + ":" + c["ticker"].split(":", 1)[1])
                        for key in ("value", "unit", "scope", "period_start", "period_end", "source_ref", "locator", "component"):
                            self.assertEqual(fact[key], observed[key])
                        self.assertTrue(local_file(ROOT, fact["source_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
