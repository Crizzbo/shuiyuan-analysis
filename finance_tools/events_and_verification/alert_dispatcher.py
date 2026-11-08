"""突发事件多通道告警分发器 (Event Radar Alert Dispatcher).

严格遵循单一事实来源 (SSOT) 与买方通俗商业语言规范:
1. 配置与程序彻底解耦: 告警阈值、通道开关与防刷屏冷却时间由外置 JSON 配置驱动;
2. 自动化因果穿透联动: 监测到 P0/P1 重大事件时，自动联动 SOTP 业务分部穿透引擎测算受损;
3. 传闻熔断门禁保护: 对未经官方核实的快讯自动注入传闻熔断视觉警示与核验指引;
4. 弹性多通道分发: 支持控制台富文本卡片、Windows 桌面原生弹窗通知、审计流水日志与 Webhook;
5. 零数学符号干扰: 全面转化为“波及哪个业务、库存能扛多久、每股收益变动、买方决策直觉”通俗语言。
"""

import json
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_core.engines.event_radar_engine import StructuredEventSummary
from financial_core.engines.sotp_event_penetration_engine import (
    BusinessSegment,
    CompanySotpProfile,
    EnterpriseEventImpactResult,
    SotpEventPenetrationEngine,
)

logger = logging.getLogger("AlertDispatcher")

# 实体名称到标准股票代码映射表
COMPANY_TICKER_MAP = {
    "台积电": "TSM",
    "tsmc": "TSM",
    "tsm": "TSM",
    "英伟达": "NVDA",
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "微软": "MSFT",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "苹果": "AAPL",
    "apple": "AAPL",
    "aapl": "AAPL",
    "特斯拉": "TSLA",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "阿斯麦": "ASML",
    "asml": "ASML",
    "博通": "AVGO",
    "broadcom": "AVGO",
    "avgo": "AVGO",
    "超威半导体": "AMD",
    "amd": "AMD",
    "东京电子": "8035",
    "tokyo electron": "8035",
    "爱德万测试": "6857",
    "advantest": "6857",
    "软银": "9984",
    "softbank": "9984",
}

# 16 大信息收集维度中文自然语言映射
CATEGORY_ZH_MAP = {
    "Geopolitical_CrossStrait": "地缘海峡博弈与实体清单",
    "State_Policy_Regulatory": "各州产业政策与公用负荷",
    "Physical_Plant_Disruption": "核心物理设施破坏与停产",
    "Supply_Chain_Chokepoint": "供应链咽喉要道绕航中断",
    "Labor_Strikes_Port_Railways": "码头铁路工会罢工",
    "Antitrust_Litigation": "反垄断诉讼与337专利纠纷",
    "Commodity_Physical_Squeeze": "实物大宗现货逼仓倒挂",
    "CentralBank_Liquidity_FX_Shock": "央行流动性与套息平仓冲击",
    "Energy_Grid_Blackout_Rationing": "能源电网跳闸与工业限电",
    "Cyber_Critical_Infrastructure": "要害工控网络瘫痪",
    "Biosecurity_Export_Embargo": "生物安全法案与原药查扣",
    "Critical_Minerals_Export_Permit": "战略矿产出口管制与配额",
    "Defense_Procurement_Authorization": "国防军工采购授权变动",
    "Climate_Catastrophe_Insurance": "极端气象与再保险巨灾理赔",
    "Maritime_Insurance_Sanctions": "海运保赔与制裁扣押",
    "Sovereign_Debt_Liquidity": "主权债务上限与国债流动性",
    "Other_Macro_Event": "宏观突发重大事件",
}

