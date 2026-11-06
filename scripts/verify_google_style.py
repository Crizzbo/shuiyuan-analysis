#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Python 编程风格自动化全息巡检器 (Google Python Style Guide Verifier).

依据《references/google_python_style_guide.md》与《SPEC-12 质量工程与全息测试验收标准》设计，
对系统 Python 代码库进行自动化的静态风格规范审计，确保：
1. 模块命名规范 (snake_case.py)；
2. 类命名规范 (CapWords / PascalCase)；
3. 函数与方法命名规范 (snake_case，杜绝 camelCase)；
4. 严格禁止通配符导入 (from ... import *)；
5. financial_core 核心层物理纯洁性 (零外围反向依赖)；
6. 公共类与模块级函数 Google 风格文档字符串 (Docstrings) 覆盖度。
"""

import ast
import os
import re
import sys
from typing import Any, Dict, List, Set, Tuple


TARGET_DIRS = [
    "financial_core",
    "financial_reporting",
    "finance_tools",
    "scripts",
]

# 允许忽略的方法名白名单 (如 unittest 标准接口)
FUNCTION_WHITELIST = {
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "assertAlmostEqual",
    "assertEqual",
    "assertTrue",
    "assertFalse",
    "assertRaises",
    "assertIn",
    "assertNotIn",
    "assertIsNone",
    "assertIsNotNone",
}


class GoogleStyleAuditor(ast.NodeVisitor):
    """AST 访问器，针对单个 Python 文件执行 Google 风格合规审计."""

    def __init__(self, file_path: str, rel_path: str) -> None:
        self.file_path = file_path
        self.rel_path = rel_path.replace("\\", "/")
        self.violations: List[Tuple[str, int, str]] = []  # (category, line, message)
        self.classes_count = 0
        self.functions_count = 0
        self.docstring_count = 0

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # 审计规则 1: 严禁通配符导入 (from module import *)
        for alias in node.names:
            if alias.name == "*":
                self.violations.append(
                    ("WILDCARD_IMPORT", node.lineno, f"严禁使用通配符导入: 'from {node.module} import *'")
                )

        # 审计规则 2: financial_core 内部严禁引用外层模块
        if self.rel_path.startswith("financial_core/"):
            mod = node.module or ""
            outer_modules = ["finance_tools", "financial_reporting", "scripts", "data_sources"]
            for outer in outer_modules:
                if mod == outer or mod.startswith(f"{outer}."):
                    self.violations.append(
                        ("REVERSE_DEPENDENCY", node.lineno, f"核心层严禁逆向导入外层模块: '{mod}'")
                    )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes_count += 1
        # 审计规则 3: 类名必须为大驼峰 (PascalCase / CapWords，允许单下划线前缀表示内部私有类)
        if not re.match(r"^_?[A-Z][a-zA-Z0-9]*$", node.name):
            self.violations.append(
                ("CLASS_NAMING", node.lineno, f"类名 '{node.name}' 不符合 PascalCase 规范")
            )

        # 审计规则 4: 类文档字符串检查
        if ast.get_docstring(node):
            self.docstring_count += 1
        else:
            if not node.name.startswith("_") and not self.rel_path.startswith("scripts/test_"):
                self.violations.append(
                    ("MISSING_DOCSTRING", node.lineno, f"公共类 '{node.name}' 缺失 Google 风格 Docstring")
                )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.AST) -> None:
        name = getattr(node, "name", "")
        lineno = getattr(node, "lineno", 1)
        self.functions_count += 1

        # 忽略魔术方法与白名单方法
        if name.startswith("__") and name.endswith("__"):
            return
        if name in FUNCTION_WHITELIST:
            return
        # AST visitor 框架回调方法 (如 visit_ClassDef)
        if name.startswith("visit_") and self.rel_path.endswith("verify_google_style.py"):
            return

        # 审计规则 5: 函数与方法名必须为全小写加下划线 (snake_case)
        # 允许下划线前缀表示私有方法
        clean_name = name.lstrip("_")
        if not re.match(r"^[a-z0-9_]+$", clean_name) or any(c.isupper() for c in clean_name):
            self.violations.append(
                ("FUNCTION_NAMING", lineno, f"函数/方法名 '{name}' 不符合 snake_case 规范 (禁用 camelCase)")
            )

        # 审计规则 6: 公共模块级函数文档字符串
        if not name.startswith("_") and not self.rel_path.startswith("scripts/test_"):
            if ast.get_docstring(node):
                self.docstring_count += 1
            else:
                # 仅警告核心层的公共顶层函数
                if self.rel_path.startswith("financial_core/"):
                    self.violations.append(
                        ("MISSING_DOCSTRING", lineno, f"公共函数 '{name}' 缺失 Docstring 说明")
                    )


def audit_repository(root_dir: str = ".") -> Tuple[bool, Dict[str, Any]]:
    """对代码库执行全局 Google 风格巡检."""
    all_violations: List[Tuple[str, str, int, str]] = []
    file_count = 0
    total_classes = 0
    total_functions = 0

    for target in TARGET_DIRS:
        target_path = os.path.join(root_dir, target)
        if not os.path.exists(target_path):
            continue

        for dirpath, _, filenames in os.walk(target_path):
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue

                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                file_count += 1

                # 检查文件名命名规范
                base_name = os.path.splitext(fname)[0]
                if not re.match(r"^[a-z0-9_]+$", base_name):
                    all_violations.append(
                        (rel_path, "FILE_NAMING", 1, f"文件名 '{fname}' 不符合 snake_case.py 规范")
                    )

                # 读取并解析 AST
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=full_path)
                    auditor = GoogleStyleAuditor(full_path, rel_path)
                    auditor.visit(tree)

                    total_classes += auditor.classes_count
                    total_functions += auditor.functions_count
                    for cat, lineno, msg in auditor.violations:
                        all_violations.append((rel_path, cat, lineno, msg))
                except SyntaxError as e:
                    all_violations.append((rel_path, "SYNTAX_ERROR", e.lineno or 1, str(e)))
                except Exception as e:
                    all_violations.append((rel_path, "PARSE_ERROR", 1, str(e)))

    # 分类汇总违规
    critical_violations = [v for v in all_violations if v[1] in ("WILDCARD_IMPORT", "REVERSE_DEPENDENCY", "FILE_NAMING", "SYNTAX_ERROR")]
    naming_violations = [v for v in all_violations if v[1] in ("CLASS_NAMING", "FUNCTION_NAMING")]
    doc_violations = [v for v in all_violations if v[1] == "MISSING_DOCSTRING"]

    passed = len(critical_violations) == 0 and len(naming_violations) == 0

    summary = {
        "files_audited": file_count,
        "classes_audited": total_classes,
        "functions_audited": total_functions,
        "critical_violations": critical_violations,
        "naming_violations": naming_violations,
        "doc_violations": doc_violations,
        "total_violations": len(all_violations),
        "passed": passed,
    }
    return passed, summary


def main() -> None:
    print("=" * 70)
    print("[代码规范] 启动 Google Python 编程风格自动化全息巡检")
    print("=" * 70)

    passed, summary = audit_repository()

    print(f"已扫描文件总数: {summary['files_audited']} 个")
    print(f"已审计类总数: {summary['classes_audited']} 个")
    print(f"已审计函数与方法: {summary['functions_audited']} 个")
    print("-" * 70)

    crit = summary["critical_violations"]
    naming = summary["naming_violations"]
    docs = summary["doc_violations"]

    print(f"严重破坏项 (通配符导入/逆向依赖/非法文件名): {len(crit)} 项")
    print(f"命名规范违规 (类名非PascalCase / 函数名camelCase): {len(naming)} 项")
    print(f"文档缺失提示 (公共类与顶层函数Docstring): {len(docs)} 项")
    print("-" * 70)

    if crit:
        print("[严重红线清单]:")
        for f, cat, line, msg in crit[:10]:
            print(f"  - [{cat}] {f}:{line} -> {msg}")
        if len(crit) > 10:
            print(f"  ... 另有 {len(crit) - 10} 项严重违规未展开")

    if naming:
        print("[命名违规清单]:")
        for f, cat, line, msg in naming[:10]:
            print(f"  - [{cat}] {f}:{line} -> {msg}")
        if len(naming) > 10:
            print(f"  ... 另有 {len(naming) - 10} 项命名违规未展开")

    if passed:
        print("=" * 70)
        print("[巡检合格] 代码风格极其规范，零严重违规，零命名违例！")
        print("=" * 70)
        sys.exit(0)
    else:
        print("=" * 70)
        print(f"[巡检未通过] 发现 {len(crit) + len(naming)} 项硬性规则违例，需逐项治理！")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
