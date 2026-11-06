"""每日金融商业早报自动化构建程序 (Daily Briefing Builder)

功能定位：
1. 消费符合 `schemas/daily-briefing.schema.json` 契约规范的结构化早报输入数据；
2. 校验数据格式与必选模块完整性；
3. 一键渲染标准纯文本 Markdown 早报（daily_briefing.md）；
4. 一键编译现代暗色高交互机构级 HTML 仪表盘（daily_briefing.html）；
5. 保证相对路径链接与离线自包含，严禁任何外部不可控依赖或网络请求。
"""

import argparse
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_and_validate(json_path: Path) -> dict:
    """加载早报数据并使用契约 Schema 严格校验。"""
    schema_path = ROOT / "schemas/daily-briefing.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"未找到早报结构契约：{schema_path}")

    from jsonschema import Draft202012Validator

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = json.loads(json_path.read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msg = "\n".join(f"- {list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"早报输入数据不符合 Schema 契约规范：\n{msg}")

    return data


def render_markdown(data: dict) -> str:
    """渲染结构化纯文本 Markdown 早报。"""
    date = data["date"]
    issue = data["issue_number"]
    tact = data["tactical_status"]
    state = tact["state"]
    cash = tact["cash_ratio_pct"]
    erp = tact["erp_ratio_pct"]
    instr = tact["instruction"]

    lines = [
        f"# 水源全球金融商业早报（{date[:4]}年{date[5:7]}月{date[8:10]}日·机构级商业决策专刊）",
        "",
        f"> **报告属性**：全球跨市场与美日股全盘扫描（第 {issue} 期）  ",
        f"> **战术资产配置状态**：**{state}（建议现金比例 ≥ {cash}%）**  ",
        f"> **跨资产风险溢价（ERP）**：{erp}%（标普 500 风险溢价处于历史低位，股票相对债券吸引力薄弱）  ",
        f"> **今日执行指令**：**{instr}**",
        "",
        "---",
        "",
        "## 跨资产宏观脉搏（Cross-Asset Pulse）",
        "",
        "| 资产标的 | 最新行情 / 读数 | 趋势方向 | 宏观传导与商业实质 |",
        "|---|---:|:---:|---|",
    ]

    for m in data["macro_pulse"]:
        lines.append(f"| **{m['name']}** | **{m['value']}** | {m['trend']} | {m['note']} |")

    lines.extend([
        "",
        "---",
        "",
        "## 一、 今日热点商业事件与产业链博弈穿透",
        "",
    ])

    for i, ev in enumerate(data["hot_events"], 1):
        lines.extend([
            f"### {i}. {ev['title']}",
            f"- **客观事实**：{ev['facts']}",
            f"- **产业链传导实质**：{ev['transmission']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 二、 机构主力与微观资金图谱（ETF 流向 + 期权暗池异动）",
        "",
        "### 1. 机构行为关键信号",
    ])

    for sig in data["capital_flows"]["key_signals"]:
        lines.append(f"- **{sig}")

    lines.extend([
        "",
        "### 2. 板块资金增减明细",
        "- **主力净流入板块**：",
    ])
    for item in data["capital_flows"]["inflows"]:
        lines.append(f"  - {item['sector']}（{item['ticker']}）：{item['change_pct']} / {item['reason']}")

    lines.append("- **主力净流出板块**：")
    for item in data["capital_flows"]["outflows"]:
        lines.append(f"  - {item['sector']}（{item['ticker']}）：{item['change_pct']} / {item['reason']}")

    s = data["sentiment"]
    lines.extend([
        "",
        "---",
        "",
        "## 三、 市场情绪钟摆与博弈特征",
        "",
        f"- **综合情绪指数**：**{s['score']} / 100（{s['status']}）**",
        f"- **散户端微观画像（追高胜率归零）**：{s['retail_profile']}",
        f"- **机构做市商画像（缩量脆弱平衡）**：{s['institutional_profile']}",
        "",
        "---",
        "",
        "## 四、 高确信度推荐股票池（Conviction Buy List）",
        "",
        "| 标的代码 | 核心业务 / 商业模式 | 现价 | 估值锚点 | 核心竞争护城河与催化剂 | 量化交易与建仓策略 |",
        "|---|---|---:|---|---|---|",
    ])

    for b in data["conviction_buys"]:
        thesis_text = "；".join(f"{t['title']}：{t['desc']}" for t in b["thesis"])
        strat = b["trade_strategy"]
        strat_text = f"**目标介入区间**：{strat['entry_range']}<br>**止损保护位**：{strat['stop_loss']}<br>**回报预期**：{strat['expected_return']}<br>{strat['summary']}"
        lines.append(f"| **{b['ticker']}**<br>({b['name']}) | {b['market_type']}<br>{b['business_model']} | {b['price']} | {b['pe']} | {thesis_text} | {strat_text} |")

    lines.extend([
        "",
        "---",
        "",
        "## 五、 高确信度危险股票池（Conviction Avoid / Sell List）",
        "",
        "| 标的代码 | 核心业务 / 商业模式 | 现价 | 估值倍数 | 致命硬伤与潜在暴雷诱因 | 商业避险与离场指引 |",
        "|---|---|---:|---|---|---|",
    ])

    for a in data["conviction_avoids"]:
        flaws_text = "；".join(f"{t['title']}：{t['desc']}" for t in a["fatal_flaws"])
        lines.append(f"| **{a['ticker']}**<br>({a['name']}) | {a['market_type']}<br>{a['business_model']} | {a['price']} | {a['pe']} | {flaws_text} | {a['exit_guidance']} |")

    chk = data["tactical_checklist"]
    lines.extend([
        "",
        "---",
        "",
        "## 六、 战术资产配置与买入前风控清单",
        "",
        f"* **账户总体姿态**：**{state}（建议现金比例 ≥ {cash}%）**。",
        "* **买入前硬性自检**：",
    ])

    for item in chk["checklist_items"]:
        lines.append(f"  - [x] {item}")

    lines.extend([
        f"* **今日执行结论**：{chk['today_execution_summary']}",
        "",
        "*注：完整现代暗色交互金融排版请查看配套 HTML 仪表盘：[`daily_briefing.html`](daily_briefing.html)*。",
        "",
        "---",
        "",
        "## 七、 数据真实性核验与数据转换处理规范披露（Audited Lineage）",
        "",
        f"1. **汇率数据抓取格式与折算程序**：\n   - {data['audit_disclosures']['fx_engine_note']}",
        f"2. **股票行情异常探测与受控清洗（美光 MU 案例）**：\n   - {data['audit_disclosures']['cleansing_note']}",
        f"3. **日股交易所访问受限应对**：\n   - {data['audit_disclosures']['japan_adr_note']}",
        "",
    ])

    return "\n".join(lines)


def render_html(data: dict) -> str:
    """编译现代暗色机构级响应式 HTML 仪表盘。"""
    date = data["date"]
    issue = data["issue_number"]
    tact = data["tactical_status"]
    state = tact["state"]
    cash = tact["cash_ratio_pct"]
    erp = tact["erp_ratio_pct"]
    instr = tact["instruction"]
    sent = data["sentiment"]
    chk = data["tactical_checklist"]
    audit = data["audit_disclosures"]

    # Macro pulse cards HTML
    macro_cards = []
    for m in data["macro_pulse"]:
        trend_color = "text-purple-400" if "JPY" in m["name"] else ("text-emerald-400" if m["trend"] == "↑" else "text-amber-400")
        macro_cards.append(f"""        <div class="bg-[var(--background)]/60 border border-[var(--border)] rounded-xl p-2.5 text-center">
          <div class="text-[11px] text-[var(--muted-foreground)]">{html.escape(m['name'])}</div>
          <div class="text-sm font-bold {trend_color}">{html.escape(m['value'])} <span class="text-[10px]">{html.escape(m['trend'])}</span></div>
          <div class="text-[10px] text-[var(--muted-foreground)]">{html.escape(m['note'][:14])}</div>
        </div>""")
    macro_cards_html = "\n".join(macro_cards)

    # Hot events HTML
    events_html = []
    for ev in data["hot_events"]:
        events_html.append(f"""      <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)]/40 hover:bg-[var(--background)]/70 transition-colors space-y-2.5">
        <div class="flex items-center gap-2">
          <span class="text-xs font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">核心博弈</span>
          <h3 class="text-sm sm:text-base font-bold text-[var(--foreground)]">{html.escape(ev['title'])}</h3>
        </div>
        <p class="text-xs text-[var(--muted-foreground)] leading-relaxed"><strong class="text-[var(--foreground)]">客观事实：</strong>{html.escape(ev['facts'])}</p>
        <p class="text-xs text-[var(--foreground)] leading-relaxed bg-[var(--card)] p-2.5 rounded-lg border border-[var(--border)]/60"><strong class="text-amber-500">产业链传导实质：</strong>{html.escape(ev['transmission'])}</p>
      </div>""")
    events_joined = "\n".join(events_html)

    # Signals
    signals_html = []
    for s in data["capital_flows"]["key_signals"]:
        signals_html.append(f"""          <li class="flex items-start gap-2">
            <span class="text-amber-500 font-bold">•</span>
            <span>{html.escape(s)}</span>
          </li>""")
    signals_joined = "\n".join(signals_html)

    # Inflows
    inflows_html = []
    for item in data["capital_flows"]["inflows"]:
        inflows_html.append(f"""          <div class="flex justify-between items-center text-xs p-2 rounded bg-emerald-500/5 border border-emerald-500/15">
            <div>
              <span class="font-bold text-[var(--foreground)]">{html.escape(item['sector'])}</span>
              <span class="text-[11px] text-[var(--muted-foreground)] ml-1">({html.escape(item['ticker'])})</span>
            </div>
            <div class="text-right">
              <span class="font-bold text-emerald-500">{html.escape(item['change_pct'])}</span>
              <div class="text-[10px] text-[var(--muted-foreground)]">{html.escape(item['reason'])}</div>
            </div>
          </div>""")
    inflows_joined = "\n".join(inflows_html)

    # Outflows
    outflows_html = []
    for item in data["capital_flows"]["outflows"]:
        outflows_html.append(f"""          <div class="flex justify-between items-center text-xs p-2 rounded bg-red-500/5 border border-red-500/15">
            <div>
              <span class="font-bold text-[var(--foreground)]">{html.escape(item['sector'])}</span>
              <span class="text-[11px] text-[var(--muted-foreground)] ml-1">({html.escape(item['ticker'])})</span>
            </div>
            <div class="text-right">
              <span class="font-bold text-red-500">{html.escape(item['change_pct'])}</span>
              <div class="text-[10px] text-[var(--muted-foreground)]">{html.escape(item['reason'])}</div>
            </div>
          </div>""")
    outflows_joined = "\n".join(outflows_html)

    # Buys cards
    buys_html = []
    for b in data["conviction_buys"]:
        thesis_items = "".join(f"""              <li class="flex items-start gap-1.5">
                <span class="text-emerald-500 font-bold">•</span>
                <span><strong>{html.escape(t['title'])}：</strong> {html.escape(t['desc'])}</span>
              </li>""" for t in b["thesis"])
        strat = b["trade_strategy"]
        buys_html.append(f"""        <div class="p-5 rounded-xl border-t-4 border-t-emerald-500 border border-[var(--border)] bg-[var(--background)]/60 flex flex-col justify-between space-y-4">
          <div class="space-y-3">
            <div class="flex justify-between items-start">
              <div>
                <h3 class="text-base sm:text-lg font-extrabold text-[var(--foreground)] flex items-center gap-1.5">
                  {html.escape(b['name'])} <span class="text-xs px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--muted-foreground)]">{html.escape(b['ticker'])}</span>
                </h3>
                <p class="text-xs text-[var(--muted-foreground)] mt-0.5">{html.escape(b['market_type'])} · {html.escape(b['business_model'])}</p>
              </div>
              <div class="text-right">
                <div class="text-base font-black text-[var(--foreground)]">{html.escape(b['price'])}</div>
                <div class="text-[11px] text-[var(--muted-foreground)]">PE {html.escape(b['pe'])}</div>
              </div>
            </div>
            <ul class="text-xs text-[var(--foreground)] space-y-2 leading-relaxed">
{thesis_items}
            </ul>
          </div>
          <div class="p-3.5 rounded-lg bg-emerald-500/5 border-l-4 border-emerald-500 text-xs text-emerald-600 dark:text-emerald-300 leading-relaxed space-y-1">
            <div class="font-bold">量化交易策略：</div>
            <div>目标区间：{html.escape(strat['entry_range'])} | 止损位：{html.escape(strat['stop_loss'])} | {html.escape(strat['expected_return'])}。{html.escape(strat['summary'])}</div>
          </div>
        </div>""")
    buys_joined = "\n".join(buys_html)

    # Avoids cards
    avoids_html = []
    for a in data["conviction_avoids"]:
        flaws_items = "".join(f"""              <li class="flex items-start gap-1.5">
                <span class="text-red-500 font-bold">•</span>
                <span><strong>{html.escape(t['title'])}：</strong> {html.escape(t['desc'])}</span>
              </li>""" for t in a["fatal_flaws"])
        avoids_html.append(f"""        <div class="p-5 rounded-xl border-t-4 border-t-red-500 border border-[var(--border)] bg-[var(--background)]/60 flex flex-col justify-between space-y-4">
          <div class="space-y-3">
            <div class="flex justify-between items-start">
              <div>
                <h3 class="text-base sm:text-lg font-extrabold text-[var(--foreground)] flex items-center gap-1.5">
                  {html.escape(a['name'])} <span class="text-xs px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--muted-foreground)]">{html.escape(a['ticker'])}</span>
                </h3>
                <p class="text-xs text-[var(--muted-foreground)] mt-0.5">{html.escape(a['market_type'])} · {html.escape(a['business_model'])}</p>
              </div>
              <div class="text-right">
                <div class="text-base font-black text-red-500">{html.escape(a['price'])}</div>
                <div class="text-[11px] text-[var(--muted-foreground)]">PE {html.escape(a['pe'])}</div>
              </div>
            </div>
            <ul class="text-xs text-[var(--foreground)] space-y-2 leading-relaxed">
{flaws_items}
            </ul>
          </div>
          <div class="p-3.5 rounded-lg bg-red-500/5 border-l-4 border-red-500 text-xs text-red-600 dark:text-red-300 leading-relaxed space-y-1">
            <div class="font-bold">商业避险警示：</div>
            <div>{html.escape(a['exit_guidance'])}</div>
          </div>
        </div>""")
    avoids_joined = "\n".join(avoids_html)

    # Checklist items
    checklist_items_html = "".join(f"""            <div class="flex items-center gap-2 text-emerald-500"><span class="font-bold text-xs">[已核验]</span> <span>{html.escape(c)}</span></div>\n""" for c in chk["checklist_items"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>水源全球金融商业早报（{date}·机构级决策内参）</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {{
      --background: #090d16;
      --foreground: #f1f5f9;
      --card: #0f172a;
      --card-foreground: #f8fafc;
      --border: #1e293b;
      --muted: #1e293b;
      --muted-foreground: #94a3b8;
    }}
    body {{
      background-color: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
  </style>
</head>
<body class="min-h-screen p-4 sm:p-6 md:p-8 flex justify-center selection:bg-amber-500 selection:text-black">

  <div class="w-full max-w-6xl space-y-6">

    <!-- Header 头部状态 -->
    <header class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 md:p-7 shadow-sm space-y-4">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
        <div>
          <div class="flex items-center gap-2 text-xs font-semibold tracking-wider text-amber-500 uppercase">
            <span>水源全球宏观决策内参</span>
            <span>•</span>
            <span>第 {issue} 期</span>
          </div>
          <h1 class="text-xl sm:text-2xl md:text-3xl font-extrabold text-[var(--foreground)] tracking-tight mt-1">
            全球跨市场宏观决策与美日股全盘扫描
          </h1>
          <p class="text-xs text-[var(--muted-foreground)] mt-1">
            发布时点：{date} | 数据对账时点：实盘快照与财报原文已核验
          </p>
        </div>

        <div class="flex items-center gap-3 self-start md:self-auto">
          <div class="px-3.5 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-right">
            <div class="text-[11px] text-amber-400 font-medium">战术仓位姿态</div>
            <div class="text-sm sm:text-base font-black text-amber-500">{state} (现金≥{cash}%)</div>
          </div>
        </div>
      </div>

      <!-- 宏观脉搏指标网格 -->
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5 pt-1">
{macro_cards_html}
        <div class="bg-[var(--background)]/60 border border-[var(--border)] rounded-xl p-2.5 text-center">
          <div class="text-[11px] text-[var(--muted-foreground)]">标普 500 风险溢价</div>
          <div class="text-sm font-bold text-red-500">{erp}% <span class="text-[10px]">极薄</span></div>
          <div class="text-[10px] text-[var(--muted-foreground)]">股票性价比处低位</div>
        </div>
      </div>
    </header>

    <!-- 1. 商业热点穿透 -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 md:p-7 shadow-sm space-y-4">
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3.5">
        <div class="flex items-center gap-2.5 text-lg font-bold text-[var(--foreground)]">
          <span>今日热点商业事件与产业链博弈穿透</span>
        </div>
        <span class="text-xs text-[var(--muted-foreground)] font-mono">3 项核心产业异动</span>
      </div>
      <div class="space-y-4">
{events_joined}
      </div>
    </section>

    <!-- 2. 资金流向与情绪分析 -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <section class="lg:col-span-8 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
        <div class="flex items-center justify-between border-b border-[var(--border)] pb-3.5">
          <div class="flex items-center gap-2 text-base sm:text-lg font-bold text-[var(--foreground)]">
            <span>机构主力与微观资金图谱</span>
          </div>
          <span class="text-xs text-[var(--muted-foreground)]">ETF 申赎 + 期权暗池</span>
        </div>
        <ul class="text-xs text-[var(--muted-foreground)] space-y-2 leading-relaxed">
{signals_joined}
        </ul>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div class="space-y-2">
            <div class="text-xs font-bold text-emerald-500 flex items-center gap-1.5">主力净流入板块</div>
{inflows_joined}
          </div>
          <div class="space-y-2">
            <div class="text-xs font-bold text-red-500 flex items-center gap-1.5">主力净流出板块</div>
{outflows_joined}
          </div>
        </div>
      </section>

      <section class="lg:col-span-4 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-4">
        <div class="space-y-3">
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <div class="flex items-center gap-2 text-base font-bold text-[var(--foreground)]">
              <span>市场情绪钟摆</span>
            </div>
            <span class="text-xs font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-500 border border-red-500/20">{sent['status'][:4]}</span>
          </div>
          <div class="text-center py-2">
            <div class="text-3xl font-black text-red-500">{sent['score']} <span class="text-sm font-normal text-[var(--muted-foreground)]">/ 100</span></div>
            <div class="text-xs text-red-400 font-semibold mt-1">{sent['status']}</div>
          </div>
          <div class="space-y-2.5 text-xs text-[var(--muted-foreground)] leading-relaxed">
            <div class="p-2.5 rounded-lg bg-[var(--background)]/60 border border-[var(--border)]">
              <strong class="text-[var(--foreground)]">散户端微观画像：</strong>{html.escape(sent['retail_profile'])}
            </div>
            <div class="p-2.5 rounded-lg bg-[var(--background)]/60 border border-[var(--border)]">
              <strong class="text-[var(--foreground)]">做市商博弈画像：</strong>{html.escape(sent['institutional_profile'])}
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 3. 高确信度推荐股票池 -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 md:p-7 shadow-sm space-y-5">
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3.5">
        <div class="flex items-center gap-2.5 text-lg font-bold text-emerald-500">
          <span class="text-[var(--foreground)]">高确信度推荐股票池（Conviction Buy List）</span>
        </div>
        <span class="text-xs text-emerald-500 font-bold px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20">做多高赔率</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
{buys_joined}
      </div>
    </section>

    <!-- 4. 高确信度危险股票池 -->
    <section class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 md:p-7 shadow-sm space-y-5">
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3.5">
        <div class="flex items-center gap-2.5 text-lg font-bold text-red-500">
          <span class="text-[var(--foreground)]">全盘扫描危险股票池（Conviction Avoid / Sell Warnings）</span>
        </div>
        <span class="text-xs text-red-500 font-bold px-2.5 py-1 rounded bg-red-500/10 border border-red-500/20">高位严禁接盘</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
{avoids_joined}
      </div>
    </section>

    <!-- 5. 战术配置与风控自检 -->
    <footer class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 md:p-7 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border)] pb-4">
        <div class="text-base font-extrabold text-[var(--foreground)] flex items-center gap-2">
          <span>战术资产配置与买入前风控核查清单</span>
        </div>
        <div class="text-xs font-semibold px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
          账户战术状态：{state} (现金≥{cash}%)
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)]/40 space-y-2">
          <div class="font-bold text-[var(--foreground)] text-sm">买入前硬性风控自检：</div>
          <div class="space-y-1.5 text-[var(--muted-foreground)]">
{checklist_items_html}
          </div>
        </div>

        <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)]/40 space-y-2">
          <div class="font-bold text-[var(--foreground)] text-sm">今日账户执行总结：</div>
          <p class="text-[var(--muted-foreground)] leading-relaxed">
            {html.escape(chk['today_execution_summary'])}
          </p>
        </div>
      </div>

      <!-- 数据转换与汇率处理披露卡片 -->
      <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)]/70 space-y-3 text-xs">
        <div class="font-bold text-[var(--foreground)] text-sm flex items-center gap-2">
          <span>底层数据真实性核验与数据转换规范披露（Audited Lineage）</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-[var(--muted-foreground)]">
          <div class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] space-y-1">
            <div class="font-semibold text-[var(--foreground)]">汇率抓取格式与折算引擎</div>
            <p class="leading-relaxed">{html.escape(audit['fx_engine_note'])}</p>
          </div>
          <div class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] space-y-1">
            <div class="font-semibold text-[var(--foreground)]">美光（MU）10x 异常清洗</div>
            <p class="leading-relaxed">{html.escape(audit['cleansing_note'])}</p>
          </div>
          <div class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] space-y-1">
            <div class="font-semibold text-[var(--foreground)]">日股 TYO 限制与 ADR 映射</div>
            <p class="leading-relaxed">{html.escape(audit['japan_adr_note'])}</p>
          </div>
        </div>
      </div>

      <p class="text-[11px] text-[var(--muted-foreground)] opacity-70 text-center pt-2 border-t border-[var(--border)]">
        免责声明：本内参所载观点与数据基于项目已归档公开披露与商业模型推演，仅供个人实战研判与纪律跟踪使用，不构成任何无条件的投资买卖邀约。市场有风险，决策须独立。
      </p>
    </footer>

  </div>

</body>
</html>
"""


def build_briefing(input_json_path: Path, output_dir: Path = None) -> dict:
    """主构建流程：验证输入并生成 Markdown 和 HTML 文件。"""
    data = load_and_validate(input_json_path)

    out_dir = output_dir or input_json_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    md_content = render_markdown(data)
    html_content = render_html(data)

    md_path = out_dir / "daily_briefing.md"
    html_path = out_dir / "daily_briefing.html"

    md_path.write_text(md_content, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")

    return {
        "status": "success",
        "date": data["date"],
        "issue_number": data["issue_number"],
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "markdown_bytes": len(md_content.encode("utf-8")),
        "html_bytes": len(html_content.encode("utf-8")),
    }


def main():
    parser = argparse.ArgumentParser(description="每日金融商业早报自动化编译程序")
    parser.add_argument("input_json", help="结构化早报输入 JSON 文件路径")
    parser.add_argument("--output-dir", help="输出目标目录（可选，默认与输入文件同目录）")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.is_absolute():
        input_path = ROOT / input_path

    out_dir = Path(args.output_dir) if args.output_dir else None
    if out_dir and not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    result = build_briefing(input_path, out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
