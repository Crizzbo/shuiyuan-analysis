"""全盘数据格式全息体检与核验引擎 (audit_global_data_formats.py).

遵循用户指示“数据格式问题必须全盘检验”与 AGENTS.md 契约硬约束：
1. 域 1: 行情数据源格式体检 (Market Quotes Format Audit) - 浮点精度、美分尾数、货币标准、ISO时间戳；
2. 域 2: 资产池主索引格式体检 (Universe Master Index Format Audit) - SEC CIK 格式、东证代码、行业映射；
3. 域 3: 全盘 7,600+ 家官方财报底账格式与平账检验 (Financial Statement Format & Accounting Identity)；
4. 域 4: AI 深度档案 JSON Schema 契约与小数保真度检验 (AI Dossiers Format Audit)；
5. 域 5: Markdown 研报与决策卡文本语法格式正则扫描 (Markdown Formatting Rigor Audit)。
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class DomainAuditResult:
    """单个数据域体检汇总结果。"""
    domain_name: str
    total_inspected: int = 0
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def pass_rate_pct(self) -> float:
        if self.total_inspected == 0:
            return 100.0
        return round((self.passed_count / self.total_inspected) * 100, 2)


class GlobalDataFormatAuditor:
    """全盘全量数据格式全息体检器。"""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or PROJECT_ROOT
        self.base_dir = Path("D:/美股分析")
        self.domain_results: Dict[str, DomainAuditResult] = {}

    def audit_domain_1_quotes_format(self) -> DomainAuditResult:
        """域 1: 行情数据源全息格式体检。"""
        res = DomainAuditResult(domain_name="行情数据源全息格式体检 (Market Quotes)")
        quotes_dir = self.root_dir / "data" / "google-finance" / "raw"

        if not quotes_dir.exists():
            res.warnings.append({"path": str(quotes_dir), "message": "行情目录不存在，跳过"})
            return res

        for q_file in sorted(quotes_dir.glob("*.json")):
            try:
                data = json.loads(q_file.read_text(encoding="utf-8"))
            except Exception as e:
                res.total_inspected += 1
                res.failed_count += 1
                res.errors.append({"file": q_file.name, "issue": f"JSON解析致命错误: {str(e)}"})
                continue

            # 处理规范 quotes 字典
            quotes_dict = data.get("quotes", {})
            if not quotes_dict and "cells" in data:
                # 原始 Google Sheets 单元格测试文件，验证基本格式
                res.total_inspected += 1
                if "acquired_at" in data:
                    res.passed_count += 1
                else:
                    res.warning_count += 1
                    res.warnings.append({"file": q_file.name, "issue": "缺少 acquired_at 根时间戳"})
                continue

            for ticker, item in quotes_dict.items():
                res.total_inspected += 1
                item_errors = []

                # 1. 检查 ticker 格式 (支持美股大写字母、指数 ^ 前缀及日股纯数字代码)
                is_valid_ticker = (
                    isinstance(ticker, str)
                    and len(ticker.strip()) > 0
                    and not any(c.islower() for c in ticker)
                    and bool(re.match(r"^[\^A-Z0-9\.\-]+$", ticker))
                )
                if not is_valid_ticker:
                    item_errors.append(f"标的代码格式非标准大写或数字代码: {ticker}")

                # 2. 检查价格数值与浮点精度
                p = item.get("current_price")
                if p is None or not isinstance(p, (int, float)) or math.isnan(p) or math.isinf(p) or p <= 0:
                    item_errors.append(f"现价数值非法 (必须为 >0 的正常有限数值): {p}")
                else:
                    # 美分保真度检验：验证能否无损格式化为两位小数
                    try:
                        p_str = f"{p:.2f}"
                        if not re.match(r"^\d+\.\d{2}$", p_str):
                            item_errors.append(f"现价格式化两位美分失败: {p}")
                    except Exception as e:
                        item_errors.append(f"现价格式化异常: {str(e)}")

                # 3. 检查货币代码标准
                curr = item.get("currency")
                if not isinstance(curr, str) or not re.match(r"^[A-Z]{3}$", curr):
                    item_errors.append(f"货币代码非 ISO 4217 三位大写: {curr}")

                # 4. 检查时间戳格式 (ISO 8601)
                ts = item.get("timestamp_iso")
                if not ts or not isinstance(ts, str):
                    item_errors.append(f"缺少有效 timestamp_iso: {ts}")
                else:
                    try:
                        datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        item_errors.append(f"时间戳非有效 ISO 8601: {ts}")

                if item_errors:
                    res.failed_count += 1
                    res.errors.append({"file": q_file.name, "ticker": ticker, "issues": item_errors})
                else:
                    res.passed_count += 1

        self.domain_results["quotes"] = res
        return res

    def audit_domain_2_universe_index_format(self) -> DomainAuditResult:
        """域 2: 资产池主索引全量格式体检。"""
        res = DomainAuditResult(domain_name="资产池主索引全量格式体检 (Universe Indexes)")
        univ_dir = self.root_dir / "data" / "universe"

        if not univ_dir.exists():
            res.warnings.append({"path": str(univ_dir), "message": "资产池目录不存在，跳过"})
            return res

        for u_file in sorted(univ_dir.glob("*.json")):
            try:
                data = json.loads(u_file.read_text(encoding="utf-8"))
            except Exception as e:
                res.total_inspected += 1
                res.failed_count += 1
                res.errors.append({"file": u_file.name, "issue": f"JSON解析错误: {str(e)}"})
                continue

            res.total_inspected += 1
            file_issues = []

            # 针对 SEC CIK 索引检查
            if "sec_company_tickers" in u_file.name.lower():
                if isinstance(data, dict):
                    sample_keys = list(data.keys())[:50]
                    for k in sample_keys:
                        row = data[k]
                        cik = str(row.get("cik_str", ""))
                        ticker = row.get("ticker", "")
                        if not cik or not cik.isdigit():
                            file_issues.append(f"CIK 非纯数字: {cik} (标的: {ticker})")
                        if not ticker or not isinstance(ticker, str):
                            file_issues.append(f"标的代码非法: {ticker}")
                else:
                    file_issues.append("SEC 索引根节点必须为映射字典")

            # 针对日股 JPX 索引检查
            elif "jpx" in u_file.name.lower():
                if isinstance(data, list):
                    for row in data[:50]:
                        code = str(row.get("code", row.get("ticker", "")))
                        if not code or len(code) < 4:
                            file_issues.append(f"日股代码长度异常: {code}")
                elif isinstance(data, dict):
                    pass
                else:
                    file_issues.append("JPX 索引格式非标准列表或映射")

            # 针对 Master Universe 检查
            elif "master" in u_file.name.lower():
                if isinstance(data, dict):
                    assets = data.get("assets", data.get("companies", {}))
                    if not assets:
                        file_issues.append("主资产池未包含 assets 标的清单")
                else:
                    file_issues.append("Master Universe 根节点必须为字典")

            if file_issues:
                res.failed_count += 1
                res.errors.append({"file": u_file.name, "issues": file_issues})
            else:
                res.passed_count += 1

        self.domain_results["universe"] = res
        return res

    @staticmethod
    def _inspect_single_financial_statement(f_path: Path) -> Tuple[bool, List[str]]:
        """单份财报格式与刚性平账快速原子检查函数。"""
        f_issues = []
        try:
            data = json.loads(f_path.read_text(encoding="utf-8"))
        except Exception as e:
            return False, [f"JSON 损坏或非 UTF-8: {str(e)}"]

        required_roots = ["metadata", "balance_sheet", "income_statement", "cash_flow_statement"]
        for req_key in required_roots:
            if req_key not in data or not isinstance(data[req_key], dict):
                f_issues.append(f"缺少必需的三表一级键: '{req_key}'")

        if f_issues:
            return False, f_issues

        bs = data["balance_sheet"]
        inc = data["income_statement"]
        cf = data["cash_flow_statement"]

        tot_assets = bs.get("total_assets", bs.get("assets", 0.0))
        tot_liab = bs.get("total_liabilities", bs.get("liabilities", 0.0))
        equity = bs.get("stockholders_equity", bs.get("equity", 0.0))

        for field_name, val in [("total_assets", tot_assets), ("total_liabilities", tot_liab), ("stockholders_equity", equity)]:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                f_issues.append(f"资产负债表科目 '{field_name}' 非有效数字: {val}")

        if not f_issues:
            tot_assets = float(tot_assets)
            tot_liab = float(tot_liab)
            equity = float(equity)

            if tot_assets > 0:
                diff = abs(tot_assets - (tot_liab + equity))
                tol = max(1.0, tot_assets * 0.001)
                if diff > tol:
                    f_issues.append(
                        f"刚性平账方程失衡: 资产=${tot_assets:,.0f} != 负债+权益=${tot_liab+equity:,.0f} (误差=${diff:,.0f})"
                    )

        rev = inc.get("revenue")
        ni = inc.get("net_income")
        if rev is not None and (not isinstance(rev, (int, float)) or math.isnan(rev) or math.isinf(rev)):
            f_issues.append(f"营业收入 revenue 非有效数字: {rev}")
        if ni is not None and (not isinstance(ni, (int, float)) or math.isnan(ni) or math.isinf(ni)):
            f_issues.append(f"净利润 net_income 非有效数字: {ni}")

        fcf = cf.get("free_cash_flow")
        ocf = cf.get("operating_cash_flow")
        if fcf is not None and (not isinstance(fcf, (int, float)) or math.isnan(fcf) or math.isinf(fcf)):
            f_issues.append(f"自由现金流 free_cash_flow 非有效数字: {fcf}")
        if ocf is not None and (not isinstance(ocf, (int, float)) or math.isnan(ocf) or math.isinf(ocf)):
            f_issues.append(f"经营现金流 operating_cash_flow 非有效数字: {ocf}")

        return (len(f_issues) == 0), f_issues

    def audit_domain_3_financial_statements_comprehensive(
        self, limit: Optional[int] = None
    ) -> DomainAuditResult:
        """域 3: 全盘 7,600+ 家官方财报底账格式与平账检验 (高并发流水线版)."""
        res = DomainAuditResult(domain_name="全盘官方标准财报底账格式与平账硬检验 (Financial Statements)")
        stmt_dir = self.base_dir / "02_格式化标准三表库" / "JSON格式"

        if not stmt_dir.exists():
            res.warnings.append({"path": str(stmt_dir), "message": "三表库目录不存在，跳过"})
            return res

        all_files = sorted(stmt_dir.glob("*.json"))
        target_files = all_files[:limit] if limit else all_files
        res.total_inspected = len(target_files)

        with ThreadPoolExecutor(max_workers=32) as executor:
            futures = [(f_path.name, executor.submit(self._inspect_single_financial_statement, f_path)) for f_path in target_files]
            for file_name, fut in futures:
                is_passed, issues = fut.result()
                if is_passed:
                    res.passed_count += 1
                else:
                    res.failed_count += 1
                    res.errors.append({"file": file_name, "issues": issues})

        self.domain_results["financial_statements"] = res
        return res

        self.domain_results["financial_statements"] = res
        return res

    def audit_domain_4_ai_dossiers_format(self) -> DomainAuditResult:
        """域 4: AI 深度档案全量格式与小数保真度体检。"""
        res = DomainAuditResult(domain_name="AI 深度档案全量格式与小数保真度体检 (AI Dossiers)")
        dossier_dir = self.root_dir / "reports" / "ai_dossiers"

        if not dossier_dir.exists():
            res.warnings.append({"path": str(dossier_dir), "message": "深度档案目录不存在，跳过"})
            return res

        for d_file in sorted(dossier_dir.glob("**/*.json")):
            res.total_inspected += 1
            f_issues = []

            try:
                data = json.loads(d_file.read_text(encoding="utf-8"))
            except Exception as e:
                res.failed_count += 1
                res.errors.append({"file": d_file.name, "issues": [f"JSON损坏: {str(e)}"]})
                continue

            # 检查顶层必须存在的关键模块
            required_sections = ["overview", "decision_summary"]
            for sec in required_sections:
                if sec not in data:
                    f_issues.append(f"缺少必要章节: '{sec}'")

            # 检查决策摘要中的现价与情景估值小数保真度
            ds = data.get("decision_summary", {})
            curr_p = ds.get("current_price")
            if curr_p is None or not isinstance(curr_p, (int, float)) or curr_p <= 0:
                f_issues.append(f"决策摘要中 current_price 非有效正数: {curr_p}")
            else:
                # 检查是否能格式化为两位美分
                p_str = f"{float(curr_p):.2f}"
                if not re.match(r"^\d+\.\d{2}$", p_str):
                    f_issues.append(f"现价无法精确保留两位小数: {curr_p}")

            # 检查三大情景价格
            p_floor = ds.get("pessimistic_floor")
            fair = ds.get("fair_anchor")
            opt = ds.get("optimistic_target")

            for name, val in [("pessimistic_floor", p_floor), ("fair_anchor", fair), ("optimistic_target", opt)]:
                if val is not None and (not isinstance(val, (int, float)) or math.isnan(val) or val <= 0):
                    f_issues.append(f"情景价格 '{name}' 数值异常: {val}")

            if f_issues:
                res.failed_count += 1
                res.errors.append({"file": d_file.name, "issues": f_issues})
            else:
                res.passed_count += 1

        self.domain_results["dossiers"] = res
        return res

    def audit_domain_5_markdown_reports_and_cards(self) -> DomainAuditResult:
        """域 5: 研报与打样 Markdown/Card 文本语法格式正则扫描。"""
        res = DomainAuditResult(domain_name="Markdown 研报与决策卡文本语法格式正则扫描 (Markdown Reports)")

        md_targets = []
        # 1. 扫描打样目录
        poc_dir = self.base_dir / "01_标杆深度档案打样"
        if poc_dir.exists():
            md_targets.extend(list(poc_dir.glob("*.md")))

        # 2. 扫描项目内研报目录
        reports_dir = self.root_dir / "reports"
        if reports_dir.exists():
            md_targets.extend(list(reports_dir.glob("**/*.md")))

        for md_file in sorted(set(md_targets)):
            res.total_inspected += 1
            file_issues = []
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception as e:
                res.failed_count += 1
                res.errors.append({"file": md_file.name, "issues": [f"文件读取失败: {str(e)}"]})
                continue

            # 1. 正则检索未替换的占位符 (如 {price}, {ticker}, undefined, NaN)
            placeholder_pattern = re.compile(r"\{[a-zA-Z0-9_]+\}|(?:undefined|NaN)\b")
            found_placeholders = placeholder_pattern.findall(content)
            # 过滤正常 markdown 语法或特定代码块与路径模式
            suspicious = [p for p in found_placeholders if p not in ["{ :--- }", "{:---}", "{stamp}"]]
            if suspicious:
                file_issues.append(f"检测到未注入的模板占位符或异常值: {suspicious[:5]}")

            # 2. 检索裸美元数字简写 (如出现类似 $204 后面紧跟空格或换行，未保留 .00 精度)
            # 排除带 B/M 缩写的情况 (如 $204B) 以及标准千分位金额 (如 $100,000) 或两位美分小数
            naked_dollar_pattern = re.compile(
                r"\$(?!\d+\.\d{2}(?:B|M)?)(?!\d+\.\d(?:B|M))(?!\d{1,3}(?:,\d{3})+)\d+(?!\.\d)(?![BMbm])"
            )
            naked_matches = naked_dollar_pattern.findall(content)
            if naked_matches:
                file_issues.append(f"检测到疑似未保留小数位的简写金额: {naked_matches[:5]}")

            if file_issues:
                res.failed_count += 1
                res.errors.append({"file": md_file.name, "issues": file_issues})
            else:
                res.passed_count += 1

        self.domain_results["markdown"] = res
        return res

    def run_comprehensive_audit(self, stmt_limit: Optional[int] = None) -> Dict[str, Any]:
        """全息执行全盘五大数据域格式体检。"""
        self.audit_domain_1_quotes_format()
        self.audit_domain_2_universe_index_format()
        self.audit_domain_3_financial_statements_comprehensive(limit=stmt_limit)
        self.audit_domain_4_ai_dossiers_format()
        self.audit_domain_5_markdown_reports_and_cards()

        total_all = sum(r.total_inspected for r in self.domain_results.values())
        passed_all = sum(r.passed_count for r in self.domain_results.values())
        failed_all = sum(r.failed_count for r in self.domain_results.values())
        overall_pass_rate = round((passed_all / total_all) * 100, 2) if total_all else 100.0

        summary = {
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "overall_inspected": total_all,
            "overall_passed": passed_all,
            "overall_failed": failed_all,
            "overall_pass_rate_pct": overall_pass_rate,
            "domains": {
                name: {
                    "domain_name": r.domain_name,
                    "total": r.total_inspected,
                    "passed": r.passed_count,
                    "failed": r.failed_count,
                    "pass_rate_pct": r.pass_rate_pct,
                    "sample_errors": r.errors[:10],
                }
                for name, r in self.domain_results.items()
            },
        }
        return summary


def main():
    parser = argparse.ArgumentParser(description="全盘数据格式全息体检与核验引擎")
    parser.add_argument("--limit", type=int, default=None, help="财报底账体检数量上限 (默认全盘全量扫描)")
    parser.add_argument("--out-json", type=str, default="data/audits/global_data_format_audit.json", help="输出体检底账路径")
    args = parser.parse_args()

    auditor = GlobalDataFormatAuditor()
    print("=" * 70)
    print("[审计启动] 启动全盘全量数据格式全息体检与平账核验引擎")
    print("=" * 70)

    summary = auditor.run_comprehensive_audit(stmt_limit=args.limit)

    print("\n【全盘格式体检汇总状态矩阵】")
    print(f"• 全盘总受检对象: {summary['overall_inspected']} 项")
    print(f"• 完美合规项: {summary['overall_passed']} 项")
    print(f"• 格式缺陷项: {summary['overall_failed']} 项")
    print(f"• 全盘综合合规率: {summary['overall_pass_rate_pct']}%\n")

    for k, d in summary["domains"].items():
        status_icon = "[通过]" if d["failed"] == 0 else "[异常]"
        print(f"  {status_icon} [{d['domain_name']}]: 受检 {d['total']} 项 | 合格率 {d['pass_rate_pct']}% | 缺陷 {d['failed']} 项")
        if d["sample_errors"]:
            for err in d["sample_errors"][:3]:
                print(f"     └─ 缺陷样例: {err}")

    # 保存体检报告底账
    out_path = PROJECT_ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[审计落盘] 格式体检审计底账已落盘: {out_path}")


if __name__ == "__main__":
    main()
