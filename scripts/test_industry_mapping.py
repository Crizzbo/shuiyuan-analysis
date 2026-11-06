"""行业映射与会计准则保真回归测试套件。网络访问在整个测试进程中被禁止。"""
import copy
import json
import os
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not os.getenv("_VENV_BOOTSTRAPPED"):
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_py.is_file():
        venv_py = ROOT / ".venv" / "bin" / "python"
    current_exe = Path(sys.executable).resolve()
    if venv_py.is_file() and venv_py.resolve() != current_exe:
        import subprocess

        env = dict(os.environ)
        env["_VENV_BOOTSTRAPPED"] = "1"
        res = subprocess.run([str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
        sys.exit(res.returncode)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def deny(*a, **kw):
    raise AssertionError("行业映射回归禁止网络")


socket.socket.connect = deny
socket.create_connection = deny

from financial_reporting.industry_mapping import map_industry, verify_mapping
from data_store import LocalStore


class MappingTests(unittest.TestCase):
    """行业映射管道与会计口径保真测试类。"""

    @classmethod
    def setUpClass(cls):
        index = json.loads((ROOT / "data/financial/industry-mapping-verification.json").read_text(encoding="utf-8"))
        cls.samples = [json.loads((ROOT / p["snapshot_path"]).read_text(encoding="utf-8")) for p in index["examples"]]

    def test_real_three_sample_results(self):
        """【FT-INDMAP-01: 三家真实样本行业映射全息核验与营业利润率精准对齐】

        1. 测试功能与测试点:
           - 验证真实样本企业（Intuit 美股、Sony 日股 IFRS、Nintendo 日股 J-GAAP）行业映射完整性。
           - 严格断言映射观测指标数恰好为 2。
           - 严格断言分类状态为 'unreviewed'，行业闸门状态为 'blocked'。
           - 严格断言必需缺失指标数恰好为 3 项。
           - 验证营业利润率 (operating_margin) 数值保真度分别对齐 5884/21448 与 360117/2313051。

        2. 正常函数业务边界与参数契约:
           - 映射快照必须满足官方 Schema，通过 verify_mapping 校验。

        3. 测试数据与模拟场景说明:
           - 读取 industry-mapping-verification.json 索引指向的 3 份真实映射快照对象。

        4. 预期断言与结果验证:
           - verify_mapping(r) 成功无异常。
           - 观测值精确匹配财务底账。
        """
        for r in self.samples:
            verify_mapping(r)
            self.assertEqual(len(r["observations"]), 2)
            self.assertEqual(r["classification_status"], "unreviewed")
            self.assertEqual(r["industry_gate_status"], "blocked")
            self.assertEqual(len(r["missing_required_metric_ids"]), 3)
        margin = next(o for o in self.samples[0]["observations"] if o["metric_id"] == "operating_margin")
        self.assertAlmostEqual(margin["value"]["value"], 5884 / 21448)
        margin = next(o for o in self.samples[2]["observations"] if o["metric_id"] == "operating_margin")
        self.assertAlmostEqual(margin["value"]["value"], 360117 / 2313051)

    def test_original_scope_and_gaap_preserved(self):
        """【UT-INDMAP-02: 原始合并范围与会计准则(IFRS/J-GAAP)保真无篡改核验】

        1. 测试功能与测试点:
           - 验证行业映射管道忠实保留原始底层会计准则。
           - 验证索尼 (Sony) 映射观测保留 IFRS 准则且可比性附注明确标注持续经营合并口径 ('consolidated_continuing')。
           - 验证任天堂 (Nintendo) 映射观测保留 J-GAAP 准则。

        2. 正常函数业务边界与参数契约:
           - accounting_basis 枚举值只能为官方准则代码，严禁私自转码。

        3. 测试数据与模拟场景说明:
           - 样本 1: 索尼 20-F；样本 2: 任天堂有价证券报告书。

        4. 预期断言与结果验证:
           - 索尼观测 accounting_basis == 'IFRS' 且注记包含 'consolidated_continuing'。
           - 任天堂观测 accounting_basis == 'J-GAAP'。
        """
        self.assertTrue(all(o["accounting_basis"] == "IFRS" and "consolidated_continuing" in o["comparability_notes"] for o in self.samples[1]["observations"]))
        self.assertTrue(all(o["accounting_basis"] == "J-GAAP" for o in self.samples[2]["observations"]))

    def test_modified_value_rejected(self):
        """【UT-INDMAP-03: 篡改指标观测值物理阻断与一致性核验(verify_mapping)】

        1. 测试功能与测试点:
           - 验证 verify_mapping 对篡改指标事实的防御性校验。
           - 人为篡改指标观测数值（将营业利润率改为 1）。
           - 验证系统立即抛出包含“不一致”的 ValueError。

        2. 正常函数业务边界与参数契约:
           - 映射快照中的值必须与底层财报推导一致。

        3. 测试数据与模拟场景说明:
           - 拷贝 Intuit 样本映射快照，篡改首个观测值。

        4. 预期断言与结果验证:
           - 抛出 ValueError，正则匹配 '不一致'。
        """
        r = copy.deepcopy(self.samples[0])
        r["observations"][0]["value"]["value"] = 1
        with self.assertRaisesRegex(ValueError, "不一致"):
            verify_mapping(r)

    def test_industry_gap_cannot_be_removed(self):
        """【UT-INDMAP-04: 行业必需指标缺口强制守恒与私自清空缺口拦截】

        1. 测试功能与测试点:
           - 验证行业指标缺口守恒定律。
           - 人为清空必需缺失指标列表 (missing_required_metric_ids = [])。
           - 验证 verify_mapping 拒绝放行并刚性抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - 行业指标缺口未实际补全前，严禁伪造完整状态。

        3. 测试数据与模拟场景说明:
           - 篡改 missing_required_metric_ids 为空列表。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        r = copy.deepcopy(self.samples[0])
        r["missing_required_metric_ids"] = []
        with self.assertRaises(ValueError):
            verify_mapping(r)

    def test_future_evidence_unavailable(self):
        """【UT-INDMAP-05: 行业映射前视未来数据(Lookahead)与早于可用时间刚性熔断】

        1. 测试功能与测试点:
           - 验证 map_industry 对因果时序边界的强硬约束。
           - 传入早于可用时间的截止时点，严禁前视未来数据。
           - 刚性抛出 ValueError 阻断。

        2. 正常函数业务边界与参数契约:
           - as_of 时间必须晚于或等于材料可用时间。

        3. 测试数据与模拟场景说明:
           - 传入 2026-07-07 时点，但数据尚未产生。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        with self.assertRaises(ValueError):
            map_industry("JP:7974", "media_entertainment", "2026-03-31", "2026-07-07T00:00:00Z")

    def test_unreviewed_financial_industry_blocked(self):
        """【UT-INDMAP-06: 未审核金融行业映射物理阻断(status=blocked)】

        1. 测试功能与测试点:
           - 验证将一般科技企业 (Intuit) 错误映射至银行业 (banks) 时的风控逻辑。
           - 银行行业模型尚未完成全面审核，必须阻断映射。
           - 验证返回的 observations 为空列表，mapping_results 全部为 'blocked'。

        2. 正常函数业务边界与参数契约:
           - 未经审核行业映射不得输出有效观测。

        3. 测试数据与模拟场景说明:
           - 实体 US:INTU:CIK896878 绑定 banks 行业。

        4. 预期断言与结果验证:
           - r['observations'] 为空。
           - mapping_results 状态全为 'blocked'。
        """
        r = map_industry("US:INTU:CIK896878", "banks", "2026-07-31", self.samples[0]["as_of"])
        self.assertFalse(r["observations"])
        self.assertTrue(all(x["status"] == "blocked" for x in r["mapping_results"]))

    def test_no_scope_substitution(self):
        """【UT-INDMAP-07: 合并范围不可随意替换与跨范围映射拦截】

        1. 测试功能与测试点:
           - 验证不同合并报表范围（例如普通合并 consolidated 与持续经营合并 consolidated_continuing）严禁混用或自动替换。
           - 传入不匹配的 scope 时，拒绝映射。

        2. 正常函数业务边界与参数契约:
           - 范围代码必须与官方登记事实精确匹配。

        3. 测试数据与模拟场景说明:
           - 索尼硬件业务使用 'consolidated' 范围尝试映射。

        4. 预期断言与结果验证:
           - r['observations'] 为空。
        """
        r = map_industry("JP:6758:CIK313838", "hardware", "2026-03-31", self.samples[1]["as_of"], "consolidated")
        self.assertFalse(r["observations"])

    def test_invalid_industry_path(self):
        """【UT-INDMAP-08: 行业分类越界路径('../software')注入拦截】

        1. 测试功能与测试点:
           - 验证输入路径安全防御。
           - 拦截包含相对路径穿越 ('../software') 的非法行业代码。

        2. 正常函数业务边界与参数契约:
           - industry_id 必须为安全合规标识符，严禁包含路径分隔符。

        3. 测试数据与模拟场景说明:
           - 传入 '../software' 目录穿透 payload。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        with self.assertRaises(ValueError):
            map_industry("JP:7974", "../software", "2026-03-31", self.samples[2]["as_of"])

    def test_saved_research_revision(self):
        """【IT-INDMAP-09: 本地数据治理库研究版本演进与状态追溯】

        1. 测试功能与测试点:
           - 验证 LocalStore 核心数据治理体系对研究草稿 (research) 的版本管理。
           - 获取 intu-2026-financial-evidence-draft 版本 2，断言包含 2 项观测。
           - 验证研究步骤 steps 全部为 'pending'，计算验证状态全部为 'unchecked'。
           - 对比版本 1 观测数为 0，确保历史版本不可变且演进清晰。

        2. 正常函数业务边界与参数契约:
           - 数据仓库按版本号有序检索并校验密码学签名。

        3. 测试数据与模拟场景说明:
           - 读取本地 SQLite catalog.sqlite3 数据库中的研究草稿版本。

        4. 预期断言与结果验证:
           - 版本 2 观测数为 2，步骤为 pending。
           - 版本 1 观测数为 0。
        """
        c = LocalStore()
        try:
            r = c.get_research("intu-2026-financial-evidence-draft", 2)
            self.assertEqual(len(r["observations"]), 2)
            self.assertTrue(all(s["status"] == "pending" for s in r["steps"]))
            self.assertTrue(all(x["verification_status"] == "unchecked" for x in r["calculations"]))
            self.assertEqual(len(c.get_research("intu-2026-financial-evidence-draft", 1)["observations"]), 0)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
