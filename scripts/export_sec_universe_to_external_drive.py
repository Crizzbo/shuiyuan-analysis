"""美股万家上市公司全盘分批收集、格式化三表对齐与外部存储归档调度器.

执行目标:
针对用户指定的存储目录 (默认: D:\\美股分析)，建立买方机构级的数据资产架构，
分批次从 SEC EDGAR 官方免费公共开放接口获取万家公司的官方财报底账，
执行会计恒等式刚性平账核验 (Assets = Liabilities + Equity)，
并完成买方级多维格式化 (结构化 JSON、总览索引表、三表汇总 Excel、断点续传账本)。

目录规范:
D:\\美股分析\\
├── 00_资产池全息总索引\\
│   ├── 美股上市公司总览底账_Master_Universe.xlsx
│   ├── 美股上市公司总览底账_Master_Universe.json
│   └── 资产池分级与覆盖进度_README.md
├── 01_官方原始财报底稿\\ (SEC EDGAR Raw Facts JSON)
├── 02_格式化标准三表库\\
│   ├── JSON格式\\ (格式化对齐三表底稿)
│   └── 汇总Excel报表\\ (买方机构级多Sheet工作簿)
└── 03_批次调度与断点续传账本\\
    ├── sec_collection_progress.json (进度账本)
    └── 待补数与异常清单_Replenishment_Gaps.json (缺失或不平账企业清单)
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from financial_core.engines.sec_edgar_collector import (
    OfficialSecEdgarCollector,
    SecExtractedFinancialFacts,
)
from financial_core.engines.tiered_universe_manager import (
    TieredUniverseManager,
    UniverseCompanyRecord,
)
from financial_core.engines.filing_mapper import (
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)

DEFAULT_EXTERNAL_DIR = Path("D:/美股分析")


class ExternalDriveLayoutManager:
    """管理外部硬盘目录结构与文件组织."""

    def __init__(self, base_dir: Path = DEFAULT_EXTERNAL_DIR):
        self.base_dir = base_dir
        self.dir_index = self.base_dir / "00_资产池全息总索引"
        self.dir_raw = self.base_dir / "01_官方原始财报底稿"
        self.dir_formatted = self.base_dir / "02_格式化标准三表库"
        self.dir_formatted_json = self.dir_formatted / "JSON格式"
        self.dir_formatted_excel = self.dir_formatted / "汇总Excel报表"
        self.dir_ledger = self.base_dir / "03_批次调度与断点续传账本"

    def ensure_layout(self) -> None:
        """确保全套文件架构完整存在."""
        for d in [
            self.dir_index,
            self.dir_raw,
            self.dir_formatted,
            self.dir_formatted_json,
            self.dir_formatted_excel,
            self.dir_ledger,
        ]:
            d.mkdir(parents=True, exist_ok=True)


class ExternalCollectionProgressTracker:
    """外部存储专用断点续传进度与异常追踪状态机."""

    def __init__(self, ledger_dir: Path):
        self.progress_file = ledger_dir / "sec_collection_progress.json"
        self.gap_file = ledger_dir / "待补数与异常清单_Replenishment_Gaps.json"
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.progress_file.exists():
            try:
                return json.loads(self.progress_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "version": "1.0.0",
            "title": "美股万家公司官方数据批量收集与平账进度账本",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_companies_target": 0,
                "total_attempted": 0,
                "perfect_balanced_count": 0,
                "deficient_or_unbalanced_count": 0,
            },
            "companies": {},
        }

    def save(self) -> None:
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = self.progress_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.progress_file)

    def is_completed(self, ticker: str) -> bool:
        rec = self.data["companies"].get(ticker.upper())
        return rec is not None and rec.get("status") == "COMPLETED"

    def is_processed(self, ticker: str, retry_deficient: bool = False) -> bool:
        rec = self.data["companies"].get(ticker.upper())
        if rec is None:
            return False
        if retry_deficient:
            return rec.get("status") == "COMPLETED"
        return True

    def record_success(self, facts: SecExtractedFinancialFacts, company_name: str) -> None:
        self.data["companies"][facts.ticker.upper()] = {
            "status": "COMPLETED",
            "cik": facts.cik,
            "company_name": company_name,
            "fiscal_year": facts.fiscal_year,
            "fiscal_year_end": facts.fiscal_year_end,
            "form": facts.form,
            "revenue": facts.revenue,
            "total_assets": facts.total_assets,
            "total_liabilities": facts.total_liabilities,
            "stockholders_equity": facts.stockholders_equity,
            "net_income": facts.net_income,
            "operating_cash_flow": facts.operating_cash_flow,
            "free_cash_flow": facts.free_cash_flow,
            "is_balanced": facts.is_balanced,
            "balance_sheet_diff": facts.balance_sheet_diff,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.data["summary"]["perfect_balanced_count"] = sum(
            1 for c in self.data["companies"].values() if c.get("status") == "COMPLETED"
        )
        self.data["summary"]["total_attempted"] = len(self.data["companies"])

    def record_deficient(self, ticker: str, cik: str, company_name: str, reason: str) -> None:
        self.data["companies"][ticker.upper()] = {
            "status": "DEFICIENT",
            "cik": cik,
            "company_name": company_name,
            "reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.data["summary"]["deficient_or_unbalanced_count"] = sum(
            1 for c in self.data["companies"].values() if c.get("status") == "DEFICIENT"
        )
        self.data["summary"]["total_attempted"] = len(self.data["companies"])

    def save_gap_manifest(self, deficient_list: List[Dict[str, Any]]) -> None:
        if not deficient_list:
            return
        existing_gaps = []
        if self.gap_file.exists():
            try:
                existing_gaps = json.loads(self.gap_file.read_text(encoding="utf-8")).get("gaps", [])
            except Exception:
                pass

        seen_tickers = {g["ticker"] for g in existing_gaps}
        for item in deficient_list:
            if item["ticker"] not in seen_tickers:
                existing_gaps.append(item)
                seen_tickers.add(item["ticker"])

        manifest = {
            "title": "美股待补数与异常财务底账清单",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_gaps": len(existing_gaps),
            "description": "记录在官方披露中缺失标准科目或未通过会计恒等式刚性平账自检的主体，保留真实凭据供后续定性核验",
            "gaps": existing_gaps,
        }
        self.gap_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def export_master_universe_index(layout: ExternalDriveLayoutManager, universe_mgr: TieredUniverseManager) -> None:
    """生成并导出全美股万家公司全息总览底账 (Excel & JSON)."""
    universe_mgr.load_universe()
    companies = list(universe_mgr._us_companies.values())

    # 按照代码字母排序
    companies.sort(key=lambda c: c.ticker)

    print(f"\n[索引构建] 正在生成美股全市场上市公司全息总索引 (共计 {len(companies)} 家)...")

    sp500_set = set(getattr(universe_mgr, "_sp500_tickers", set()))

    # 加载权威标普500 GICS行业底账
    sp500_sector_map = {}
    sp500_file = ROOT / "data" / "universe" / "sp500_universe.json"
    if sp500_file.exists():
        try:
            sp_data = json.loads(sp500_file.read_text(encoding="utf-8"))
            for item in sp_data.get("constituents", []):
                sym = item.get("symbol", "").upper()
                if sym:
                    sec_en = item.get("sector", "")
                    sec_zh = {
                        "Information Technology": "信息技术 (Information Technology)",
                        "Health Care": "医疗保健 (Health Care)",
                        "Consumer Discretionary": "可选消费 (Consumer Discretionary)",
                        "Financials": "金融 (Financials)",
                        "Industrials": "工业 (Industrials)",
                        "Communication Services": "通信服务 (Communication Services)",
                        "Consumer Staples": "必需消费 (Consumer Staples)",
                        "Energy": "能源 (Energy)",
                        "Utilities": "公用事业 (Utilities)",
                        "Real Estate": "房地产 (Real Estate)",
                        "Materials": "原材料 (Materials)",
                    }.get(sec_en, sec_en)
                    sp500_sector_map[sym] = {"sector": sec_zh, "industry": item.get("industry", "")}
        except Exception:
            pass

    # 1. 导出 JSON
    json_path = layout.dir_index / "美股上市公司总览底账_Master_Universe.json"
    json_data = {
        "title": "美股全市场上市公司总览底账 (Master Universe)",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(companies),
        "source": "SEC EDGAR Official Registry & US Exchange Listings",
        "companies": [
            {
                "ticker": c.ticker,
                "cik": str(c.cik).zfill(10) if c.cik else "",
                "company_name": c.company_name,
                "market": c.market,
                "tier": c.tier,
                "sector": (c.sector or sp500_sector_map.get(c.ticker.upper(), {}).get("sector", "未分类广谱长尾池 (Unclassified)")),
                "industry": (c.industry or sp500_sector_map.get(c.ticker.upper(), {}).get("industry", "--")),
                "is_sp500": c.ticker in sp500_set or c.tier == "TIER_0",
            }
            for c in companies
        ],
    }
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [总览落盘] 已输出总览底账 JSON: {json_path}")

    # 2. 导出 Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "美股全市场上市公司总表"

    headers = [
        "序号", "股票代码", "SEC CIK", "公司全称", "资产分级", "标普500成分", "官方行业板块", "细分业务赛道"
    ]
    ws.append(headers)

    # 样式配置
    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # 逐行填入
    for idx, c in enumerate(companies, start=1):
        is_sp500_flag = c.ticker in sp500_set or c.tier == "TIER_0"
        row = [
            idx,
            c.ticker,
            str(c.cik).zfill(10) if c.cik else "--",
            c.company_name,
            "核心蓝筹 (Tier 0)" if c.tier == "TIER_0" else ("主线成长 (Tier 1)" if c.tier == "TIER_1" else "全市场标的 (Tier 2/3)"),
            "是" if is_sp500_flag else "否",
            c.sector or "--",
            c.industry or "--",
        ]
        ws.append(row)
        curr_row = idx + 1
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = thin_border
            if col_idx in [1, 2, 3, 5, 6]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

    # 自动调整列宽
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            # 中文字符宽度按2计算
            val_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
            if val_len > max_len:
                max_len = val_len
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    excel_path = layout.dir_index / "美股上市公司总览底账_Master_Universe.xlsx"
    wb.save(str(excel_path))
    print(f"  [透视落盘] 已输出总览底账 Excel: {excel_path}")

    # 3. 导出 README 架构说明
    readme_path = layout.dir_index / "资产池分级与覆盖进度_README.md"
    readme_content = f"""# 美股万家上市公司官方数据资产总库

