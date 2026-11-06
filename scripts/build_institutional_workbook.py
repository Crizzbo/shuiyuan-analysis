"""买方机构级 5-Sheet Excel 深度投研工作簿构建入口 (Institutional Workbook CLI).

遵循 SPEC-01 与 SPEC-02 设计规范：
1. Sheet 1: 00_投资备忘录与决策中枢 (Executive Memo, 估值走廊, 击球区, 诺奖宏观指标)
2. Sheet 2: 01_行业与护城河竞争格局 (AI商业模式画像, AI供应链上下游集中度, AI护城河五维解构)
3. Sheet 3: 02_官方三表全息审计底稿 (动态年限三表底账, 杜邦拆解, 刚性平账自检行 Assets = Liab + Equity)
4. Sheet 4: 03_内生估值与敏感度走廊 (伍德福德动态WACC折现, 动态FCF预测, 永续 g vs WACC 双变量敏感度走廊)
5. Sheet 5: 04_审计溯源与重大事件跟踪 (真实官方文件SHA-256登记, 财年年报/重大披露按需触发PDF事件台账)
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_reporting.excel_dossier_builder import ExcelDossierBuilder


def build_workbook_from_dossier_data(
    dossier_data: Dict[str, Any],
    output_dir: Optional[Path] = None,
    output_filename: Optional[str] = None,
) -> Path:
    """根据标准 deep_dossier 结构化字典构建 5-Sheet Excel 工作簿."""
    target_dir = output_dir or (ROOT / "reports" / "excel_workbooks")
    target_dir.mkdir(parents=True, exist_ok=True)
    builder = ExcelDossierBuilder(output_dir=target_dir)
    return builder.build_workbook(dossier_data=dossier_data, output_filename=output_filename)


def main():
    parser = argparse.ArgumentParser(
        description="构建买方机构级 5-Sheet Excel 深度投研工作簿 (FAST Standard)"
    )
    parser.add_argument(
        "--json-file",
        type=str,
        help="输入的目标公司 JSON 档案文件路径",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="标的代码 (若在 reports/ai_dossiers 中存在则直接加载)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(ROOT / "reports" / "excel_workbooks"),
        help="Excel 文件输出目录",
    )
    parser.add_argument(
        "--output-filename",
        type=str,
        help="自定义导出的 Excel 文件名",
    )
    args = parser.parse_args()

    dossier_data = None
    if args.json_file:
        j_path = Path(args.json_file)
        if not j_path.is_absolute():
            j_path = ROOT / j_path
        if not j_path.is_file():
            print(f"[ERROR] 指定的 JSON 文件不存在: {j_path}", file=sys.stderr)
            sys.exit(1)
        dossier_data = json.loads(j_path.read_text(encoding="utf-8"))
    elif args.ticker:
        # 尝试从 reports/ai_dossiers 中查找
        t_clean = args.ticker.strip().upper()
        candidates = list((ROOT / "reports" / "ai_dossiers").glob(f"*{t_clean}*.json"))
        if candidates:
            dossier_data = json.loads(candidates[0].read_text(encoding="utf-8"))
        else:
            print(f"[ERROR] 未找到标的 {t_clean} 的现有档案 JSON，请使用 --json-file 指定", file=sys.stderr)
            sys.exit(1)
    else:
        print("[ERROR] 必须指定 --json-file 或 --ticker 参数", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    out_path = build_workbook_from_dossier_data(
        dossier_data=dossier_data,
        output_dir=Path(args.output_dir),
        output_filename=args.output_filename,
    )
    print(f"[完成] 成功生成买方机构级 5-Sheet Excel 工作簿: {out_path}")


if __name__ == "__main__":
    main()
