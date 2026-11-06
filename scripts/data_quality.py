"""项目内研究数据质量提醒；不自动填补、转换单位或发出交易信号。"""
import argparse
import json
from validate_knowledge_structure import ROOT, local_file
from validate_research import instant, load, validate

def report(record):
    validate(record)
    policy = load(ROOT / "data/quality-policy.json")
    metrics = {m["id"]: m for m in load(ROOT / "knowledge/metrics/catalog.json")["metrics"]}
    rules = {r["industry_id"]: r for r in load(ROOT / "knowledge/taxonomy/industry_rules.json")["rules"]}
    cutoff = instant(record["as_of"])
    issues = []
    usable = set()
    for o in record["observations"]:
        if o["value"] is None:
            issues.append({"kind": "missing_value", "observation_id": o["id"], "detail": o["missing_reason"]})
            continue
        usable.add((o["metric_id"], o["segment_id"]))
        cadence = metrics[o["metric_id"]]["cadence"]
        limit = policy["max_age_calendar_days"].get(cadence)
        age = (cutoff - instant(o["available_at"])).total_seconds()/86400
        if limit is None:
            issues.append({"kind": "freshness_requires_review", "observation_id": o["id"], "detail": "无统一更新预算，需按数据源检查"})
        elif age > limit:
            issues.append({"kind": "stale_observation", "observation_id": o["id"], "age_calendar_days": round(age, 3), "max_age_calendar_days": limit})
    for segment in record["subject"]["segments"]:
        for industry_id in segment["industry_ids"]:
            for metric_id in rules[industry_id]["metric_ids"]:
                if (metric_id, segment["id"]) not in usable:
                    issues.append({"kind": "missing_industry_driver", "segment_id": segment["id"], "metric_id": metric_id,
                        "detail": "行业指标无有效分部观测；不以公司合并值静默替代"})
    if record["subject"]["classification_status"] != "reviewed":
        issues.append({"kind": "classification_unreviewed", "detail": "业务分类尚未取证复核"})
    if record["is_fictional"]:
        issues.append({"kind": "synthetic_only", "detail": "仅合成测试，不能支持真实判断"})
    return {"research_id": record["research_id"], "revision": record["revision"], "as_of": record["as_of"],
        "status": "synthetic_only" if record["is_fictional"] else ("needs_review" if issues else "metadata_checks_passed"),
        "issues": issues, "note": "质量提醒不改变步骤状态；通过仍需检查原文、指标口径和金融判断"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    try:
        print(json.dumps(report(load(local_file(ROOT, args.record))), ensure_ascii=False, indent=2))
    except ValueError as exc:
        parser.exit(1, f"FAIL: {exc}\n")

if __name__ == "__main__":
    main()
