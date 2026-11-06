"""生成纯合成研究示例与待填模板；不得作为真实研究记录。"""
import copy
import json
from pathlib import Path

from validate_knowledge_structure import ROOT
from validate_research import GATES

T = "2026-10-10T12:00:00Z"

def quantity(value):
    return {"value": value, "unit": "currency_per_share", "currency": "USD"}

def assessment():
    return {"verdict": "synthetic_test_only", "claim_refs": ["c_inference"], "limitations": ["无真实市场证据"]}

def period():
    return {"start": "2026-10-10", "end": "2027-10-10", "basis": "custom"}

def make():
    evidence = []
    for eid, locator in (("e_main", "基础信息"), ("e_counter", "反证"), ("e_check", "计算核对")):
        evidence.append({"id": eid, "source_path": "examples/support/fictional_evidence.md", "locator": locator,
            "source_kind": "synthetic", "published_at": T, "available_at": T, "acquired_at": T,
            "excerpt_or_summary": "合成输入，仅验证结构", "limitations": ["不能支持真实交易"]})
    claims = []
    for cid, kind in (("c_fact", "fact"), ("c_inference", "inference"), ("c_assumption", "assumption")):
        claims.append({"id": cid, "kind": kind, "statement": "合成测试判断，不对应真实公司", "evidence_refs": ["e_main"],
            "observation_refs": [], "counterevidence_refs": ["e_counter"], "assumption_refs": [], "uncertainty": "无真实证据，禁止行动"})
    data = {"schema_version": "1.0.0", "research_id": "fictional_demo", "revision": 1, "is_fictional": True,
        "as_of": T, "recorded_at": "2026-10-11T00:00:00Z", "market_session_date": "2026-10-09", "investment_horizon_months": 12,
        "subject": {"company_id": "fictional_company", "security_ids": ["fictional_security"], "segments": [{"id": "segment_software",
            "name": "虚构软件分部", "industry_ids": ["software"], "business_model_ids": ["subscription"],
            "classification_evidence_refs": ["e_main"], "subindustry_description": "虚构订阅业务，仅字段演示",
            "weight_basis": "unknown", "weight": None, "weight_period": None, "weight_evidence_refs": []}],
            "is_adr": False, "is_reit": False, "classification_status": "reviewed", "unallocated_or_elimination_notes": "测试没有真实分部权重"},
        "evidence": evidence, "observations": [{"id": "o_price", "metric_id": "market_price", "segment_id": None,
            "period": {"start": "2026-10-09", "end": "2026-10-09", "basis": "point_in_time"}, "available_at": T,
            "value": quantity(100), "missing_reason": None, "accounting_basis": "不适用；合成收盘价",
            "comparability_notes": "合成单位，非真实行情", "evidence_refs": ["e_main"]}],
        "claims": claims, "calculations": [], "steps": [], "invalidation_events": []}
    scenarios = []
    for name, factor in (("bear", .8), ("base", 1), ("bull", 1.2)):
        cid = "calc_" + name
        data["calculations"].append({"id": cid, "method": "synthetic price times factor", "method_version": "demo-1",
            "implementation_path": "examples/support/scenario_demo.py", "input_observation_refs": ["o_price"],
            "assumption_refs": ["c_assumption"], "outputs": [quantity(100*factor)], "verification_status": "checked",
            "verification_evidence_refs": ["e_check"]})
        scenarios.append({"name": name, "assumption_refs": ["c_assumption"], "intrinsic_value_per_share": quantity(100*factor),
            "calculation_refs": [cid], "probability": None})
    for cid, value, method in (("calc_cross", 100, "synthetic crosscheck"), ("calc_sensitivity", 110, "synthetic sensitivity")):
        data["calculations"].append({"id": cid, "method": method, "method_version": "demo-1",
            "implementation_path": "examples/support/scenario_demo.py", "input_observation_refs": ["o_price"],
            "assumption_refs": ["c_assumption"], "outputs": [quantity(value)], "verification_status": "checked", "verification_evidence_refs": ["e_check"]})
    trigger = {"id": "trigger_demo", "description": "合成假设改变", "metric_ids": ["software_driver_1"],
        "condition_description": "出现新的可比留存证据", "claim_refs": ["c_inference"], "target_steps": ["S1"]}
    outputs = [
        {"segment_positions": [{"segment_id": "segment_software", "industry_rule_id": "software", "positions": {d: assessment() for d in ("lifecycle", "supply_demand", "earnings", "credit", "sentiment", "pricing")}}], "research_priorities": ["验证真实数据；演示不能用于行动"], "conclusion_claim_refs": ["c_inference"]},
        {"checks": {k: assessment() for k in ("business_model", "demand_growth", "competition", "financial_quality", "cash_flow", "debt_liquidity", "governance", "capital_allocation")}, "thesis_claim_refs": ["c_inference"], "critical_unknown_claim_refs": []},
        {"catalysts": [], "no_catalyst_reason": "合成例子不含真实催化剂", "monitoring_indicators": [{"metric_id": "software_driver_1", "rationale": "演示软件留存跟踪", "cadence": "quarterly", "baseline_observation_refs": [], "missing_baseline_reason": "没有真实留存数据"}], "invalidation_triggers": [trigger]},
        {"valuation_method": "synthetic arithmetic, NOT financial valuation", "applicability_claim_refs": ["c_inference"], "price_observation_ref": "o_price", "scenarios": scenarios,
            "probability_basis_claim_refs": [], "crosscheck_calculation_refs": ["calc_cross"], "sensitivity_calculation_refs": ["calc_sensitivity"],
            "market_expectation_claim_refs": ["c_inference"], "value_bridge_claim_refs": ["c_inference"], "valuation_horizon": period(), "investment_horizon": period(), "limitations": ["演示计算，非金融模型"]},
        {"decision": "watch", "company_quality": assessment(), "price_attractiveness": assessment(), "action_suitability": assessment(),
            "permanent_loss_risks": [assessment()], "entry_conditions": ["真实数据与验证规则未具备，不行动"], "exit_conditions": ["仅示例"],
            "portfolio_assessment": "not_assessed", "portfolio_evidence_refs": [], "portfolio_calculation_refs": [], "position_fraction": None,
            "validated_rule_refs": [], "decision_claim_refs": ["c_inference"]},
        {"monitoring_plan": [{"metric_id": "software_driver_1", "cadence": "quarterly", "owner": "用户", "last_observation_ref": None, "next_due_at": "2026-11-01T00:00:00Z"}],
            "triggers": [trigger], "review_records": [], "next_review_at": "2026-11-01T00:00:00Z"}]
    for i, output in enumerate(outputs, 1):
        sid = f"S{i}"
        data["steps"].append({"id": sid, "version": 1, "status": "completed", "updated_at": T,
            "inputs": {"dependencies": [{"step_id": f"S{j}", "version": 1} for j in range(1, i)], "evidence_refs": ["e_main"], "observation_refs": ["o_price"], "claim_refs": ["c_inference"]},
            "gates": [{"id": gid, "result": "pass", "reason": "仅合成结构验收，非真实研究通过", "evidence_refs": ["e_check"]} for gid in GATES[sid]],
            "output": output, "notes": ["合成演示禁止交易"]})
    return data

