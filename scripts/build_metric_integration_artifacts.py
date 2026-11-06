"""生成覆盖清单和接入样板；合成数字明确标注，不从二次报告补造原始数据。"""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finance_tools.metric_pipeline import BINDINGS


def save(relative, content):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    # 新输入契约保留中文标题与业务说明，可生成独立字段表。
    def field(kind, title, description, **extra):
        return dict(type=kind, title=title, description=description, **extra)
    def obj(properties, title):
        return {"type": "object", "title": title, "properties": properties,
                "required": list(properties), "additionalProperties": False}
    source_schema = obj({
        "path": field("string", "来源路径", "项目内 UTF-8 文本相对路径；不能指向项目外"),
        "sha256": field("string", "来源内容摘要", "原文件字节 SHA-256，运行时比对", pattern="^[a-f0-9]{64}$"),
        "locator": field("string", "来源定位", "页码、表名或行号，不仅记录文件名", minLength=1),
        "excerpt": field("string", "原文摘录", "需要在本地文本中逐字找到；不自动证明数值含义", minLength=1),
        "kind": field("string", "来源类型", "真实数据仅 primary，合成数据仅 synthetic", enum=["primary", "secondary", "synthetic"]),
        "published_at": field(["string", "null"], "发布时间", "精确来源发布时间；1.1.0 未核实时填 null，不补造时刻", format="date-time"),
        "available_at": field("string", "可得时间", "带时区，不得晚于研究时点", format="date-time")}, "输入来源")
    period_schema = obj({
        "start": field("string", "期间起日", "财务统计期间开始", format="date"),
        "end": field("string", "期间止日", "财务统计期间结束", format="date"),
        "basis": field("string", "期间口径", "季度、年度或滚动十二个月", enum=["quarter", "annual", "ttm"])}, "财务期间")
    fact_schema = obj({
        "id": field("string", "原始事实标识", "批内原始事实 ID，不是正式研究 observation ID", minLength=1),
        "field": field("string", "原始字段代码", "执行绑定规定的输入字段", minLength=1),
        "entity_id": field("string", "公司标识", "必须与请求公司一致", minLength=1),
        "scope_id": field("string", "业务范围标识", "合并或指定分部，禁止混用", minLength=1),
        "period": {"$ref": "#/$defs/period", "title": "财务期间", "description": "分子分母需完全匹配"},
        "accounting_basis": field("string", "会计口径", "本批仅支持 GAAP", enum=["GAAP"]),
        "value": field("number", "金额数值", "有限实际数值，不自动填零"),
        "unit": field("string", "量纲", "本批分子分母均为金额", enum=["currency"]),
        "currency": field("string", "币种", "三位大写 ASCII 代码", pattern="^[A-Z]{3}$"),
        "scale": field("number", "金额尺度乘数", "如百万美元填 1000000；统一为基础货币单位后计算", minimum=0),
        "source": {"$ref": "#/$defs/source", "title": "来源与时点", "description": "定位、内容及可得时间"}}, "原始输入事实")
    schema = obj({
        "schema_version": {"enum": ["1.0.0", "1.1.0"], "title": "请求契约版本", "description": "1.1.0 支持未知精确发布时间；可得时间仍必填"},
        "entity_id": field("string", "公司标识", "本批同一公司", minLength=1),
        "scope_id": field("string", "业务范围标识", "本批统一合并或分部范围", minLength=1),
        "industry_id": field("string", "行业标识", "须在项目行业契约中存在", minLength=1),
        "currency": field("string", "批币种", "全部输入同币种，不自动兑换", pattern="^[A-Z]{3}$"),
        "as_of": field("string", "研究时点", "禁止使用晚于此时点可得的资料", format="date-time"),
        "is_synthetic": field("boolean", "是否合成数据", "合成结果不能替代真实公司研究"),
        "facts": field("array", "原始事实列表", "真实缺失时允许为空；对应指标阻断", items={"$ref": "#/$defs/fact"}),
        "requests": field("array", "请求指标列表", "现有指标 ID，不自动计算全部指标", items={"type": "string", "minLength": 1}, minItems=1, uniqueItems=True)}, "行业指标批输入")
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:shuiyuan:metric-batch:1.1.0",
                   "$defs": {"fact": fact_schema, "period": period_schema, "source": source_schema}})
    save("schemas/metric-batch.schema.json", schema)
    lines = ["# 指标批输入数据字典统一目录", "", "契约版本：1.1.0，兼容 1.0.0。1.1.0 允许精确发布时间未知；结构与执行语义共同校验。", "", "[功能设计](10-指标计算接入与行业样板.md)", ""]
    dictionary = ROOT / "docs/metric-batch-dictionary"
    dictionary.mkdir(parents=True, exist_ok=True)
    for name, node in [("batch", schema), *schema["$defs"].items()]:
        lines.append(f"- [{name} · {node['title']}](metric-batch-dictionary/{name}.md)")
        table = [f"# {name} · {node['title']}", "", "[返回统一目录](../10a-指标批输入数据字典.md)", "", "全部字段必填；仅 1.1.0 的 source.published_at 允许 null。禁止额外字段。scale 必须大于零，由执行语义校验补充。", "", "| 字段 | 中文名称 | 类型/引用 | 业务含义 |", "| --- | --- | --- | --- |"]
        for key, definition in node["properties"].items():
            kind = definition.get("type", definition.get("$ref", "const"))
            table.append(f"| {key} | {definition['title']} | {kind} | {definition['description']} |")
        table += ["", "## 精确结构", "", "```json", json.dumps(node, ensure_ascii=False, indent=2), "```", ""]
        (dictionary / f"{name}.md").write_text("\n".join(table), encoding="utf-8")
    (ROOT / "docs/10a-指标批输入数据字典.md").write_text("\n".join(lines), encoding="utf-8")
    definitions = json.loads((ROOT / "knowledge/contracts/metric-definitions.json").read_text(encoding="utf-8"))["definitions"]
    metrics = []
    for item in definitions:
        binding = BINDINGS.get(item["metric_id"])
        metrics.append({"metric_id": item["metric_id"], "name_zh": item["name_zh"],
                        "design_definition_status": item["definition_status"],
                        "execution_status": "bound_for_software" if binding else "unbound",
                        "binding": binding, "statistical_validation_status": "not_validated"})
    industries = []
    for path in sorted((ROOT / "knowledge/contracts/industries").glob("*.json")):
        profile = json.loads(path.read_text(encoding="utf-8"))
        industries.append({"industry_id": profile["industry_id"], "name_zh": profile["name_zh"],
                           "required_driver_ids": profile["required_metric_ids"],
                           "shared_binding_ids": list(BINDINGS) if profile["industry_id"] == "software" else [],
                           "driver_execution_status": "blocked_pending_definition_and_inputs"})
    save("knowledge/contracts/metric-execution-coverage.json", {"schema_version": "1.0.0", "metrics": metrics, "industries": industries})
    source_path = "examples/support/software-financials.synthetic.txt"
    (ROOT / source_path).write_text("合成财务样板，不能支持真实交易。\n2025 年营业利润 20，收入 100，普通股净利润 10，平均普通股权益 50；单位百万 USD。\n", encoding="utf-8")
    data = (ROOT / source_path).read_bytes()
    excerpt = data.decode("utf-8").splitlines()[1]
    source = {"path": source_path, "sha256": hashlib.sha256(data).hexdigest(), "locator": "第 2 行",
              "excerpt": excerpt, "kind": "synthetic", "published_at": "2026-02-01T00:00:00Z", "available_at": "2026-02-01T00:00:00Z"}
    facts = [{"id": f"raw-{field}", "field": field, "entity_id": "synthetic_software", "scope_id": "consolidated",
              "period": {"start": "2025-01-01", "end": "2025-12-31", "basis": "annual"},
              "accounting_basis": "GAAP", "value": value, "unit": "currency", "currency": "USD", "scale": 1000000,
              "source": dict(source)} for field, value in [("operating_income", 20), ("revenue", 100),
                                                          ("common_net_income", 10), ("average_common_equity", 50)]]
    shared = {"schema_version": "1.0.0", "entity_id": "synthetic_software", "scope_id": "consolidated",
              "industry_id": "software", "currency": "USD", "as_of": "2026-03-01T00:00:00Z",
              "is_synthetic": True, "facts": facts, "requests": ["operating_margin", "roe", "software_driver_1", "software_driver_2", "software_driver_3"]}
    save("examples/software-metric-batch.synthetic.json", shared)
    # 本地 INTU 报告只提供二次分析，缺少分子分母及原始财报，明确传空事实。
    real = dict(shared, entity_id="INTU", as_of="2026-10-11T00:00:00Z", is_synthetic=False, facts=[])
    save("examples/intu-metric-batch.blocked.json", real)
    report_path = "knowledge/sources/cat_reference/intu_research.txt"
    save("knowledge/contracts/intu-source-readiness.json", {
        "entity_id": "INTU", "source_path": report_path,
        "source_sha256": hashlib.sha256((ROOT / report_path).read_bytes()).hexdigest(),
        "source_kind": "secondary", "status": "insufficient_evidence",
        "limitations": ["二次分析报告不能替代原始财报", "缺少经核对的普通股净利润、平均权益及同期间营业利润/收入",
                        "报告分析日期不等于财报发布时间或历史可得时间", "在线生态可能与正式分部交叉，不可直接合计"],
        "required_next_inputs": ["项目内原始财报或已核对文本", "逐项可得时间、单位尺度与原文定位", "软件订阅/用量及留存驱动口径"]})
    print(f"覆盖 {len(metrics)} 个指标、{len(industries)} 个行业；绑定 {len(BINDINGS)} 个软件共享指标")


if __name__ == "__main__":
    main()