更新时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
底账来源: 美国证券交易委员会 (SEC EDGAR) 官方登记册与纽交所/纳斯达克全市场代码库
目标总规模: {len(companies)} 家上市公司

## 目录组织与功能职责
1. `00_资产池全息总索引/`: 美股万家公司底账索引 (Master Universe Excel & JSON) 与分级标准。
2. `01_官方原始财报底稿/`: 来自 SEC EDGAR 官方公共开放接口的原始 XBRL CompanyFacts JSON 原件（作为可追溯的法证级证据）。
3. `02_格式化标准三表库/`:
   - `JSON格式/`: 经由会计恒等式 (Assets = Liabilities + Equity) 刚性平账自检后清洗出的标准财务数据。
   - `汇总Excel报表/`: 结构化、买方机构级多 Sheet 财务报表工作簿。
4. `03_批次调度与断点续传账本/`: 维护分批抓取进度账本与待补数清单，支持随时断点续传与平账自检追踪。

## 分级资产池架构
- **核心蓝筹 (Tier 0, P0)**: 涵盖标普 500 成分股与超大型行业巨头，提供高频动态跟踪与全息三表对齐。
- **主线成长 (Tier 1, P1)**: 涵盖各赛道高流动性中大型成长股及行业胜负手代表公司。
- **全市场标的 (Tier 2/3, P2/P3)**: 覆盖全美股数千家上市主体，分批自动化抓取建档与增量平账入库。
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"  [架构文档] 已输出架构说明文档: {readme_path}")


