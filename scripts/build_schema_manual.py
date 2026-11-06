"""按实际 Schema 生成完整字段说明；缺说明或字段漂移时失败。只用项目内文件。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIELD_MEANINGS = json.loads((ROOT / 'schemas/schema-field-meanings.json').read_text(encoding='utf-8'))['meanings']
FIELD_NAMES = json.loads((ROOT / 'schemas/schema-field-names.json').read_text(encoding='utf-8'))['names_zh']

def label(schema):
    if isinstance(schema, bool):
        return "允许任意值" if schema else "不允许额外项"
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "anyOf" in schema:
        return " / ".join(label(s) for s in schema["anyOf"])
    if "const" in schema:
        return "固定值 " + str(schema["const"])
    if "enum" in schema:
        return "枚举"
    if schema.get("type") == "array":
        if "prefixItems" in schema:
            return "array<" + ", ".join(label(s) for s in schema["prefixItems"]) + ">"
        return "array<" + label(schema.get("items", {})) + ">"
    kind=schema.get('type','限定结构')
    return ' / '.join(kind) if isinstance(kind,list) else kind

def constraints(schema):
    parts = []
    for key, cn in (("enum", "枚举"), ("const", "固定"), ("minimum", "最小"), ("maximum", "最大"),
                    ("minItems", "至少项数"), ("maxItems", "最多项数"), ("minLength", "最短字符"), ("format", "格式")):
        if key in schema:
            parts.append(f"{cn}={schema[key]}")
    if schema.get("uniqueItems"):
        parts.append("项不能重复")
    if schema.get("additionalProperties") is False:
        parts.append("不接受额外字段")
    if "pattern" in schema:
        parts.append("正则限定；本地路径另做真实路径检查")
    if "anyOf" in schema:
        for child in schema["anyOf"]:
            text = constraints(child)
            if text:
                parts.append(text)
    if "$ref" in schema:
        parts.append("引用=" + schema["$ref"])
    return "；".join(parts) or "无显式附加结构约束"

def properties(node, logical, pointer):
    rows = []
    required = node.get("required", [])
    for key, child in node.get("properties", {}).items():
        path = f'{logical}.{key}'
        if path not in FIELD_MEANINGS:
            raise ValueError(f'字段缺少独立业务释义：{path}')
        description = FIELD_MEANINGS[path]
        if path not in FIELD_NAMES or not FIELD_NAMES[path].strip():
            raise ValueError(f'字段缺少中文名称：{path}')
        rows.append({"field": path, "name_zh": FIELD_NAMES[path], "schema_pointer": f"{pointer}/properties/{key}", "type": label(child),
            "required": key in required, "nullable": any(s.get("type") == "null" for s in child.get("anyOf", [])),
            "constraints": constraints(child), "description": description,
            "structural_schema": child})
        rows.extend(properties(child, path, f"{pointer}/properties/{key}"))
        if isinstance(child.get("items"), dict):
            rows.extend(properties(child["items"], path+"[]", f"{pointer}/properties/{key}/items"))
        for i, variant in enumerate(child.get("anyOf", [])):
            rows.extend(properties(variant, path, f"{pointer}/properties/{key}/anyOf/{i}"))
    return rows

def generate():
    documents = [("research", "schemas/research.schema.json"), ("source_manifest", "schemas/source-manifest.schema.json")]
    all_rows = []
    index = []
    output_dir = ROOT / "docs/schema-dictionary"
    output_dir.mkdir(parents=True, exist_ok=True)
    for document, path in documents:
        schema = json.loads((ROOT/path).read_text(encoding="utf-8"))
        groups = [(document, schema, "#")] + [(name, node, "#/$defs/"+name) for name, node in schema.get("$defs", {}).items()]
        for logical, node, pointer in groups:
            rows = properties(node, logical, pointer)
            if not rows:
                continue
            sections = []
            group_id = f"OBJ-{len(index)+1:03d}"
            filename = f"{document}--{logical}.md"
            doc_file = "docs/schema-dictionary/" + filename
            index.append(f"| {group_id} | [{logical}](schema-dictionary/{filename}) | `{path}` | `{pointer}` | {len(rows)} |")
            references = []
            def find_refs(value, location="#"):
                if isinstance(value, dict):
                    if value.get("$ref") == pointer:
                        references.append(location)
                    for k, v in value.items():
                        find_refs(v, location+"/"+k)
                elif isinstance(value, list):
                    for i, v in enumerate(value):
                        find_refs(v, location+"/"+str(i))
            if pointer != "#":
                find_refs(schema)
            usage = "根对象" if pointer == "#" else "；".join(f"`{r}`" for r in references) or "内联对象"
            sections.append(f"# {group_id} · {logical} 单表说明\n\n文档版本：1.5.0；契约版本：1.1.0，兼容 1.0.0。\n\n[返回统一目录](../05a-Schema逐字段数据字典.md) · [配套说明书](../05-Schema配套说明书.md) · [规则索引](../05b-Schema规则索引.md)\n\n## 1. 对象定义\n\n- 所属契约：[{path}](../../{path})。\n- 定义位置：`{pointer}`。\n- 引用位置（Schema 指针）：{usage}。\n- 对象额外字段：{'禁止' if node.get('additionalProperties') is False else '由各内联对象定义决定'}。\n- 属性定义数：{len(rows)}（含当前表所属内联对象属性，不含引用对象的展开属性）。\n\n字段标识用于定位定义，不能直接当作实例路径。必填按所属对象解释；结构约束与跨字段规则应同时满足。\n\n## 2. 字段表\n\n| 定义字段标识 | 中文名称 | JSON 类型／引用对象 | 必填 | 允许 null | 结构约束摘要 | 业务含义与填写说明 |\n|---|---|---|---|---|---|---|\n")
            for row in rows:
                all_rows.append({"schema_file": path, "documentation_file": doc_file, **row})
                conditional=row['field'] in {'evidence.published_date','evidence.publication_precision','source_manifest.published_date','source_manifest.publication_precision'}
                required='1.1.0 必须' if conditional else '是' if row['required'] else '否'
                values = [f"`{row['field']}`", row['name_zh'], row["type"], required, "是" if row["nullable"] else "否", row["constraints"], row["description"]]
                sections.append("| " + " | ".join(v.replace("|", "\\|").replace("\n", " ") for v in values) + " |\n")
            sections.append("\n")
            related = sorted({ref.split('/')[-1] for row in rows for ref in _refs(row['structural_schema'])})
            sections.append("## 3. 关联对象\n\n")
            if related:
                sections.extend(f"- [{name}]({document}--{name}.md)：本表引用的公共对象定义。\n" for name in related if properties(schema.get('$defs', {}).get(name, {}), name, '#/$defs/'+name))
            else:
                sections.append("本表未引用其他公共对象。\n")
            sections.append("\n## 4. 精确结构定义\n\n以下逐字段保留分支、枚举、引用、数组成员和正则；摘要不能替代该定义。跨字段约束见规则索引。\n\n")
            for row in rows:
                sections.append(f"<details>\n<summary>{row['field']} · {row['name_zh']}</summary>\n\nSchema 指针：`{row['schema_pointer']}`。\n\n```json\n"+json.dumps(row["structural_schema"], ensure_ascii=False, indent=2)+"\n```\n\n</details>\n\n")
            (output_dir/filename).write_text(''.join(sections), encoding='utf-8')
    guide = {"guide_version": "1.5.0", "schema_version": "1.1.0", "fields": all_rows}
    (ROOT/"schemas/schema-field-guide.json").write_text(json.dumps(guide, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    intro = """# Schema 数据字典统一目录

