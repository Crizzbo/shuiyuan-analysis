"""验证知识库内部引用；不验证金融判断、来源真实性或指标阈值。"""
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "knowledge"

def local_file(base, target):
    raw = unquote(target.split("#")[0])
    if not raw:
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) or raw.startswith(("/", "\\")):
        raise ValueError(f"禁止项目外/绝对引用：{target}")
    resolved = (base / raw).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"引用越过项目根目录：{target}")
    if not resolved.is_file():
        raise ValueError(f"引用文件不存在：{target}")
    return resolved

def read(relative):
    return json.loads((K / relative).read_text(encoding="utf-8"))

def unique(items):
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids)), "重复 ID"
    return set(ids)

def main():
    nodes = read("taxonomy/industries.json")["nodes"]
    models = read("taxonomy/business_models.json")["models"]
    metrics = read("metrics/catalog.json")["metrics"]
    node_ids, model_ids, metric_ids = unique(nodes), unique(models), unique(metrics)
    node_map = {n["id"]: n for n in nodes}
    for n in nodes:
        parent = n["parent_id"]
        assert parent is None or parent in node_ids, n
        seen = {n["id"]}
        while parent is not None:
            assert parent not in seen, "循环父节点"
            seen.add(parent)
            parent = node_map[parent]["parent_id"]
        if n["level"] == "sector":
            assert n["parent_id"] is None
        else:
            assert n["parent_id"] is not None
            local_file(ROOT, n["profile_path"])
            assert set(n["business_model_ids"]) <= model_ids
    for m in models:
        local_file(ROOT, m["profile_path"])
        assert set(m["metric_ids"]) <= metric_ids, m
    for m in metrics:
        for key in ("definition", "unit", "applicability", "validation_status"):
            assert m.get(key), m
        assert m["threshold"] is None, "未验证种子不得带硬阈值"
    example = read("templates/company_segments.example.json")
    assert example["is_fictional"] is True
    for s in example["segments"]:
        assert set(s["industry_ids"]) <= node_ids
        assert set(s["business_model_ids"]) <= model_ids
    rules = read("taxonomy/industry_rules.json")["rules"]
    industry_ids = {n["id"] for n in nodes if n["level"] == "industry"}
    assert {r["industry_id"] for r in rules} == industry_ids
    assert len(rules) == len(industry_ids)
    for r in rules:
        assert set(r["metric_ids"]) <= metric_ids
        assert r["statistical_validation_status"] == "not_validated"
        assert r["drawdown_threshold"] is None and r["valuation_threshold"] is None
        assert r["valuation_route"] and r["counterevidence"] and r["required_segmentation"]
        for ref in r["evidence_refs"]:
            local_file(ROOT, ref)
    for m in metrics:
        for ref in m.get("evidence_refs", []):
            local_file(ROOT, ref)
    checked_links = 0
    for p in ROOT.rglob("*.md"):
        parts = p.relative_to(ROOT).parts
        if any(part in {".git", ".codex", ".agents", ".venv", ".cache", "scratch"} or part.startswith("share-export") for part in parts):
            continue
        # 发行包许可证必须原样保留，其书目链接不属于研究运行时引用。
        # 仅豁免专用许可证目录内的许可文本，项目说明文档仍逐条检查。
        if parts[:2] == ("third_party", "finance") and "licenses" in parts and p.name.lower().startswith(("license", "copying", "notice")):
            continue
        assert p.resolve().is_relative_to(ROOT)
        for target in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if target.startswith("#"):
                continue
            local_file(p.parent, target)
            checked_links += 1
    for bad in ("../outside.md", "C:/outside.md", "file:///outside.md", "https://invalid.example", "%2e%2e/outside.md", "//host/share.md"):
        try:
            local_file(ROOT, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"未拒绝越界引用：{bad}")
    print(f"PASS: {sum(n['level']=='sector' for n in nodes)} sectors, "
          f"{sum(n['level']=='industry' for n in nodes)} industries, "
          f"{len(models)} models, {len(metrics)} metrics; {len(rules)} adaptations; {checked_links} project-contained links; boundary rejection PASS.")

if __name__ == "__main__":
    main()