def format_company_facts_to_json(
    facts: SecExtractedFinancialFacts,
    company_name: str,
    ticker: str,
    layout: ExternalDriveLayoutManager,
) -> Path:
    """将对齐财务事实格式化为标准财务事实 JSON 并落盘."""
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in company_name).strip("_")
    filename = f"{ticker.upper()}_{safe_name}_标准财报底稿.json"
    out_path = layout.dir_formatted_json / filename

    # 计算商业质量比率
    roe = (facts.net_income / facts.stockholders_equity) if facts.stockholders_equity and facts.stockholders_equity > 0 else 0.0
    debt_to_assets = (facts.total_liabilities / facts.total_assets) if facts.total_assets and facts.total_assets > 0 else 0.0
    gross_margin = (facts.gross_profit / facts.revenue) if facts.revenue and facts.revenue > 0 else 0.0
    operating_margin = (facts.operating_income / facts.revenue) if facts.revenue and facts.revenue > 0 else 0.0
    net_margin = (facts.net_income / facts.revenue) if facts.revenue and facts.revenue > 0 else 0.0
    fcf_conversion = (facts.free_cash_flow / facts.net_income) if facts.net_income and facts.net_income > 0 else 0.0
    net_cash = facts.cash_and_equivalents - facts.total_debt

    doc = {
        "metadata": {
            "ticker": ticker.upper(),
            "cik": facts.cik,
            "company_name": company_name,
            "fiscal_year": facts.fiscal_year,
            "fiscal_year_end": facts.fiscal_year_end,
            "form": facts.form,
            "currency": facts.currency or "USD",
            "source_filing": facts.source_filing,
            "formatted_at": datetime.now(timezone.utc).isoformat(),
        },
        "balance_sheet": {
            "total_assets": facts.total_assets,
            "total_liabilities": facts.total_liabilities,
            "stockholders_equity": facts.stockholders_equity,
            "cash_and_cash_equivalents": facts.cash_and_equivalents,
            "total_debt": facts.total_debt,
            "net_cash": net_cash,
            "inventory": facts.inventory,
            "balance_sheet_identity_check": {
                "equation": "Assets = Liabilities + Equity",
                "is_balanced": facts.is_balanced,
                "discrepancy_amount": facts.balance_sheet_diff,
                "discrepancy_ratio": facts.balance_sheet_rel_ratio,
                "verdict": "完美平账" if facts.is_balanced else "平账异常",
            },
        },
        "income_statement": {
            "revenue": facts.revenue,
            "cost_of_revenue": facts.cost_of_revenue,
            "gross_profit": facts.gross_profit,
            "gross_margin": gross_margin,
            "operating_income": facts.operating_income,
            "operating_margin": operating_margin,
            "net_income": facts.net_income,
            "net_margin": net_margin,
            "diluted_shares": facts.diluted_shares,
        },
        "cash_flow_statement": {
            "operating_cash_flow": facts.operating_cash_flow,
            "capital_expenditures": facts.capex,
            "free_cash_flow": facts.free_cash_flow,
            "fcf_conversion_ratio": fcf_conversion,
        },
        "business_quality_metrics": {
            "roe": roe,
            "debt_to_assets": debt_to_assets,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "net_margin": net_margin,
        },
    }

    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def export_batch_financials_excel(
    aligned_facts_list: List[Dict[str, Any]],
    output_excel_path: Path,
    batch_title: str = "美股标杆企业三表对齐汇总",
) -> None:
    """生成买方机构级格式化三表汇总 Excel 工作簿."""
    wb = openpyxl.Workbook()
    # 移除默认 sheet
    wb.remove(wb.active)

    # 1. 概览 Sheet
    ws_summary = wb.create_sheet(title="核心财务指标总览")
    headers_summary = [
        "股票代码", "公司名称", "最新财年", "报告期", "营业收入 ($B)", "净利润 ($B)",
        "经营现金流 ($B)", "自由现金流 ($B)", "总资产 ($B)", "总负债 ($B)", "股东权益 ($B)",
        "净资产收益率 (ROE)", "营业利润率", "平账状态"
    ]
    ws_summary.append(headers_summary)

    header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for col_idx in range(1, len(headers_summary) + 1):
        cell = ws_summary.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for idx, item in enumerate(aligned_facts_list, start=1):
        f = item["facts"]
        c_name = item["company_name"]
        roe = (f.net_income / f.stockholders_equity) if f.stockholders_equity and f.stockholders_equity > 0 else 0.0
        op_margin = (f.operating_income / f.revenue) if f.revenue and f.revenue > 0 else 0.0

        row_vals = [
            f.ticker,
            c_name,
            f"FY{f.fiscal_year}",
            f.fiscal_year_end,
            round(f.revenue / 1e9, 2),
            round(f.net_income / 1e9, 2),
            round(f.operating_cash_flow / 1e9, 2),
            round(f.free_cash_flow / 1e9, 2),
            round(f.total_assets / 1e9, 2),
            round(f.total_liabilities / 1e9, 2),
            round(f.stockholders_equity / 1e9, 2),
            f"{roe * 100:.2f}%",
            f"{op_margin * 100:.2f}%",
            "完美平账" if f.is_balanced else "偏差",
        ]
        ws_summary.append(row_vals)
        curr_row = idx + 1
        for col_idx in range(1, len(headers_summary) + 1):
            cell = ws_summary.cell(row=curr_row, column=col_idx)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = thin_border
            if col_idx in [1, 3, 4, 14]:
                cell.alignment = center_align
            elif col_idx == 2:
                cell.alignment = left_align
            else:
                cell.alignment = right_align

    # 自动宽度
    for col in ws_summary.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            val_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
            if val_len > max_len:
                max_len = val_len
        ws_summary.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 2. 资产负债表 Sheet
    ws_bs = wb.create_sheet(title="资产负债表与平账核验")
    headers_bs = [
        "股票代码", "公司名称", "财年", "总资产 ($B)", "总负债 ($B)", "股东权益 ($B)",
        "现金与等价物 ($B)", "总有息负债 ($B)", "存货 ($B)", "平账自检差额 ($)", "平账校验结论"
    ]
    ws_bs.append(headers_bs)
    for col_idx in range(1, len(headers_bs) + 1):
        cell = ws_bs.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = center_align

    for idx, item in enumerate(aligned_facts_list, start=1):
        f = item["facts"]
        row_vals = [
            f.ticker,
            item["company_name"],
            f"FY{f.fiscal_year}",
            round(f.total_assets / 1e9, 2),
            round(f.total_liabilities / 1e9, 2),
            round(f.stockholders_equity / 1e9, 2),
            round(f.cash_and_equivalents / 1e9, 2),
            round(f.total_debt / 1e9, 2),
            round(f.inventory / 1e9, 2),
            round(f.balance_sheet_diff, 2),
            "通过 (刚性平账)" if f.is_balanced else "未通过",
        ]
        ws_bs.append(row_vals)
        curr_row = idx + 1
        for col_idx in range(1, len(headers_bs) + 1):
            cell = ws_bs.cell(row=curr_row, column=col_idx)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = thin_border
            if col_idx in [1, 3, 11]:
                cell.alignment = center_align
            elif col_idx == 2:
                cell.alignment = left_align
            else:
                cell.alignment = right_align

    for col in ws_bs.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            val_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
            if val_len > max_len:
                max_len = val_len
        ws_bs.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 3. 利润表 Sheet
    ws_is = wb.create_sheet(title="利润表")
    headers_is = [
        "股票代码", "公司名称", "财年", "营业收入 ($B)", "营业成本 ($B)", "毛利润 ($B)",
        "毛利率", "营业利润 ($B)", "营业利润率", "净利润 ($B)", "净利率"
    ]
    ws_is.append(headers_is)
    for col_idx in range(1, len(headers_is) + 1):
        cell = ws_is.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = PatternFill(start_color="244062", end_color="244062", fill_type="solid")
        cell.alignment = center_align

    for idx, item in enumerate(aligned_facts_list, start=1):
        f = item["facts"]
        gm = (f.gross_profit / f.revenue) if f.revenue and f.revenue > 0 else 0.0
        opm = (f.operating_income / f.revenue) if f.revenue and f.revenue > 0 else 0.0
        npm = (f.net_income / f.revenue) if f.revenue and f.revenue > 0 else 0.0
        row_vals = [
            f.ticker,
            item["company_name"],
            f"FY{f.fiscal_year}",
            round(f.revenue / 1e9, 2),
            round(f.cost_of_revenue / 1e9, 2),
            round(f.gross_profit / 1e9, 2),
            f"{gm * 100:.2f}%",
            round(f.operating_income / 1e9, 2),
            f"{opm * 100:.2f}%",
            round(f.net_income / 1e9, 2),
            f"{npm * 100:.2f}%",
        ]
        ws_is.append(row_vals)
        curr_row = idx + 1
        for col_idx in range(1, len(headers_is) + 1):
            cell = ws_is.cell(row=curr_row, column=col_idx)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = thin_border
            if col_idx in [1, 3]:
                cell.alignment = center_align
            elif col_idx == 2:
                cell.alignment = left_align
            else:
                cell.alignment = right_align

    for col in ws_is.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            val_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
            if val_len > max_len:
                max_len = val_len
        ws_is.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 4. 现金流量表 Sheet
    ws_cf = wb.create_sheet(title="现金流量表")
    headers_cf = [
        "股票代码", "公司名称", "财年", "经营活动现金流 ($B)", "资本开支 ($B)", "自由现金流 ($B)", "FCF转化率"
    ]
    ws_cf.append(headers_cf)
    for col_idx in range(1, len(headers_cf) + 1):
        cell = ws_cf.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
        cell.alignment = center_align

    for idx, item in enumerate(aligned_facts_list, start=1):
        f = item["facts"]
        fcf_conv = (f.free_cash_flow / f.net_income) if f.net_income and f.net_income > 0 else 0.0
        row_vals = [
            f.ticker,
            item["company_name"],
            f"FY{f.fiscal_year}",
            round(f.operating_cash_flow / 1e9, 2),
            round(f.capex / 1e9, 2),
            round(f.free_cash_flow / 1e9, 2),
            f"{fcf_conv * 100:.2f}%",
        ]
        ws_cf.append(row_vals)
        curr_row = idx + 1
        for col_idx in range(1, len(headers_cf) + 1):
            cell = ws_cf.cell(row=curr_row, column=col_idx)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = thin_border
            if col_idx in [1, 3]:
                cell.alignment = center_align
            elif col_idx == 2:
                cell.alignment = left_align
            else:
                cell.alignment = right_align

    for col in ws_cf.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            val_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
            if val_len > max_len:
                max_len = val_len
        ws_cf.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(str(output_excel_path))


