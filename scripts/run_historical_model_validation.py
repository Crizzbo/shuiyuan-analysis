"""仅使用已归档真实历史文件进行时间滚动风险诊断与现金流基准评估。"""
from __future__ import annotations
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import importlib.metadata
from io import BytesIO, StringIO
import json
import math
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from financial_core.engines.filing_mapper import OfficialFilingMapper
from financial_core.engines.portfolio_risk_engine import PortfolioRiskAndVaREngine
from scripts.history_validation_ledger import HistoryValidationLedger, local_path, digest_file


def parse_factor_zip(raw: bytes, start: str, end: str) -> tuple[list[dict], dict]:
    """解析发布者日频CSV，百分数转小数，不插值、不补交易日。"""
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        names = [x for x in archive.namelist() if x.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError("ZIP必须恰含一个CSV文件")
        member = archive.getinfo(names[0])
        if member.file_size > 12_000_000:
            raise ValueError("展开CSV超过大小上限")
        text = archive.read(names[0]).decode("utf-8-sig")
    rows = list(csv.reader(StringIO(text)))
    header = next((i for i, r in enumerate(rows) if "Mkt-RF" in [x.strip() for x in r] and "RF" in [x.strip() for x in r]), None)
    if header is None:
        raise ValueError("缺少Mkt-RF/RF字段")
    cols = [x.strip() for x in rows[header]]
    mi, ri = cols.index("Mkt-RF"), cols.index("RF")
    result, last, excluded = [], None, []
    for line in rows[header + 1:]:
        if not line or not re.fullmatch(r"\d{8}", line[0].strip()):
            continue
        day = datetime.strptime(line[0].strip(), "%Y%m%d").date().isoformat()
        if last and day <= last:
            raise ValueError("历史日期重复或乱序")
        last = day
        if not start <= day <= end:
            continue
        values = [line[mi].strip(), line[ri].strip()]
        if any(x in ("-99.99", "-999", "-999.0", "-999.00", "") for x in values):
            excluded.append({"date": day, "reason": "publisher_missing_sentinel"})
            continue
        excess, rf = [float(x) / 100 for x in values]
        total = excess + rf
        if not all(math.isfinite(v) for v in (excess, rf, total)) or total < -1:
            raise ValueError("收益率非有限或低于有限责任下界")
        result.append({"date": day, "market_excess_return": excess, "risk_free_return": rf, "total_market_return": total})
    if not result:
        raise ValueError("所选区间无有效真实数据")
    return result, {"member": names[0], "selected_start": result[0]["date"], "selected_end": result[-1]["date"], "rows": len(result), "excluded": excluded}


def training_window(values: list, index: int, lookback: int):
    """预测第index条时只用前lookback条，禁止包含当天收益。"""
    if lookback < 10 or index < lookback or index >= len(values):
        raise ValueError("回放窗口不足或索引非法")
    return np.asarray(values[index - lookback:index], dtype=float)


def quantile_loss(loss, forecast, confidence):
    """对损失的上分位数采用一致评分；较小更好，不等于交易收益。"""
    residual = np.asarray(loss) - np.asarray(forecast)
    return (confidence - (residual < 0).astype(float)) * residual


def block_mean_interval(values, block: int, repetitions: int, seed: int):
    """移动区块重采样，保留短期时间依赖；不能保证覆盖所有长程相关。"""
    values = np.asarray(values, dtype=float)
    if len(values) < block or block < 1 or repetitions < 100:
        raise ValueError("重采样参数或样本不足")
    rng = np.random.default_rng(seed)
    n, nblocks = len(values), math.ceil(len(values) / block)
    means = []
    for _ in range(repetitions):
        starts = rng.integers(0, n - block + 1, nblocks)
        indices = (starts[:, None] + np.arange(block)).ravel()[:n]
        means.append(float(values[indices].mean()))
    return [float(x) for x in np.quantile(means, [.025, .975])]


def longest_run(flags) -> int:
    """报告连续超限的聚集程度，不据此宣称统计独立。"""
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def evaluate_risk(rows: list[dict], protocol: dict, series: str):
    """原模型逐日滚动执行，历史分位数作为事前固定的简单基准。"""
    config = protocol["evaluation"]
    lookback = config["lookback_observations"]
    values = [r["total_market_return"] for r in rows]
    predictions = []
    engine = PortfolioRiskAndVaREngine()
    for i, row in enumerate(rows):
        if not config["start"] <= row["date"] <= config["end"]:
            continue
        if i < lookback:
            raise ValueError("评价期开始前的训练历史不足，不缩短窗口")
        past = training_window(values, i, lookback)
        loss = -row["total_market_return"]
        for confidence in config["confidence_levels"]:
            result = engine.compute_var_cvar(past, portfolio_value=1_000_000, confidence_level=confidence, time_horizon_days=1, currency_symbol="$")
            baseline = max(0.0, min(1.0, float(np.quantile(-past, confidence, method="linear"))))
            forecasts = {"parametric": result.parametric_var / 1_000_000,
                         "cornish_fisher": result.cornish_fisher_var / 1_000_000,
                         "historical_baseline": baseline}
            if abs(result.historical_var / 1_000_000 - baseline) > .0000000051:
                raise ValueError("历史分位数独立基准与引擎金额输出不一致")
            for method, estimate in forecasts.items():
                predictions.append({"series": series, "date": row["date"], "training_start": rows[i-lookback]["date"],
                    "training_end": rows[i-1]["date"], "confidence": confidence, "method": method,
                    "observed_return": row["total_market_return"], "loss": loss, "var": estimate,
                    "breach": loss > estimate, "quantile_loss": float(quantile_loss(loss, estimate, confidence)),
                    "engine_historical_es": result.expected_shortfall_cvar / 1_000_000})
    summaries = []
    for confidence in config["confidence_levels"]:
        baseline = [x for x in predictions if x["method"] == "historical_baseline" and x["confidence"] == confidence]
        base_scores = np.array([x["quantile_loss"] for x in baseline])
        for method in ("parametric", "cornish_fisher", "historical_baseline"):
            current = [x for x in predictions if x["method"] == method and x["confidence"] == confidence]
            if not current:
                raise ValueError("评价区间没有预测结果")
            flags = [x["breach"] for x in current]
            delta = np.array([x["quantile_loss"] for x in current]) - base_scores
            bootstrap = config["bootstrap"]
            sensitivity = {str(block): block_mean_interval(delta, block, bootstrap["repetitions"], bootstrap["seed"]) for block in bootstrap["block_lengths"]}
            yearly = {}
            for year in sorted({x["date"][:4] for x in current}):
                subset = [x for x in current if x["date"].startswith(year)]
                yearly[year] = {"n": len(subset), "breaches": sum(x["breach"] for x in subset), "breach_rate": sum(x["breach"] for x in subset)/len(subset)}
            summaries.append({"series": series, "method": method, "confidence": confidence, "n": len(current),
                "breaches": sum(flags), "breach_rate": sum(flags) / len(flags), "nominal_breach_rate": 1 - confidence,
                "longest_breach_run": longest_run(flags), "mean_quantile_loss": float(np.mean([x["quantile_loss"] for x in current])),
                "mean_loss_difference_vs_historical": float(delta.mean()), "paired_block_bootstrap_95_intervals": sensitivity,
                "yearly": yearly, "evidence_status": "RETROSPECTIVE_REVISED_DATA_DIAGNOSTIC"})
    return predictions, summaries


def parse_microsoft_cash_flow(html: str, fiscal_year: int) -> dict:
    """从发行人现金流量表提取当年CFO/资本开支；只经Mapper清洗数字。"""
    def values(row):
        out = []
        for raw in list(row)[1:]:
            if pd.isna(raw):
                continue
            text = str(raw).strip()
            if text in ("", "$", "nan"):
                continue
            value = OfficialFilingMapper.parse_optional_financial_number(text, "cash_flow_cell")
            if value is not None:
                out.append(value)
        return out
    matches = []
    for index, table in enumerate(pd.read_html(StringIO(html))):
        full_text = table.to_string(index=False, header=False)
        if "Net cash from operations" not in full_text or "Additions to property and equipment" not in full_text:
            continue
        if "million" not in full_text.lower():
            raise ValueError("现金流量表缺少百万单位声明")
        cfo = capex = None
        years = []
        for _, row in table.iterrows():
            label = " ".join(str(row.iloc[0]).split())
            if "Year Ended June 30" in label:
                years = values(row)
            if label == "Net cash from operations":
                cfo = values(row)
            if label == "Additions to property and equipment":
                capex = values(row)
        if not years or int(years[0]) != fiscal_year or not cfo or not capex:
            raise ValueError("现金流表年份/列位置或科目不匹配")
        if capex[0] > 0:
            raise ValueError("资本开支符号与现金流出约定不一致")
        matches.append({"fiscal_year": fiscal_year, "period_end": f"{fiscal_year}-06-30", "currency": "USD", "unit": "million",
            "operating_cash_flow": cfo[0], "capex_cash_outflow_signed": capex[0], "fcf_proxy": cfo[0] + capex[0],
            "definition": "CFO plus signed cash additions to property and equipment; excludes finance-lease noncash capex; not automatically FCFF",
            "locator": f"HTML table {index}; first fiscal-year column; Net cash from operations / Additions to property and equipment"})
    if len(matches) != 1:
        raise ValueError("现金流表未唯一匹配")
    return matches[0]


def cashflow_baselines(rows):
    """仅比较现金流基准和默认10%增长情景，不把它冒称完整DCF效果。"""
    rows = sorted(rows, key=lambda r: r["fiscal_year"])
    cases = []
    for i in range(1, len(rows)):
        previous, actual = rows[i-1], rows[i]
        if actual["fiscal_year"] != previous["fiscal_year"] + 1:
            continue
        for method, prediction in (("persistence", previous["fcf_proxy"]), ("fixed_10pct_scenario", previous["fcf_proxy"] * 1.1)):
            cases.append({"method": method, "information_year": previous["fiscal_year"], "target_year": actual["fiscal_year"],
                          "prediction": prediction, "actual": actual["fcf_proxy"], "absolute_error": abs(prediction - actual["fcf_proxy"])})
    summary = []
    for method in ("persistence", "fixed_10pct_scenario"):
        selected = [x for x in cases if x["method"] == method]
        summary.append({"method": method, "n": len(selected), "mae_usd_million": float(np.mean([x["absolute_error"] for x in selected])) if selected else None,
                        "status": "SMALL_SAMPLE_BASELINE_ONLY_NOT_DCF_VALIDATION"})
    return cases, summary


def write_csv(path, rows):
    """新文件独占写入，不覆盖历史结果。"""
    if not rows:
        raise ValueError("拒绝写入空预测集")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def report_markdown(result):
    """将计算口径、历史修订限制和模型结果一起展示。"""
    lines = ["# 真实历史数据回放报告", "", f"生成时间：{result['generated_at']}", "",
        "本轮为历史数据修订版的回顾诊断，不是实时行情、严格历史可用版本回测或交易收益验证。模型和参数未根据结果调优。", "",
        "## 已归档真实资料", "", "| 数据 | 行数 | 起止 | 口径 |", "|---|---:|---|---|"]
    for series, info in result["datasets"].items():
        lines.append(f"| {series} | {info['rows']} | {info['selected_start']} 至 {info['selected_end']} | Mkt-RF + RF，百分数转小数；美元研究组合总收益 |")
    lines += [f"\n另提取微软 {len(result['cashflow_facts'])} 个财政年度的原始CFO和现金资本开支，均为百万美元。", "",
        "## 风险模型滚动结果", "", "仅使用预测日前252条记录，评价2018—2024年下一条日频记录；每个市场分别计算。", "",
        "| 市场 | 方法 | 置信度 | 预测数 | 超限数 | 实际超限率 | 名义超限率 | 最长连续超限 |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in result["risk_summary"]:
        lines.append(f"| {row['series']} | {row['method']} | {row['confidence']:.0%} | {row['n']} | {row['breaches']} | {row['breach_rate']:.2%} | {row['nominal_breach_rate']:.2%} | {row['longest_breach_run']} |")
    lines += ["", "超限率高于名义值表示该样本下损失超过VaR的次数较多，不单凭这一个指标做模型通过/不通过判定。", "",
        "## 相对于历史分位数基准的分位数损失", "", "差值为负表示平均分位数损失较低；为正表示较高。区间用成对移动区块重采样，保留部分时间相关。", "",
        "| 市场 | 方法 | 置信度 | 平均损失差 | 20日区块95%区间 |", "|---|---|---:|---:|---|"]
    for row in result["risk_summary"]:
        if row["method"] != "historical_baseline":
            lines.append(f"| {row['series']} | {row['method']} | {row['confidence']:.0%} | {row['mean_loss_difference_vs_historical']:.8f} | {row['paired_block_bootstrap_95_intervals']['20']} |")
    lines += ["", "完整结果另含5/60日区块敏感性、逐年超限数及逐日预测CSV；这不是对所有时间依赖的保证，亦非多重比较调整后的胜出声明。", "",
        "## 现金流小样本基准", "", "| 方法 | 对照年数 | MAE（百万美元） |", "|---|---:|---:|"]
    for row in result["cashflow_baseline_summary"]:
        lines.append(f"| {row['method']} | {row['n']} | {row['mae_usd_million']} |")
    lines += ["", "固定10%是预设比较情景，不是完整生产DCF的预测输出；CFO减现金资本开支也不自动等于FCFF。仅单家公司年度小样本，未验证内在价值、股票收益或行业泛化。", "",
        "## 证据边界", "",
        "- 原始文件来自Kenneth French数据发布站和微软发行人年报；来源清单、下载时刻和SHA-256与本轮结果一起保存。", "- US/JP均为研究组合收益；JP为美元计价，包含汇率影响，不等同日元TOPIX或可直接交易的ETF。", "- 今日下载的历史可能经修订。available_at使用本次采集时刻，不回填历史首次可用日期；没有声称严格point-in-time。", "- 未收集历史期权链、违约样本和可识别事件分部标签，因此没有检验这些模型的真实效果。", "- 既有独立合成核验的9个失败项仍未修复；真实样本诊断不能覆盖这些边界缺陷。", "- 本轮为探索性诊断，没有冻结的数值上线门槛，也没有宣称交易盈利。", "",
        "## 本轮文件", "", "- `risk_predictions.csv`：逐日训练区间、预测、实际损失和评分。", "- `cashflow_facts.json`：官方现金流提取值与原文定位。", "- `results.json`：汇总、逐年统计与不确定区间。", "- `attestation.json`：PredictionLedger兼容子类的产物链头及验签结果。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", help="已归档collection.json的项目内相对路径")
    args = parser.parse_args()
    collection_path = local_path(ROOT, args.collection)
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    protocol_path = collection_path.parent / "protocol.json"
    if digest_file(protocol_path) != collection["config_sha256"]:
        raise ValueError("冻结协议摘要不符")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    code_paths = (Path(__file__), ROOT/"financial_core/engines/portfolio_risk_engine.py", ROOT/"scripts/history_validation_ledger.py", ROOT/"financial_core/engines/filing_mapper.py", ROOT/"scripts/collect_model_validation_history.py")
    code_before = {p.relative_to(ROOT).as_posix(): digest_file(p) for p in code_paths}
    output = ROOT / "reports/historical_model_validation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output.mkdir(parents=True, exist_ok=False)
    archived_code = []
    for path in code_paths:
        archived = output / "code" / path.relative_to(ROOT)
        archived.parent.mkdir(parents=True, exist_ok=True)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != code_before[path.relative_to(ROOT).as_posix()]:
            raise ValueError("代码归档时摘要改变")
        archived.write_bytes(raw)
        archived_code.append(archived)
    lock_copy = output / "code/requirements-ci.lock.txt"
    lock_copy.write_bytes((ROOT/"requirements-ci.lock.txt").read_bytes())
    archived_code.append(lock_copy)
    normalized = collection_path.parent / "normalized" / output.name
    normalized.mkdir(parents=True, exist_ok=False)
    sources = {x["id"]: x for x in collection["sources"]}
    # 所有输入先验签；文件URL只作来源身份，不触发网络读取。
    artifacts = [collection_path, protocol_path, *archived_code]
    for source in sources.values():
        path = local_path(ROOT, source["path"])
        if digest_file(path) != source["sha256"]:
            raise ValueError("原始文件摘要不符：" + source["id"])
        artifacts.append(path)
    predictions, risk_summary, datasets = [], [], {}
    for key, series in (("ff_us_daily", "US_research_market_USD"), ("ff_japan_daily", "JP_research_market_USD")):
        source = sources[key]
        rows, info = parse_factor_zip(local_path(ROOT, source["path"]).read_bytes(), protocol["normalization_start"], protocol["evaluation"]["end"])
        rows_path = normalized / (key + ".csv")
        write_csv(rows_path, rows)
        artifacts.append(rows_path)
        info.update({"source_path": source["path"], "source_sha256": source["sha256"], "normalized_path": rows_path.relative_to(ROOT).as_posix(), "source_url": source["url"]})
        datasets[series] = info
        series_predictions, summary = evaluate_risk(rows, protocol, series)
        predictions.extend(series_predictions)
        risk_summary.extend(summary)
    facts, extraction_failures = [], []
    for source in sources.values():
        if source.get("role") != "microsoft_cashflow":
            continue
        try:
            fact = parse_microsoft_cash_flow(local_path(ROOT, source["path"]).read_text(encoding="utf-8-sig"), source["fiscal_year"])
            fact.update({"source_path": source["path"], "source_sha256": source["sha256"], "available_at": source["acquired_at"]})
            facts.append(fact)
        except (ValueError, ImportError) as exc:
            extraction_failures.append({"id": source["id"], "error": str(exc)})
    financial_cases, financial_summary = cashflow_baselines(facts)
    result = {"schema_version": "1.0.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "RETROSPECTIVE_DIAGNOSTIC_NOT_PRODUCTION_VALIDATION", "collection": args.collection,
        "collection_sha256": digest_file(collection_path), "protocol_sha256": digest_file(protocol_path),
        "datasets": datasets, "risk_summary": risk_summary, "cashflow_facts": facts,
        "cashflow_baseline_cases": financial_cases, "cashflow_baseline_summary": financial_summary,
        "collection_failures": collection["failures"], "extraction_failures": extraction_failures,
        "code_sha256": code_before,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": importlib.metadata.version("scipy"), "lock_sha256": digest_file(ROOT/"requirements-ci.lock.txt")}}
    if code_before != {p.relative_to(ROOT).as_posix(): digest_file(p) for p in code_paths}:
        raise ValueError("运行期间计算代码改变，结果不能验收")
    write_csv(output / "risk_predictions.csv", predictions)
    (output / "cashflow_facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "REPORT.md").write_text(report_markdown(result), encoding="utf-8")
    artifacts.extend([output/"risk_predictions.csv", output/"cashflow_facts.json", output/"results.json", output/"REPORT.md"])
    ledger = HistoryValidationLedger(ROOT, ROOT / "data/history/model_validation/validation_ledger.sqlite3")
    chain_head = ledger.append_validation(artifacts, {"scope": result["status"], "report": output.relative_to(ROOT).as_posix(), "protocol_sha256": result["protocol_sha256"]})
    verified = ledger.verify_integrity()
    (output / "attestation.json").write_text(json.dumps({"chain_head": chain_head, "ledger_verified": verified.is_valid, "error": verified.error,
        "note": "本地摘要链不构成独立外部时间见证，不证明历史预测在当年产生"}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not verified.is_valid:
        raise ValueError(verified.error)
    print(json.dumps({"report": output.relative_to(ROOT).as_posix(), "series": len(datasets), "risk_prediction_rows": len(predictions), "cashflow_years": len(facts), "extraction_failures": len(extraction_failures), "ledger_verified": True}, ensure_ascii=False))
    return int(bool(extraction_failures or collection["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
