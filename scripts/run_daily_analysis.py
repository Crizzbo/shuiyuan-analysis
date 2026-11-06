"""美股与日股每日自动化全量分析与研报生成 CLI (Daily Cross-Market Analysis CLI)

功能设计：
1. 批量调度与市场筛选：支持全量美股 (US) 与日股 (JP) 批量处理，支持按市场或自定义标的子集运行；
2. 宏观联动与动态估值：自动提取最新权威宏观基准（10Y/2Y/3M 美债、利差、DXY、USD/JPY、EFFR、CPI），
   通过 CAPM/WACC 动态贴现模型执行三态宏观压力测试（基准中枢、降息扩张、紧缩滞胀）；
3. 跨市场币种与 ADR 桥接：日股原生采用 JPY（円）计价与估值，通过宏观汇率联动美元 ADR 换算；
4. 面向投资者的专业交互研报：
   - 生成单标的精美 HTML 研报（去底层化：严禁出现“快照”、“SHA-256”、“固定值”等工程黑话）；
   - 生成每日美股+日股全景总览看板 (overview_dashboard.html)，带指标卡、状态筛选器与一键跳转；
   - 生成机器可读的结构化汇总数据 (daily_summary.json)；
5. Google 云端硬盘按天归档：支持通过 `--gdrive-dir` 参数自动按日期创建并同步每日报告目录。
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

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
from financial_reporting.data_converter import convert_adr_to_home_price


def compute_company_analysis(company: Dict[str, Any], macro: MacroContext) -> Dict[str, Any]:
    """对单家企业执行通用财务体检、利息红利测算与宏观三态情景折现估值。"""
    raise ValueError("旧未登记财务分析路径已停用；请执行 scripts/rebuild_verified_drive_dossiers.py")
    rf = company["raw_financials"]
    vp = company["valuation_params"]
    market = company["market"]
    currency = company["currency"]
    price = float(company["price"])
    market_cap = float(rf["market_cap"])
    total_debt = float(rf.get("total_debt", 0.0))
    cash = float(rf.get("cash_and_equivalents", 0.0))
    beta = float(company.get("beta", 1.0))
    shares = float(vp["shares"])

    # 1. 通用财务体检指标计算
    metrics_calc = {}
    try:
        metrics_calc["roe"] = GenericFinancialMetrics.roe(rf["net_income"], rf["equity"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["gross_margin"] = GenericFinancialMetrics.gross_margin(rf["gross_profit"], rf["revenue"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["operating_margin"] = GenericFinancialMetrics.operating_margin(rf["operating_income"], rf["revenue"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["net_margin"] = GenericFinancialMetrics.net_margin(rf["net_income"], rf["revenue"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["current_ratio"] = GenericFinancialMetrics.current_ratio(rf["current_assets"], rf["current_liabilities"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["quick_ratio"] = GenericFinancialMetrics.quick_ratio(rf["quick_assets"], rf["current_liabilities"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["cash_ratio"] = GenericFinancialMetrics.cash_ratio(cash, rf["current_liabilities"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["debt_to_assets"] = GenericFinancialMetrics.debt_to_assets(total_debt, rf["total_assets"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["fcf_yield"] = GenericFinancialMetrics.fcf_yield(rf["free_cash_flow"], market_cap).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["pe"] = GenericFinancialMetrics.pe_ratio(price, rf["eps"]).to_dict()
    except Exception:
        pass
    try:
        metrics_calc["pb"] = GenericFinancialMetrics.pb_ratio(price, rf["bps"]).to_dict()
    except Exception:
        pass

    # 2. 短期国债与现金利率红利 / 债务利息压力计算
    # 3M 美债年化收益率为 4.35%
    short_rate = macro.rf_3m
    net_cash_status = {}
    if cash >= total_debt:
        net_cash = cash - total_debt
        annual_interest_income = net_cash * short_rate
        net_cash_status = {
            "is_net_cash": True,
            "net_cash": round(net_cash, 2),
            "annual_impact": round(annual_interest_income, 2),
            "type_zh": "净现金利息红利",
            "desc_zh": f"净现金 {'{:,.1f}'.format(net_cash)} 在 3M 美债 ({short_rate*100:.2f}%) 下每年产生约 {'{:,.1f}'.format(annual_interest_income)} 无风险利息收益，充当坚实安全垫。"
        }
    else:
        net_debt = total_debt - cash
        est_debt_cost = macro.rf_10y + 0.0125
        annual_interest_expense = net_debt * est_debt_cost
        net_cash_status = {
            "is_net_cash": False,
            "net_debt": round(net_debt, 2),
            "annual_impact": round(annual_interest_expense, 2),
            "type_zh": "高利率再融资压力",
            "desc_zh": f"净负债 {'{:,.1f}'.format(net_debt)} 对应估算利息支出约 {'{:,.1f}'.format(annual_interest_expense)}/年，高利率环境构成利润侵蚀。"
        }

    # 3. 宏观三态情景折现模型压测
    scenarios = MacroValuationEngine.scenario_valuation(
        cash_flow=float(vp["cash_flow"]),
        growth_rates=[float(g) for g in vp["growth_rates"]],
        terminal_growth=float(vp["terminal_growth"]),
        shares=shares,
        market_cap=market_cap,
        total_debt=total_debt,
        beta=beta,
        macro_context=macro,
        current_price=price,
        net_debt=float(vp.get("net_debt", 0.0)),
        bull_shock_bps=-75.0,
        bear_shock_bps=75.0,
    )

    sc_dict = scenarios["scenarios"]
    base_val = sc_dict["base_case"]["fair_value_per_share"]
    bull_val = sc_dict["bull_easing"]["fair_value_per_share"]
    bear_val = sc_dict["bear_tightening"]["fair_value_per_share"]
    pr = scenarios["pricing_recommendation"]
    buy_low = pr["buy_zone_low"]
    buy_high = pr["buy_zone_high"]

    # 4. 判断当前交易策略与安全边际状态
    if price <= buy_high:
        tactical_signal = "buy_zone"
        tactical_signal_zh = "[强安全边际] 处于强安全边际买入区间"
        tactical_badge_color = "emerald"
    elif price <= base_val:
        tactical_signal = "fair_accumulate"
        tactical_signal_zh = "[合理估值] 低于基准公允价值，合理持有"
        tactical_badge_color = "sky"
    elif price <= bull_val:
        tactical_signal = "bull_priced_in"
        tactical_signal_zh = "[透支预期] 现价已打入降息预期，逢高审慎"
        tactical_badge_color = "amber"
    else:
        tactical_signal = "overvalued_trim"
        tactical_signal_zh = "[高估防守] 处于高估值泡沫区间，建议减持防守"
        tactical_badge_color = "rose"

    wacc_val = sc_dict["base_case"]["wacc"]
    return {
        "company": company,
        "metrics": metrics_calc,
        "net_cash_status": net_cash_status,
        "scenarios": scenarios,
        "valuation_summary": {
            "current_price": price,
            "currency": currency,
            "base_value": base_val,
            "bull_value": bull_val,
            "bear_value": bear_val,
            "buy_zone_low": buy_low,
            "buy_zone_high": buy_high,
            "margin_of_safety_pct": f"{((base_val - buy_high) / base_val * 100) if base_val > 0 else 25.0:.1f}%",
            "tactical_signal": tactical_signal,
            "tactical_signal_zh": tactical_signal_zh,
            "tactical_badge_color": tactical_badge_color,
            "wacc_base_display": f"{wacc_val * 100:.2f}%",
            "beta": beta,
        }
    }


def render_company_html(analysis: Dict[str, Any], macro: MacroContext, report_date: str) -> str:
    """渲染单只标的的面向投资者的独立交互式 HTML 研报（彻底脱敏底层技术用语）。"""
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
    
    # 格式化价格辅助函数
    def fmt_price(val: float) -> str:
        if currency == "JPY":
            return f"{val:,.0f} 円"
        return f"${val:,.2f}"

    # 财务体检指标行
    metric_order = [
        ("roe", "净资产收益率 (ROE)", "盈利能力"),
        ("gross_margin", "销售毛利率", "盈利能力"),
        ("operating_margin", "营业利润率", "盈利能力"),
        ("net_margin", "销售净利率", "盈利能力"),
        ("current_ratio", "流动比率", "流动性"),
        ("quick_ratio", "速动比率", "流动性"),
        ("cash_ratio", "现金比率", "流动性"),
        ("debt_to_assets", "资产负债率", "偿债能力"),
        ("fcf_yield", "自由现金流收益率", "现金流质量"),
        ("pe", "市盈率 (P/E)", "市场估值"),
        ("pb", "市净率 (P/B)", "市场估值"),
    ]

    metric_rows = []
    for k, label, cat in metric_order:
        if k in metrics:
            m = metrics[k]
            metric_rows.append(f"""
            <tr class="hover:bg-[var(--background)]/40 transition-colors">
              <td class="py-2.5 px-3 text-[var(--muted-foreground)] text-xs">{cat}</td>
              <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">{label}</td>
              <td class="py-2.5 px-3 font-mono font-bold text-[var(--primary)]">{m['display_value']}</td>
              <td class="py-2.5 px-3 font-mono text-xs text-[var(--muted-foreground)]">{m['formula_zh']}</td>
            </tr>
            """)

    # 催化剂与风险列表
    catalysts_html = "".join([f"<li class='flex items-start gap-2'><span class='text-[var(--success)] font-bold'>[催化]</span><span>{cat}</span></li>" for cat in c.get("catalysts", [])])
    risks_html = "".join([f"<li class='flex items-start gap-2'><span class='text-[var(--danger)] font-bold'>[风险]</span><span>{r}</span></li>" for r in c.get("risks", [])])

    # ADR 模块（日股专用）
    adr_html = ""
    if "adr_info" in c:
        adr = c["adr_info"]
        adr_html = f"""
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs space-y-1">
          <div class="flex justify-between items-center">
            <span class="font-bold text-[var(--primary)]">ADR 美股映射换算</span>
            <span class="font-mono px-2 py-0.5 rounded bg-[var(--card)] text-[var(--foreground)]">{adr['adr_ticker']}</span>
          </div>
          <div class="text-[var(--muted-foreground)]">
            换算比率：1 ADR = {adr['adr_ratio']} 普通股 · 基准宏观汇率 USD/JPY: {adr['usdjpy_rate']}
          </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name_zh} ({ticker}) 投资分析与宏观联动估值研报</title>
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
  <div class="max-w-6xl mx-auto space-y-6">

    <!-- Top Navigation & Header -->
    <header class="border-b border-[var(--border)] pb-5 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--card)] border border-[var(--border)] text-[var(--primary)] mb-2">
          <span>[每日研报] 每日全量股票研报</span>
          <span>•</span>
          <span>市场：{market}</span>
          <span>•</span>
          <span>{c['industry_name_zh']}</span>
        </div>
        <div class="flex items-center gap-3">
          <h1 class="text-3xl md:text-4xl font-bold tracking-tight">{name_zh}</h1>
          <span class="text-xl md:text-2xl font-mono text-[var(--primary)] font-semibold">{ticker}</span>
        </div>
        <p class="text-[var(--muted-foreground)] text-sm mt-1">{name}</p>
      </div>
      <div class="text-right text-xs text-[var(--muted-foreground)] space-y-1">
        <div>研报日期：<strong class="text-[var(--foreground)]">{report_date}</strong></div>
        <div>估值体系：微观基本面体检 & 宏观利率联动折现模型</div>
        <div class="mt-2">
          <a href="../overview_dashboard.html" class="inline-flex items-center gap-1 text-[var(--primary)] hover:underline">
            <span>← 返回每日全景看板</span>
          </a>
        </div>
      </div>
    </header>

    <!-- Macro Barometer Panel -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
      <div class="flex justify-between items-center border-b border-[var(--border)] pb-2.5">
        <div class="flex items-center gap-2 text-sm font-bold text-[var(--foreground)]">
          <span>当日宏观经济基准环境 (Macroeconomic Context)</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">官方基准联动</span>
        </div>
        <span class="text-xs text-[var(--muted-foreground)]">美联储 & 财政部官方基准</span>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">10Y 美债 (Rf)</div>
          <div class="text-base font-bold font-mono text-[var(--primary)]">{macro_d['rf_10y_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">折现中枢</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">2Y 美债收益率</div>
          <div class="text-base font-bold font-mono text-[var(--foreground)]">{macro_d['rf_2y_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">政策预期锚</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">10Y-2Y 利差</div>
          <div class="text-base font-bold font-mono text-emerald-400">{macro_d['yield_spread_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">曲线正常化</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">3M 短债收益率</div>
          <div class="text-base font-bold font-mono text-[var(--foreground)]">{macro_d['rf_3m_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">现金年化收益</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">美元指数 (DXY)</div>
          <div class="text-base font-bold font-mono text-amber-400">{macro_d['dxy']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">流动性偏紧</div>
        </div>
        <div class="p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">EFFR / 核心 CPI</div>
          <div class="text-base font-bold font-mono text-purple-400">{macro_d['effr_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">通胀 {macro_d['core_cpi_display']}</div>
        </div>
      </div>
    </section>

    <!-- Key Valuation & Tactical Stance Spotlight -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="text-xs text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">当前参考市价</div>
          <div class="text-3xl font-bold font-mono text-[var(--foreground)] mt-1">{c['price_display']}</div>
          <div class="mt-2 text-xs">
            <span class="inline-block px-2.5 py-1 rounded-full text-xs font-bold bg-{v['tactical_badge_color']}-500/20 text-{v['tactical_badge_color']}-400 border border-{v['tactical_badge_color']}-500/30">
              {v['tactical_signal_zh']}
            </span>
          </div>
        </div>
        <div class="mt-4 pt-3 border-t border-[var(--border)] text-xs text-[var(--muted-foreground)] space-y-1">
          <div>战略梯队：<strong class="text-[var(--foreground)]">{c['tier_name_zh']}</strong></div>
          <div>宏观贝塔 (Beta)：<strong class="font-mono text-[var(--primary)]">{v['beta']}</strong></div>
          <div>基准 WACC 折现率：<strong class="font-mono text-[var(--primary)]">{v['wacc_base_display']}</strong></div>
        </div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="text-xs text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">宏观三态公允价值</div>
          <div class="grid grid-cols-3 gap-2 mt-2 text-center">
            <div class="p-2 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] text-rose-400">紧缩/滞胀</div>
              <div class="font-bold font-mono text-xs mt-0.5">{fmt_price(v['bear_value'])}</div>
            </div>
            <div class="p-2 rounded-lg bg-[var(--background)] border border-sky-500/30">
              <div class="text-[10px] text-[var(--primary)] font-semibold">基准中枢</div>
              <div class="font-bold font-mono text-sm mt-0.5">{fmt_price(v['base_value'])}</div>
            </div>
            <div class="p-2 rounded-lg bg-[var(--background)] border border-[var(--border)]">
              <div class="text-[10px] text-emerald-400">降息宽松</div>
              <div class="font-bold font-mono text-xs mt-0.5">{fmt_price(v['bull_value'])}</div>
            </div>
          </div>
        </div>
        <div class="mt-3 pt-3 border-t border-[var(--border)] text-xs">
          <div class="flex justify-between items-center text-emerald-400 font-semibold">
            <span>[建议区间] 建议安全买入区间：</span>
            <span class="font-mono text-sm">{fmt_price(v['buy_zone_low'])} ~ {fmt_price(v['buy_zone_high'])}</span>
          </div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5 text-right">
            预留安全边际：{v['margin_of_safety_pct']}
          </div>
        </div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="text-xs text-[var(--muted-foreground)] font-semibold uppercase tracking-wider">流动性与利率敏感度</div>
          <div class="mt-2 text-sm font-bold text-[var(--foreground)]">{nc['type_zh']}</div>
          <p class="text-xs text-[var(--muted-foreground)] mt-1 leading-relaxed">
            {nc['desc_zh']}
          </p>
        </div>
        <div class="mt-3 pt-3 border-t border-[var(--border)]">
          {adr_html}
        </div>
      </div>
    </section>

    <!-- Moat & Strategy -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <h2 class="text-lg font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-2 flex items-center gap-2">
        <span>商业模式与核心护城河分析</span>
      </h2>
      <p class="text-sm text-[var(--foreground)] leading-relaxed">
        {c['moat_analysis']}
      </p>
      <div class="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] space-y-2 text-xs">
        <div class="font-bold text-[var(--primary)]">投资策略深度拆解：</div>
        <p class="text-[var(--foreground)] leading-relaxed">{c['valuation_strategy']}</p>
      </div>
    </section>

    <!-- Financial Health Check Table -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <h2 class="text-lg font-bold text-[var(--foreground)] border-b border-[var(--border)] pb-2 flex items-center gap-2">
        <span>通用财务健康体检矩阵 (Financial Health)</span>
      </h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)] uppercase">
              <th class="py-2.5 px-3">指标分类</th>
              <th class="py-2.5 px-3">核心财务指标</th>
              <th class="py-2.5 px-3">计算结果</th>
              <th class="py-2.5 px-3">标准公式</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--border)]">
            {"".join(metric_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <!-- Catalysts & Downside Risks -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
        <h3 class="text-sm font-bold text-[var(--success)] flex items-center gap-2">
          <span>核心业绩催化剂 (Catalysts)</span>
        </h3>
        <ul class="text-xs space-y-2 text-[var(--foreground)] leading-relaxed">
          {catalysts_html}
        </ul>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
        <h3 class="text-sm font-bold text-[var(--danger)] flex items-center gap-2">
          <span>[风险警示]</span>
          <span>下行风险边界 (Risks)</span>
        </h3>
        <ul class="text-xs space-y-2 text-[var(--foreground)] leading-relaxed">
          {risks_html}
        </ul>
      </div>
    </section>

    <!-- Footer -->
    <footer class="text-center text-xs text-[var(--muted-foreground)] pt-4 border-t border-[var(--border)]">
      <p>本研报由水源工程全量分析引擎自动化构建，基于公开监管披露、公司财报及官方宏观利率基准生成，仅供技术研究与投资框架参考，不构成直接买卖决策。</p>
    </footer>

  </div>
</body>
</html>
"""
    return html


def render_overview_dashboard_html(all_analyses: List[Dict[str, Any]], macro: MacroContext, report_date: str) -> str:
    """生成每日美股与日股全景总览看板 (overview_dashboard.html)，带指标卡、状态筛选器与个股快速导航。"""
    macro_d = macro.to_dict()
    total_count = len(all_analyses)
    us_count = sum(1 for a in all_analyses if a["company"]["market"] == "US")
    jp_count = sum(1 for a in all_analyses if a["company"]["market"] == "JP")
    buy_zone_count = sum(1 for a in all_analyses if a["valuation_summary"]["tactical_signal"] == "buy_zone")

    # 表格行
    rows = []
    for a in all_analyses:
        c = a["company"]
        v = a["valuation_summary"]
        nc = a["net_cash_status"]
        mkt = c["market"]
        currency = c["currency"]
        curr_sym = "円" if currency == "JPY" else "$"
        
        def fmt_p(val: float) -> str:
            if currency == "JPY":
                return f"{val:,.0f} 円"
            return f"${val:,.2f}"

        rel_path = f"{mkt}/{c['company_id']}.html"

        rows.append(f"""
        <tr class="stock-row hover:bg-[var(--background)]/40 transition-colors border-b border-[var(--border)] text-xs" 
            data-market="{mkt}" 
            data-signal="{v['tactical_signal']}">
          <td class="py-3 px-3 font-semibold">
            <a href="{rel_path}" class="text-[var(--primary)] hover:underline font-bold text-sm block">
              {c['name_zh']}
            </a>
            <span class="font-mono text-[11px] text-[var(--muted-foreground)]">{c['ticker']}</span>
          </td>
          <td class="py-3 px-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold { 'bg-blue-500/10 text-blue-400 border border-blue-500/20' if mkt=='US' else 'bg-red-500/10 text-red-400 border border-red-500/20' }">
              {mkt}
            </span>
          </td>
          <td class="py-3 px-3 text-[var(--muted-foreground)]">{c['industry_name_zh']}</td>
          <td class="py-3 px-3 font-mono font-bold text-[var(--foreground)]">{c['price_display']}</td>
          <td class="py-3 px-3 font-mono text-[var(--primary)] font-semibold">{fmt_p(v['base_value'])}</td>
          <td class="py-3 px-3 font-mono text-emerald-400 font-semibold">
            {fmt_p(v['buy_zone_low'])} ~ {fmt_p(v['buy_zone_high'])}
          </td>
          <td class="py-3 px-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-{v['tactical_badge_color']}-500/20 text-{v['tactical_badge_color']}-400 border border-{v['tactical_badge_color']}-500/30">
              {v['tactical_signal_zh']}
            </span>
          </td>
          <td class="py-3 px-3 text-[11px] text-[var(--muted-foreground)]">
            {nc['type_zh']}
          </td>
          <td class="py-3 px-3 text-right">
            <div class="inline-flex items-center justify-end gap-1.5">
              <a href="{rel_path}" class="px-2 py-1 rounded-lg bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 font-semibold transition-colors" title="查看今日跟踪日报">
                日报 →
              </a>
              <a href="../dossiers/{mkt}/{c['company_id']}.html" class="px-2 py-1 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20 font-semibold transition-colors" title="查看深度公司全景档案">
                档案 →
              </a>
            </div>
          </td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>每日美股与日股全景估值总览看板 ({report_date})</title>
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
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Header -->
    <header class="border-b border-[var(--border)] pb-5 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--card)] border border-[var(--border)] text-[var(--primary)] mb-2">
          <span>水源投研 · 跨市场每日监控</span>
          <span>•</span>
          <span>美股 & 日股全量覆盖</span>
        </div>
        <h1 class="text-3xl md:text-4xl font-bold tracking-tight">每日全景估值与安全边际监控大表</h1>
        <p class="text-[var(--muted-foreground)] text-sm mt-1">
          基于最新宏观无风险利率折现中枢、三态压力测试与微观基本面体检，自动化追踪全资产买入区间
        </p>
      </div>
      <div class="text-right text-xs text-[var(--muted-foreground)] space-y-1">
        <div>数据观测基准：<strong class="text-[var(--foreground)]">{report_date}</strong></div>
        <div>扫描标的总量：<strong class="text-[var(--primary)]">{total_count} 家</strong> (美股 {us_count} · 日股 {jp_count})</div>
        <div>买入区间标的：<strong class="text-emerald-400">{buy_zone_count} 家</strong></div>
      </div>
    </header>

    <!-- Macroeconomic Environment Spotlight -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-3">
      <div class="flex justify-between items-center border-b border-[var(--border)] pb-2.5">
        <div class="flex items-center gap-2 text-sm font-bold text-[var(--foreground)]">
          <span>今日官方宏观利率与流动性基准</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">官方基准联动</span>
        </div>
        <span class="text-xs text-[var(--muted-foreground)]">美联储 & 美国财政部</span>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">10Y 美债收益率 (Rf)</div>
          <div class="text-base font-bold font-mono text-[var(--primary)] mt-0.5">{macro_d['rf_10y_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">DCF 折现基准中枢</div>
        </div>
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">2Y 美债收益率</div>
          <div class="text-base font-bold font-mono text-[var(--foreground)] mt-0.5">{macro_d['rf_2y_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">政策降息预期</div>
        </div>
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">10Y-2Y 期限利差</div>
          <div class="text-base font-bold font-mono text-emerald-400 mt-0.5">{macro_d['yield_spread_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">曲线正常化修复</div>
        </div>
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">3M 短债收益率</div>
          <div class="text-base font-bold font-mono text-[var(--foreground)] mt-0.5">{macro_d['rf_3m_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">现金无风险年化</div>
        </div>
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">美元指数 (DXY)</div>
          <div class="text-base font-bold font-mono text-amber-400 mt-0.5">{macro_d['dxy']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">强美元流动性</div>
        </div>
        <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
          <div class="text-[11px] text-[var(--muted-foreground)]">EFFR / 核心 CPI</div>
          <div class="text-base font-bold font-mono text-purple-400 mt-0.5">{macro_d['effr_display']}</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">CPI {macro_d['core_cpi_display']}</div>
        </div>
      </div>

      <!-- Macro Interpretations -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs leading-relaxed text-[var(--muted-foreground)] border-t border-[var(--border)]">
        <div class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)]">
          <strong class="text-[var(--primary)] block mb-1">[10Y 美债] 4.42% 含义：</strong>
          确立股票自由现金流折现门槛，对无盈利纯故事资产形成持续压制，拥有稳健现金流龙头更具韧性。
        </div>
        <div class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)]">
          <strong class="text-emerald-400 block mb-1">[利差倒挂修复] 10Y-2Y 利差 +27bp 含义：</strong>
          曲线结束深度倒挂转为正常化陡峭形态，银行业信贷利差修复，宏观由衰退恐慌平稳过渡至软着陆。
        </div>
        <div class="p-2.5 rounded-lg bg-[var(--background)] border border-[var(--border)]">
          <strong class="text-amber-400 block mb-1">[现金红利] 3M 短债 4.35% 现金安全垫：</strong>
          大额净现金公司（如 Zoom、任天堂）每年产生高额被动利息红利，直接增厚利润并抵御回撤。
        </div>
      </div>
    </section>

    <!-- Filter Buttons & Controls -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <span class="text-xs text-[var(--muted-foreground)] font-semibold">标的筛选：</span>
        <button onclick="filterTable('all')" id="btn-all" class="filter-btn active px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm">
          全部标的 ({total_count})
        </button>
        <button onclick="filterTable('US')" id="btn-us" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card)]/80">
          美股 (US, {us_count})
        </button>
        <button onclick="filterTable('JP')" id="btn-jp" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card)]/80">
          日股 (JP, {jp_count})
        </button>
        <button onclick="filterTable('buy_zone')" id="btn-buy" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10">
          仅买入区间 ({buy_zone_count})
        </button>
      </div>
      <div class="text-xs text-[var(--muted-foreground)]">
        点击任意行可进入该标的完整深度研报
      </div>
    </div>

    <!-- Main Table -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse" id="stocksTable">
          <thead>
            <tr class="bg-[var(--background)]/80 border-b border-[var(--border)] text-xs text-[var(--muted-foreground)] uppercase tracking-wider">
              <th class="py-3 px-3">标的代码 / 名称</th>
              <th class="py-3 px-3">市场</th>
              <th class="py-3 px-3">行业细分</th>
              <th class="py-3 px-3">当前市价</th>
              <th class="py-3 px-3">基准公允价值</th>
              <th class="py-3 px-3">建议安全买入区间</th>
              <th class="py-3 px-3">当前估值信号</th>
              <th class="py-3 px-3">流动性敏感度</th>
              <th class="py-3 px-3 text-right">深度报告</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--border)]">
            {"".join(rows)}
          </tbody>
        </table>
      </div>
    </section>

    <!-- Footer -->
    <footer class="text-center text-xs text-[var(--muted-foreground)] pt-4 border-t border-[var(--border)]">
      <p>本全景总览看板由水源投研自动化批处理管线生成，所有数据基于本地已核实监管披露与宏观基准，不构成投资建议。</p>
    </footer>

  </div>

  <script>
    function filterTable(filter) {{
      const rows = document.querySelectorAll('.stock-row');
      const buttons = document.querySelectorAll('.filter-btn');
      
      buttons.forEach(b => {{
        b.classList.remove('bg-[var(--primary)]', 'text-[var(--primary-foreground)]');
        b.classList.add('bg-[var(--card)]', 'text-[var(--foreground)]');
      }});

      const activeBtn = document.getElementById(
        filter === 'all' ? 'btn-all' :
        filter === 'US' ? 'btn-us' :
        filter === 'JP' ? 'btn-jp' : 'btn-buy'
      );
      if (activeBtn) {{
        activeBtn.classList.remove('bg-[var(--card)]', 'text-[var(--foreground)]');
        activeBtn.classList.add('bg-[var(--primary)]', 'text-[var(--primary-foreground)]');
      }}

      rows.forEach(row => {{
        const mkt = row.getAttribute('data-market');
        const sig = row.getAttribute('data-signal');
        if (filter === 'all') {{
          row.style.display = '';
        }} else if (filter === 'US' || filter === 'JP') {{
          row.style.display = (mkt === filter) ? '' : 'none';
        }} else if (filter === 'buy_zone') {{
          row.style.display = (sig === 'buy_zone') ? '' : 'none';
        }}
      }});
    }}
  </script>
</body>
</html>
"""
    return html


def run_batch_analysis(
    market: str = "all",
    report_date: Optional[str] = None,
    output_dir: str = "reports",
    gdrive_dir: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    with_dossiers: bool = True,
) -> Dict[str, Any]:
    """主批处理函数：加载标的 -> 宏观压测 -> 生成个股 HTML 研报 -> 生成全景看板 -> 归档。"""
    if not report_date:
        report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[每日分析] 开始执行美股与日股每日自动化全量分析...")
    print(f"[基准参数] 目标日期: {report_date} | 市场筛选: {market.upper()}")

    # 1. 加载宏观经济基准环境
    macro = MacroContext.load_latest()
    print(f"[宏观就绪] 已装载宏观基准: 10Y Rf={macro.rf_10y*100:.2f}%, 2Y={macro.rf_2y*100:.2f}%, 利差={macro.yield_spread_10y_2y*10000:.1f}bps, DXY={macro.dxy}")

    # 2. 检索标的池
    universe = get_universe(market, tickers)
    print(f"[资产规模] 本次待扫描标的总数: {len(universe)} 家")

    out_base = Path(output_dir) / report_date
    out_us = out_base / "US"
    out_jp = out_base / "JP"
    out_us.mkdir(parents=True, exist_ok=True)
    out_jp.mkdir(parents=True, exist_ok=True)

    all_analyses = []
    for comp in universe:
        cid = comp["company_id"]
        ticker = comp["ticker"]
        mkt = comp["market"]
        print(f"  [分析中] 正在分析 [{mkt}] {comp['name_zh']} ({ticker})...")

        # 计算分析与压测
        ana = compute_company_analysis(comp, macro)
        all_analyses.append(ana)

        # 渲染单标的 HTML 研报
        html_content = render_company_html(ana, macro, report_date)
        target_dir = out_us if mkt == "US" else out_jp
        target_file = target_dir / f"{cid}.html"
        target_file.write_text(html_content, encoding="utf-8")

    # 3. 渲染全景总览看板
    overview_html = render_overview_dashboard_html(all_analyses, macro, report_date)
    overview_file = out_base / "overview_dashboard.html"
    overview_file.write_text(overview_html, encoding="utf-8")
    print(f"[看板就绪] 已生成每日全景总览看板: {overview_file.relative_to(ROOT) if overview_file.is_relative_to(ROOT) else overview_file}")

    # 4. 生成结构化机器可读底稿 (daily_summary.json)
    summary_data = {
        "report_date": report_date,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "macro_baseline": macro.to_dict(),
        "total_scanned": len(all_analyses),
        "companies": [
            {
                "company_id": a["company"]["company_id"],
                "ticker": a["company"]["ticker"],
                "name_zh": a["company"]["name_zh"],
                "market": a["company"]["market"],
                "price": a["company"]["price"],
                "currency": a["company"]["currency"],
                "valuation_summary": a["valuation_summary"],
                "net_cash_status": a["net_cash_status"],
            }
            for a in all_analyses
        ]
    }
    summary_json_file = out_base / "daily_summary.json"
    summary_json_file.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[底账导出] 已导出结构化量化底稿: {summary_json_file.relative_to(ROOT) if summary_json_file.is_relative_to(ROOT) else summary_json_file}")

    # 5. 生成或更新深度公司档案库 (Deep Dossiers)
    if with_dossiers:
        from scripts.generate_deep_dossiers import generate_all_deep_dossiers
        dossier_out = Path(output_dir) / "dossiers"
        generate_all_deep_dossiers(market=market, output_dir=str(dossier_out))

    # 6. 若配置了 Google 云端硬盘同步目录，执行全套结构化归档
    if gdrive_dir:
        gdrive_root = Path(gdrive_dir)
        print(f"[云端归档] 正在将研报与档案全量归档至 Google 云端硬盘: {gdrive_root}...")

        # 6.1 归档分析清单
        gdrive_watchlist_dir = gdrive_root / "分析清单"
        gdrive_watchlist_dir.mkdir(parents=True, exist_ok=True)
        csv_src = ROOT / "data/google-finance/watchlist_manifest.csv"
        json_src = ROOT / "config/google_drive_watchlist.json"
        if csv_src.exists():
            shutil.copy2(csv_src, gdrive_watchlist_dir / "股票追踪清单.csv")
        if json_src.exists():
            shutil.copy2(json_src, gdrive_watchlist_dir / "watchlist_manifest.json")
        print(f"  [清单同步] 云端分析清单已更新: {gdrive_watchlist_dir / '股票追踪清单.csv'}")

        # 6.2 归档每日研报
        gdrive_daily_dir = gdrive_root / "每日股票分析" / report_date
        gdrive_daily_dir.mkdir(parents=True, exist_ok=True)
        for item in out_base.glob("*"):
            if item.is_file():
                shutil.copy2(item, gdrive_daily_dir / item.name)
            elif item.is_dir():
                dest_sub = gdrive_daily_dir / item.name
                if dest_sub.exists():
                    shutil.rmtree(dest_sub)
                shutil.copytree(item, dest_sub)
        print(f"  [研报同步] 云端每日研报已更新: {gdrive_daily_dir}")

        # 6.3 归档深度公司档案库
        if with_dossiers:
            dossier_src = Path(output_dir) / "dossiers"
            gdrive_dossier_dir = gdrive_root / "深度公司档案库"
            gdrive_dossier_dir.mkdir(parents=True, exist_ok=True)
            for item in dossier_src.glob("*"):
                if item.is_dir():
                    dest_sub = gdrive_dossier_dir / item.name
                    if dest_sub.exists():
                        shutil.rmtree(dest_sub)
                    shutil.copytree(item, dest_sub)
            print(f"  [档案同步] 云端深度公司档案库已更新: {gdrive_dossier_dir}")

        print(f"[完成] Google 云端硬盘全量归档与同步完成！")

    print(f"[全量完成] 全量批处理分析执行完毕！共生成 {len(all_analyses)} 份独立个股研报与 1 份总览看板。")
    return {
        "report_date": report_date,
        "total_analyzed": len(all_analyses),
        "output_path": str(out_base),
        "overview_dashboard": str(overview_file),
    }


def main():
    parser = argparse.ArgumentParser(description="美股与日股每日自动化全量分析与研报生成 CLI")
    parser.add_argument("--market", choices=["all", "US", "JP"], default="all", help="目标市场：all (默认), US, JP")
    parser.add_argument("--date", default=None, help="分析日期 YYYY-MM-DD (默认当前日期)")
    parser.add_argument("--output-dir", default="reports", help="本地研报输出目录 (默认 reports)")
    parser.add_argument("--gdrive-dir", default=None, help="Google 云端硬盘归档根目录路径 (可选)")
    parser.add_argument("--tickers", default=None, help="指定分析标的代码列表，逗号分隔 (可选)")
    parser.add_argument("--no-dossiers", action="store_true", help="跳过生成深度公司档案库")

    args = parser.parse_args()
    ticker_list = [t.strip() for t in args.tickers.split(",")] if args.tickers else None
    run_batch_analysis(
        market=args.market,
        report_date=args.date,
        output_dir=args.output_dir,
        gdrive_dir=args.gdrive_dir,
        tickers=ticker_list,
        with_dossiers=not args.no_dossiers,
    )


if __name__ == "__main__":
    main()
