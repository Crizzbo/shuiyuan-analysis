"""计算登记、编排与研究契约适配；不会自动选择行业模型或生成证据。"""

import hashlib
import inspect
import json
from importlib.metadata import version
from functools import lru_cache
from finance_tools import VERSION, basic, valuation
from finance_tools.validation import number, finite_output

REGISTRY = {
    "cashflow": (basic.cashflow, "numpy-financial"),
    "dated_cashflow": (basic.dated_cashflow, "pyxirr"),
    "financial_ratio": (basic.financial_ratio, "financetoolkit"),
    "wacc": (basic.wacc, "financetoolkit"),
    "fixed_dcf": (basic.fixed_dcf, "financetoolkit"),
    "performance": (basic.performance, "quantstats"),
    "multistage_dcf": (valuation.multistage_dcf, None),
    "residual_income": (valuation.residual_income, None),
    "reverse_dcf": (valuation.reverse_dcf, None),
    "reit_bridge": (valuation.reit_bridge, None),
    "nav": (valuation.nav, None),
    "multiple_valuation": (valuation.multiple_valuation, None),
}


@lru_cache(maxsize=16)
def _library_version(library):
    """当前解释器生命周期内复用依赖版本，避免每笔计算扫描发行版元数据。

    运行中不支持安装/替换依赖；升级环境后须重启解释器，否则已加载模块也不会更新。
    只缓存依赖版本，不缓存输入、结果或实现文件哈希。
    """
    try:
        return version(library)
    except Exception:
        # 从项目依赖清单读取规范版本
        from pathlib import Path
        manifest_file = Path(__file__).resolve().parents[2] / "third_party/finance/dependency-manifest.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                for item in data:
                    if item.get("name") == library:
                        return item.get("version")
            except Exception:
                pass
        return "project-native"


def calculate(method, parameters):
    """返回实现版本、输入摘要及全部中间结果；未知字段会被签名校验拒绝。"""
    if method not in REGISTRY or not isinstance(parameters, dict):
        raise ValueError("未知工具或参数不是对象")
    function, library = REGISTRY[method]
    inspect.signature(function).bind(**parameters)
    # 先固化输入，禁止 NaN/Infinity；摘要不能替代证据引用。
    encoded = json.dumps(parameters, sort_keys=True, ensure_ascii=False, allow_nan=False)
    output = finite_output(function(**parameters))
    implementation = "finance_tools/basic.py" if library else "finance_tools/valuation.py"
    from pathlib import Path
    code_bytes = (Path(__file__).resolve().parents[2] / implementation).read_bytes()
    return {"method": method, "method_version": VERSION,
            "implementation_sha256": hashlib.sha256(code_bytes).hexdigest(),
            "implementation_path": implementation,
            "library": library, "library_version": _library_version(library) if library else None,
            "parameters": json.loads(encoded),
            "input_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "result": output}


def scenarios(method, cases):
    """显式情景概率，总和必须为 1；不自行补齐或归一化概率。"""
    if method not in ("multistage_dcf", "residual_income", "nav", "fixed_dcf", "multiple_valuation"):
        raise ValueError("情景工具仅支持输出每股价值的估值模型")
    if not isinstance(cases, list) or not cases:
        raise ValueError("情景列表不能为空")
    rows, names = [], set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"name", "probability", "parameters"}:
            raise ValueError("情景必须包含 name/probability/parameters")
        name = case["name"]
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("情景名称必须非空且唯一")
        names.add(name)
        weight = number(case["probability"], "probability", nonnegative=True)
        if weight > 1:
            raise ValueError("情景概率不能大于 1")
        rows.append({"name": name, "probability": weight,
                     "calculation": calculate(method, case["parameters"])})
    if abs(sum(x["probability"] for x in rows) - 1) > 1e-10:
        raise ValueError("概率总和必须为 1")
    # 相同计量单位由调用方契约保证；DCF 的 scope 不允许在同组中混用。
    if method in ("multistage_dcf", "multiple_valuation") and len({x["calculation"]["parameters"]["scope"] for x in rows}) != 1:
        raise ValueError("情景不能混合 FCFF 与 FCFE")
    if method != "residual_income" and len({x["calculation"]["parameters"]["shares"] for x in rows}) != 1:
        raise ValueError("情景必须使用同一股数口径；稀释情景需单独建模后评估")
    return finite_output({"scenarios": rows, "expected_value_per_share": sum(
        x["probability"] * x["calculation"]["result"]["value_per_share"] for x in rows)})


def sensitivity(parameters, discount_rates, terminal_growth_rates):
    """完整二维矩阵；无效终值组合报错，禁止跳过坏格而隐瞒边界。"""
    from finance_tools.validation import sequence
    rates = sequence(discount_rates, "discount_rates", rates=True)
    growths = sequence(terminal_growth_rates, "terminal_growth_rates", rates=True)
    return [{"discount_rate": discount, "terminal_growth": growth,
             "calculation": calculate("multistage_dcf", dict(parameters,
                 discount_rate=discount, terminal_growth=growth))}
            for discount in rates for growth in growths]


def research_record(calculation, calculation_id, output_specifications,
                    observation_refs, assumption_refs):
    """映射现有 research.calculation；结果默认 unchecked，核对证据需另行登记。"""
    if not isinstance(calculation_id, str) or not calculation_id.strip():
        raise ValueError("计算 ID 不能为空")
    for refs in (observation_refs, assumption_refs):
        if not isinstance(refs, list) or any(not isinstance(x, str) or not x for x in refs) or len(refs) != len(set(refs)):
            raise ValueError("引用必须为不重复的非空字符串列表")
    if not isinstance(output_specifications, list) or not output_specifications:
        raise ValueError("需要显式指定输出字段、单位和币种")
    outputs = []
    for spec in output_specifications:
        if set(spec) != {"field", "unit", "currency"} or not isinstance(spec["unit"], str) or not spec["unit"]:
            raise ValueError("输出映射必须包含 field/unit/currency")
        currency = spec["currency"]
        if currency is not None and (not isinstance(currency, str) or len(currency) != 3 or not currency.isupper()):
            raise ValueError("币种使用三位大写代码，非金额为 null")
        if spec["unit"] in ("currency", "currency_per_share") and currency is None:
            raise ValueError("金额与每股价值必须提供币种")
        value = number(calculation["result"][spec["field"]], "输出值")
        outputs.append({"value": value, "unit": spec["unit"], "currency": currency})
    suffix = f";{calculation['library']}={calculation['library_version']}" if calculation["library"] else ""
    return {"id": calculation_id, "method": calculation["method"],
            "method_version": calculation["method_version"] + suffix,
            "implementation_path": calculation["implementation_path"],
            "input_observation_refs": observation_refs, "assumption_refs": assumption_refs,
            "outputs": outputs, "verification_status": "unchecked", "verification_evidence_refs": []}
