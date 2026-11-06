"""确认正式 Schema 的业务字段都有说明且元数据无漂移。"""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(schema, pointer):
    node = schema
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def collect_schema_fields(node, schema_file, actual_fields, pointer="#"):
    if not isinstance(node, dict):
        return
    if "properties" in node:
        for key, child in node["properties"].items():
            child_pointer = pointer + "/properties/" + key
            actual_fields[(schema_file, child_pointer)] = (child, key in node.get("required", []))
    for key, value in node.items():
        if key in {"if", "then", "allOf", "description", "title", "enum", "const"}:
            continue
        if isinstance(value, dict):
            for name, child in value.items():
                if isinstance(child, dict):
                    collect_schema_fields(child, schema_file, actual_fields, pointer + "/" + key + "/" + name)
            if key == "items":
                collect_schema_fields(value, schema_file, actual_fields, pointer + "/items")
        elif isinstance(value, list) and key in ("anyOf", "prefixItems"):
            for index, child in enumerate(value):
                collect_schema_fields(child, schema_file, actual_fields, pointer + "/" + key + "/" + str(index))


class SchemaManualTests(unittest.TestCase):
    """Schema逐字段数据字典、元数据防漂移与规范说明书核验测试类。"""

    def setUp(self):
        self.guide = load(ROOT / "schemas/schema-field-guide.json")
        self.meaning_source = load(ROOT / "schemas/schema-field-meanings.json")
        self.name_source = load(ROOT / "schemas/schema-field-names.json")

    def test_metadata_versions_and_sources_alignment(self):
        """【FT-SCHEMA-01: Schema字段指南/中文名称源/释义源版本与元数据100%对齐断言】

        1. 测试功能与测试点:
           - 验证 schema-field-guide.json, schema-field-meanings.json, schema-field-names.json 三大元数据文件。
           - 验证文档版本 (document_version) 与 schema_version 严格对齐。
           - 验证全部中文名称集合与指南字段 100% 集合恒等（无未翻译遗漏，无过期废弃字段）。
           - 验证全部业务释义集合与指南字段 100% 集合恒等。

        2. 正常函数业务边界与参数契约:
           - 三方配置文件结构合法且版本字符串一致。

        3. 测试数据与模拟场景说明:
           - schemas/ 下登记的元数据基准文件。

        4. 预期断言与结果验证:
           - document_version == guide_version。
           - set(names_zh) == set(fields)。
           - set(meanings) == set(fields)。
        """
        self.assertEqual(self.name_source["document_version"], self.guide["guide_version"])
        self.assertEqual(self.name_source["schema_version"], self.guide["schema_version"])
        self.assertEqual(
            set(self.name_source["names_zh"]),
            {row["field"] for row in self.guide["fields"]},
            "中文名称未完整覆盖字段或含过期字段",
        )
        self.assertEqual(self.meaning_source["schema_version"], self.guide["schema_version"])
        self.assertEqual(self.meaning_source["document_version"], self.guide["guide_version"])
        self.assertEqual(
            set(self.meaning_source["meanings"]),
            {row["field"] for row in self.guide["fields"]},
            "业务释义源遗漏字段或含过期字段",
        )

    def test_actual_schema_property_collection_and_coverage(self):
        """【UT-SCHEMA-02: 实际Schema(research/source-manifest)属性与指南字段1:1集合恒等闭环】

        1. 测试功能与测试点:
           - 遍历收集 research.schema.json 与 source-manifest.schema.json 的所有属性节点。
           - 验证指南中收录的字段文档与实际 Schema 遍历出的属性键值集合 1:1 恒等对齐。
           - 验证指南收录字段无重复项。

        2. 正常函数业务边界与参数契约:
           - JSON Schema 对象遍历无越界无死循环。

        3. 测试数据与模拟场景说明:
           - schemas/research.schema.json 与 schemas/source-manifest.schema.json。

        4. 预期断言与结果验证:
           - len(documented) == len(guide['fields'])。
           - set(documented) == set(actual_fields)。
        """
        actual_fields = {}
        schemas = {}
        for name, path in (("research", "schemas/research.schema.json"), ("source_manifest", "schemas/source-manifest.schema.json")):
            schema = load(ROOT / path)
            schemas[path] = schema
            version = schema["properties"]["schema_version"]
            self.assertIn(self.guide["schema_version"], version.get("enum", [version.get("const")]))
            collect_schema_fields(schema, path, actual_fields)

        documented = {(row["schema_file"], row["schema_pointer"]): row for row in self.guide["fields"]}
        self.assertEqual(len(documented), len(self.guide["fields"]), "字段说明重复")
        self.assertEqual(set(documented), set(actual_fields), "字段说明未完整覆盖实际 Schema")

    def test_dictionary_tables_and_chinese_names_invariance(self):
        """【FT-SCHEMA-03: 数据字典单表文档中文名称/精确指针与JSON片段同步性核验】

        1. 测试功能与测试点:
           - 遍历 docs/schema-dictionary/ 下全部单表 Markdown 文档。
           - 验证单表包含“中文名称”列，且每个字段名称均包含有效中文字符。
           - 验证字段名称与 names_zh 严格一致，精确指针 pointer 正确嵌入。
           - 验证 Markdown 文档中内嵌的 ```json 片段与 Schema 真实定义节点完全对齐。
           - 验证 docs/05a-Schema逐字段数据字典.md 统一目录收录全部单表。

        2. 正常函数业务边界与参数契约:
           - 路径在 docs/schema-dictionary 内，不可越界。

        3. 测试数据与模拟场景说明:
           - docs/schema-dictionary/*.md 与 schemas/*.json。

        4. 预期断言与结果验证:
           - table_files 集合严格恒等于目录内全部 Markdown。
           - 字段结构、必填状态、可空性、约束条件 100% 对齐。
        """
        actual_fields = {}
        schemas = {}
        for name, path in (("research", "schemas/research.schema.json"), ("source_manifest", "schemas/source-manifest.schema.json")):
            schema = load(ROOT / path)
            schemas[path] = schema
            collect_schema_fields(schema, path, actual_fields)

        documented = {(row["schema_file"], row["schema_pointer"]): row for row in self.guide["fields"]}
        manual = (ROOT / "docs/05a-Schema逐字段数据字典.md").read_text(encoding="utf-8")
        table_files = set()

        for key, row in documented.items():
            table_path = (ROOT / row["documentation_file"]).resolve()
            self.assertTrue(table_path.is_relative_to((ROOT / "docs/schema-dictionary").resolve()), "单表说明越界")
            table_files.add(table_path)
            table = table_path.read_text(encoding="utf-8")
            self.assertIn("| 中文名称 |", table, "单表遗漏中文名称列")
            self.assertEqual(row["name_zh"], self.name_source["names_zh"][row["field"]])
            self.assertTrue(any("一" <= char <= "鿿" for char in row["name_zh"]), "字段名称缺少中文")
            self.assertIn(f"| `{row['field']}` | {row['name_zh']} |", table, "名称未显示在对应字段行")
            self.assertIn(f"schema-dictionary/{table_path.name}", manual, "目录未收录单表")
            self.assertIn("[返回统一目录](../05a-Schema逐字段数据字典.md)", table)

            node, required = actual_fields[key]
            self.assertEqual(resolve(schemas[key[0]], key[1]), node)
            self.assertEqual(row["structural_schema"], node, "精确结构定义与实际 Schema 不一致")
            self.assertEqual(row["required"], required)
            self.assertEqual(row["nullable"], any(s.get("type") == "null" for s in node.get("anyOf", [])))
            if "$ref" in node:
                self.assertEqual(row["type"], node["$ref"].split("/")[-1])
            elif "const" in node:
                self.assertIn(str(node["const"]), row["type"])
            elif "enum" in node:
                self.assertTrue("枚举" in row["type"] and str(node["enum"]) in row["constraints"])
            elif "type" in node:
                kind = node["type"]
                self.assertTrue(row["type"].startswith(" / ".join(kind) if isinstance(kind, list) else kind))

            for constraint, label in (
                ("minimum", "最小"),
                ("maximum", "最大"),
                ("minItems", "至少项数"),
                ("maxItems", "最多项数"),
                ("minLength", "最短字符"),
                ("format", "格式"),
            ):
                if constraint in node:
                    self.assertIn(f"{label}={node[constraint]}", row["constraints"])

            self.assertTrue(row["description"].strip())
            self.assertEqual(row["description"], self.meaning_source["meanings"][row["field"]], "字段释义与独立维护源不一致")
            self.assertTrue(f"`{row['field']}`" in table and row["description"] in table)
            self.assertIn(f"`{row['schema_pointer']}`", table, "单表遗漏精确字段指针")

            chunks = re.findall(r"```json\n(.*?)\n```", table, re.S)
            self.assertIn(node, [json.loads(chunk) for chunk in chunks], "单表精确结构未同步")

        self.assertEqual(table_files, set((ROOT / "docs/schema-dictionary").glob("*.md")), "存在未收录的单表文件")
        self.assertNotIn("## 2. 字段表", manual, "统一目录仍混入字段表")

    def test_schema_rules_index_and_spec_identifiers(self):
        """【FT-SCHEMA-04: 规范文档标准编号(SY-SPEC/SY-DD/SY-RULE)与28项强规则索引完备性对账】

        1. 测试功能与测试点:
           - 验证 docs/05-Schema配套说明书.md 包含统一规范标识 SY-SPEC-001。
           - 验证 docs/05a-Schema逐字段数据字典.md 包含统一标识 SY-DD-001。
           - 验证 docs/05b-Schema规则索引.md 包含统一标识 SY-RULE-001。
           - 验证当前基准版本号均为 1.5.0。
           - 验证规则索引中提取的规则 ID（STR, REF, LOC, TIME, OBS, CALC, FLOW, VAL, DEC, INV, GOV, MAN, DQ）无重复且恰好为 28 项。

        2. 正常函数业务边界与参数契约:
           - 正则匹配所有规则表格项。

        3. 测试数据与模拟场景说明:
           - docs/05*.md 说明书与规则索引文档。

        4. 预期断言与结果验证:
           - 规范编号存在，版本号对齐，规则总数严格为 28 项无重复。
        """
        manual = (ROOT / "docs/05a-Schema逐字段数据字典.md").read_text(encoding="utf-8")
        spec = (ROOT / "docs/05-Schema配套说明书.md").read_text(encoding="utf-8")
        rules = (ROOT / "docs/05b-Schema规则索引.md").read_text(encoding="utf-8")

        self.assertIn("SY-SPEC-001", spec)
        self.assertIn("SY-DD-001", manual)
        self.assertIn("SY-RULE-001", rules)
        self.assertIn("1.5.0", manual)
        self.assertEqual(self.guide["guide_version"], "1.5.0")

        rule_ids = re.findall(
            r"^\| ((?:STR|REF|LOC|TIME|OBS|CALC|FLOW|VAL|DEC|INV|GOV|MAN|DQ)-\d{3}) \|",
            rules,
            re.M,
        )
        self.assertEqual(len(rule_ids), len(set(rule_ids)), "规则编号存在重复")
        self.assertEqual(len(rule_ids), 28, "规则编号缺失，必须严格为 28 项")


def main():
    """兼容历史直接调用契约输出。"""
    suite = unittest.TestLoader().loadTestsFromTestCase(SchemaManualTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    table_files_count = len(list((ROOT / "docs/schema-dictionary").glob("*.md")))
    guide = load(ROOT / "schemas/schema-field-guide.json")
    print(
        f"PASS: {table_files_count} indexed table files and {len(guide['fields'])} business property definitions independently checked against 2 schemas."
    )


if __name__ == "__main__":
    main()