| 文档属性 | 值 |
|---|---|
| 文档编号 | SY-DD-001 |
| 文档版本 | 1.5.0 |
| 契约版本 | 1.1.0，兼容 1.0.0 |
| 状态 | 项目内部规范；不代表外部标准认证 |
| 生成方式 | 从两份正式 Schema 提取结构；业务释义按完整字段标识由 schema-field-meanings.json 独立维护 |
| 覆盖口径 | 属性定义计数；条件分支中的重复声明不重复计数 |

操作说明见 [Schema 配套说明书](05-Schema配套说明书.md)，跨字段约束见 [规则索引](05b-Schema规则索引.md)。机器可读说明见 [字段指南](../schemas/schema-field-guide.json)，业务释义维护源见 [逐字段释义](../schemas/schema-field-meanings.json)，本次修正依据见 [业务释义核对记录](05c-数据字典业务释义核对记录.md)。

## 阅读约定

各字段的中文名称由 [中文名称维护源](../schemas/schema-field-names.json)按完整字段标识独立维护，机器可读字典使用 `name_zh` 属性。中文名称是阅读标签，JSON 实例仍使用原有英文属性键；同名英文属性在不同业务对象中可有不同中文名称。

本文件仅维护统一目录及阅读约定。每个对象表在 `schema-dictionary/` 中独立成文，包含对象定义、字段表、关联对象和精确结构定义。下面的对象名均可点击进入单表说明；每个单表都有返回目录的入口。这里的“表”指 Schema 对象字段表，不意味着新增数据库物理表。

“定义字段标识”是对象定义名加属性名，**不是可以直接复制使用的实例 JSON 路径**。例如 `observation.value` 对应实例 `$.observations[0].value`，`step2_output.checks` 对应 `$.steps[1].output.checks`。精确 Schema 指针定位规范定义，不定位实例数据或原文证据。

JSON 类型保留 string、integer、number、boolean、object、array、null；枚举与固定值的实际类型由精确结构定义中的值确定。引用对象名表示必须展开相应定义，不是新增 JSON 类型。

必填、可空、空数组是三个独立维度。本字典不推断默认值，也不要求所有复用对象同时实例化。业务说明中的示例、建议和项目默认范围不是新增结构约束。

“必须出现”按所属对象解释，不表示该对象在任何状态都要实例化。允许 null 的必填字段也必须写出键；例如 pending 步骤 output=null。数组允许空与 null 是不同含义。所有当前定义对象禁止额外字段。

表中约束是结构约束；证据引用、未来信息、单位、状态、概率、来源绑定和历史版本等跨字段规则另由校验器检查。相同对象通过 $ref 复用时参考其独立表。定义对象不另复制到 research 顶层。

内联对象的字段用点号/[] 表示数据路径；schema_pointer 为精确 Schema 位置，不是原文证据 locator。

"""
    contents = "## 对象索引\n\n| 对象编号 | 定义名 | 契约文件 | 定义指针 | 属性数 |\n|---|---|---|---|---|\n"+"\n".join(index)+"\n\n"
    (ROOT/"docs/05a-Schema逐字段数据字典.md").write_text(intro+contents, encoding="utf-8")
    print(f"Wrote field dictionary: {len(index)} individual tables, {len(all_rows)} property definitions, 2 schemas.")

def _refs(node):
    if isinstance(node, dict):
        if '$ref' in node:
            yield node['$ref']
        for value in node.values():
            yield from _refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _refs(value)

if __name__ == "__main__":
    generate()
