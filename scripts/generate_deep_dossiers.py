"""深度公司档案与全景投资分析文件生成程序 (Deep Company Dossier Generator)

业务定位：
1. 为清单中的每只股票构建机构级“深度公司档案与投资全景研报” (Deep Dossier)；
2. 涵盖 9 大核心研究维度：
   - 企业全景与全球证券架构（含日股 ADR 换算与原生 JPY 对齐）；
   - 商业模式透视与四维护城河多维解构（网络效应、转换壁垒、成本优势、品牌无形资产）；
   - 通用财务健康体检全息透视（杜邦 ROE、盈利边际、偿债流动性、FCF 收益率）；
   - 41 行业专属胜负手驱动指标映射；
   - 宏观经济基准联动与三态情景折现估值（动态 WACC、基准中枢、紧缩防御底、降息乐观靶心、严苛买入区间）；
   - 资产负债表现金利息红利与债务利率敏感度；
   - 三大长期战略业绩催化剂；
   - 三大核心下行风险与黑天鹅底线；
   - 机构级建仓纪律与仓位配置指引。
3. 严格遵循面向用户的交付标准：彻底杜绝“快照”、“SHA-256”、“固定值”等底层工程黑话；
4. 支持导出至本地目录及 Google 云端硬盘“深度公司档案库” (`深度公司档案库/US/` 与 `深度公司档案库/JP/`)。
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional

# Windows 终端 GBK 兼容性保护
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.company_universe import COMPANY_UNIVERSE, get_universe
from financial_reporting.generic_metrics import GenericFinancialMetrics
from financial_reporting.macro_valuation import MacroContext, MacroValuationEngine
from scripts.run_daily_analysis import compute_company_analysis


def render_deep_dossier_html(analysis: Dict[str, Any], macro: MacroContext) -> str:
    """渲染单家企业的机构级深度档案 HTML 文件。"""
    from financial_reporting.evidence_dossiers import render_dossier_html
    if analysis.get('schema_version')!='2.0.0':
        raise ValueError('旧分析对象没有登记事实封套，拒绝渲染')
    return render_dossier_html(analysis)
    c = analysis["company"]
    v = analysis["valuation_summary"]
    nc = analysis["net_cash_status"]
    sc = analysis["scenarios"]
    metrics = analysis["metrics"]
    macro_d = macro.to_dict()

    ticker = c["ticker"]
    name_zh = c["name_zh"]
    name = c["name"]
    market = c["market"]
    currency = c["currency"]
    curr_sym = "円" if currency == "JPY" else "$"

    def fmt_p(val: float) -> str:
        if currency == "JPY":
            return f"{val:,.0f} 円"
        return f"${val:,.2f}"

    # 财务体检指标行
    metric_order = [
        ("roe", "净资产收益率 (ROE)", "盈利能力"),
        ("gross_margin", "销售毛利率", "盈利能力"),
        ("operating_margin", "营业利润率", "盈利能力"),
        ("net_margin", "销售净利率", "盈利能力"),
        ("current_ratio", "流动比率", "短期偿债"),
        ("quick_ratio", "速动比率", "流动性质量"),
        ("cash_ratio", "现金比率", "绝对变现能力"),
        ("debt_to_assets", "资产负债率", "杠杆水平"),
        ("fcf_yield", "自由现金流收益率 (FCF Yield)", "现金造血质量"),
        ("pe", "市盈率 (P/E)", "估值乘数"),
        ("pb", "市净率 (P/B)", "资产乘数"),
    ]

    metric_rows = []
    for k, label, cat in metric_order:
        if k in metrics:
            m = metrics[k]
            metric_rows.append(f"""
            <tr class="hover:bg-[var(--background)]/50 transition-colors">
              <td class="py-2.5 px-3 text-[var(--muted-foreground)] text-xs font-mono">{cat}</td>
              <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">{label}</td>
              <td class="py-2.5 px-3 font-mono font-bold text-[var(--primary)]">{m['display_value']}</td>
              <td class="py-2.5 px-3 font-mono text-xs text-[var(--muted-foreground)]">{m['formula_zh']}</td>
            </tr>
            """)

    # 催化剂与风险 HTML
    catalysts_html = "".join([f"<li class='flex items-start gap-2.5 leading-relaxed'><span class='text-[var(--success)] font-bold text-xs'>[催化]</span><span>{cat}</span></li>" for cat in c.get("catalysts", [])])
    risks_html = "".join([f"<li class='flex items-start gap-2.5 leading-relaxed'><span class='text-[var(--danger)] font-bold text-xs'>[风险]</span><span>{r}</span></li>" for r in c.get("risks", [])])

    # ADR 模块（日股专用）
    adr_block = ""
    if "adr_info" in c:
        adr = c["adr_info"]
        adr_block = f"""
        <div class="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs space-y-1.5 mt-3">
          <div class="flex justify-between items-center">
            <span class="font-bold text-[var(--primary)]">美股 ADR 跨境折算架构</span>
            <span class="font-mono px-2 py-0.5 rounded bg-[var(--card)] text-[var(--foreground)] font-bold">{adr['adr_ticker']}</span>
          </div>
          <div class="text-[var(--muted-foreground)] leading-relaxed">
            折算比率：<strong>1 ADR = {adr['adr_ratio']} 普通股</strong> · 宏观基准汇率 USD/JPY: <strong>{adr['usdjpy_rate']}</strong> · 原生记账本位币: <strong>{currency}</strong>
          </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name_zh} ({ticker}) 深度公司档案与投资全景研报</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --background: #0f172a;
      --card: #1e293b;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --border: #334155;
      --primary: #38bdf8;
      --accent: #818cf8;
      --success: #34d399;
      --warning: #fbbf24;
      --danger: #f87171;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --background: #f8fafc;
        --card: #ffffff;
        --foreground: #0f172a;
        --muted-foreground: #64748b;
        --border: #e2e8f0;
        --primary: #0284c7;
        --accent: #6366f1;
        --success: #059669;
        --warning: #d97706;
        --danger: #dc2626;
      }}
    }}
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-4 md:p-8 min-h-screen">
  <div class="max-w-6xl mx-auto space-y-7">

    <!-- Top Header -->
    <header class="border-b border-[var(--border)] pb-6 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--card)] border border-[var(--border)] text-[var(--primary)] mb-2">
          <span>深度公司档案库</span>
          <span>•</span>
          <span>市场：{market}</span>
          <span>•</span>
          <span>{c['industry_name_zh']}</span>
          <span>•</span>
          <span>{c['tier_name_zh']}</span>
        </div>
        <div class="flex items-center gap-3">
          <h1 class="text-3xl md:text-5xl font-extrabold tracking-tight">{name_zh}</h1>
          <span class="text-2xl md:text-3xl font-mono text-[var(--primary)] font-bold">{ticker}</span>
        </div>
        <p class="text-[var(--muted-foreground)] text-sm md:text-base mt-1.5">{name}</p>
      </div>
      <div class="text-right text-xs text-[var(--muted-foreground)] space-y-1">
        <div>归档版本：<strong class="text-[var(--foreground)]">机构级完整档案</strong></div>
        <div>宏观联动：10Y 美债 {macro_d['rf_10y_display']} 折现中枢</div>
        <div class="mt-2">
          <a href="../../overview_dashboard.html" class="inline-flex items-center gap-1 text-[var(--primary)] hover:underline font-semibold">
            <span>← 返回每日全景总览看板</span>
          </a>
        </div>
      </div>
    </header>

    <!-- Macro Barometer -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
      <div class="flex justify-between items-center border-b border-[var(--border)] pb-2.5">
        <div class="flex items-center gap-2 text-sm font-bold text-[var(--foreground)]">
          <span>宏观经济环境锚点 (Macro Benchmark Environment)</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">官方基准联动</span>
        </div>
        <span class="text-xs text-[var(--muted-foreground)]">美联储 & 美国财政部官方发布</span>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">10Y 美债 (Rf)</div>
          <div class="text-base font-bold font-mono text-[var(--primary)]">{macro_d['rf_10y_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">DCF 贴现门槛</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">2Y 美债收益率</div>
          <div class="text-base font-bold font-mono text-[var(--foreground)]">{macro_d['rf_2y_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">小步慢走降息</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">10Y-2Y 期限利差</div>
          <div class="text-base font-bold font-mono text-emerald-400">{macro_d['yield_spread_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">利差修复陡峭化</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">3M 短债收益率</div>
          <div class="text-base font-bold font-mono text-[var(--foreground)]">{macro_d['rf_3m_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">现金年化收益率</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">美元指数 (DXY)</div>
          <div class="text-base font-bold font-mono text-amber-400">{macro_d['dxy']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">流动性相对偏紧</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">EFFR / 核心 CPI</div>
          <div class="text-base font-bold font-mono text-purple-400">{macro_d['effr_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">粘性 {macro_d['core_cpi_display']}</div>
        </div>
      </div>
    </section>

    <!-- Executive Valuation & Stance Card Grid -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="text-xs text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">最新交易市价</div>
          <div class="text-3xl font-extrabold font-mono text-[var(--foreground)] mt-1.5">{c['price_display']}</div>
          <div class="mt-2.5">
            <span class="inline-block px-3 py-1 rounded-full text-xs font-bold bg-{v['tactical_badge_color']}-500/20 text-{v['tactical_badge_color']}-400 border border-{v['tactical_badge_color']}-500/30">
              {v['tactical_signal_zh']}
            </span>
          </div>
        </div>
        <div class="mt-5 pt-3.5 border-t border-[var(--border)] text-xs text-[var(--muted-foreground)] space-y-1.5">
          <div>战略梯队：<strong class="text-[var(--foreground)]">{c['tier_name_zh']}</strong></div>
          <div>宏观敏感度 (Beta)：<strong class="font-mono text-[var(--primary)] font-bold">{v['beta']}</strong></div>
          <div>联动 WACC 资本成本：<strong class="font-mono text-[var(--primary)] font-bold">{v['wacc_base_display']}</strong></div>
        </div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="text-xs text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">宏观三态情景压力测试</div>
          <div class="grid grid-cols-3 gap-2 mt-2.5 text-center">
            <div class="p-2 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] text-rose-400">紧缩滞胀</div>
              <div class="font-bold font-mono text-xs mt-0.5">{fmt_p(v['bear_value'])}</div>
            </div>
            <div class="p-2 rounded-xl bg-[var(--background)] border border-sky-500/40">
              <div class="text-[10px] text-[var(--primary)] font-bold">基准中枢</div>
              <div class="font-bold font-mono text-sm mt-0.5">{fmt_p(v['base_value'])}</div>
            </div>
            <div class="p-2 rounded-xl bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] text-emerald-400">降息宽松</div>
              <div class="font-bold font-mono text-xs mt-0.5">{fmt_p(v['bull_value'])}</div>
            </div>
          </div>
        </div>
        <div class="mt-4 pt-3.5 border-t border-[var(--border)] text-xs">
          <div class="flex justify-between items-center text-emerald-400 font-bold">
            <span>建议安全买入区间：</span>
            <span class="font-mono text-sm">{fmt_p(v['buy_zone_low'])} ~ {fmt_p(v['buy_zone_high'])}</span>
          </div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-1 text-right">
            安全边际垫：{v['margin_of_safety_pct']}
          </div>
        </div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="text-xs text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">资产负债表与利率敞口</div>
          <div class="mt-2 text-sm font-bold text-[var(--foreground)]">{nc['type_zh']}</div>
          <p class="text-xs text-[var(--muted-foreground)] mt-1.5 leading-relaxed">
            {nc['desc_zh']}
          </p>
        </div>
        {adr_block}
      </div>
    </section>

    <!-- Deep Moat & Business Architecture -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <h2 class="text-lg font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-2.5 flex items-center gap-2">
        <span>商业模式透视与核心护城河深度拆解 (Economic Moat)</span>
      </h2>
      <p class="text-sm text-[var(--foreground)] leading-relaxed">
        {c['moat_analysis']}
      </p>
      <div class="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] space-y-2 text-xs">
        <div class="font-bold text-[var(--primary)] flex items-center gap-1.5">
          <span>机构级投资策略深度拆解与仓位建议：</span>
        </div>
        <p class="text-[var(--foreground)] leading-relaxed">{c['valuation_strategy']}</p>
      </div>
    </section>

    <!-- Financial Health Matrix Table -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <h2 class="text-lg font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-2.5 flex items-center gap-2">
        <span>通用财务健康体检全息透视 (Financial Diagnostic)</span>
      </h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)] uppercase">
              <th class="py-2.5 px-3">指标维度</th>
              <th class="py-2.5 px-3">财务指标名称</th>
              <th class="py-2.5 px-3">计算结果</th>
              <th class="py-2.5 px-3">计算审计公式</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--border)]">
            {"".join(metric_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <!-- Catalysts & Downside Risks Grid -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
        <h3 class="text-sm font-bold text-[var(--success)] flex items-center gap-2">
          <span>三大核心业绩催化剂 (Top Catalysts)</span>
        </h3>
        <ul class="text-xs space-y-2.5 text-[var(--foreground)] leading-relaxed">
          {catalysts_html}
        </ul>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
        <h3 class="text-sm font-bold text-[var(--danger)] flex items-center gap-2">
          <span>三大核心下行风险与黑天鹅边界 (Downside Risks)</span>
        </h3>
        <ul class="text-xs space-y-2.5 text-[var(--foreground)] leading-relaxed">
          {risks_html}
        </ul>
      </div>
    </section>

    <!-- Footer -->
    <footer class="text-center text-xs text-[var(--muted-foreground)] pt-5 border-t border-[var(--border)] space-y-1">
      <p>本深度档案由水源工程投研系统自动化生成，基于公司正式财报披露与美联储/财政部权威基准，仅供技术研究与框架参考。</p>
      <p class="text-[11px] text-[var(--muted-foreground)]/80">归档存储路径：Google Drive/深度公司档案库/{market}/{c['company_id']}.html</p>
    </footer>

  </div>
</body>
</html>
"""
    return html


def generate_all_deep_dossiers(
    market: str = "all",
    output_dir: str = "reports/dossiers",
    gdrive_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """批量生成清单内所有标的的深度档案文件并按规范归档。"""
    macro = MacroContext.load_latest()
    universe = get_universe(market)
    print(f"[档案生成] 开始生成深度公司档案库 (共 {len(universe)} 家标的)...")

    base_out = Path(output_dir)
    us_out = base_out / "US"
    jp_out = base_out / "JP"
    us_out.mkdir(parents=True, exist_ok=True)
    jp_out.mkdir(parents=True, exist_ok=True)

    generated_files = []
    for comp in universe:
        cid = comp["company_id"]
        mkt = comp["market"]
        ana = compute_company_analysis(comp, macro)
        html_content = render_deep_dossier_html(ana, macro)

        target_dir = us_out if mkt == "US" else jp_out
        target_file = target_dir / f"{cid}.html"
        target_file.write_text(html_content, encoding="utf-8")
        generated_files.append(target_file)
        print(f"  [完成] [{mkt}] {comp['name_zh']} ({comp['ticker']}) 深度档案已生成")

    # 若指定了 Google 云盘目录，镜像至 Google Drive/深度公司档案库/
    if gdrive_dir:
        cloud_target = Path(gdrive_dir) / "深度公司档案库"
        print(f"[云端同步] 正在将深度档案同步至 Google 云端硬盘: {cloud_target}...")
        cloud_target.mkdir(parents=True, exist_ok=True)
        for item in base_out.glob("*"):
            if item.is_dir():
                dest_sub = cloud_target / item.name
                if dest_sub.exists():
                    shutil.rmtree(dest_sub)
                shutil.copytree(item, dest_sub)
        print(f"[完成] 深度档案已成功归档至 Google 云端硬盘: {cloud_target}")

    return {
        "total_generated": len(generated_files),
        "local_path": str(base_out),
    }


def main():
    parser = argparse.ArgumentParser(description="深度公司档案与全景投资分析文件生成程序")
    parser.add_argument("--market", choices=["all", "US", "JP"], default="all", help="目标市场")
    parser.add_argument("--output-dir", default="reports/dossiers", help="本地输出目录")
    parser.add_argument("--gdrive-dir", default=None, help="Google 云盘根目录路径")
    args = parser.parse_args()

    generate_all_deep_dossiers(
        market=args.market,
        output_dir=args.output_dir,
        gdrive_dir=args.gdrive_dir,
    )


if __name__ == "__main__":
    main()