def main():
    metric_path = ROOT / "knowledge/metrics/catalog.json"
    catalog = json.loads(metric_path.read_text(encoding="utf-8"))
    if not any(m["id"] == "market_price" for m in catalog["metrics"]):
        catalog["metrics"].append({"id": "market_price", "name": "研究基准每股价格", "definition": "指定交易日、时段和价格类型的每股价格",
            "unit": "currency_per_share", "comparability_notes": "记录币种、盘段、复权及股数口径，与估值基准一致", "source_candidates": "项目内行情证据，尚未接入",
            "cadence": "daily", "applicability": "上市证券", "validation_status": "draft", "threshold": None})
        metric_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    complete = make()
    pending = copy.deepcopy(complete)
    pending["research_id"] = "fictional_pending"
    pending["calculations"] = []
    for step in pending["steps"]:
        step.update(status="pending", gates=[], output=None)
        step["inputs"] = {"dependencies": [], "evidence_refs": [], "observation_refs": [], "claim_refs": []}
    blocked = copy.deepcopy(pending)
    blocked["research_id"] = "fictional_blocked"
    blocked["steps"][0]["status"] = "insufficient_evidence"
    blocked["steps"][0]["notes"] = ["缺真实分部与生命周期证据，后续不启动"]
    for name, value in (("completed.synthetic.json", complete), ("pending.synthetic.json", pending), ("blocked.synthetic.json", blocked)):
        (ROOT / "examples" / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    governed = copy.deepcopy(complete)
    governed["revision"] = 2
    for step in governed["steps"]:
        step["version"] = 2
        for dep in step["inputs"]["dependencies"]:
            dep["version"] = 2
        step["notes"].append("合成演示重新归档，固定数据契约与来源版本")
    (ROOT / "examples/governed-revision.synthetic.json").write_text(json.dumps(governed, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    template = copy.deepcopy(pending)
    template.update(schema_version='1.1.0',research_id="replace_research_id", is_fictional=False, evidence=[], observations=[], claims=[])
    template["subject"]["classification_status"] = "unreviewed"
    template["subject"]["company_id"] = "replace_company_id"
    template["subject"]["security_ids"] = ["replace_security_id"]
    for step in template["steps"]:
        step["notes"] = ["待填；未开始真实分析"]
    for segment in template["subject"]["segments"]:
        segment["classification_evidence_refs"] = []
        segment["name"] = "待填业务分部"
        segment["subindustry_description"] = "待取证；当前软件分类仅模板占位"
    (ROOT / "knowledge/templates/research.pending.json").write_text(json.dumps(template, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Wrote 3 synthetic examples and pending template; added market_price metric.")

if __name__ == "__main__":
    main()
