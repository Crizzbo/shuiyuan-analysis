"""指标接入独立回归：证据边界、时点、公司/分部、量纲及行业覆盖。"""

import copy
import hashlib
import json
from pathlib import Path
import sys
import socket
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def deny_network(*args, **kwargs):
    raise AssertionError("测试禁止网络")


socket.socket.connect = deny_network
socket.create_connection = deny_network
from finance_tools.metric_pipeline import run_batch, BINDINGS


class MetricTests(unittest.TestCase):
    """指标接入管道独立回归测试类。"""

    def setUp(self):
        self.batch = json.loads((ROOT / "examples/software-metric-batch.synthetic.json").read_text(encoding="utf-8"))

    def test_synthetic_known_answers(self):
        """【FT-METRIC-01: 合成指标批计算已知标准答案对齐(营业利润率/ROE)与关卡阻断断言】

        1. 测试功能与测试点:
           - 验证软件行业合成指标批次 run_batch 正确推导营业利润率 (operating_margin: 0.2) 与净资产收益率 (roe: 0.2)。
           - 验证缺失行业驱动指标数恰好为 3 项。
           - 验证研究就绪闸门 S2 为 'blocked'。
           - 验证研究导出状态包含 'staging_only'，防范半成品流出。

        2. 正常函数业务边界与参数契约:
           - run_batch(batch) 返回结构化报表。

        3. 测试数据与模拟场景说明:
           - examples/software-metric-batch.synthetic.json 合成基准数据。

        4. 预期断言与结果验证:
           - operating_margin.value == 0.2，roe.value == 0.2。
           - missing_industry_driver_ids 长度为 3。
           - S2 == 'blocked'。
        """
        report = run_batch(self.batch)
        values = {row["metric_id"]: row for row in report["results"]}
        self.assertAlmostEqual(values["operating_margin"]["value"], .2)
        self.assertAlmostEqual(values["roe"]["value"], .2)
        self.assertEqual(len(report["missing_industry_driver_ids"]), 3)
        self.assertEqual(report["research_readiness"]["S2"], "blocked")
        self.assertIn("staging_only", report["research_export_status"])

    def test_scale_conversion(self):
        """【UT-METRIC-02: 指标数值量纲(Scale/单位美元)自适应缩放保真计算核验】

        1. 测试功能与测试点:
           - 验证指标量纲自适应缩放逻辑。
           - 将以百万为单位的输入改为实际单量美元 (scale=1, value=20,000,000)。
           - 验证计算结果依然保真等于 0.2，避免发生数量级错配。

        2. 正常函数业务边界与参数契约:
           - scale 支持任意合法正整数幂。

        3. 测试数据与模拟场景说明:
           - 动态变异首个财务事实的 value 与 scale。

        4. 预期断言与结果验证:
           - results[0].value == 0.2。
        """
        # 一个输入改为实际美元，结果仍应相同，不混淆百万金额。
        self.batch["facts"][0]["value"] = 20000000
        self.batch["facts"][0]["scale"] = 1
        self.assertAlmostEqual(run_batch(self.batch)["results"][0]["value"], .2)

    def test_real_local_company_is_blocked(self):
        """【FT-METRIC-03: 本地未审核真实企业标的(Intuit)全量计算指标物理阻断(status=blocked)】

        1. 测试功能与测试点:
           - 验证真实公司数据在未经正式多步审核前，系统拒绝直接计算发布。
           - 读取 Intuit 真实批次，断言 is_synthetic 为 False。
           - 断言全量指标计算状态均为 'blocked' 且数值为空 (None)。

        2. 正常函数业务边界与参数契约:
           - 未放行实体指标物理阻断。

        3. 测试数据与模拟场景说明:
           - examples/intu-metric-batch.blocked.json 真实阻断样本。

        4. 预期断言与结果验证:
           - is_synthetic 为 False。
           - 所有 row.status == 'blocked'，row.value is None。
        """
        batch = json.loads((ROOT / "examples/intu-metric-batch.blocked.json").read_text(encoding="utf-8"))
        report = run_batch(batch)
        self.assertFalse(report["is_synthetic"])
        self.assertTrue(all(row["status"] == "blocked" and row["value"] is None for row in report["results"]))

    def test_bad_fact_mutations_block_calculation(self):
        """【UT-METRIC-04: 财务事实字段(数值/单位/币种/会计基础等9项)变异防御性阻断拦截】

        1. 测试功能与测试点:
           - 验证 9 种财务事实异常变异注入拦截：
             1. value 为 None；
             2. value 为布尔型 True；
             3. value 为非数 NaN；
             4. unit 错配为 ratio；
             5. currency 错配为非美元 CNY；
             6. scale 为非法 0；
             7. entity_id 实体错配 OTHER；
             8. scope_id 范围错配 segment；
             9. accounting_basis 会计基础非标 adjusted。

        2. 正常函数业务边界与参数契约:
           - 任何字段变异必须被阻断，非数直接抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 深拷贝基准批次，对 facts[0] 遍历 9 种异常属性。

        4. 预期断言与结果验证:
           - 浮点数抛出 ValueError；其余返回 status == 'blocked'。
        """
        changes = [("value", None), ("value", True), ("value", float("nan")), ("unit", "ratio"),
                   ("currency", "CNY"), ("scale", 0), ("entity_id", "OTHER"),
                   ("scope_id", "segment"), ("accounting_basis", "adjusted")]
        for key, value in changes:
            with self.subTest(field=key, value=value):
                batch = copy.deepcopy(self.batch)
                batch["facts"][0][key] = value
                # 非有限 JSON 的整个请求不能生成可归档结果。
                if key == "value" and isinstance(value, float):
                    with self.assertRaises(ValueError):
                        run_batch(batch)
                else:
                    self.assertEqual(run_batch(batch)["results"][0]["status"], "blocked")

    def test_bad_source_mutations(self):
        """【UT-METRIC-05: 证据来源元数据(哈希/越界路径/时序倒置/空定位符等7项)变异拦截】

        1. 测试功能与测试点:
           - 验证 7 种证据来源违规注入拦截：
             1. sha256 损坏 ('bad')；
             2. path 路径穿越 ('../outside.txt')；
             3. kind 非法来源类型 ('secondary')；
             4. available_at 未来时间穿越 ('2027-01-01T00:00:00Z')；
             5. published_at 为空 (None)；
             6. excerpt 不存在伪造摘录；
             7. locator 定位符为空。

        2. 正常函数业务边界与参数契约:
           - 来源元数据不合规必须导致指标状态为 'blocked'。

        3. 测试数据与模拟场景说明:
           - 动态变异 facts[0]['source'] 各核心字段。

        4. 预期断言与结果验证:
           - run_batch(batch)['results'][0]['status'] == 'blocked'。
        """
        for key, value in [("sha256", "bad"), ("path", "../outside.txt"), ("kind", "secondary"),
                           ("available_at", "2027-01-01T00:00:00Z"), ("published_at", None),
                           ("excerpt", "不存在的摘录"), ("locator", "")]:
            with self.subTest(field=key):
                batch = copy.deepcopy(self.batch)
                batch["facts"][0]["source"][key] = value
                self.assertEqual(run_batch(batch)["results"][0]["status"], "blocked")

    def test_period_mismatch(self):
        """【UT-METRIC-06: 会计期间口径错配(TTM混用年度)计算阻断验证】

        1. 测试功能与测试点:
           - 验证不同会计期间口径（如以 TTM 替代年度 annual）时的刚性阻断。
           - 严禁不同期间口径直接混算。

        2. 正常函数业务边界与参数契约:
           - 期间基准 period.basis 必须精准对齐。

        3. 测试数据与模拟场景说明:
           - 将 facts[0]['period']['basis'] 篡改为 'ttm'。

        4. 预期断言与结果验证:
           - results[0].status == 'blocked'。
        """
        self.batch["facts"][0]["period"]["basis"] = "ttm"
        self.assertEqual(run_batch(self.batch)["results"][0]["status"], "blocked")

    def test_duplicate_fact_and_nonpositive_denominator(self):
        """【UT-METRIC-07: 重复财务事实注入与非正分母(分母为0)除零防御拦截】

        1. 测试功能与测试点:
           - 验证向输入批次注入重复事实项时的风控拦截。
           - 验证分母为 0 时的除零防御拦截。

        2. 正常函数业务边界与参数契约:
           - 输入事实 ID 唯一，分母必须为有限正数。

        3. 测试数据与模拟场景说明:
           - 场景 1: 追加重复事实 facts[0]；场景 2: 将分母 facts[1]['value'] 置为 0。

        4. 预期断言与结果验证:
           - 两种场景均返回 status == 'blocked'。
        """
        self.batch["facts"].append(copy.deepcopy(self.batch["facts"][0]))
        self.assertEqual(run_batch(self.batch)["results"][0]["status"], "blocked")
        self.batch["facts"].pop()
        self.batch["facts"][1]["value"] = 0
        self.assertEqual(run_batch(self.batch)["results"][0]["status"], "blocked")

    def test_other_industry_not_implicitly_supported(self):
        """【UT-METRIC-08: 未经审核非软件行业指标隐式支持拦截(跨行业安全隔离)】

        1. 测试功能与测试点:
           - 验证跨行业隐式映射拦截。
           - 将软件行业指标批次强行指定为其他行业 ID 时，系统拒绝静默放行。

        2. 正常函数业务边界与参数契约:
           - industry_id 必须与指标绑定的行业严格一致。

        3. 测试数据与模拟场景说明:
           - 选取非 software 的其他已登记行业。

        4. 预期断言与结果验证:
           - results[0].status == 'blocked'。
        """
        ids = [x.stem for x in (ROOT / "knowledge/contracts/industries").glob("*.json") if x.stem != "software"]
        self.batch["industry_id"] = ids[0]
        self.assertEqual(run_batch(self.batch)["results"][0]["status"], "blocked")

    def test_full_coverage_is_truthful(self):
        """【FT-METRIC-09: 146个指标与41个行业全量覆盖真实性/统计验证状态对账】

        1. 测试功能与测试点:
           - 验证 metric-execution-coverage.json 与知识库指标目录 100% 集合恒等。
           - 验证指标总数严格为 146 项。
           - 验证行业总数严格为 41 个。
           - 验证 software 绑定指标与代码常量 BINDINGS 严格一致。
           - 验证未完成统计校准的指标状态真实声明为 'not_validated'。

        2. 正常函数业务边界与参数契约:
           - 底账与元数据无孤立无死项。

        3. 测试数据与模拟场景说明:
           - 读取项目底层覆盖清单与指标 catalog。

        4. 预期断言与结果验证:
           - 指标集合恒等，指标数 146，行业数 41，绑定与常量一致，状态均为 not_validated。
        """
        coverage = json.loads((ROOT / "knowledge/contracts/metric-execution-coverage.json").read_text(encoding="utf-8"))
        catalog = json.loads((ROOT / "knowledge/metrics/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual({x["metric_id"] for x in coverage["metrics"]}, {x["id"] for x in catalog["metrics"]})
        self.assertEqual(len(coverage["metrics"]), 146)
        self.assertEqual(len(coverage["industries"]), 41)
        bound = {x["metric_id"] for x in coverage["metrics"] if x["execution_status"] == "bound_for_software"}
        self.assertEqual(bound, set(BINDINGS))
        self.assertTrue(all(x["statistical_validation_status"] == "not_validated" for x in coverage["metrics"]))

    def test_schema_and_dictionary_match(self):
        """【FT-METRIC-10: 指标批输入Schema与数据字典文档(10a)属性定义100%对齐】

        1. 测试功能与测试点:
           - 验证 metric-batch.schema.json 元模式合法性并校验合成批次数据。
           - 验证数据字典索引 docs/10a-指标批输入数据字典.md 包含所有子定义。
           - 验证每个子定义文档严格包含字段、标题与描述说明。

        2. 正常函数业务边界与参数契约:
           - Schema 校验与文档双向互验。

        3. 测试数据与模拟场景说明:
           - 解析 JSON Schema 与 docs/metric-batch-dictionary/*.md。

        4. 预期断言与结果验证:
           - structural 校验通过。
           - 字段名、title 与 description 100% 存在于文档中。
        """
        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_research import structural, check_schema
        schema = json.loads((ROOT / "schemas/metric-batch.schema.json").read_text(encoding="utf-8"))
        check_schema(schema, schema)
        structural(self.batch, schema, schema)
        index = (ROOT / "docs/10a-指标批输入数据字典.md").read_text(encoding="utf-8")
        for name, node in [("batch", schema), *schema["$defs"].items()]:
            self.assertIn(f"metric-batch-dictionary/{name}.md", index)
            text = (ROOT / f"docs/metric-batch-dictionary/{name}.md").read_text(encoding="utf-8")
            for key, definition in node["properties"].items():
                self.assertIn(f"| {key} | {definition['title']} |", text)
                self.assertIn(definition["description"], text)
        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_research import structural, check_schema
        schema = json.loads((ROOT / "schemas/metric-batch.schema.json").read_text(encoding="utf-8"))
        check_schema(schema, schema)
        structural(self.batch, schema, schema)
        index = (ROOT / "docs/10a-指标批输入数据字典.md").read_text(encoding="utf-8")
        for name, node in [("batch", schema), *schema["$defs"].items()]:
            self.assertIn(f"metric-batch-dictionary/{name}.md", index)
            text = (ROOT / f"docs/metric-batch-dictionary/{name}.md").read_text(encoding="utf-8")
            for key, definition in node["properties"].items():
                self.assertIn(f"| {key} | {definition['title']} |", text)
                self.assertIn(definition["description"], text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
