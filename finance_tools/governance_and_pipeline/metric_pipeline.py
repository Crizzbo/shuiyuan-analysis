"""指标接入层：校验事实口径、证据与可得时间，再调用现有开源计算接口。"""

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from finance_tools.service import calculate
from finance_tools.validation import number

ROOT = Path(__file__).resolve().parents[2]

# 此表是版本化执行口径，不自动改变原行业指标的经验验证状态。
BINDINGS = {
    "operating_margin": {"operation": "operating_margin", "inputs": ["operating_income", "revenue"],
                         "name_zh": "营业利润率", "formula": "同期间营业利润/同期间收入",
                         "basis": "GAAP", "denominator": "同期间合并收入"},
    "roe": {"operation": "roe", "inputs": ["common_net_income", "average_common_equity"],
            "name_zh": "普通股权益收益率", "formula": "普通股归属净利润/同期间平均普通股权益",
            "basis": "GAAP", "denominator": "需已有期初、期末权益平均值的核对依据"},
}


def instant(value):
    """时间必须带时区，禁止把分析日期自动当成财报可得时间。"""
    if not isinstance(value, str):
        raise ValueError("缺少可得时间")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("时间必须含时区")
    return result


def check_fact(fact, field, batch):
    """量纲/尺度/来源均显式校验；来源属性仍需研究者如实登记。"""
    required = {"id", "field", "entity_id", "scope_id", "period", "accounting_basis",
                "value", "unit", "currency", "scale", "source"}
    if not isinstance(fact, dict) or set(fact) != required or fact["field"] != field:
        raise ValueError(f"{field} 输入事实结构或字段含义错误")
    for key in ("id", "entity_id", "scope_id", "currency"):
        if not isinstance(fact[key], str) or not fact[key].strip():
            raise ValueError(f"{key} 必须非空")
    if fact["entity_id"] != batch["entity_id"] or fact["scope_id"] != batch["scope_id"]:
        raise ValueError("不能混用公司或合并/分部口径")
    if fact["unit"] != "currency" or fact["currency"] != batch["currency"]:
        raise ValueError("输入必须为同币种金额")
    if fact["accounting_basis"] != "GAAP":
        raise ValueError("本批绑定仅支持明确的 GAAP 口径，不混合调整后指标")
    period = fact["period"]
    if not isinstance(period, dict) or set(period) != {"start", "end", "basis"}:
        raise ValueError("期间结构错误")
    start, end = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
    if start > end or period["basis"] not in ("quarter", "annual", "ttm"):
        raise ValueError("期间无效；年度、季度和 TTM 不得混用")
    source = fact["source"]
    if not isinstance(source, dict) or set(source) != {"path", "sha256", "locator", "excerpt", "kind", "published_at", "available_at"}:
        raise ValueError("来源结构错误")
    if source["kind"] != ("synthetic" if batch["is_synthetic"] else "primary"):
        raise ValueError("真实计算需要原始来源，二次报告不能冒充原始财报")
    path = Path(source["path"])
    if path.is_absolute() or ":" in source["path"] or "\\" in source["path"] or ".." in path.parts:
        raise ValueError("来源必须是项目内相对路径")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError("来源文件不存在或越界")
    data = resolved.read_bytes()
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError("来源内容摘要不匹配")
    if not isinstance(source["locator"], str) or not source["locator"].strip():
        raise ValueError("缺少来源定位")
    if not isinstance(source["excerpt"], str) or not source["excerpt"].strip() or source["excerpt"] not in data.decode("utf-8"):
        raise ValueError("来源摘录无法在文本中核对；PDF需先按项目规则提取文本")
    published = instant(source["published_at"]) if source["published_at"] is not None else None
    if published is None and batch['schema_version'] != '1.1.0':
        raise ValueError('旧版请求必须提供精确发布时间；日期精度来源使用 1.1.0')
    available = instant(source["available_at"])
    if (published is not None and published > available) or available > instant(batch["as_of"]):
        raise ValueError("来源可得时间无效或晚于研究时点")
    if end > available.date():
        raise ValueError("期间结束晚于来源可得日期，不能把预测当成实际值")
    value = number(fact["value"], field)
    scale = number(fact["scale"], "scale", positive=True)
    return number(value * scale, "尺度换算结果")


