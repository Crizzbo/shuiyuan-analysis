"""运行独立金融模型核验，保存JSON和中文报告；失败返回非零退出码。"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.model_validation_lab import build_report, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/financial_model_validation", help="项目内相对输出目录")
    args = parser.parse_args()
    relative = Path(args.output)
    if relative.is_absolute() or ":" in args.output or args.output.startswith(("/", "\\")):
        parser.error("输出必须是项目内相对路径")
    output = (ROOT / relative).resolve()
    if not output.is_relative_to(ROOT):
        parser.error("输出不能越界")
    output = output / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    report = build_report(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "REPORT.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"report": str(output), "counts": report["counts"], "empirical_status": report["empirical_status"]}, ensure_ascii=False))
    return int(bool(report["counts"]["FAIL"] or report["counts"]["ERROR"] or not report["snapshot_stable"]))


if __name__ == "__main__":
    raise SystemExit(main())
