"""离线执行工程发布契约审计。"""

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 导入四类模块登记探针，保持原有编号和分组。
from scripts.test_support.release_checks import unit, functional, component, integration
from scripts.test_support.release_checks.common import CHECKS, install_isolation


LAYERS = {"UT": "单元测试", "FT": "功能测试", "CT": "单体测试", "IT": "结合测试"}
PLAN = ROOT / "docs/38-水源投研工程四类测试点与验收清单.md"
STAGE_PLAN = ROOT / "scripts/test_support/release_plan.json"


def coverage_rows():
    """将探针回链到清单，空列表表示暂无直接探针。"""
    mapped = {}
    for case in CHECKS:
        for point in case.points:
            mapped.setdefault(point, []).append(case.key)
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| ([A-Z]{2}-\d{2}) · (P[01]) \| ([^|]+) \|", line)
        if match:
            point, severity, title = match.groups()
            yield {"point": point, "severity": severity, "title": title.strip(), "checks": sorted(mapped.get(point, []))}


def stage_plan():
    """校验设计引用、阶段归属和探针登记，避免矩阵漏跑或引用失效。"""
    plan = json.loads(STAGE_PLAN.read_text(encoding="utf-8"))
    stages = [stage["id"] for stage in plan["stages"]]
    ids = set()
    known = {case.key for case in CHECKS}
    assigned = set()
    if len(stages) != len(set(stages)) or not stages:
        raise ValueError("验收阶段不能为空或重复")
    for row in plan["scenarios"]:
        reference = Path(row["design"])
        target = (ROOT / reference).resolve()
        if (row["id"] in ids or row["stage"] not in stages or not row["scenario"] or not row["evidence"]
                or reference.is_absolute() or not target.is_relative_to(ROOT / "docs") or not target.is_file()):
            raise ValueError(f"无效场景登记 {row['id']}")
        ids.add(row["id"])
        unknown = set(row["checks"]) - known
        if unknown:
            raise ValueError(f"{row['id']} 引用未登记探针 {sorted(unknown)}")
        assigned.update(row["checks"])
    if assigned != known:
        raise ValueError(f"以下探针未分配验收阶段 {sorted(known - assigned)}")
    spec_ids = set()
    referenced = set()
    for spec in plan["specs"]:
        reference = Path(spec["design"])
        target = (ROOT / reference).resolve()
        scenarios = spec["scenarios"]
        if (spec["id"] in spec_ids or not scenarios or set(scenarios) - ids or reference.is_absolute()
                or not target.is_relative_to(ROOT / "docs") or not target.is_file()):
            raise ValueError(f"无效设计书映射 {spec['id']}")
        spec_ids.add(spec["id"])
        referenced.update(scenarios)
    if referenced != ids:
        raise ValueError(f"以下场景未回链到 SPEC {sorted(ids - referenced)}")
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    filters = parser.add_mutually_exclusive_group()
    filters.add_argument("--group", action="append", choices=sorted({case.group for case in CHECKS}),
                         help="只跑指定领域，可重复传入")
    filters.add_argument("--check", action="append", choices=[case.key for case in CHECKS],
                         help="只跑指定编号，可重复传入")
    filters.add_argument("--layer", action="append", choices=LAYERS, help="按清单分类运行，可重复传入")
    filters.add_argument("--point", action="append", choices=[row["point"] for row in coverage_rows()],
                         help="按 docs/38 测试点运行，可重复传入")
    filters.add_argument("--coverage", action="store_true", help="列出清单测试点及现有直接探针")
    filters.add_argument("--stage", action="append", metavar="阶段", help="按设计验收阶段执行，可重复或传 all")
    filters.add_argument("--spec", action="append", metavar="SPEC-编号", help="执行指定设计书的关联场景，可重复")
    filters.add_argument("--matrix", action="store_true", help="显示设计场景矩阵和未自动化的验收证据")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果，适合 CI 或前后对比")
    args = parser.parse_args(argv)
    if args.coverage:
        coverage = list(coverage_rows())
        if args.json:
            print(json.dumps({"coverage": coverage}, ensure_ascii=False, indent=2))
        else:
            for row in coverage:
                checks = "、".join(row["checks"]) or "暂无直接探针"
                print(f"{row['point']} {row['severity']} {row['title']}  {checks}")
        return 0
    scoped_rows = []
    stage_checks = None
    if args.stage or args.spec or args.matrix:
        plan = stage_plan()
        if args.matrix:
            if args.json:
                print(json.dumps(plan, ensure_ascii=False, indent=2))
            else:
                for stage in plan["stages"]:
                    print(stage["title"])
                    for row in plan["scenarios"]:
                        if row["stage"] == stage["id"]:
                            status = "、".join(row["checks"]) or "待补验收"
                            print(f"  {row['id']} {row['scenario']} — {status}。取证 {row['evidence']}")
                for spec in plan["specs"]:
                    print(f"  {spec['id']} {spec['design']} — {'、'.join(spec['scenarios'])}")
            return 0
        available = [stage["id"] for stage in plan["stages"]]
        if args.spec:
            specs = {spec["id"]: spec["scenarios"] for spec in plan["specs"]}
            if set(args.spec) - specs.keys():
                parser.error("设计书编号必须为 " + "、".join(specs))
            selected = {scenario for spec in args.spec for scenario in specs[spec]}
            scoped_rows = [row for stage in available for row in plan["scenarios"]
                           if row["stage"] == stage and row["id"] in selected]
        else:
            requested = available if args.stage == ["all"] else args.stage
            if set(requested) - set(available):
                parser.error("阶段必须为 " + "、".join(available) + "，或单独使用 all")
            scoped_rows = [row for stage in available if stage in requested
                           for row in plan["scenarios"] if row["stage"] == stage]
        # 同一探针可以为多个场景举证，按首次出现顺序只执行一次。
        stage_checks = dict.fromkeys(key for row in scoped_rows for key in row["checks"])
    cases = [case for case in CHECKS
             if (not args.group or case.group in args.group)
             and (not args.check or case.key in args.check)
             and (not args.layer or case.layer in args.layer)
             and (not args.point or any(point in case.points for point in args.point))
             and (stage_checks is None or case.key in stage_checks)]
    if stage_checks is not None:
        indexed = {case.key: case for case in cases}
        cases = [indexed[key] for key in stage_checks]
    if not cases:
        parser.error("所选测试点暂无直接探针，请查看 --coverage")
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    results = []
    with TemporaryDirectory(prefix="project-audit-", dir=cache) as directory:
        work = Path(directory)
        # 父目录本身也在允许范围内，退出时可清理整棵临时目录。
        install_isolation(work)
        for case in cases:
            sandbox = work / case.key
            sandbox.mkdir()
            log = io.StringIO()
            try:
                with patch("tempfile.tempdir", str(sandbox)), redirect_stdout(log), redirect_stderr(log):
                    detail = case.run(sandbox)
                status = "PASS"
            except AssertionError as error:
                status, detail = "FAIL", str(error)
            except Exception as error:
                status, detail = "ERROR", f"{type(error).__name__}: {error}"
            result = {"id": case.key, "group": case.group, "severity": case.severity,
                      "layer": case.layer, "points": case.points,
                      "status": status, "location": case.location, "detail": detail}
            if status == "ERROR" and log.getvalue():
                result["log_tail"] = log.getvalue().splitlines()[-5:]
            results.append(result)

    counts = Counter(row["status"] for row in results)
    summary = {key: counts[key] for key in ("PASS", "FAIL", "ERROR")}
    pending = [row for row in scoped_rows if not row["checks"]]
    by_check = {row["id"]: row["status"] for row in results}
    scenarios = []
    for row in scoped_rows:
        statuses = {by_check[key] for key in row["checks"]}
        status = next((candidate for candidate in ("FAIL", "ERROR", "PASS") if candidate in statuses), "PENDING")
        scenarios.append(dict(row, status=status))
    if args.json:
        report = {"summary": summary, "checks": results}
        if scoped_rows:
            report["scenarios"] = scenarios
            report["pending_scenarios"] = [row["id"] for row in pending]
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for row in results:
            points = "/".join(row["points"])
            print(f"[{row['status']}] {row['id']} ({points}) {row['severity']} {row['location']} — {row['detail']}")
        print(f"总计 {len(results)} 项，" + "，".join(f"{key} {count}" for key, count in summary.items()))
        for row in pending:
            print(f"[PENDING] {row['id']} {row['scenario']} — {row['evidence']}")
    return int(bool(counts["FAIL"] or counts["ERROR"] or pending))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