def execute_batch_collection_pipeline(
    target_dir: Path = DEFAULT_EXTERNAL_DIR,
    target_group: str = "sp500",
    tickers_override: Optional[List[str]] = None,
    limit: Optional[int] = None,
    batch_size: int = 50,
    delay_sec: float = 0.15,
    resume: bool = True,
    retry_deficient: bool = False,
    generate_excel: bool = True,
) -> Dict[str, Any]:
    """主控执行批量收集、平账与外部归档流水线."""
    layout = ExternalDriveLayoutManager(target_dir)
    layout.ensure_layout()
    tracker = ExternalCollectionProgressTracker(layout.dir_ledger)

    universe_mgr = TieredUniverseManager.get_instance()
    universe_mgr.load_universe()

    # 1. 自动生成或更新万家公司总览索引
    export_master_universe_index(layout, universe_mgr)

    # 2. 确定本次待收集标的清单
    candidates: List[UniverseCompanyRecord] = []
    if tickers_override:
        for t in tickers_override:
            rec = universe_mgr.lookup(t, "US")
            if rec:
                candidates.append(rec)
            else:
                candidates.append(
                    UniverseCompanyRecord(ticker=t.upper(), company_name=t.upper(), market="US", tier="TIER_3")
                )
    elif target_group == "sp500":
        candidates = universe_mgr.get_sp500_priority_collection_list(unarchived_only=False)
    else:  # all_sec
        # 提取全部万家普通股与经营实体
        candidates = [c for c in universe_mgr._us_companies.values() if "-" not in c.ticker]

    valid_candidates = [c for c in candidates if c.cik]

    if resume:
        pending_candidates = [c for c in valid_candidates if not tracker.is_processed(c.ticker, retry_deficient=retry_deficient)]
    else:
        pending_candidates = valid_candidates

    if limit is not None and limit > 0:
        pending_candidates = pending_candidates[:limit]

    print("\n" + "=" * 80)
    print(f"【美股官方数据分批收集与格式化归档管道】")
    print(f"存储路径: {layout.base_dir}")
    print(f"目标标的总数: {len(valid_candidates)} 家 | 本次待处理数: {len(pending_candidates)} 家")
    print(f"批次切片规模: 每批 {batch_size} 家 | 请求速率延迟: {delay_sec} 秒")
    print("=" * 80)

    # 3. 分批次抓取、平账、格式化与导出
    all_aligned_facts: List[Dict[str, Any]] = []
    deficient_items: List[Dict[str, Any]] = []

    total_batches = (len(pending_candidates) + batch_size - 1) // batch_size if pending_candidates else 0

    for i in range(0, len(pending_candidates), batch_size):
        chunk = pending_candidates[i : i + batch_size]
        batch_no = (i // batch_size) + 1
        print(f"\n>>> 正在处理批次 [{batch_no}/{total_batches}] (本批规模: {len(chunk)} 家) <<<")

        batch_aligned: List[Dict[str, Any]] = []

        for rec in chunk:
            ticker = rec.ticker
            cik = rec.cik
            company_name = rec.company_name

            try:
                # A. 优先从项目本地已归档的二级来源复用 (避免重复网络抓取)
                local_sec_archive = ROOT / "data" / "official_filings" / "sec" / f"CIK{str(cik).zfill(10)}.json"
                dest_raw_path = layout.dir_raw / f"CIK{str(cik).zfill(10)}.json"
                if not dest_raw_path.exists() and local_sec_archive.exists():
                    shutil.copy2(str(local_sec_archive), str(dest_raw_path))

                # 抓取或读取原始 Facts JSON 到外部目录 01_官方原始财报底稿/
                raw_facts = OfficialSecEdgarCollector.fetch_company_facts_by_cik(
                    cik=cik,
                    cache_dir=layout.dir_raw,
                    timeout=15.0,
                    force_refresh=False,
                )

                # B. 解析并进行会计恒等式刚性平账自检
                aligned = OfficialSecEdgarCollector.extract_aligned_financial_facts(
                    companyfacts=raw_facts,
                    ticker=ticker,
                )

                # C. 格式化并落盘标准三表底稿 JSON
                format_company_facts_to_json(
                    facts=aligned,
                    company_name=company_name,
                    ticker=ticker,
                    layout=layout,
                )

                # D. 记录成功状态
                tracker.record_success(aligned, company_name)
                batch_aligned.append({"facts": aligned, "company_name": company_name})
                all_aligned_facts.append({"facts": aligned, "company_name": company_name})

                diff_str = f"${aligned.balance_sheet_diff:,.0f}" if aligned.balance_sheet_diff > 0 else "0.00"
                print(
                    f"  [平账入库] {ticker:5s} (CIK:{cik}) | FY{aligned.fiscal_year} | "
                    f"营收: ${aligned.revenue / 1e9:6.2f}B | 净利润: ${aligned.net_income / 1e9:6.2f}B | "
                    f"资产: ${aligned.total_assets / 1e9:6.2f}B | 平账偏差: {diff_str}"
                )

            except (BalanceSheetIdentityError, IncompleteFilingFactError, FileNotFoundError, RuntimeError) as e:
                err_msg = str(e)
                tracker.record_deficient(ticker, cik, company_name, err_msg)
                deficient_items.append({
                    "ticker": ticker,
                    "market": "US",
                    "company_name": company_name,
                    "cik": cik,
                    "reason": err_msg,
                })
                print(f"  [阻断待补] {ticker:5s} (CIK:{cik}) | 原因: {err_msg}")

            if delay_sec > 0:
                time.sleep(delay_sec)

        # 批次保存账本
        tracker.save()
        print(f"  -> 第 [{batch_no}/{total_batches}] 批落盘完成，当前累计已平账入库: {tracker.data['summary']['perfect_balanced_count']} 家")

    # 4. 生成或更新三表汇总 Excel 工作簿
    if generate_excel and all_aligned_facts:
        excel_name = f"美股标杆企业_标准财务三表汇总_打样.xlsx" if limit and limit <= 20 else f"美股上市公司_标准财务三表汇总_{datetime.now().strftime('%Y%m%d')}.xlsx"
        excel_out_path = layout.dir_formatted_excel / excel_name
        export_batch_financials_excel(all_aligned_facts, excel_out_path)
        print(f"\n[汇总落盘] 已成功生成机构级三表汇总工作簿: {excel_out_path}")

    # 5. 保存待补数清单
    if deficient_items:
        tracker.save_gap_manifest(deficient_items)
        print(f"[缺口登记] 已记录 {len(deficient_items)} 家待补数标的至 {layout.dir_ledger / '待补数与异常清单_Replenishment_Gaps.json'}")

    summary = {
        "status": "COMPLETED",
        "total_attempted_this_run": len(pending_candidates),
        "balanced_this_run": len(all_aligned_facts),
        "deficient_this_run": len(deficient_items),
        "cumulative_balanced": tracker.data["summary"]["perfect_balanced_count"],
        "cumulative_deficient": tracker.data["summary"]["deficient_or_unbalanced_count"],
        "target_directory": str(layout.base_dir),
    }

    print("\n" + "=" * 80)
    print("【批量收集与格式化归档完成】")
    print(f"本次处理标的: {summary['total_attempted_this_run']} 家")
    print(f"本次平账入库: {summary['balanced_this_run']} 家")
    print(f"累计平账入库: {summary['cumulative_balanced']} 家")
    print(f"数据总库目录: {summary['target_directory']}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="美股万家公司官方数据批量收集与格式化归档调度器")
    parser.add_argument("--target-dir", type=str, default="D:/美股分析", help="目标外部存储目录 (默认: D:/美股分析)")
    parser.add_argument("--target-group", choices=["sp500", "all_sec"], default="sp500", help="收集标的群体")
    parser.add_argument("--tickers", nargs="+", help="显式指定股票代码列表")
    parser.add_argument("--batch-size", type=int, default=50, help="批次切片大小 (默认 50)")
    parser.add_argument("--limit", type=int, default=None, help="最大处理数量")
    parser.add_argument("--delay", type=float, default=0.15, help="请求速率延迟 (秒)")
    parser.add_argument("--no-resume", action="store_true", help="禁用断点续传")
    parser.add_argument("--retry-deficient", action="store_true", help="重新尝试此前被阻断或异常的标的 (默认跳过)")
    parser.add_argument("--sample", action="store_true", help="打样模式 (处理前 5 家顶层蓝筹标杆企业)")

    args = parser.parse_args()

    target_path = Path(args.target_dir)

    if args.sample:
        sample_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
        execute_batch_collection_pipeline(
            target_dir=target_path,
            tickers_override=sample_tickers,
            limit=len(sample_tickers),
            batch_size=5,
            delay_sec=args.delay,
            resume=not args.no_resume,
            retry_deficient=args.retry_deficient,
            generate_excel=True,
        )
    else:
        execute_batch_collection_pipeline(
            target_dir=target_path,
            target_group=args.target_group,
            tickers_override=args.tickers,
            limit=args.limit,
            batch_size=args.batch_size,
            delay_sec=args.delay,
            resume=not args.no_resume,
            retry_deficient=args.retry_deficient,
            generate_excel=True,
        )
