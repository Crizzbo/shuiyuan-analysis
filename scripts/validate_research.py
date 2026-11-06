"""离线校验六步研究。仅实现本项目 Schema 使用的关键字；不是通用 JSON Schema 引擎。"""
import argparse
import json
import math
import re
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import sys

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from validate_knowledge_structure import ROOT, local_file

GATES = {
    "S1": ["classification", "cycle_dimensions", "evidence_traceable"],
    "S2": ["mandatory_checks", "counterevidence", "financial_comparability"],
    "S3": ["transmission", "monitoring", "invalidation_conditions"],
    "S4": ["model_applicability", "scenario_calculations", "crosscheck", "sensitivity", "value_bridge"],
    "S5": ["permanent_loss", "action_conditions", "portfolio_scope", "decision_evidence"],
    "S6": ["monitoring_schedule", "rerun_triggers", "review_plan"],
}
SUPPORTED = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "properties", "required",
    "additionalProperties", "items", "prefixItems", "minItems", "maxItems", "uniqueItems", "minLength",
    "minimum", "maximum", "pattern", "format", "const", "enum", "anyOf", "allOf", "if", "then"}

class ValidationError(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise ValidationError(message)

def load(path):
    def pairs(values):
        result = {}
        for key, value in values:
            need(key not in result, f"重复 JSON 键：{key}")
            result[key] = value
        return result
    def bad(value):
        raise ValidationError(f"禁止非有限 JSON 数字：{value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=bad)

def instant(value):
    need(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value), "日期时间须含时区")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"无效日期时间：{value}") from exc

def check_schema(node, root):
    if isinstance(node, bool):
        return
    need(isinstance(node, dict), "Schema 必须为对象/布尔值")
    need(not set(node) - SUPPORTED, f"离线校验器不支持：{set(node)-SUPPORTED}")
    if "$ref" in node:
        need(node["$ref"].startswith("#/$defs/"), "Schema 只允许当前文件内部 $ref")
        need(node["$ref"].split("/")[-1] in root["$defs"], "Schema 引用不存在")
    for key in ("properties", "$defs"):
        for child in node.get(key, {}).values():
            check_schema(child, root)
    for key in ("anyOf", "allOf", "prefixItems"):
        for child in node.get(key, []):
            check_schema(child, root)
    for key in ("items", "if", "then"):
        if key in node:
            check_schema(node[key], root)

def structural(value, schema, root, path="$"):
    if schema is True:
        return
    need(schema is not False, f"{path}: 不允许该值")
    if "$ref" in schema:
        structural(value, root["$defs"][schema["$ref"].split("/")[-1]], root, path)
    if "type" in schema:
        kind = schema["type"]
        valid = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
            "null": value is None, "boolean": isinstance(value, bool), "integer": type(value) is int,
            "number": type(value) in (int, float) and math.isfinite(value)}
        # JSON Schema 允许 type 为候选数组，例如精确发布时间 string/null。
        kinds = kind if isinstance(kind, list) else [kind]
        need(any(valid[k] for k in kinds), f"{path}: 应为 {kind}")
    if "const" in schema:
        need(type(value) is type(schema["const"]) and value == schema["const"], f"{path}: const 不匹配")
    if "enum" in schema:
        need(any(type(value) is type(v) and value == v for v in schema["enum"]), f"{path}: enum 不匹配")
    if "anyOf" in schema:
        passed = False
        for child in schema["anyOf"]:
            try:
                structural(value, child, root, path)
                passed = True
                break
            except ValidationError:
                pass
        need(passed, f"{path}: 不匹配 anyOf")
    for child in schema.get("allOf", []):
        structural(value, child, root, path)
    if "if" in schema:
        try:
            structural(value, schema["if"], root, path)
        except ValidationError:
            pass
        else:
            structural(value, schema["then"], root, path)
    if isinstance(value, dict):
        need(set(schema.get("required", [])) <= set(value), f"{path}: 缺必填字段")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            need(set(value) <= set(props), f"{path}: 未知字段 {set(value)-set(props)}")
        for key, child in props.items():
            if key in value:
                structural(value[key], child, root, f"{path}.{key}")
    if isinstance(value, list):
        need(len(value) >= schema.get("minItems", 0), f"{path}: 数组过短")
        need(len(value) <= schema.get("maxItems", math.inf), f"{path}: 数组过长")
        if schema.get("uniqueItems"):
            need(len({json.dumps(v, sort_keys=True) for v in value}) == len(value), f"{path}: 重复项")
        prefix = schema.get("prefixItems", [])
        for i, item in enumerate(value):
            child = prefix[i] if i < len(prefix) else schema.get("items", True)
            structural(item, child, root, f"{path}[{i}]")
    if isinstance(value, str):
        need(len(value) >= schema.get("minLength", 0), f"{path}: 空字符串")
        if "pattern" in schema:
            need(re.search(schema["pattern"], value) is not None, f"{path}: 格式不符")
        if schema.get("format") == "date-time":
            instant(value)
        if schema.get("format") == "date":
            need(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None, f"{path}: 日期格式不符")
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError(f"{path}: 无效日期") from exc
    if type(value) in (int, float):
        need(math.isfinite(value), f"{path}: 非有限数字")
        need(value >= schema.get("minimum", -math.inf), f"{path}: 低于下限")
        need(value <= schema.get("maximum", math.inf), f"{path}: 高于上限")