def run_batch(batch):
    """逐项返回 blocked/computed；任何缺失值不填零，不执行失败项。"""
    expected = {"schema_version", "entity_id", "scope_id", "industry_id", "currency",
                "as_of", "is_synthetic", "facts", "requests"}
    if not isinstance(batch, dict) or set(batch) != expected or batch["schema_version"] not in ("1.0.0", "1.1.0"):
        raise ValueError("批请求结构错误")
    if type(batch["is_synthetic"]) is not bool:
        raise ValueError("is_synthetic 必须为布尔值")
    instant(batch["as_of"])
    if not isinstance(batch["facts"], list) or not isinstance(batch["requests"], list) or not batch["requests"]:
        raise ValueError("facts/requests 必须为列表，请求不能为空")
    catalog = json.loads((ROOT / "knowledge/metrics/catalog.json").read_text(encoding="utf-8"))
    ids = {x["id"] for x in catalog["metrics"]}
    industry_path = ROOT / "knowledge/contracts/industries" / f"{batch['industry_id']}.json"
    # 行业 ID 只允许现有文件的 stem，防止以行业参数绕过项目边界。
    industries = {x.stem for x in (ROOT / "knowledge/contracts/industries").glob("*.json")}
    if batch["industry_id"] not in industries:
        raise ValueError("未知行业")
    if not isinstance(batch["currency"], str) or len(batch["currency"]) != 3 or not batch["currency"].isascii() or not batch["currency"].isalpha() or not batch["currency"].isupper():
        raise ValueError("币种必须为三位大写 ASCII 代码")
    industry = json.loads(industry_path.read_text(encoding="utf-8"))
    rows = []
    for metric in batch["requests"]:
        if metric not in ids:
            raise ValueError("未知指标 ID")
        if metric not in BINDINGS:
            rows.append({"metric_id": metric, "status": "blocked", "value": None,
                         "reason": "尚无经明确口径的执行绑定，不能用相似公式替代"})
            continue
        binding = BINDINGS[metric]
        try:
            if batch["industry_id"] != "software":
                raise ValueError("首批执行口径仅审核了软件行业，其他行业须先完成适用性映射")
            selected, values = [], []
            for field in binding["inputs"]:
                candidates = [x for x in batch["facts"] if isinstance(x, dict) and x.get("field") == field]
                if len(candidates) != 1:
                    raise ValueError(f"{field} 缺失或有多个候选，必须明确选择")
                selected.append(candidates[0])
                values.append(check_fact(candidates[0], field, batch))
            if selected[0]["id"] == selected[1]["id"]:
                raise ValueError("不同输入事实不能使用同一 ID")
            if selected[0]["period"] != selected[1]["period"]:
                raise ValueError("分子分母期间不同")
            calc = calculate("financial_ratio", {"operation": binding["operation"],
                            "numerator": values[0], "denominator": values[1]})
            rows.append({"metric_id": metric, "status": "computed", "unit": "ratio", "currency": None,
                         "period": selected[0]["period"], "value": calc["result"]["value"],
                         "input_fact_refs": [x["id"] for x in selected], "input_facts": selected, "calculation": calc})
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            rows.append({"metric_id": metric, "status": "blocked", "value": None, "reason": str(error)})
    blocked = [x["metric_id"] for x in rows if x["status"] == "blocked"]
    required = industry["required_metric_ids"]
    missing = [x for x in required if not any(r["metric_id"] == x and r["status"] == "computed" for r in rows)]
    return {"schema_version": "1.0.0", "entity_id": batch["entity_id"], "industry_id": batch["industry_id"],
            "as_of": batch["as_of"], "is_synthetic": batch["is_synthetic"], "binding_version": "1.0.0",
            "input_batch_sha256": hashlib.sha256(json.dumps(batch, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest(),
            "binding_implementation_path": "finance_tools/metric_pipeline.py",
            "binding_implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "results": rows, "blocked_metric_ids": blocked, "missing_industry_driver_ids": missing,
            "research_readiness": {"S1": "pending_industry_evidence", "S2": "blocked" if blocked or missing else "pending_review",
                                   "S3": "pending_transmission_evidence", "S4": "pending_valuation_inputs",
                                   "S5": "pending_risk_evidence", "S6": "pending_monitoring_plan"},
            "research_export_status": "staging_only_raw_facts_not_registered_as_research_observations"}