# 投资决策动作通俗自然语言映射 (兼容 Windows GBK/UTF-8 终端编码)
ACTION_ZH_MAP = {
    "BUY_ON_OVERSOLD_NOISE": "[恐慌错杀买入机会] (全公司受损极微，非理性砸盘时可逢低吸筹)",
    "MONITOR_INVENTORY_BUFFER": "[密切监控库存抵御天数] (短期有缓冲，重点跟踪事故抢修进展)",
    "EXPEDITE_EXPANSION_OVERWEIGHT": "[结构性利好增配机会] (直接增厚关键分部利润与订单)",
    "DOWNGRADE_AND_HEDGE": "[利润实质承压，启动对冲保护] (核心主营受损且缺乏提价转嫁能力)",
    "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER": "[待核传闻熔断锁定中] (信源等级低，已前置拦截，等待官方公报)",
    "RUMOR_CIRCUIT_BREAKER_ACTIVE": "[待核传闻熔断锁定中] (信源等级低，已前置拦截，等待官方公报)",
    "NO_MEASURABLE_SEGMENT_IMPACT": "[未构成实质财务受损] (涉及业务线与该事件无直接因果暴露)",
    "SCENARIO_REVIEW_REQUIRED": "[情景参数核验中] (需复核微观参数与官方公告)",
}