def registry(values, label):
    result = {v["id"]: v for v in values}
    need(len(result) == len(values), f"{label}: ID 重复")
    return result

def semantic(data, context=None):
    as_of, recorded = instant(data["as_of"]), instant(data["recorded_at"])
    need(as_of <= recorded, "记录时间早于研究截止时间")
    need(date.fromisoformat(data["market_session_date"]) <= as_of.date(), "交易日晚于截止日")
    evidence = registry(data["evidence"], "证据")
    observations = registry(data["observations"], "观测")
    claims = registry(data["claims"], "判断")
    calculations = registry(data["calculations"], "计算")
    segments = registry(data["subject"]["segments"], "分部")
    context = context or {}
    taxonomy = context.get("industries") or load(ROOT / "knowledge/taxonomy/industries.json")
    industry_ids = {n["id"] for n in taxonomy["nodes"] if n["level"] == "industry"}
    model_ids = {m["id"] for m in (context.get("business_models") or load(ROOT / "knowledge/taxonomy/business_models.json"))["models"]}
    metrics = {m["id"]: m for m in (context.get("metrics") or load(ROOT / "knowledge/metrics/catalog.json"))["metrics"]}
    industry_rules = {r["industry_id"]: r for r in (context.get("industry_rules") or load(ROOT / "knowledge/taxonomy/industry_rules.json"))["rules"]}
    def refs(ids, table, label):
        need(set(ids) <= set(table), f"{label}: 存在悬空引用 {set(ids)-set(table)}")
    def scan(node):
        if isinstance(node, dict):
            if set(node) == {"start", "end", "basis"}:
                need(node["start"] <= node["end"], "时间窗口起止倒置")
            for key, value in node.items():
                if key.endswith("evidence_refs"):
                    refs(value, evidence, key)
                elif key.endswith("claim_refs") or key == "assumption_refs":
                    refs(value, claims, key)
                elif key.endswith("observation_refs"):
                    refs(value, observations, key)
                elif key.endswith("calculation_refs"):
                    refs(value, calculations, key)
                elif key in ("price_observation_ref", "last_observation_ref") and value is not None:
                    refs([value], observations, key)
                elif key == "metric_id":
                    refs([value], metrics, key)
                elif key == "metric_ids":
                    refs(value, metrics, key)
                scan(value)
        elif isinstance(node, list):
            for value in node:
                scan(value)
    scan(data)
    for e in evidence.values():
        local_file(ROOT, e["source_path"])
        need(instant(e['available_at']) <= as_of, '证据包含未来信息')
        if e['published_at'] is not None:
            need(instant(e['published_at']) <= instant(e['available_at']), '证据发布时间倒置')
            if e.get('published_date') is not None:
                need(e['published_date']==instant(e['published_at']).date().isoformat(),'证据发布日期与精确时间不一致')
        if e.get('published_date') is not None:
            # 日期缺时区时只排除在全球最早可能日界之后的明显未来日期；时点可用性仍以 available_at 判定。
            latest_possible_date=instant(e['acquired_at']).astimezone(timezone(timedelta(hours=14))).date()
            need(date.fromisoformat(e['published_date'])<=latest_possible_date,'证据发布日期明显晚于获取时点')
        need(instant(e["available_at"]) <= instant(e["acquired_at"]) <= recorded, "证据获取时间倒置")
        need(data["is_fictional"] or e["source_kind"] != "synthetic", "真实研究禁止合成证据")
    for s in segments.values():
        refs(s["industry_ids"], industry_ids, "行业")
        refs(s["business_model_ids"], model_ids, "商业模式")
        if s["weight"] is not None:
            need(s["weight_basis"] != "unknown" and s["weight_period"] is not None and s["weight_evidence_refs"], "权重缺口径或证据")
    for o in observations.values():
        need(o["segment_id"] is None or o["segment_id"] in segments, "观测分部不存在")
        need(instant(o["available_at"]) <= as_of, "观测包含未来信息")
        need(o["period"]["start"] <= o["period"]["end"] <= data["as_of"][:10], "历史观测期间无效")
        if o["value"] is None:
            need(o["missing_reason"] is not None, "缺失观测必须说明原因")
        else:
            need(o["missing_reason"] is None and o["evidence_refs"], "有效观测需证据且不能带缺失原因")
            q = o["value"]
            need(q["unit"] not in ("unknown", "context_defined"), "观测必须明确实际单位")
            expected = metrics[o["metric_id"]]["unit"]
            need(expected == "context_defined" or q["unit"] == expected, "观测单位不匹配指标定义")
            if q["unit"] in ("currency", "currency_per_share"):
                need(q["currency"] is not None, "金额必须明确币种")
            for eid in o["evidence_refs"]:
                need(instant(evidence[eid]["available_at"]) <= instant(o["available_at"]), "观测早于来源可得时间")
    for c in claims.values():
        if c["kind"] == "fact":
            need(c["evidence_refs"], "事实判断必须有原始证据")
            if not data["is_fictional"]:
                need(any(evidence[eid]["source_kind"] in ("primary", "secondary") for eid in c["evidence_refs"]), "项目设计文档不能充当真实公司事实证据")
        if c["kind"] == "inference":
            need(c["evidence_refs"] or c["observation_refs"] or c["assumption_refs"], "推断缺依据")
        for aid in c["assumption_refs"]:
            need(claims[aid]["kind"] == "assumption", "假设引用类型错误")
    visiting, visited = set(), set()
    def visit(cid):
        need(cid not in visiting, "假设引用循环")
        if cid in visited:
            return
        visiting.add(cid)
        for aid in claims[cid]["assumption_refs"]:
            visit(aid)
        visiting.remove(cid)
        visited.add(cid)
    for cid in claims:
        visit(cid)
    for calc in calculations.values():
        local_file(ROOT, calc["implementation_path"])
        for aid in calc["assumption_refs"]:
            need(claims[aid]["kind"] == "assumption", "计算假设类型错误")
        for oid in calc["input_observation_refs"]:
            need(observations[oid]["value"] is not None, "计算使用缺失观测")
        if calc["verification_status"] == "checked":
            need(calc["verification_evidence_refs"], "计算校验缺记录证据")
    for i, step in enumerate(data["steps"]):
        need(instant(step["updated_at"]) <= recorded, "步骤时间晚于记录时间")
        deps = step["inputs"]["dependencies"]
        registry([{**dep, "id": dep["step_id"]} for dep in deps], "依赖")
        for dep in deps:
            index = int(dep["step_id"][1:]) - 1
            need(index < i, "步骤依赖不是前序")
            if step["status"] != "invalidated":
                need(dep["version"] == data["steps"][index]["version"], "上游版本已变，结果过期")
        if step["status"] in ("in_progress", "completed", "insufficient_evidence", "needs_review"):
            need(all(s["status"] == "completed" for s in data["steps"][:i]), "禁止跳过未完成步骤")
            need({d["step_id"] for d in deps} == {f"S{x}" for x in range(1, i+1)}, "缺上游版本快照")
        if step["status"] == "completed":
            gates = registry(step["gates"], "验收门槛")
            need(set(gates) == set(GATES[step["id"]]), "步骤门槛不完整")
            need(all(g["result"] == "pass" for g in gates.values()), "必需门槛必须通过，不能以不适用跳过")
            need(step["inputs"]["evidence_refs"], "完成步骤缺输入证据")
            if step["id"] == "S1":
                need(data["subject"]["classification_status"] == "reviewed", "分类未复核")
                need(all(s["classification_evidence_refs"] for s in segments.values()), "分部分类缺证据")
                positions = step["output"]["segment_positions"]
                need(len(positions) == len(segments) and {p["segment_id"] for p in positions} == set(segments), "周期分析未覆盖所有分部")
                for p in positions:
                    need(p["industry_rule_id"] in segments[p["segment_id"]]["industry_ids"], "行业规则与分部不匹配")
            if step["id"] == "S2":
                need(any(c["counterevidence_refs"] for c in claims.values()), "深入研究缺反证取证")
            if step["id"] == "S3":
                out = step["output"]
                need(bool(out["catalysts"]) != bool(out["no_catalyst_reason"]), "无催化剂必须说明原因，有催化剂不得填无催化剂原因")
                for m in out["monitoring_indicators"]:
                    need(bool(m["baseline_observation_refs"]) != bool(m["missing_baseline_reason"]), "跟踪基线或缺失原因须二选一")
            if step["id"] == "S4":
                out = step["output"]
                need(len(out["scenarios"]) == 3 and {s["name"] for s in out["scenarios"]} == {"bear", "base", "bull"}, "三情景缺失或重复")
                price = observations[out["price_observation_ref"]]
                need(price["metric_id"] == "market_price" and price["value"] is not None, "估值价格引用错误")
                probs = [s["probability"] for s in out["scenarios"]]
                need(all(p is None for p in probs) or (all(p is not None for p in probs) and abs(sum(probs)-1) < 1e-9 and out["probability_basis_claim_refs"]), "情景概率需完整、合计为1并有依据")
                for s in out["scenarios"]:
                    for aid in s["assumption_refs"]:
                        need(claims[aid]["kind"] == "assumption", "情景输入须为假设")
                    q = s["intrinsic_value_per_share"]
                    need(q["unit"] == "currency_per_share" and q["currency"] == price["value"]["currency"], "情景与市场价格单位/币种不同")
                    need(any(q in calculations[cid]["outputs"] for cid in s["calculation_refs"]), "情景结果不能与计算输出脱节")
                for cid in [c for s in out["scenarios"] for c in s["calculation_refs"]] + out["crosscheck_calculation_refs"] + out["sensitivity_calculation_refs"]:
                    need(calculations[cid]["verification_status"] == "checked", "估值计算尚未校验")
                need(out["crosscheck_calculation_refs"] != out["sensitivity_calculation_refs"], "交叉检查和敏感性不能使用完全相同引用")
            if step["id"] == "S5":
                out = step["output"]
                if out["portfolio_assessment"] == "not_assessed":
                    need(out["position_fraction"] is None and not out["portfolio_calculation_refs"], "未评估组合不得输出仓位")
                else:
                    need(out["portfolio_evidence_refs"] and out["portfolio_calculation_refs"], "组合评估缺数据或计算")
                if out["decision"] == "action_conditions_met":
                    need(not data["is_fictional"], "合成示例不得成为可行动研究")
                    need(out["validated_rule_refs"], "行动缺已验证规则")
                    valid = {r["industry_id"] for r in industry_rules.values() if r["statistical_validation_status"] == "validated"}
                    refs(out["validated_rule_refs"], valid, "已验证规则")
                    need(not data["steps"][1]["output"]["critical_unknown_claim_refs"], "关键未知尚未解决")
            if step["id"] == "S6":
                out = step["output"]
                need(instant(out["next_review_at"]) > as_of, "下次复盘时间必须晚于研究截止时间")
                for plan in out["monitoring_plan"]:
                    need(instant(plan["next_due_at"]) > as_of, "下次指标更新必须晚于研究截止时间")
                for review in out["review_records"]:
                    need(instant(review["reviewed_at"]) <= recorded, "复盘记录晚于记录时间")
    registry(data["invalidation_events"], "回退事件")
    for event in data["invalidation_events"]:
        start = int(event["earliest_step"][1:]) - 1
        need(set(event["affected_steps"]) == {f"S{i}" for i in range(start+1, 7)}, "回退必须覆盖全部下游")
        need(instant(event["occurred_at"]) <= recorded, "回退时间无效")
        baseline = registry([{**v, "id": v["step_id"]} for v in event["baseline_versions"]], "回退快照")
        need(set(baseline) == set(event["affected_steps"]), "回退缺全部受影响步骤版本")
        if event["status"] == "open":
            need(event["resolved_at"] is None, "未解决事件不能填解决时间")
            need(all(s["status"] in ("invalidated", "pending") for s in data["steps"][start:]), "回退后仍保留有效下游结论")
        else:
            need(event["resolved_at"] is not None and instant(event["occurred_at"]) <= instant(event["resolved_at"]) <= recorded, "解决时间无效")
            need(all(s["status"] == "completed" for s in data["steps"][start:]), "回退尚未完成重分析")
            need(all(s["version"] > baseline[s["id"]]["version"] for s in data["steps"][start:]), "重分析未更新步骤版本")

def validate(data, context=None):
    schema = (context or {}).get("schema") or load(ROOT / "schemas/research.schema.json")
    check_schema(schema, schema)
    structural(data, schema, schema)
    semantic(data, context)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="相对于项目根目录的研究记录")
    args = parser.parse_args()
    try:
        path = local_file(ROOT, args.file)
        validate(load(path))
    except (ValueError, KeyError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print(f"PASS: {args.file}（结构与流程；不代表事实/估值真实或可执行交易）")

if __name__ == "__main__":
    main()
