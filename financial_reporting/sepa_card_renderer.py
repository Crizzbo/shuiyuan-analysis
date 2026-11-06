"""米奈尔维尼 SEPA 买方时机与操盘卡片渲染器 (Minervini SEPA Card Renderer).

严格遵循 Google Python 编程风格指南与《SPEC-07 买方时机决策与技术足迹分析引擎设计书》:
1. 统一输出 HTML、Markdown 与 Excel 三种载体形式的专业买方操盘卡片;
2. 禁用抽象工程代号，使用通俗中文商业直觉与投资动作指令;
3. 显式呈现核心价格防线与时机参数:
   - 股票生命周期阶段 (TrendStageState)
   - VCP 波动收敛形态与经典技术足迹 (如 '8W 28/2.5 4T')
   - 枢轴买点价格基准 (美分级)
   - 刚性硬止损线 (Max 5%~7%)
   - 移动保本止损触发线 (3R 保本线)
   - 超买脱轨追高上限防线 (+5% 追高拦截)
   - 深蹲震仓保护状态 (Squat Watch)
4. 深度适配 Daily Briefing、投委会晨报 Memo 与 5-Sheet Excel 交互工作簿。
"""

# 1. Python 标准库
from typing import Any, Dict, List, Optional, Tuple, Union

# 2. 第三方依赖库
import openpyxl

# 3. 内部核心库 (纯净金融与样式依赖)
from financial_core.engines.sepa_buy_signal_engine import (
    BuySignalTier,
    SepaBuySignalResult,
    SepaPriceBoundaries,
    TrendStageState,
    VcpContractionStatus,
)
from financial_reporting.excel_styler import (
    COLOR_BUY_ZONE_GREEN,
    COLOR_BUY_ZONE_TEXT,
    COLOR_CALC_BLACK,
    COLOR_WARNING_ORANGE,
    COLOR_WARNING_TEXT,
    FMT_CURRENCY_JPY_INT,
    FMT_CURRENCY_USD_DEC,
    ExcelStyler,
)


def _normalize_sepa_result(
    result: Union[SepaBuySignalResult, Dict[str, Any]]
) -> SepaBuySignalResult:
    """自适应规范化入参：支持强类型 SepaBuySignalResult 对象与原始字典解析.

    Args:
        result: 强类型 SepaBuySignalResult 实例或同等字段字典.

    Returns:
        标准化 SepaBuySignalResult 实例.

    Raises:
        TypeError: 当传入不受支持的结果对象类型时.
    """
    if isinstance(result, SepaBuySignalResult):
        return result
    if isinstance(result, dict):
        p_dict = result.get("price_boundaries", {})
        if isinstance(p_dict, dict):
            boundaries = SepaPriceBoundaries(
                val_pivot_price=float(p_dict.get("val_pivot_price", 0.0)),
                val_stop_loss_price=float(p_dict.get("val_stop_loss_price", 0.0)),
                val_recommended_stop_price=float(
                    p_dict.get("val_recommended_stop_price", 0.0)
                ),
                val_risk_unit_usd=float(p_dict.get("val_risk_unit_usd", 0.0)),
                val_breakeven_trigger_price=float(
                    p_dict.get("val_breakeven_trigger_price", 0.0)
                ),
                val_extended_limit_price=float(
                    p_dict.get("val_extended_limit_price", 0.0)
                ),
                val_target_profit_price=float(
                    p_dict.get("val_target_profit_price", 0.0)
                ),
                pct_hard_stop_loss=float(p_dict.get("pct_hard_stop_loss", 7.0)),
                pct_recommended_stop_loss=float(
                    p_dict.get("pct_recommended_stop_loss", 5.0)
                ),
                pct_current_to_pivot=float(p_dict.get("pct_current_to_pivot", 0.0)),
                is_within_buy_range=bool(p_dict.get("is_within_buy_range", False)),
            )
        else:
            boundaries = p_dict

        return SepaBuySignalResult(
            ticker=result.get("ticker", "UNKNOWN"),
            val_current_price=float(result.get("val_current_price", 0.0)),
            status_trend_stage=result.get(
                "status_trend_stage", TrendStageState.STAGE_2_MARKUP.value
            ),
            status_vcp_contraction=result.get(
                "status_vcp_contraction", VcpContractionStatus.TIGHT_PIVOT_READY.value
            ),
            status_buy_signal=result.get(
                "status_buy_signal", BuySignalTier.PIVOT_TRIGGERED.value
            ),
            is_trend_template_passed=bool(result.get("is_trend_template_passed", True)),
            trend_criteria_checks=result.get("trend_criteria_checks", {}),
            technical_footprint_code=result.get("technical_footprint_code", "0W 0/0 0T"),
            cnt_contractions=int(result.get("cnt_contractions", 0)),
            is_volume_dryup_confirmed=bool(result.get("is_volume_dryup_confirmed", True)),
            is_breakout_volume_confirmed=bool(
                result.get("is_breakout_volume_confirmed", True)
            ),
            is_squat_holding=bool(result.get("is_squat_holding", False)),
            price_boundaries=boundaries,
            directive_action_zh=result.get("directive_action_zh", ""),
            meta_trend_stage=result.get("meta_trend_stage", {}),
            meta_vcp_status=result.get("meta_vcp_status", {}),
            meta_buy_signal=result.get("meta_buy_signal", {}),
        )
    raise TypeError(f"不支持的 SEPA 结果类型: {type(result)}")


