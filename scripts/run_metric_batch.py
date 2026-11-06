"""项目内指标批计算入口；输出为研究准备记录，不伪造完成六步分析。"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finance_tools.metric_pipeline import run_batch
from calculate_finance import local_path
from validate_research import load, structural
from jsonschema import Draft202012Validator, FormatChecker


def main():
    parser = argparse.ArgumentParser(description="本地行业指标接入验证")
    parser.add_argument("request")
    parser.add_argument("--output")
    args = parser.parse_args()
    request = load(local_path(args.request))
    schema = load(ROOT / "schemas/metric-batch.schema.json")
    # 标准校验器支持 1.1.0 的可空时间；旧简化校验器只支持单一 type。
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(request)
    result = run_batch(request)
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        target = local_path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            stream.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
