"""构建项目 JSON Schema（纯标准库）。生成文件是交付契约，不下载远程 meta-schema。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "schemas"

def obj(properties, required=None):
    return {"type": "object", "properties": properties, "required": list(properties) if required is None else required, "additionalProperties": False}

def arr(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}

def ref(name):
    return {"$ref": f"#/$defs/{name}"}

S = {"type": "string", "minLength": 1}
NULL = {"type": "null"}
IDS = {"type": "array", "items": S, "uniqueItems": True}
DATE = {"type": "string", "format": "date"}
TIME = {"type": "string", "format": "date-time"}
POS = {"type": "integer", "minimum": 1}

def enum(*values):
    return {"enum": list(values)}

def maybe(schema):
    return {"anyOf": [schema, NULL]}

def build():
    defs = {}
    defs["local_path"] = {"type": "string", "minLength": 1, "pattern": r"^(?![A-Za-z][A-Za-z0-9+.-]*:)(?![/\\]).+"}
    defs["quantity"] = obj({"value": {"type": "number"}, "unit": S, "currency": maybe(S)})
    defs["period"] = obj({"start": DATE, "end": DATE, "basis": enum("quarter", "year", "ttm", "point_in_time", "custom")})
    defs["evidence"] = obj({"id": S, "source_path": ref("local_path"), "locator": S,
        "source_kind": enum("primary", "secondary", "project_design", "synthetic"), "published_at": maybe(TIME),
        "available_at": TIME, "acquired_at": TIME, "excerpt_or_summary": S, "limitations": arr(S)})
    defs['evidence']['properties'].update({'published_date':maybe(DATE),
        'publication_precision':enum('instant','date','unknown')})
    defs['evidence']['allOf']=[
        {'if':{'required':['publication_precision'],'properties':{'publication_precision':{'const':'instant'}}},
         'then':{'properties':{'published_at':TIME}}},
        {'if':{'required':['publication_precision'],'properties':{'publication_precision':{'const':'date'}}},
         'then':{'properties':{'published_at':NULL,'published_date':DATE}}},
        {'if':{'required':['publication_precision'],'properties':{'publication_precision':{'const':'unknown'}}},
         'then':{'properties':{'published_at':NULL,'published_date':NULL}}}]
    defs["observation"] = obj({"id": S, "metric_id": S, "segment_id": maybe(S), "period": ref("period"),
        "available_at": TIME, "value": maybe(ref("quantity")), "missing_reason": maybe(S),
        "accounting_basis": S, "comparability_notes": S, "evidence_refs": IDS})
    defs["claim"] = obj({"id": S, "kind": enum("fact", "inference", "assumption", "unknown", "not_applicable"),
        "statement": S, "evidence_refs": IDS, "observation_refs": IDS, "counterevidence_refs": IDS,
        "assumption_refs": IDS, "uncertainty": S})
    defs["calculation"] = obj({"id": S, "method": S, "method_version": S, "implementation_path": ref("local_path"),
        "input_observation_refs": IDS, "assumption_refs": IDS, "outputs": arr(ref("quantity"), 1),
        "verification_status": enum("unchecked", "checked"), "verification_evidence_refs": IDS})
    defs["segment"] = obj({"id": S, "name": S, "industry_ids": {**IDS, "minItems": 1},
        "business_model_ids": {**IDS, "minItems": 1}, "classification_evidence_refs": IDS,
        "subindustry_description": S, "weight_basis": enum("revenue", "operating_profit", "assets", "unknown"),
        "weight": maybe({"type": "number", "minimum": 0, "maximum": 1}), "weight_period": maybe(ref("period")),
        "weight_evidence_refs": IDS})
    defs["subject"] = obj({"company_id": S, "security_ids": {**IDS, "minItems": 1},
        "segments": arr(ref("segment"), 1), "is_adr": {"type": "boolean"}, "is_reit": {"type": "boolean"},
        "classification_status": enum("unreviewed", "reviewed"), "unallocated_or_elimination_notes": S})
    defs["assessment"] = obj({"verdict": S, "claim_refs": {**IDS, "minItems": 1}, "limitations": arr(S)})
    cycle_props = {dimension: ref("assessment") for dimension in
        ("lifecycle", "supply_demand", "earnings", "credit", "sentiment", "pricing")}
    defs["step1_output"] = obj({"segment_positions": arr(obj({"segment_id": S, "industry_rule_id": S,
        "positions": obj(cycle_props)}), 1), "research_priorities": arr(S, 1), "conclusion_claim_refs": {**IDS, "minItems": 1}})
    defs["step2_output"] = obj({"checks": obj({key: ref("assessment") for key in
        ("business_model", "demand_growth", "competition", "financial_quality", "cash_flow", "debt_liquidity", "governance", "capital_allocation")}),
        "thesis_claim_refs": {**IDS, "minItems": 1}, "critical_unknown_claim_refs": IDS})
    defs["trigger"] = obj({"id": S, "description": S, "metric_ids": IDS, "condition_description": S,
        "claim_refs": IDS, "target_steps": {"type": "array", "items": enum("S1", "S2", "S3", "S4", "S5"), "minItems": 1, "uniqueItems": True}})
    defs["step3_output"] = obj({"catalysts": arr(obj({"id": S, "event": S, "transmission": S, "expected_window": ref("period"), "claim_refs": {**IDS, "minItems": 1}})),
        "no_catalyst_reason": maybe(S), "monitoring_indicators": arr(obj({"metric_id": S, "rationale": S,
        "cadence": S, "baseline_observation_refs": IDS, "missing_baseline_reason": maybe(S)}), 1), "invalidation_triggers": arr(ref("trigger"), 1)})
    defs["scenario"] = obj({"name": enum("bear", "base", "bull"), "assumption_refs": {**IDS, "minItems": 1},
        "intrinsic_value_per_share": ref("quantity"), "calculation_refs": {**IDS, "minItems": 1},
        "probability": maybe({"type": "number", "minimum": 0, "maximum": 1})})
    defs["step4_output"] = obj({"valuation_method": S, "applicability_claim_refs": {**IDS, "minItems": 1},
        "price_observation_ref": S, "scenarios": arr(ref("scenario"), 3), "probability_basis_claim_refs": IDS,
        "crosscheck_calculation_refs": {**IDS, "minItems": 1}, "sensitivity_calculation_refs": {**IDS, "minItems": 1},
        "market_expectation_claim_refs": {**IDS, "minItems": 1}, "value_bridge_claim_refs": {**IDS, "minItems": 1},
        "valuation_horizon": ref("period"), "investment_horizon": ref("period"), "limitations": arr(S)})
    defs["step5_output"] = obj({"decision": enum("watch", "action_conditions_met", "conditions_not_met", "unable_to_judge"),
        "company_quality": ref("assessment"), "price_attractiveness": ref("assessment"), "action_suitability": ref("assessment"),
        "permanent_loss_risks": arr(ref("assessment"), 1), "entry_conditions": arr(S, 1), "exit_conditions": arr(S, 1),
        "portfolio_assessment": enum("not_assessed", "assessed"), "portfolio_evidence_refs": IDS,
        "portfolio_calculation_refs": IDS, "position_fraction": maybe({"type": "number", "minimum": 0, "maximum": 1}),
        "validated_rule_refs": IDS, "decision_claim_refs": {**IDS, "minItems": 1}})
    defs["step6_output"] = obj({"monitoring_plan": arr(obj({"metric_id": S, "cadence": S, "owner": S,
        "last_observation_ref": maybe(S), "next_due_at": TIME}), 1), "triggers": arr(ref("trigger"), 1),
        "review_records": arr(obj({"reviewed_at": TIME, "new_evidence_refs": IDS, "changed_claim_refs": IDS,
        "conclusion": S})), "next_review_at": TIME})
    defs["dependency"] = obj({"step_id": enum("S1", "S2", "S3", "S4", "S5"), "version": POS})
    defs["gate"] = obj({"id": S, "result": enum("pass", "fail", "not_applicable"), "reason": S, "evidence_refs": IDS})
    defs["inputs"] = obj({"dependencies": arr(ref("dependency")), "evidence_refs": IDS, "observation_refs": IDS, "claim_refs": IDS})
    states = enum("pending", "in_progress", "completed", "insufficient_evidence", "needs_review", "invalidated")
    for i in range(1, 7):
        defs[f"step{i}"] = obj({"id": {"const": f"S{i}"}, "version": POS, "status": states, "updated_at": TIME,
            "inputs": ref("inputs"), "gates": arr(ref("gate")), "output": maybe(ref(f"step{i}_output")), "notes": arr(S)})
        defs[f"step{i}"]["allOf"] = [
            {"if": {"properties": {"status": {"const": "completed"}}}, "then": {"properties": {"output": ref(f"step{i}_output"), "gates": {"minItems": 1}}}},
            {"if": {"properties": {"status": {"const": "pending"}}}, "then": {"properties": {"output": NULL}}}
        ]
    defs["snapshot"] = obj({"step_id": enum("S1", "S2", "S3", "S4", "S5", "S6"), "version": POS})
    defs["invalidation"] = obj({"id": S, "occurred_at": TIME, "reason": S, "evidence_refs": IDS,
        "earliest_step": enum("S1", "S2", "S3", "S4", "S5", "S6"),
        "affected_steps": {"type": "array", "items": enum("S1", "S2", "S3", "S4", "S5", "S6"), "minItems": 1, "uniqueItems": True},
        "status": enum("open", "resolved"), "baseline_versions": arr(ref("snapshot"), 1), "resolved_at": maybe(TIME)})
    props = {"schema_version": enum('1.0.0','1.1.0'), "research_id": S, "revision": POS, "is_fictional": {"type": "boolean"},
        "as_of": TIME, "recorded_at": TIME, "market_session_date": DATE, "investment_horizon_months": {"type": "integer", "minimum": 1},
        "subject": ref("subject"), "evidence": arr(ref("evidence")), "observations": arr(ref("observation")),
        "claims": arr(ref("claim")), "calculations": arr(ref("calculation")),
        "steps": {"type": "array", "prefixItems": [ref(f"step{i}") for i in range(1, 7)], "items": False, "minItems": 6, "maxItems": 6},
        "invalidation_events": arr(ref("invalidation"))}
    schema = obj(props)
    schema['allOf']=[
        {'if':{'properties':{'schema_version':{'const':'1.0.0'}}},
         'then':{'properties':{'evidence':{'items':{'properties':{'published_at':TIME}}}}}},
        {'if':{'properties':{'schema_version':{'const':'1.1.0'}}},
         'then':{'properties':{'evidence':{'items':{'required':['published_date','publication_precision']}}}}}]
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:shuiyuan:research:1.1.0",
        "title": "水源六步研究记录", "description": "结构契约＋本地语义校验；$schema URI 仅是标准标识，不进行网络解析", "$defs": defs})
    OUT.mkdir(exist_ok=True)
    path = OUT / "research.schema.json"
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote schemas/research.schema.json")

if __name__ == "__main__":
    build()