class SepaCardRenderer:
    """米奈尔维尼 SEPA 买方时机决策卡片渲染中枢 (Google Python Style Guide 设计)."""

    @classmethod
    def render_sepa_card_html(
        cls,
        result: Union[SepaBuySignalResult, Dict[str, Any]],
        market: str = "US",
    ) -> str:
        """渲染买方机构级 A4 矢量 HTML 操盘决策卡片.

        Args:
            result: SEPA 买入信号计算结果对象或字典.
            market: 交易市场标识 ('US' 或 'JP').

        Returns:
            符合出版级排版与自适应宽度的 HTML 渲染片段字符串.
        """
        res = _normalize_sepa_result(result)
        curr_symbol = "$" if market == "US" else "¥"
        p = res.price_boundaries

        badge_bg, badge_text, status_desc_color = cls._resolve_badge_palette_and_text(
            res.status_buy_signal
        )

        stage_name = res.meta_trend_stage.get("state_name", res.status_trend_stage)
        vcp_name = res.meta_vcp_status.get("state_name", res.status_vcp_contraction)

        html = f"""
        <div style="background: #ffffff; border: 1.5px solid #cbd5e0; border-left: 5px solid {badge_bg}; border-radius: 6px; padding: 10px 14px; margin-top: 8px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 13px; font-weight: 800; color: #1a202c;">米奈尔维尼 SEPA 时机与买点决策卡</span>
              <span style="background: {badge_bg}; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">{badge_text}</span>
            </div>
            <div style="font-size: 11px; color: #718096; font-weight: 600;">
              技术足迹代码: <strong style="color: #2b6cb0; font-size: 12px;">{res.technical_footprint_code}</strong>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 8px; margin-bottom: 8px; text-align: center;">
            <div>
              <div style="font-size: 10px; color: #718096;">枢轴买点 (Pivot)</div>
              <div style="font-size: 13px; font-weight: 800; color: #2b6cb0;">{curr_symbol}{p.val_pivot_price:.2f}</div>
              <div style="font-size: 9.5px; color: #718096;">突破阻力线基准</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #718096;">刚性硬止损 (-{p.pct_hard_stop_loss:.1f}%)</div>
              <div style="font-size: 13px; font-weight: 800; color: #c53030;">{curr_symbol}{p.val_stop_loss_price:.2f}</div>
              <div style="font-size: 9.5px; color: #e53e3e;">跌破无条件砍仓</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #718096;">追高上限 (+5.0%)</div>
              <div style="font-size: 13px; font-weight: 800; color: #dd6b20;">{curr_symbol}{p.val_extended_limit_price:.2f}</div>
              <div style="font-size: 9.5px; color: #c05621;">超过此价严禁追高</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #718096;">移动保本触发 (3R)</div>
              <div style="font-size: 13px; font-weight: 800; color: #2f855a;">{curr_symbol}{p.val_breakeven_trigger_price:.2f}</div>
              <div style="font-size: 9.5px; color: #276749;">涨至此价止损提至保本</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #718096;">目标止盈靶心 (3:1)</div>
              <div style="font-size: 13px; font-weight: 800; color: #276749;">{curr_symbol}{p.val_target_profit_price:.2f}</div>
              <div style="font-size: 9.5px; color: #2f855a;">基准盈亏比目标位</div>
            </div>
          </div>

          <div style="font-size: 11px; line-height: 1.45; color: #4a5568;">
            <div style="margin-bottom: 3px;">
              <strong>【趋势与形态透视】</strong>
              生命周期阶段: <span style="font-weight: 700; color: #2d3748;">{stage_name}</span> (8大趋势指标全票通过: {"是" if res.is_trend_template_passed else "否"}) |
              VCP收敛评级: <span style="font-weight: 700; color: #2d3748;">{vcp_name}</span> ({res.cnt_contractions}次收缩，地量抽干: {"已确认" if res.is_volume_dryup_confirmed else "未确认"})
            </div>
            <div>
              <strong style="color: {status_desc_color};">【买方实战操盘指引】</strong>
              <span style="color: #1a202c;">{res.directive_action_zh}</span>
            </div>
          </div>
        </div>
        """
        return html

    @classmethod
    def render_sepa_card_markdown(
        cls,
        result: Union[SepaBuySignalResult, Dict[str, Any]],
        market: str = "US",
    ) -> str:
        """渲染买方投委会专用决策纪要 Markdown 文本卡片.

        Args:
            result: SEPA 买入信号计算结果对象或字典.
            market: 交易市场标识 ('US' 或 'JP').

        Returns:
            标准化 Markdown 富文本卡片字符串.
        """
        res = _normalize_sepa_result(result)
        curr = "$" if market == "US" else "¥"
        p = res.price_boundaries
        stage_name = res.meta_trend_stage.get("state_name", res.status_trend_stage)
        vcp_name = res.meta_vcp_status.get("state_name", res.status_vcp_contraction)
        sig_name = res.meta_buy_signal.get("state_name", res.status_buy_signal)

        md = f"""
### 【米奈尔维尼 SEPA 时机与买入信号决策卡 ({res.ticker})】
* **决策状态**: **{sig_name}** | **技术足迹**: `{res.technical_footprint_code}` | **趋势阶段**: {stage_name}
* **关键价格防线与击球走廊**:
  * **枢轴买点 (Pivot)**: `{curr}{p.val_pivot_price:.2f}` (突破阻力线基准)
  * **刚性止损 (-{p.pct_hard_stop_loss:.1f}%)**: `{curr}{p.val_stop_loss_price:.2f}` (盘中最大浮亏红线)
  * **超买追高上限 (+5.0%)**: `{curr}{p.val_extended_limit_price:.2f}` (超过此价绝对严禁追高)
  * **移动保本触发 (3R)**: `{curr}{p.val_breakeven_trigger_price:.2f}` (涨至此价止损无条件提至买入成本)
  * **目标靶心 (3:1)**: `{curr}{p.val_target_profit_price:.2f}`
* **形态收敛与地量状态**: {vcp_name} (收缩 {res.cnt_contractions} 次，地量抽干: {'已确认' if res.is_volume_dryup_confirmed else '未确认'})
* **买方操盘指令**: {res.directive_action_zh}
"""
        return md.strip()

    @classmethod
    def populate_sepa_section_excel(
        cls,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        start_row: int,
        result: Union[SepaBuySignalResult, Dict[str, Any]],
        market: str = "US",
    ) -> int:
        """向公司深度档案 Excel 工作簿 (Sheet 1 投资备忘录) 写入专属 SEPA 时机与操盘决策表.

        Args:
            ws: openpyxl 目标工作表对象.
            start_row: 起始行号 (1-indexed).
            result: SEPA 信号计算结果对象或字典.
            market: 交易市场代码 ('US' 或 'JP').

        Returns:
            写入完毕后的下一可用行号 (int).
        """
        res = _normalize_sepa_result(result)
        r = start_row
        r = ExcelStyler.apply_section_header(
            ws,
            r,
            "三、米奈尔维尼 SEPA 价格时机与买入决策操盘卡 (Minervini SEPA Timing & Tactical Cockpit)",
            max_col=10,
        )

        headers = ["时机与风控指标", "数值 / 价格", "单位", "判定基准与形态特征", "机构操盘指令与动作"]
        r = ExcelStyler.apply_table_headers(ws, r, headers, start_col=1)

        p = res.price_boundaries
        curr_fmt = FMT_CURRENCY_USD_DEC if market == "US" else FMT_CURRENCY_JPY_INT
        unit_curr = "$" if market == "US" else "¥"

        stage_name = res.meta_trend_stage.get("state_name", res.status_trend_stage)
        vcp_name = res.meta_vcp_status.get("state_name", res.status_vcp_contraction)
        sig_name = res.meta_buy_signal.get("state_name", res.status_buy_signal)

        rows = cls._build_excel_rows(
            res=res,
            p=p,
            stage_name=stage_name,
            vcp_name=vcp_name,
            sig_name=sig_name,
            unit_curr=unit_curr,
        )

        for idx, row_data in enumerate(rows):
            is_buy = (
                res.status_buy_signal == BuySignalTier.PIVOT_TRIGGERED.value
                and idx in (2, 3)
            )
            is_warning = (
                res.status_buy_signal == BuySignalTier.EXTENDED_OVERBOUGHT.value
                and idx in (2, 5)
            )
            bg = (
                COLOR_BUY_ZONE_GREEN
                if is_buy
                else (COLOR_WARNING_ORANGE if is_warning else None)
            )
            font_color = (
                COLOR_BUY_ZONE_TEXT
                if is_buy
                else (COLOR_WARNING_TEXT if is_warning else COLOR_CALC_BLACK)
            )
            n_fmt = (
                curr_fmt
                if idx in (3, 4, 5, 6, 7) and isinstance(row_data[1], (int, float))
                else None
            )

            r = ExcelStyler.write_data_row(
                ws,
                r,
                row_data,
                start_col=1,
                num_formats=[None, n_fmt, None, None, None],
                is_bold=(idx in (2, 3, 4)),
                font_color=font_color,
                bg_color=bg,
            )

        r += 1
        return r

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _resolve_badge_palette_and_text(
        status_buy_signal: str,
    ) -> Tuple[str, str, str]:
        """解析状态徽章色彩与文案 (私有辅助方法)."""
        if status_buy_signal == BuySignalTier.PIVOT_TRIGGERED.value:
            badge_bg = "#2f855a"  # 墨绿色
            badge_text = "【买入触发】放量突破枢轴买点"
            status_desc_color = "#276749"
        elif status_buy_signal == BuySignalTier.EXTENDED_OVERBOUGHT.value:
            badge_bg = "#c53030"  # 红色警告
            badge_text = "【超买拦截】脱离买点超 5%，严禁追高"
            status_desc_color = "#9b2c2c"
        elif status_buy_signal == BuySignalTier.SQUAT_REVERSAL_WATCH.value:
            badge_bg = "#d69e2e"  # 警戒金黄色
            badge_text = "【深蹲洗盘】缩量回踩守住止损，等待逆转"
            status_desc_color = "#b7791f"
        elif status_buy_signal == BuySignalTier.WATCHLIST_FORMING.value:
            badge_bg = "#3182ce"  # 经典蓝色
            badge_text = "【自选跟踪】第二阶段整理，等待收敛"
            status_desc_color = "#2b6cb0"
        else:
            badge_bg = "#718096"  # 灰色
            badge_text = "【趋势否决】未处于第二阶段主升浪"
            status_desc_color = "#4a5568"
        return badge_bg, badge_text, status_desc_color

    @staticmethod
    def _build_excel_rows(
        res: SepaBuySignalResult,
        p: SepaPriceBoundaries,
        stage_name: str,
        vcp_name: str,
        sig_name: str,
        unit_curr: str,
    ) -> List[List[Any]]:
        """构建写入 Excel 的各指标行数据 (私有辅助方法)."""
        return [
            [
                "生命周期阶段 (Trend Stage)",
                stage_name,
                "阶段",
                f"8大趋势指标: {'全票通过' if res.is_trend_template_passed else '未通过'}",
                "只在第二阶段做多",
            ],
            [
                "VCP波动收缩状态 (VCP Status)",
                f"{vcp_name} [{res.technical_footprint_code}]",
                "形态",
                f"收缩次数: {res.cnt_contractions}T, 地量抽干: {'已确认' if res.is_volume_dryup_confirmed else '未确认'}",
                "确认抛盘供给彻底耗尽",
            ],
            [
                "买入信号判定 (Buy Signal Tier)",
                sig_name,
                "决策",
                f"现价溢价买点: {p.pct_current_to_pivot:+.2f}%",
                res.directive_action_zh,
            ],
            [
                "枢轴买点价格 (Pivot Price)",
                p.val_pivot_price,
                unit_curr,
                "最后一次紧密收缩突破阻力线",
                "放量突破瞬间开火",
            ],
            [
                "刚性硬止损价 (Hard Stop Loss)",
                p.val_stop_loss_price,
                unit_curr,
                f"买点下方 -{p.pct_hard_stop_loss:.1f}% 绝对风控线",
                "击穿无条件斩仓离场",
            ],
            [
                "超买脱轨上限价 (Extended Limit)",
                p.val_extended_limit_price,
                unit_curr,
                "突破点上方 +5.0% 极限溢价",
                "超过此价坚决严禁追高",
            ],
            [
                "移动保本触发价 (3R Trailing Stop)",
                p.val_breakeven_trigger_price,
                unit_curr,
                "浮盈达3倍单股风险敞口 (3R)",
                "涨至此价止损提至买入价保本",
            ],
            [
                "目标止盈靶心 (3:1 Target Price)",
                p.val_target_profit_price,
                unit_curr,
                "保持 3:1 盈亏比标准卖方目标位",
                "高位分批兑现超额利润",
            ],
        ]

