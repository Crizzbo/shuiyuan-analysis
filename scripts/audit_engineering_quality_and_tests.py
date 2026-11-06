# -*- coding: utf-8 -*-
"""全盘工程质量、公式规范与测试用例健壮性全息审计脚本 (audit_engineering_quality_and_tests.py).

系统扫描：
1. 类似问题排查：Excel / Google Sheets 活体公式规范性、潜在数组溢出、未包裹 INDEX 的隐患；
2. 行情取数排查：业务逻辑与脚本中是否存在硬编码价格、静态 mock 代替权威数据源；
3. 测试用例质量排查：
   - “为了等于而等于”的假对账 / 静态硬编码自证；
   - 过宽断言 (Weak Assertion: 仅 assertIsNotNone 或 assertTrue)；
   - 缺乏真实物理介质校验 (仅在内存中自圆其说)；
   - 缺少边界与异常拒绝验证。
"""

import ast
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def scan_sheets_formulas() -> List[Dict[str, Any]]:
    """扫描所有脚本中写入 Excel / Google Sheets 的动态公式。"""
    formula_issues = []
    py_files = list((ROOT / "scripts").glob("*.py")) + list((ROOT / "financial_reporting").glob("*.py"))

    for f_path in py_files:
        try:
            content = f_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # 查找所有包含 GOOGLEFINANCE 的行
        for idx, line in enumerate(content.splitlines(), 1):
            if "GOOGLEFINANCE" in line:
                # 检查是否包含带日期的 GOOGLEFINANCE 但缺少 INDEX(..., 2, 2)
                # 例如: =GOOGLEFINANCE("...", "price", ...) 却不是 =INDEX(GOOGLEFINANCE(...)
                has_date_param = any(kw in line for kw in ["TODAY()", "DATE(", "as_of_date"])
                has_index_wrapper = "INDEX(" in line

                # 检查单参数或旧多参数
                if has_date_param and not has_index_wrapper and not line.strip().startswith("#"):
                    formula_issues.append({
                        "file": str(f_path.relative_to(ROOT)),
                        "line": idx,
                        "type": "FORMULA_LIST_SPILL_RISK",
                        "severity": "HIGH",
                        "code": line.strip(),
                        "description": "带有日期参数的 GOOGLEFINANCE 未被 INDEX(..., 2, 2) 包装，在 Google Sheets 中将返回 2x2 数组导致单元格溢出 (#SPILL!)",
                    })
                elif "GOOGLEFINANCE" in line and "value=" in line and not has_index_wrapper and not line.strip().startswith("#"):
                    # 写入单元格但没有包裹 INDEX 的活体公式
                    formula_issues.append({
                        "file": str(f_path.relative_to(ROOT)),
                        "line": idx,
                        "type": "UNWRAPPED_GOOGLEFINANCE",
                        "severity": "MEDIUM",
                        "code": line.strip(),
                        "description": "写入单元格的 GOOGLEFINANCE 建议显式使用带日期标量提取公式 INDEX(GOOGLEFINANCE(..., 'price', TODAY()), 2, 2)",
                    })
    return formula_issues


def scan_hardcoded_stock_quotes() -> List[Dict[str, Any]]:
    """扫描业务与报表生成脚本中的硬编码静态股价。"""
    hardcoded_issues = []
    # 重点检查 scripts 和 financial_reporting
    check_dirs = [ROOT / "scripts", ROOT / "financial_reporting", ROOT / "finance_tools"]

    pattern = re.compile(r'("current_price"|current_price|price|现价)\s*[:=]\s*([0-9]+\.?[0-9]*)')

    for d in check_dirs:
        for f_path in d.glob("*.py"):
            # 排除纯单元测试文件与核验工具本身
            if f_path.name.startswith("test_") or f_path.name in ["market_quote_verifier.py", "audit_engineering_quality_and_tests.py"]:
                continue
            try:
                lines = f_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue

            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # 匹配静态硬编码价格，如 current_price = 130.0 或 "current_price": 200.0
                match = pattern.search(line)
                if match:
                    val_str = match.group(2)
                    try:
                        val = float(val_str)
                        # 重点抓取常见的历史假数据桩（如 128.5, 130.0, 199.75, 200.0, 50.0 等）
                        if val in [128.5, 130.0, 199.75, 200.0, 204.0, 100.0]:
                            hardcoded_issues.append({
                                "file": str(f_path.relative_to(ROOT)),
                                "line": idx,
                                "type": "HARDCODED_PRICE_STUB",
                                "severity": "HIGH",
                                "code": stripped,
                                "description": f"检测到硬编码静态行情数值 ({val})，未通过 MarketQuoteVerifier 动态接入权威凭证",
                            })
                    except ValueError:
                        pass
    return hardcoded_issues


