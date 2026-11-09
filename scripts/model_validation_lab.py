"""金融模型独立核验：只运行本地、明确标记的合成实验，不作投资有效性评级。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sqlite3
import statistics
import platform
import sys
from typing import Callable


@dataclass
class Check:
    """单项核验记录，数值容忍度仅用于计算验证。"""
    case_id: str
    model: str
    description: str
    status: str
    actual: float | str | None = None
    expected: float | str | None = None
    tolerance: float | None = None
    error: str = ""
    data_origin: str = "synthetic"


def compare(case_id: str, model: str, description: str, actual: float,
            expected: float, tolerance: float = 1e-8) -> Check:
    """只接受有限数值，误差超容忍度如实报告。"""
    valid = math.isfinite(actual) and math.isfinite(expected)
    passed = valid and abs(actual - expected) <= tolerance
    return Check(case_id, model, description, "PASS" if passed else "FAIL",
                 actual if math.isfinite(actual) else repr(actual), expected, tolerance)


def require_rejection(case_id: str, model: str, description: str,
                      call: Callable[[], object]) -> Check:
    """非法输入必须显式拒绝；异常类型错误不能算保护通过。"""
    try:
        call()
    except (ValueError, TypeError) as exc:
        return Check(case_id, model, description, "PASS", type(exc).__name__, "ValueError/TypeError")
    except Exception as exc:
        return Check(case_id, model, description, "ERROR", error=f"{type(exc).__name__}: {exc}")
    return Check(case_id, model, description, "FAIL", "silently_accepted", "explicit_rejection")


def bsm_reference(spot: float, strike: float, rate: float,
                  sigma: float, years: float, is_call: bool = True) -> float:
    """独立标准库解析参考，仅限零分红欧式期权；不调用被测定价实现。"""
    if years == 0:
        return max(0.0, spot - strike if is_call else strike - spot)
    if sigma == 0:
        payoff = spot - strike * math.exp(-rate * years)
        return max(0.0, payoff if is_call else -payoff)
    normal = statistics.NormalDist().cdf
    d1 = (math.log(spot / strike) + (rate + sigma * sigma / 2) * years) / (sigma * math.sqrt(years))
    d2 = d1 - sigma * math.sqrt(years)
    if is_call:
        return spot * normal(d1) - strike * math.exp(-rate * years) * normal(d2)
    return strike * math.exp(-rate * years) * normal(-d2) - spot * normal(-d1)


def run_dcf() -> list[Check]:
    """零增长永续流的解析值和经济等价变换，不复制引擎衰减算法。"""
    from financial_core.engines.monte_carlo_engine import MonteCarloDCFInput, MonteCarloValuationEngine
    engine = MonteCarloValuationEngine()
    p = MonteCarloDCFInput(
        base_cash_flow=100, current_price=10, shares_outstanding=100, net_debt=200,
        growth_mean=0, growth_std=0, wacc_mean=.1, wacc_std=0,
        terminal_g_mean=0, terminal_g_std=0)
    def value(params):
        return engine.run_monte_carlo_dcf("SYNTHETIC_VALIDATION", params, iterations=1000).mean_fair_value
    out = [compare("DCF-01", "DCF", "零增长现金流解析值：max(FCF/r-净债务,0)/股数", value(p), 8)]
    out.append(compare("DCF-02", "DCF", "现金流/净债务/股数同比缩放保持每股价值", value(replace(p, base_cash_flow=1000, net_debt=2000, shares_outstanding=1000)), 8))
    out.append(compare("DCF-03", "DCF", "现价改变不应反向改变模型公允价值", value(replace(p, current_price=100)), 8))
    out.append(compare("DCF-04", "DCF", "净债务增加100对应每股价值减少1", value(replace(p, net_debt=300)), 7))
    out.append(compare("DCF-05", "DCF", "零增长折现率提高的解析参考", value(replace(p, wacc_mean=.125)), 6))
    out.append(compare("DCF-06", "DCF", "持续负现金流且无现金储备的有限责任价值应为零", value(replace(p, base_cash_flow=-100, net_debt=0)), 0))
    small = replace(p, base_cash_flow=.001, net_debt=.002, shares_outstanding=.001)
    out.append(compare("DCF-07", "DCF", "极小但有效的百万单位股数与现金流保持比例", value(small), 8))
    out.append(require_rejection("DCF-08", "DCF", "零股数不能静默替换为其他股数", lambda: value(replace(p, shares_outstanding=0))))
    out.append(require_rejection("DCF-09", "DCF", "缺失企业财务字段不能生成默认估值", lambda: MonteCarloDCFInput.from_firm_financial_fact(object())))
    return out


def run_options() -> list[Check]:
    """解析参照和美式价值边界；容忍度预设为离散价格误差而非收益门槛。"""
    from financial_core.engines.american_option_tree_engine import AmericanOptionTreeInput, AmericanOptionTreeEngine
    engine = AmericanOptionTreeEngine()
    p = AmericanOptionTreeInput(100, 100, 1, .05, .2, steps=300)
    out = []
    for index, strike in enumerate((80, 100, 120), 1):
        x = replace(p, strike_price=strike)
        out.append(compare(f"OPT-0{index}", "OPTION", "无分红正利率美式Call与独立欧式解析值比较", engine.price_crr_tree(x)["american_price"], bsm_reference(100, strike, .05, .2, 1), .04))
    put = engine.price_crr_tree(replace(p, is_call=False, spot_price=80))
    lower = max(20, bsm_reference(80, 100, .05, .2, 1, False))
    out.append(compare("OPT-04", "OPTION", "美式Put不能低于立即行权和欧式Put", float(put["american_price"] + 1e-4 >= lower), 1, 0))
    zero = replace(p, implied_vol=0, risk_free_rate=0)
    try:
        out.append(compare("OPT-05", "OPTION", "零波动零利率平价期权应为零或明确拒绝", engine.price_crr_tree(zero)["american_price"], 0, 1e-4))
    except ValueError:
        out.append(Check("OPT-05", "OPTION", "零波动不支持时明确拒绝", "PASS", "ValueError", "correct_limit_or_rejection"))
    out.append(require_rejection("OPT-06", "OPTION", "负到期时间应显式拒绝", lambda: engine.price_crr_tree(replace(p, time_to_expiry_years=-1))))
    out.append(require_rejection("OPT-07", "OPTION", "非有限现价应显式拒绝", lambda: engine.price_crr_tree(replace(p, spot_price=float("nan")))))
    return out


def run_risk() -> list[Check]:
    """用标准库分位数核对参数VaR；不把合成样本当历史风险校准。"""
    from financial_core.engines.portfolio_risk_engine import PortfolioRiskAndVaREngine
    returns = [i / 10000 for i in range(-200, 201)]
    engine = PortfolioRiskAndVaREngine()
    def risk(values=returns, **kwargs):
        return engine.compute_var_cvar(values, portfolio_value=1_000_000, **kwargs)
    out = []
    for index, confidence in enumerate((.95, .99), 1):
        expected = statistics.NormalDist().inv_cdf(confidence) * statistics.stdev(returns)
        # 公开比例字段舍入至四位小数；使用金额字段并容忍半分的输出舍入误差。
        out.append(compare(f"RISK-0{index}", "RISK", "独立正态分位数与样本标准差核验参数VaR金额", risk(confidence_level=confidence).parametric_var, expected * 1_000_000, .0050001))
    expected_ten = statistics.NormalDist().inv_cdf(.95) * statistics.stdev(returns) * math.sqrt(10) * 1_000_000
    out.append(compare("RISK-03", "RISK", "单期正态假设下的10日期限缩放金额", risk(time_horizon_days=10).parametric_var, expected_ten, .0050001))
    out.append(require_rejection("RISK-04", "RISK", "置信度超过1应显式拒绝", lambda: risk(confidence_level=1.2)))
    out.append(require_rejection("RISK-05", "RISK", "非有限收益率应显式拒绝", lambda: risk([float("nan")] + returns)))
    out.append(require_rejection("RISK-06", "RISK", "零风险期限应显式拒绝", lambda: risk(time_horizon_days=0)))
    return out


def run_sotp() -> list[Check]:
    """强制指定暴露，检验传导边界；不验证自然语言冲击识别的准确率。"""
    from financial_core.engines.sotp_event_penetration_engine import BusinessSegment, SotpEventPenetrationEngine
    from financial_core.engines.event_radar_engine import StructuredEventSummary
    event = StructuredEventSummary(
        event_id="SYNTHETIC_VALIDATION", timestamp="2026-01-01T00:00:00Z",
        category="Other_Macro_Event", involved_entities=["SYNTHETIC"],
        micro_physical_impact="合成成本增加10%", estimated_duration="30天",
        affected_business_segments=["合成"], severity_level="P1", requires_deep_analysis=True,
        raw_title="合成成本冲击", source_name="synthetic_fixture")
    segment = BusinessSegment("TEST", "合成", "Synthetic", 100, 1, .2, 20, 0, 0)
    engine = SotpEventPenetrationEngine()
    def impact(s=segment, exposure=1):
        return engine.calculate_segment_impact(s, event, exposure, "合成固定暴露")
    out = [compare("SOTP-01", "SOTP", "零暴露不得产生盈利冲击", impact(exposure=0).operating_income_impact, 0)]
    out.append(compare("SOTP-02", "SOTP", "完全成本转嫁时净成本冲击归零", impact(replace(segment, cost_pass_through_power=1)).operating_income_impact, 0))
    base = impact().operating_income_impact
    out.append(compare("SOTP-03", "SOTP", "较高库存缓冲不得加剧同一不利成本冲击", float(abs(impact(replace(segment, inventory_buffer_days=30)).operating_income_impact) <= abs(base)), 1, 0))
    out.append(compare("SOTP-04", "SOTP", "相同暴露下规模翻倍对应EBIT冲击翻倍", impact(replace(segment, revenue=200, operating_income=40)).operating_income_impact, 2 * base))
    return out


def run_checks() -> list[Check]:
    """每个模型组单独隔离异常，保证失败模型仍被报告。"""
    rows = []
    for name, fn in (("DCF", run_dcf), ("OPTION", run_options), ("RISK", run_risk), ("SOTP", run_sotp)):
        try:
            rows.extend(fn())
        except Exception as exc:
            rows.append(Check(f"{name}-RUNNER", name, "模型组执行异常", "ERROR", error=f"{type(exc).__name__}: {exc}"))
    return rows


def inventory(root: Path) -> dict:
    """只读盘点账本结构和时间范围，不输出私有预测或写入正式账本。"""
    path = root / ".cache/model_validation_input/predictions_ledger.sqlite3"
    if not path.exists():
        path = root / "data/ledger/predictions_ledger.sqlite3"
    result = {"status": "INSUFFICIENT_EVIDENCE", "reason": "现有账本不能单独证明输入历史可用性、固定期限或独立存证", "database_present": path.exists()}
    if path.exists():
        result["input_path"] = path.relative_to(root).as_posix()
        result["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
            result["rows"] = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in ("predictions", "outcomes", "retrospective_reviews") if t in tables}
            if "predictions" in tables:
                result["prediction_dates"] = list(conn.execute("select min(prediction_date),max(prediction_date) from predictions").fetchone())
                columns = {r[1] for r in conn.execute("pragma table_info(predictions)")}
                required = ["model_version", "information_cutoff", "horizon_end", "input_manifest_sha256", "data_origin", "experiment_id"]
                result["missing_first_class_columns"] = [name for name in required if name not in columns]
    result["not_scored"] = ["历史预测有效性", "真实交易收益", "概率校准", "因果效应"]
    return result


def source_digest(root: Path) -> dict[str, str]:
    """绑定实际参与验证的核心和测试源码，排除运行产物。"""
    paths = list((root / "financial_core").rglob("*.py"))
    paths += [root / "scripts/model_validation_lab.py", root / "scripts/run_financial_model_validation.py"]
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def build_report(root: Path) -> dict:
    """代码运行前后摘要一致才允许称为同一快照结果。"""
    before = source_digest(root)
    rows = run_checks()
    after = source_digest(root)
    snapshot = root / "config/model_validation_source_snapshot.json"
    lock = root / "requirements-ci.lock.txt"
    return {
        "schema_version": "1.0.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "synthetic_independent_calculation_and_boundary_checks",
        "empirical_status": "INSUFFICIENT_EVIDENCE", "snapshot_stable": before == after,
        "source_sha256": before, "inventory": inventory(root),
        "environment": {"python": platform.python_version(), "executable": str(Path(sys.executable).relative_to(root)),
                        "numpy": importlib.metadata.version("numpy"), "scipy": importlib.metadata.version("scipy"),
                        "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
                        "source_snapshot_manifest_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest() if snapshot.exists() else None},
        "counts": {s: sum(r.status == s for r in rows) for s in ("PASS", "FAIL", "ERROR")},
        "checks": [asdict(r) for r in rows],
    }


def render_markdown(report: dict) -> str:
    """研究效果与计算检查分开呈现，失败不被成功总数掩盖。"""
    lines = ["# 金融模型独立核验结果", "", f"生成时间：{report['generated_at']}", "",
             "本轮全部计算输入为合成数据，不涉及实时行情。真实预测/投资有效性：证据不足。", "",
             f"计算检查：{report['counts']}；运行期间源码稳定：{report['snapshot_stable']}。", "",
             "| 编号 | 模型 | 核验 | 状态 | 实际 | 参考/要求 | 容忍度 |", "|---|---|---|---|---|---|---|"]
    for row in report["checks"]:
        lines.append("| " + " | ".join(str(row[k]).replace("|", "/").replace("\n", " ") for k in ("case_id", "model", "description", "status", "actual", "expected", "tolerance")) + " |")
        if row["error"]:
            lines.append(f"\n执行错误：{row['error']}\n")
    lines += ["", "## 历史样本盘点", "", "```json", json.dumps(report["inventory"], ensure_ascii=False, indent=2), "```", "",
              "## 解读边界", "", "PASS 只支持对应计算特例或边界，不证明历史预测有效。FAIL 为需要人工复核的独立挑战结果，本轮不修改模型。", "",
              "下一步：建立带可用时间、输入摘要、固定期限及模型版本的真实样本，再冻结基准与时间切分，开展样本外评估。", ""]
    return "\n".join(lines)
