"""每日美日股大盘总行情与深度推荐研报生产引擎 (Daily Briefing Production Engine).

严格遵循 schemas/daily_briefing.schema.json 与 2026-10-14 行情新鲜度时效硬约束.
核心能力：
1. 宏观流动性、情绪恐慌度 (VIX/Nikkei VI)、资金流向与期权 PCR 解析；
2. 重点推荐股票独立富文本卡片化推演（悲观底线/中性公允/乐观靶心与触发事件）；
3. 严格 Schema 校验；
4. 买方 A4 矢量 HTML 渲染；
5. Microsoft Edge Headless 纯净 PDF 编译；
6. Google Drive 云端自动建档与流式同步。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jsonschema

from financial_reporting.quote_freshness_gateway import QuoteFreshnessGateway
from financial_reporting.ai_research_agent import AIResearchAgent
from financial_reporting.sepa_card_renderer import SepaCardRenderer

# 工具路径动态探测 (杜绝硬编码特定用户个人绝对路径)
def _discover_gdrive_exe() -> Optional[str]:
    """动态探测 gdrive CLI 可执行文件路径 (优先环境变量，次选用户 Antigravity 插件与 PATH)."""
    env_path = os.getenv("GDRIVE_EXECUTABLE") or os.getenv("GDRIVE_EXE")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path).resolve())
    home = Path.home()
    plugin_bin_dir = home / ".gemini" / "antigravity" / "plugin_data" / "gdrive" / "bin"
    if plugin_bin_dir.is_dir():
        candidates = list(plugin_bin_dir.glob("gdrive*.exe"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return str(candidates[0].resolve())
    which_path = shutil.which("gdrive")
    if which_path:
        return str(Path(which_path).resolve())
    return None


def _discover_edge_exe() -> Optional[str]:
    """动态探测 Microsoft Edge 或兼容 Chromium 浏览器路径以渲染 PDF."""
    env_path = os.getenv("EDGE_EXECUTABLE") or os.getenv("EDGE_EXE")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path).resolve())
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c.resolve())
    for name in ("msedge", "chrome", "chromium"):
        which_path = shutil.which(name)
        if which_path:
            return str(Path(which_path).resolve())
    return None


DAILY_PARENT_FOLDER_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET" # 每日行情分析 根目录


class DailyBriefingEngine:
    """买方机构级大盘研报自动化引擎。"""

    def __init__(
        self,
        gdrive_exe: Optional[str] = None,
        edge_exe: Optional[str] = None,
        daily_parent_folder_id: Optional[str] = None,
    ):
        self.gdrive_exe = gdrive_exe or _discover_gdrive_exe()
        self.edge_exe = edge_exe or _discover_edge_exe()
        self.daily_parent_folder_id = daily_parent_folder_id or DAILY_PARENT_FOLDER_ID

        schema_file = ROOT / "schemas" / "daily_briefing.schema.json"
        if not schema_file.exists():
            raise FileNotFoundError(f"缺失日报 Schema 契约文件: {schema_file}")
        self.schema = json.loads(schema_file.read_text(encoding="utf-8"))

    def validate_briefing_data(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """严格核验数据符合 schemas/daily_briefing.schema.json。"""
        if not self.schema:
            raise FileNotFoundError("缺失日报 Schema 时阻断")
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            return True, "Schema 强校验 100% 契合通过"
        except jsonschema.ValidationError as e:
            return False, f"Schema 校验失败: {e.message}"

    def render_briefing_html(self, data: Dict[str, Any]) -> str:
        """渲染买方机构级 A4 矢量 HTML 研报。"""
        h = data["header"]
        m = data["macro_and_liquidity"]
        s = data["market_sentiment_and_options"]
        news = data["market_moving_news"]
        stocks = data["recommended_stocks"]
        is_us = (h["market"] == "US")
        accent_color = "#2b6cb0" if is_us else "#c53030"
        tag_bg = "#ebf8ff" if is_us else "#fff5f5"
        tag_border = "#bee3f8" if is_us else "#feb2b2"

        news_html = "".join([f"""
        <div style="background: #f7fafc; border-left: 3px solid {accent_color}; padding: 6px 10px; margin-bottom: 6px; border-radius: 2px;">
          <div style="font-weight: 700; color: #2d3748; font-size: 11.5px;">【重大要闻】{item['headline']}</div>
          <div style="font-size: 11px; color: #4a5568; margin-top: 2px;"><strong>【盘面影响】</strong>{item['impact_analysis']}</div>
        </div>
        """ for item in news])

        cards_html = ""
        for st in stocks:
            pess = st["pessimistic_deduction"]
            base = st["neutral_deduction"]
            opt = st["optimistic_deduction"]

            sepa_block = ""
            sepa_data = st.get("sepa_result") or st.get("sepa_signal")
            if sepa_data:
                sepa_block = SepaCardRenderer.render_sepa_card_html(sepa_data, market=h["market"])

            cards_html += f"""
            <div style="background: #ffffff; border: 1.5px solid #cbd5e0; border-left: 5px solid #2f855a; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div>
                  <span style="font-size: 15px; font-weight: 700; color: #1a202c;">{st['company_name']}</span>
                  <span style="font-size: 12px; color: #718096; margin-left: 6px; font-weight: 600;">{h['market']}:{st['ticker']}</span>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                  <span style="background: #2f855a; color: #ffffff; padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 12px;">{st['rating']}</span>
                  <span style="font-size: 13px; font-weight: 700; color: {accent_color};">最新市价: {st['current_price']}</span>
                </div>
              </div>

              <div style="background: #f7fafc; border: 1px solid #edf2f7; border-radius: 4px; padding: 7px 10px; margin-bottom: 8px; font-size: 11.5px; color: #4a5568; line-height: 1.45;">
                <strong style="color: {accent_color};">【核心业务与护城河简述】</strong>{st['business_intro']}
              </div>

              <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; margin-bottom: 8px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                  <thead>
                    <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                      <th style="padding: 7px 10px; font-size: 11px; font-weight: 700; color: #276749; width: 22%; border-right: 1px solid #e2e8f0;">严苛安全买入线</th>
                      <th style="padding: 7px 10px; font-size: 11px; font-weight: 700; color: #9b2c2c; width: 26%; border-right: 1px solid #e2e8f0;">悲观紧缩防御底</th>
                      <th style="padding: 7px 10px; font-size: 11px; font-weight: 700; color: #2b6cb0; width: 26%; border-right: 1px solid #e2e8f0;">中性公允内在价值</th>
                      <th style="padding: 7px 10px; font-size: 11px; font-weight: 700; color: #234e52; width: 26%;">乐观降息弹性靶心</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style="border-bottom: 1px dashed #e2e8f0; background: #ffffff;">
                      <td style="padding: 6px 10px; font-size: 15px; font-weight: 800; color: #2f855a; border-right: 1px solid #e2e8f0;">{st['margin_of_safety_trigger']}</td>
                      <td style="padding: 6px 10px; font-size: 14px; font-weight: 800; color: #c53030; border-right: 1px solid #e2e8f0;">{pess['implied_price']} <span style="font-size: 10px; font-weight: 600; color: #e53e3e;">({pess['downside_gap']})</span></td>
                      <td style="padding: 6px 10px; font-size: 14px; font-weight: 800; color: #2b6cb0; border-right: 1px solid #e2e8f0;">{base['implied_price']} <span style="font-size: 10px; font-weight: 600; color: #3182ce;">({base['upside_gap']})</span></td>
                      <td style="padding: 6px 10px; font-size: 14px; font-weight: 800; color: #2f855a;">{opt['implied_price']} <span style="font-size: 10px; font-weight: 600; color: #38a169;">({opt['potential_gain']})</span></td>
                    </tr>
                    <tr style="background: #fafafa; vertical-align: top;">
                      <td style="padding: 7px 10px; font-size: 10px; color: #4a5568; line-height: 1.45; border-right: 1px solid #e2e8f0;">
                        <strong style="color: #276749;">【触发机制】</strong><br>现价跌破防御底，进入历史高胜率击球区间。
                      </td>
                      <td style="padding: 7px 10px; font-size: 10px; color: #742a2a; line-height: 1.45; border-right: 1px solid #e2e8f0; background: #fffaf0;">
                        <strong style="color: #c53030;">【如果发生以下情况跌至此价】</strong><br>{pess['trigger_event']}
                      </td>
                      <td style="padding: 7px 10px; font-size: 10px; color: #2c5282; line-height: 1.45; border-right: 1px solid #e2e8f0;">
                        <strong style="color: #2b6cb0;">【常态基准预期对应状态】</strong><br>{base['trigger_event']}
                      </td>
                      <td style="padding: 7px 10px; font-size: 10px; color: #22543d; line-height: 1.45; background: #f0fff4;">
                        <strong style="color: #2f855a;">【如果发生以下利好推升至此价】</strong><br>{opt['trigger_event']}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {sepa_block}

              <div style="font-size: 11.5px; color: #2d3748; background: #edf2f7; border-radius: 4px; padding: 6px 10px;">
                <strong>【机构战术建议与买点指引】</strong>{st['tactical_action']}
              </div>
            </div>
            """

        raw_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{h['report_date']} {h['market_name_zh']} 每日大盘行情研报与深度推荐</title>
<style>
  @page {{
    size: A4;
    margin: 12mm 14mm 12mm 14mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    color: #1a202c;
    background: #ffffff;
    line-height: 1.45;
    font-size: 11.5px;
    margin: 0;
    padding: 0;
  }}
  .header {{
    border-bottom: 2.5px solid {accent_color};
    padding-bottom: 8px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .title-main {{
    font-size: 20px;
    font-weight: 800;
    color: #1a202c;
    letter-spacing: -0.3px;
  }}
  .title-sub {{
    font-size: 12px;
    color: {accent_color};
    font-weight: 600;
    margin-top: 3px;
  }}
  .badge {{
    background: {tag_bg};
    border: 1px solid {tag_border};
    color: {accent_color};
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }}
  .section {{
    margin-bottom: 12px;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: 700;
    color: #2d3748;
    border-bottom: 1.5px solid #e2e8f0;
    padding-bottom: 4px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .grid-macro {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 6px;
    margin-bottom: 8px;
  }}
  .macro-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 6px 8px;
    text-align: center;
  }}
  .macro-label {{
    font-size: 10px;
    color: #718096;
    margin-bottom: 2px;
  }}
  .macro-val {{
    font-size: 12.5px;
    font-weight: 700;
    color: #1a202c;
  }}
  .ai-summary-box {{
    background: #ebf8ff;
    border-left: 4px solid #3182ce;
    border-radius: 0 4px 4px 0;
    padding: 10px 12px;
    margin-bottom: 12px;
    font-size: 11.5px;
    color: #2b6cb0;
    line-height: 1.55;
  }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title-main">{h['market_name_zh']} 每日总行情与深度投资决策研报</div>
      <div class="title-sub">水源高级投研系统 · 买方机构决策级分析 · 官方底账穿透</div>
    </div>
    <div style="text-align: right;">
      <span class="badge">报告日期: {h['report_date']}</span>
      <div style="font-size: 10px; color: #a0aec0; margin-top: 4px;">契约规范: daily_briefing.schema.json</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">一、宏观流动性与基准利率全景 (Macro Liquidity & Rates)</div>
    <div class="grid-macro">
      <div class="macro-card">
        <div class="macro-label">10Y 基准收益率</div>
        <div class="macro-val">{m['us_10y_yield']}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">2Y 政策敏感端</div>
        <div class="macro-val">{m['us_2y_yield']}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">利差 (10Y-2Y)</div>
        <div class="macro-val">{m['yield_spread_10_2']}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">美元指数 DXY</div>
        <div class="macro-val">{m['dxy_index']}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">美元兑日元 USD/JPY</div>
        <div class="macro-val">{m['usd_jpy_rate']}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">基准政策利率</div>
        <div class="macro-val">{m['effr_policy_rate']}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">二、市场恐慌度、主力资金净流向与期权多空博弈 (Sentiment & Options Flow)</div>
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 8px 10px; margin-bottom: 6px;">
      <div style="display: flex; gap: 14px; margin-bottom: 6px;">
        <div><strong>恐慌指数:</strong> <span style="color: #2b6cb0; font-weight: 700;">{s['vix_index']}</span></div>
        <div><strong>情绪温度计:</strong> <span style="color: #d69e2e; font-weight: 700;">{s['fear_greed_gauge']}</span></div>
        <div><strong>期权 Put/Call Ratio:</strong> <span style="color: #2f855a; font-weight: 700;">{s['put_call_ratio']}</span></div>
      </div>
      <div style="font-size: 11px; color: #4a5568; margin-bottom: 4px;"><strong>主力资金流向:</strong> {s['capital_flow_summary']}</div>
      <div style="font-size: 11px; color: #4a5568;"><strong>期权博弈态势:</strong> {s['options_market_dynamics']}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">三、当日核心突发新闻与宏观事件透视 (Market-Moving News & Events)</div>
    {news_html}
  </div>

  <div class="section">
    <div class="section-title">四、AI 顶层决策研判 (AI Strategic Investment Synthesis)</div>
    <div class="ai-summary-box">
      <strong>【买方宏观与多因子顶层决策】</strong><br>
      {data['ai_executive_summary'].replace(chr(10), '<br>')}
    </div>
  </div>

  <div class="section">
    <div class="section-title">五、今日重点推荐与三态估值推演卡片 (High-Conviction Stock Deep Cards)</div>
    <div style="font-size: 11px; color: #718096; margin-bottom: 8px;">
      严格遵循买方投研标准：严禁罗列无信息量的机械大表；每只标的穿透官方底账、悲观下行触发事件、中性公允及乐观弹性靶心。
    </div>
    {cards_html}
  </div>

  <div style="margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 8px; text-align: center; color: #a0aec0; font-size: 10px;">
    水源系统自动化研报流水线 · 严格遵守数据治理契约 · 本地化离线证据引擎 · 仅供专业机构研判参考
  </div>
</body>
</html>
"""
        return AIResearchAgent.clean_text_no_emoji(raw_html)

    def render_committee_memo_markdown(self, briefing_data: Dict[str, Any]) -> str:
        """渲染买方投委会专用决策晨报纪要 (Markdown 格式)."""
        h = briefing_data.get("header", {})
        m = briefing_data.get("macro_and_liquidity", {})
        s = briefing_data.get("market_sentiment_and_options", {})
        news = briefing_data.get("market_moving_news", [])
        stocks = briefing_data.get("recommended_stocks", [])

        lines = [
            f"# {h.get('report_date', '')} 投资委员会决策晨会备忘录 ({h.get('market_name_zh', '')})",
            "",
            "> 水源高级投研系统 · 买方机构决策级分析 · 官方底账穿透",
            "",
            "## 一、宏观流动性与基准利率全景",
            f"- 10Y 基准收益率: {m.get('us_10y_yield', 'N/A')}",
            f"- 2Y 政策敏感端: {m.get('us_2y_yield', 'N/A')}",
            f"- 期限利差 (10Y-2Y): {m.get('yield_spread_10_2', 'N/A')}",
            f"- 美元指数 DXY: {m.get('dxy_index', 'N/A')} | USD/JPY: {m.get('usd_jpy_rate', 'N/A')}",
            f"- 基准政策利率 EFFR: {m.get('effr_policy_rate', 'N/A')}",
            "",
            "## 二、市场情绪温度计与期权资金流向",
            f"- 波动率恐慌指数 (VIX): {s.get('vix_index', 'N/A')}",
            f"- 情绪温度计: {s.get('fear_greed_gauge', 'N/A')}",
            f"- 期权沽购比 (Put/Call Ratio): {s.get('put_call_ratio', 'N/A')}",
            f"- 主力资金动向: {s.get('capital_flow_summary', 'N/A')}",
            f"- 期权博弈态势: {s.get('options_market_dynamics', 'N/A')}",
            "",
            "## 三、今日核心要闻与盘面冲击",
        ]
        for n in news:
            lines.append(f"### [要闻] {n.get('headline', '')}")
            lines.append(f"**【盘面影响】**: {n.get('impact_analysis', '')}")
            lines.append("")

        lines.append("## 四、AI 顶层决策研判")
        lines.append(briefing_data.get("ai_executive_summary", "待 AI 策略汇总"))
        lines.append("")

        lines.append("## 五、重点推荐标的与三态估值推演卡片")
        for st in stocks:
            lines.append(f"### {st.get('company_name', '')} ({st.get('ticker', '')}) — 评级: {st.get('rating', '')}")
            lines.append(f"- 最新市价: {st.get('current_price', '')}")
            lines.append(f"- 严格安全买入线: {st.get('margin_of_safety_trigger', '')}")
            lines.append(f"- 业务简述: {st.get('business_intro', '')}")
            pess = st.get('pessimistic_deduction', {})
            base = st.get('neutral_deduction', {})
            opt = st.get('optimistic_deduction', {})
            lines.append(f"- 悲观防御底: {pess.get('implied_price', '')} ({pess.get('downside_gap', '')}) — 触发机制: {pess.get('trigger_event', '')}")
            lines.append(f"- 中性内在价值: {base.get('implied_price', '')} ({base.get('upside_gap', '')}) — 基准预期: {base.get('trigger_event', '')}")
            lines.append(f"- 乐观弹性靶心: {opt.get('implied_price', '')} ({opt.get('potential_gain', '')}) — 催化机制: {opt.get('trigger_event', '')}")
            lines.append(f"- 机构战术建议: {st.get('tactical_action', '')}")
            lines.append("")

        return "\n".join(lines)

    def produce_briefing_bundle(
        self,
        briefing_data: Dict[str, Any],
        output_dir: Path,
        generate_excel: bool = True,
        us_screener_pool: Optional[List[Dict[str, Any]]] = None,
        jp_screener_pool: Optional[List[Dict[str, Any]]] = None,
        compile_pdf: bool = False,
    ) -> Dict[str, Any]:
        """一键生产投委会晨报完整交付资产束 (JSON + HTML + MD + Excel + 可选 PDF)."""
        is_valid, msg = self.validate_briefing_data(briefing_data)
        if not is_valid:
            raise ValueError(f"晨报数据契约校验失败: {msg}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        h = briefing_data.get("header", {})
        market = h.get("market", "US")
        report_date = h.get("report_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # 1. 结构化 JSON 底稿落盘
        json_file = output_dir / f"{market}_daily_briefing.json"
        json_file.write_text(json.dumps(briefing_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. 买方 A4 矢量 HTML 研报渲染与落盘
        html_code = self.render_briefing_html(briefing_data)
        html_file = output_dir / f"{market}_daily_briefing.html"
        html_file.write_text(html_code, encoding="utf-8")

        # 3. 投委会 Markdown 决策纪要渲染与落盘
        memo_md = self.render_committee_memo_markdown(briefing_data)
        memo_file = output_dir / f"{market}_committee_morning_memo.md"
        memo_file.write_text(memo_md, encoding="utf-8")

        # 4. 5-Sheet Excel 每日大盘工作簿
        excel_path = None
        if generate_excel:
            try:
                excel_filename = f"每日市场深度与价值洼地筛选_{report_date}_{market}.xlsx"
                excel_path = self.generate_excel_screener(
                    briefing_data=briefing_data,
                    us_screener_pool=us_screener_pool,
                    jp_screener_pool=jp_screener_pool,
                    output_filename=excel_filename,
                )
            except Exception as e:
                excel_path = None

        # 5. 受控 PDF 编译
        pdf_path = None
        if compile_pdf:
            candidate_pdf = output_dir / f"{report_date}_{market}_每日大盘总行情与深度推荐.pdf"
            if self.compile_pdf(html_file, candidate_pdf, force=True):
                pdf_path = candidate_pdf

        return {
            "status": "success",
            "market": market,
            "report_date": report_date,
            "json_path": str(json_file.resolve()),
            "html_path": str(html_file.resolve()),
            "markdown_path": str(memo_file.resolve()),
            "excel_path": str(excel_path.resolve()) if excel_path else None,
            "pdf_path": str(pdf_path.resolve()) if pdf_path else None,
        }

    def generate_excel_screener(
        self,
        briefing_data: Dict[str, Any],
        us_screener_pool: Optional[List[Dict[str, Any]]] = None,
        jp_screener_pool: Optional[List[Dict[str, Any]]] = None,
        output_filename: Optional[str] = None,
    ) -> Path:
        """调用买方级 ExcelDailyScreenerBuilder 生成 5-Sheet Excel 大盘与价值洼地挑选工作簿."""
        from financial_reporting.excel_daily_screener_builder import ExcelDailyScreenerBuilder
        builder = ExcelDailyScreenerBuilder()
        return builder.build_workbook(
            briefing_data=briefing_data,
            us_screener_pool=us_screener_pool,
            jp_screener_pool=jp_screener_pool,
            output_filename=output_filename,
        )

    def compile_pdf(
        self,
        html_path: Path,
        pdf_path: Path,
        is_annual_filing: bool = False,
        is_material_disclosure: bool = False,
        force: bool = False,
    ) -> bool:
        """调用 Microsoft Edge Headless 编译无杂质纯净矢量 PDF。

        硬约束门禁：
        用户明确要求“pdf只需要财年或者重大信息披露的时候生成”，常规高频日常研报不再机械批量打印 PDF。
        仅当 is_annual_filing=True 或 is_material_disclosure=True 或 force=True 时才放行执行渲染。
        """
        if not (is_annual_filing or is_material_disclosure or force):
            # 依规跳过非重大披露的高频常规 PDF 生成
            return False

        if not self.edge_exe or not Path(self.edge_exe).exists():
            return False
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.edge_exe,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path.resolve()}",
            str(html_path.resolve()),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if pdf_path.exists() and pdf_path.stat().st_size > 10000:
                return True
            return False
        except Exception:
            return False

    def upload_excel_to_drive(self, xlsx_path: Path, folder_id: str) -> Optional[str]:
        """上传专业 Excel 投研工作簿至指定的 Google Drive 文件夹."""
        if not self.gdrive_exe or not Path(self.gdrive_exe).exists():
            return None
        cmd = [
            self.gdrive_exe,
            "mutate",
            "upload",
            str(xlsx_path.resolve()),
            "--parent",
            folder_id,
            "--mime-type",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", res.stdout)
                if m:
                    return m.group(1)
                m = re.search(r'"id":\s*"([^"]+)"', res.stdout)
                if m:
                    return m.group(1)
            return None
        except Exception:
            return None

    def upload_to_drive(self, file_path: Path, folder_id: str) -> Optional[str]:
        """上传凭据文件至 Google Drive (严格禁止上传 HTML 研报)."""
        # 铁律防御：用户明确指令“html我不希望上传”
        if file_path.suffix.lower() in (".html", ".htm"):
            return None

        mime_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "application/octet-stream"
        if file_path.suffix.lower() == ".xlsx":
            return self.upload_excel_to_drive(file_path, folder_id)

        if not self.gdrive_exe or not Path(self.gdrive_exe).exists():
            return None
        cmd = [
            self.gdrive_exe,
            "mutate",
            "upload",
            str(file_path.resolve()),
            "--parent",
            folder_id,
            "--mime-type",
            mime_type,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", res.stdout)
                if m:
                    return m.group(1)
                m = re.search(r'"id":\s*"([^"]+)"', res.stdout)
                if m:
                    return m.group(1)
            return None
        except Exception:
            return None