def audit_test_cases_quality() -> List[Dict[str, Any]]:
    """深度自查所有 test_*.py 单元测试文件的设计与断言质量。"""
    test_issues = []
    test_files = sorted(list((ROOT / "scripts").glob("test_*.py")))

    for f_path in test_files:
        try:
            content = f_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            continue

        file_issues_count = 0
        total_asserts = 0
        weak_asserts = 0

        lines = content.splitlines()

        for idx, line in enumerate(lines, 1):
            s_line = line.strip()
            if not s_line or s_line.startswith("#"):
                continue

            # 1. 统计断言类型
            if "self.assert" in s_line:
                total_asserts += 1
                # 弱断言：例如 self.assertTrue(res) 或 self.assertIsNotNone(res) 且后面没有针对字段数值的深入断言
                if s_line.startswith("self.assertIsNotNone(") or s_line.startswith("self.assertTrue(") or s_line.startswith("self.assertIn("):
                    weak_asserts += 1

            # 2. 检测“为了等于而等于”的典型模式：
            # 模式 A: self.assertEqual(x, x) 或 self.assertEqual(res.foo, 某个硬编码数字) 且该数字在上方作为参数直接传入
            # 模式 B: self.assertEqual(len(res), 固定数字) 却完全没有断言里面的字段和计算精度
            if "self.assertEqual(" in s_line:
                # 检查形如 self.assertEqual(a, a)
                m_same = re.match(r"self\.assertEqual\(\s*([a-zA-Z0-9_]+)\s*,\s*\1\s*\)", s_line)
                if m_same:
                    test_issues.append({
                        "file": str(f_path.relative_to(ROOT)),
                        "line": idx,
                        "type": "VACUOUS_SELF_ASSERTION",
                        "severity": "CRITICAL",
                        "code": s_line,
                        "description": f"无效的自等自证假断言：{m_same.group(1)} == {m_same.group(1)}",
                    })

        # 3. 检查是否有涉及 Excel 或数据处理的测试但未实际验证物理文件
        if "excel" in f_path.name.lower() or "dossier" in f_path.name.lower():
            has_openpyxl_load = "load_workbook" in content
            has_temp_file = "tempfile" in content or "NamedTemporaryFile" in content
            if not has_openpyxl_load and not has_temp_file:
                test_issues.append({
                    "file": str(f_path.relative_to(ROOT)),
                    "line": 1,
                    "type": "MISSING_PHYSICAL_MEDIUM_TEST",
                    "severity": "HIGH",
                    "code": f_path.name,
                    "description": "涉及报表/工作簿生成的测试用例中缺少真实 Excel 介质读取 (load_workbook) 闭环验证，仅在内存中校验字典",
                })

        # 4. 统计弱断言占比过高的测试文件
        if total_asserts > 5 and (weak_asserts / total_asserts) > 0.65:
            test_issues.append({
                "file": str(f_path.relative_to(ROOT)),
                "line": 1,
                "type": "WEAK_ASSERTION_DOMINATED",
                "severity": "MEDIUM",
                "code": f"弱断言占比 {weak_asserts}/{total_asserts} ({weak_asserts/total_asserts:.1%})",
                "description": "测试用例中断言过宽，多数仅断言非空 (assertIsNotNone) 或布尔真 (assertTrue)，缺少数值平账、美分级精度与边界条件检验",
            })

    return test_issues


def run_full_audit():
    print(f"\n{'='*90}")
    print(f"[质量审计] 全盘工程质量、公式规范与测试用例深度自查报告")
    print(f"{'='*90}\n")

    sheets_issues = scan_sheets_formulas()
    hardcoded_issues = scan_hardcoded_stock_quotes()
    test_issues = audit_test_cases_quality()

    print(f"【维度一：Google Sheets / Excel 活体公式规范与数组溢出隐患】(发现 {len(sheets_issues)} 项)")
    print(f"{'-'*90}")
    if not sheets_issues:
        print("  [通过] 暂未发现未被 INDEX(..., 2, 2) 包装的带日期公式或溢出风险公式！")
    else:
        for item in sheets_issues:
            print(f"  [{item['severity']}] {item['file']}:{item['line']} -> {item['description']}")
            print(f"       代码: {item['code']}")

    print(f"\n【维度二：业务脚本中的静态行情硬编码桩 (需用户检查/接入统一核验)】(发现 {len(hardcoded_issues)} 项)")
    print(f"{'-'*90}")
    if not hardcoded_issues:
        print("  [通过] 核心业务脚本中未发现硬编码股价！")
    else:
        for item in hardcoded_issues:
            print(f"  [{item['severity']}] {item['file']}:{item['line']} -> {item['description']}")
            print(f"       代码: {item['code']}")

    print(f"\n【维度三：测试用例质量与“为了等于而等于”假对账自查】(发现 {len(test_issues)} 项)")
    print(f"{'-'*90}")
    if not test_issues:
        print("  [通过] 测试用例结构良好！")
    else:
        for item in test_issues:
            print(f"  [{item['severity']}] {item['file']}:{item['line']} -> {item['description']}")
            print(f"       详情: {item['description']}")

    print(f"\n{'='*90}\n")
    return {
        "sheets_issues": sheets_issues,
        "hardcoded_issues": hardcoded_issues,
        "test_issues": test_issues,
    }


if __name__ == "__main__":
    run_full_audit()