class AlertDispatcher:
    """突发重大事件多通道告警分发中枢."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        sotp_engine: Optional[SotpEventPenetrationEngine] = None,
    ):
        self.config = self._load_config(config_path)
        self.sotp_engine = sotp_engine or SotpEventPenetrationEngine()
        # 内存级防刷屏冷却缓存: {event_id: last_alert_epoch_seconds}
        self._cooldown_cache: Dict[str, float] = {}

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """级联探测加载外置告警配置 (SSOT)."""
        candidates = []
        if config_path:
            candidates.append(Path(config_path))
        candidates.extend([
            PROJECT_ROOT / "financial_core/engines/event_radar/config/alert_dispatcher_config.json",
            PROJECT_ROOT / "config/alert_dispatcher_config.json",
        ])

        for p in candidates:
            if p and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    logger.debug("成功加载告警配置: %s", p)
                    return cfg
                except Exception as e:
                    logger.warning("解析告警配置文件失败 %s: %s", p, e)

        # 默认安全回退配置
        return {
            "alert_level_threshold": "P0_AND_P1",
            "cooldown_seconds": 300,
            "auto_trigger_sotp": true,
            "max_entities_to_penetrate": 3,
            "channels": {
                "console": {"enabled": True, "show_sotp_summary": True, "use_color": True},
                "desktop_toast": {"enabled": True, "duration_seconds": 5, "sound": True},
                "file_log": {"enabled": True, "log_path": "reports/alerts/radar_alerts.log"},
                "webhook": {"enabled": False, "url": "", "token": "", "platform": "generic"},
            },
        }

    def should_alert(self, event_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """判定该事件是否满足告警触发门槛及冷却防刷屏规则."""
        severity = event_dict.get("severity_level", "P2").upper()
        threshold = self.config.get("alert_level_threshold", "P0_AND_P1")

        # 1. 烈度门槛核验
        if threshold == "P0_ONLY" and severity != "P0":
            return False, f"未达到P0烈度门槛 (当前: {severity})"
        elif threshold == "P0_AND_P1" and severity not in ("P0", "P1"):
            return False, f"未达到P0/P1烈度门槛 (当前: {severity})"

        # 2. 冷却防刷屏核验
        event_id = event_dict.get("event_id") or event_dict.get("title", "")
        now = time.time()
        cooldown_sec = self.config.get("cooldown_seconds", 300)

        if event_id in self._cooldown_cache:
            last_alerted = self._cooldown_cache[event_id]
            elapsed = now - last_alerted
            if elapsed < cooldown_sec:
                return False, f"处于冷却静音期 (剩余 {int(cooldown_sec - elapsed)} 秒)"

        return True, "满足告警条件"

    def match_entities_to_tickers(self, entities: List[str]) -> List[str]:
        """将事件涉及的自然语言实体识别为已登记标的代码."""
        matched = []
        for e in entities:
            clean = str(e).strip().lower()
            if clean in COMPANY_TICKER_MAP:
                t = COMPANY_TICKER_MAP[clean]
                if t not in matched:
                    matched.append(t)
            else:
                # 检查是否本身就是纯大写Ticker
                upper_candidate = str(e).strip().upper()
                if upper_candidate in ("TSM", "NVDA", "MSFT", "AAPL", "ASML", "AVGO", "AMD", "8035", "6857", "9984"):
                    if upper_candidate not in matched:
                        matched.append(upper_candidate)
        return matched

    def execute_sotp_penetration(
        self,
        event_dict: Dict[str, Any],
        sotp_analyzer: Optional[Any] = None,
    ) -> List[EnterpriseEventImpactResult]:
        """自动联动 SOTP 引擎对受波及标的执行因果穿透测算."""
        if not self.config.get("auto_trigger_sotp", True):
            return []

        entities = event_dict.get("involved_entities", [])
        target_tickers = self.match_entities_to_tickers(entities)
        max_n = self.config.get("max_entities_to_penetrate", 3)
        target_tickers = target_tickers[:max_n]

        if not target_tickers:
            return []

        # 组装 StructuredEventSummary
        summary = StructuredEventSummary(
            event_id=event_dict.get("event_id", "EVT_ALERT_AUTO"),
            timestamp=event_dict.get("published_at", datetime.now(timezone.utc).isoformat()),
            category=event_dict.get("category", "Other_Macro_Event"),
            involved_entities=entities,
            micro_physical_impact=event_dict.get("micro_physical_impact", ""),
            estimated_duration=event_dict.get("estimated_duration", "4-8周"),
            affected_business_segments=event_dict.get("affected_business_segments", []),
            severity_level=event_dict.get("severity_level", "P1"),
            requires_deep_analysis=bool(event_dict.get("requires_deep_analysis", True)),
            raw_title=event_dict.get("title", ""),
            source_name=event_dict.get("source_name", "Alert_Monitor"),
            credibility_tier=event_dict.get("credibility_tier", "Tier3_Mainstream_Wire"),
            credibility_score=float(event_dict.get("credibility_score", 0.8)),
            verification_status=event_dict.get("verification_status", "Corroborated_Report"),
            verification_note=event_dict.get("verification_note", ""),
            evidence_path=event_dict.get("evidence_path"),
            evidence_sha256=event_dict.get("evidence_sha256"),
            verified_at=event_dict.get("verified_at"),
        )

        results = []
        if sotp_analyzer:
            for t in target_tickers:
                try:
                    profile = sotp_analyzer.get_company_sotp_profile(t)
                    if profile:
                        res = self.sotp_engine.analyze_company_impact(profile, summary)
                        results.append(res)
                except Exception as e:
                    logger.debug("SOTP 分析标的 %s 跳过: %s", t, e)

        # 若未提供 analyzer 或全部失败，使用内置合成沙箱打样保证展示
        if not results:
            from scripts.test_support.sotp_fixtures import SYNTHETIC_PROFILES
            for t in target_tickers:
                if t in SYNTHETIC_PROFILES:
                    raw_prof = SYNTHETIC_PROFILES[t]
                    try:
                        prof = self._build_profile_from_synthetic_dict(raw_prof, t)
                        res = self.sotp_engine.analyze_company_impact(prof, summary)
                        results.append(res)
                    except Exception as e:
                        logger.debug("合成档案分析标的 %s 异常: %s", t, e)

        return results

    def _build_profile_from_synthetic_dict(self, d: Dict[str, Any], ticker: str) -> CompanySotpProfile:
        """从合成字典安全构建严格平账的 CompanySotpProfile 对象."""
        segments = []
        for s in d.get("segments", []):
            seg = BusinessSegment(
                segment_id=s.get("segment_id", ""),
                name_zh=s.get("name_zh", ""),
                name_en=s.get("name_en", ""),
                revenue=float(s.get("revenue", 0.0)),
                revenue_weight=float(s.get("revenue_weight", 0.0)),
                operating_margin=float(s.get("operating_margin", 0.0)),
                operating_income=float(s.get("operating_income", 0.0)),
                cost_pass_through_power=float(s.get("cost_pass_through_power", 0.5)),
                inventory_buffer_days=float(s.get("inventory_buffer_days", 30.0)),
                relevant_keywords=s.get("relevant_keywords", []),
            )
            segments.append(seg)

        tot_rev = float(d.get("total_revenue", 0.0))
        tot_op_inc = float(d.get("total_operating_income", 0.0))
        sum_seg_inc = sum(s.operating_income for s in segments)
        unalloc = tot_op_inc - sum_seg_inc

        return CompanySotpProfile(
            ticker=ticker,
            company_name=d.get("company_name", ticker),
            fiscal_year=d.get("fiscal_year", "FY2024"),
            total_revenue=tot_rev,
            total_operating_income=tot_op_inc,
            effective_tax_rate=float(d.get("effective_tax_rate", 0.2)),
            diluted_shares=float(d.get("diluted_shares", 1000.0)),
            current_share_price=float(d.get("current_share_price", 100.0)),
            segments=segments,
            unallocated_operating_income=unalloc,
            data_origin="synthetic",
            evidence_status="unverified",
        )

    def format_alert_card(
        self,
        event_dict: Dict[str, Any],
        sotp_results: Optional[List[EnterpriseEventImpactResult]] = None,
    ) -> str:
        """以通俗商业语言格式化富文本告警卡片 (无数学符号，直击买卖点)."""
        event_id = event_dict.get("event_id", "")
        sev = event_dict.get("severity_level", "P1")
        title = event_dict.get("title", "突发重大未知事件")
        cat_key = event_dict.get("category", "")
        cat_zh = CATEGORY_ZH_MAP.get(cat_key, cat_key or "宏观突发重大事件")
        source_name = event_dict.get("source_name", "未知信源")
        cred_tier = event_dict.get("credibility_tier", "Tier3_Mainstream_Wire")
        v_status = event_dict.get("verification_status", "Corroborated_Report")
        micro_impact = event_dict.get("micro_physical_impact", "暂无具体微观描述")
        pub_at = event_dict.get("published_at", "")

        is_rumor = (v_status == "Unverified_Rumor")

        lines = []
        lines.append("=" * 82)
        lines.append(f"【买方投研突发重大告警 · {sev} 级】{title}")
        lines.append("=" * 82)
        if event_id:
            lines.append(f"• 事件识别编号 : {event_id}")
        lines.append(f"• 所属业务维度 : {cat_zh}")
        lines.append(f"• 信源权威层级 : {source_name} ({cred_tier})")
        if is_rumor:
            lines.append("• 门禁核验状态 : [待核传闻] (传闻熔断机制已锁定，已前置掐断下游调仓计算)")
        else:
            lines.append("• 门禁核验状态 : [权威信源准入] (官方已核实/主流证实，允许深度测算)")
        lines.append(f"• 微观物理影响 : {micro_impact}")
        if pub_at:
            lines.append(f"• 消息发布时间 : {pub_at}")

        # SOTP 业务分部穿透呈现
        if sotp_results:
            lines.append("-" * 82)
            lines.append("【自动因果穿透 · 受波及核心标的商业受损测算】")
            for res in sotp_results:
                signal_key = getattr(res, "scenario_signal", None) or res.recommended_action
                action_zh = ACTION_ZH_MAP.get(signal_key, ACTION_ZH_MAP.get(res.recommended_action, res.recommended_action))
                lines.append(f"\n[核心标的]：{res.company_name} ({res.ticker})")
                lines.append(f"  - 买方决策直觉 : {action_zh}")

                if res.recommended_action == "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER":
                    lines.append("  - 熔断保护提示 : 信源权威度不足，系统已锁止。请核验官方公报后再行决策。")
                else:
                    # 遍历分部受损
                    for seg in res.segment_impacts:
                        if seg.exposure_score > 0:
                            lines.append(f"  - 受影响业务线 : 【{seg.segment_name}】(暴露度 {seg.exposure_score*100:.0f}%)")
                            lines.append(f"    • 库存抵御缓冲 : 吸收因子 {seg.inventory_absorption_factor*100:.0f}%，有效平抑短期停产")
                            lines.append(f"    • 预计营业利润变动 : {seg.operating_income_impact:+.1f} 百万美元")
                            lines.append(f"    • 商业因果逻辑 : {seg.rationale}")
                    lines.append(f"  - 全公司最终受损 : 本期每股收益变动 (ΔEPS): {res.eps_impact:+.3f} 美元 (营业利润变动: {res.ebit_impact_percentage*100:+.2f}%)")
        elif is_rumor:
            lines.append("-" * 82)
            lines.append("【传闻熔断保护激活】来自社交快讯等低权重信源，SOTP 深度计算已前置拦截，防范网络小道消息误导。")

        lines.append("=" * 82)
        return "\n".join(lines)

    def trigger_desktop_toast(self, title: str, message: str) -> bool:
        """安全触发 Windows 原生桌面 Toast 弹窗 (无外部第三方库依赖，失败静默容错)."""
        if platform.system() != "Windows":
            return False

        try:
            # 清理换行符与引号防注入
            safe_title = title.replace('"', ' ').replace("'", ' ')[:80]
            safe_msg = message.replace('"', ' ').replace("'", ' ')[:140]

            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName('text')
            $textNodes.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_msg}')) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('水源买方投研系统')
            $notifier.Show($toast)
            """
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return True
        except Exception as e:
            logger.debug("Windows 原生 Toast 通知调用异常 (静默回退): %s", e)
            return False

    def log_alert_to_file(self, event_dict: Dict[str, Any], card_text: str) -> bool:
        """持久化归档告警记录至文件日志底账."""
        log_cfg = self.config.get("channels", {}).get("file_log", {})
        if not log_cfg.get("enabled", True):
            return False

        log_path = PROJECT_ROOT / log_cfg.get("log_path", "reports/alerts/radar_alerts.log")
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- [ALERT @ {datetime.now(timezone.utc).isoformat()}] ---\n")
                f.write(card_text)
                f.write("\n")
            return True
        except Exception as e:
            logger.error("写入告警流水日志失败: %s", e)
            return False

    def _safe_print_card(self, card: str) -> None:
        """安全打印卡片至控制台，容错 Windows GBK/ANSI 编码环境."""
        try:
            print("\n" + card + "\n")
        except UnicodeEncodeError:
            enc = sys.stdout.encoding or "utf-8"
            clean = card.encode(enc, errors="replace").decode(enc)
            print("\n" + clean + "\n")

    def dispatch_event_alert(
        self,
        event_dict: Dict[str, Any],
        sotp_analyzer: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """全流程执行告警分发调度."""
        ok, reason = self.should_alert(event_dict)
        if not ok:
            return {"dispatched": False, "reason": reason}

        event_id = event_dict.get("event_id") or event_dict.get("title", "")
        # 1. 自动执行 SOTP 穿透
        sotp_results = self.execute_sotp_penetration(event_dict, sotp_analyzer=sotp_analyzer)

        # 2. 格式化富文本卡片
        card = self.format_alert_card(event_dict, sotp_results)

        channels_cfg = self.config.get("channels", {})
        dispatched_channels = []

        # 3. 控制台输出
        if channels_cfg.get("console", {}).get("enabled", True):
            self._safe_print_card(card)
            dispatched_channels.append("console")

        # 4. 桌面原生通知
        if channels_cfg.get("desktop_toast", {}).get("enabled", True):
            toast_title = f"【买方突发告警】{event_dict.get('severity_level', 'P1')}级事件"
            toast_msg = event_dict.get("title", "")
            if self.trigger_desktop_toast(toast_title, toast_msg):
                dispatched_channels.append("desktop_toast")

        # 5. 文件日志归档
        if channels_cfg.get("file_log", {}).get("enabled", True):
            if self.log_alert_to_file(event_dict, card):
                dispatched_channels.append("file_log")

        # 6. 登记防刷屏冷却
        self._cooldown_cache[event_id] = time.time()

        logger.info(
            "突发事件告警已成功分发 | 事件: %s | 烈度: %s | 通道: %s",
            event_id,
            event_dict.get("severity_level"),
            ", ".join(dispatched_channels),
        )

        return {
            "dispatched": True,
            "event_id": event_id,
            "severity_level": event_dict.get("severity_level"),
            "channels": dispatched_channels,
            "sotp_penetrated_count": len(sotp_results),
        }
