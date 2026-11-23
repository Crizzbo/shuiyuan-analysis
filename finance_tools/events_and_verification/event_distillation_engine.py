# -*- coding: utf-8 -*-
"""突发事件因果解析与买方研判提炼引擎 (Event Distillation & Interpretation Engine).

职责：
1. 从非结构化官方公告与快讯（SEC 8-K/10-K/10-Q、日本央行/美联储/欧洲央行公报、科技巨头官方发布）中提炼微观物理事实与买方研判；
2. 剥离无用 HTML 标签，解析 SEC 8-K 具体披露 Item 编号并映射为中文商业影响；
3. 动态穿透关联企业 CIK -> 真实上市 Ticker，赋予即时下钻与 DCF 估值穿透能力；
4. 杜绝机械复制标题，确保每条事件均有具有买方投研深度的微观因果解读与影响评估。
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# SEC Form 8-K 披露事项标准买方中文映射字典 (SEC Regulation S-K Item Mappings)
SEC_8K_ITEM_MAP: Dict[str, Tuple[str, str, str]] = {
    # Item: (中文名称, 严重等级, 业务分部)
    "1.01": ("签署重大实质性协议", "P1", "重大商业协议与合同"),
    "1.02": ("重大实质性协议终止", "P1", "商业合同与合作变更"),
    "1.03": ("公司破产重组或司法接管", "P0", "破产清算与重组"),
    "1.04": ("矿山安全合规停产通报", "P2", "安全生产与矿山合规"),
    "1.05": ("重大网络安全侵害事件", "P0", "网络与数据安全"),
    "2.01": ("完成重大资产收购或处置剥离", "P1", "并购重组与资产交易"),
    "2.02": ("季度经营业绩与财务状况披露 (财报发布)", "P1", "公司财报与经营业绩"),
    "2.03": ("产生重大直接债务或表外融资承诺", "P1", "债务融资与负债结构"),
    "2.04": ("触发重大债务加速清偿违约条款", "P0", "信用违约与债务清偿"),
    "2.05": ("关停退出或资产处置重大会计重组费用", "P1", "重组退出与裁员减值"),
    "2.06": ("计提重大资产/商誉减值准备", "P1", "资产质量与减值计提"),
    "3.01": ("收到退市警告或不满足持续上市标准通告", "P0", "交易所上市合规"),
    "3.02": ("未登记股权证券私募发行与增发", "P1", "股权融资与股份稀释"),
    "3.03": ("证券持有人权利重大变更", "P1", "公司治理与股东权益"),
    "4.01": ("独立审计师/会计师事务所聘任变更", "P1", "财务审计与内控"),
    "4.02": ("前期财务报表重述不可信警示 (重大会计差错)", "P0", "会计合规与重述风险"),
    "5.01": ("公司实际控制权变更", "P1", "控制权与实控人变更"),
    "5.02": ("核心董监高人员离任/新任命及薪酬变动", "P1", "核心管理团队与治理"),
    "5.03": ("公司章程/治理细则修订或财年变更", "P2", "公司治理与章程修订"),
    "5.04": ("员工福利计划临时停牌与交易限制", "P2", "员工持股与福利计划"),
    "5.05": ("职业道德规范修订或豁免", "P2", "企业伦理与道德规范"),
    "5.06": ("空壳公司状态变更", "P2", "壳公司与资产注入"),
    "5.07": ("股东大会提案投票表决结果", "P2", "股东大会决议"),
    "5.08": ("股东提名董事事项公告", "P2", "董事会提名与治理"),
    "7.01": ("公平披露规则 (Reg FD) 口径业务沟通交流", "P2", "投资者关系与Reg FD"),
    "8.01": ("董事会认定的其他重大临时事项", "P2", "其他重大临时公告"),
    "9.01": ("财务报表及相关展件补充披露", "P2", "财务报表展件"),
}


class EventDistillationEngine:
    """突发事件多源事实因果解析引擎."""

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or Path(__file__).resolve().parents[2]
        self._cik_to_ticker_cache: Optional[Dict[str, str]] = None
        self._cik_to_name_cache: Optional[Dict[str, str]] = None

    def _load_sec_tickers(self) -> None:
        """从项目底账加载 SEC CIK -> Ticker 权威映射 (仅一次，缓存内存)."""
        if self._cik_to_ticker_cache is not None:
            return

        self._cik_to_ticker_cache = {}
        self._cik_to_name_cache = {}
        sec_tickers_path = self.root / "data" / "universe" / "sec_company_tickers.json"
        if not sec_tickers_path.exists():
            return

        try:
            with open(sec_tickers_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.values():
                cik_padded = str(item.get("cik_str", "")).zfill(10)
                ticker = str(item.get("ticker", "")).strip().upper()
                name = str(item.get("title", "")).strip()
                if cik_padded and ticker:
                    self._cik_to_ticker_cache[cik_padded] = ticker
                    self._cik_to_name_cache[cik_padded] = name
        except Exception as e:
            logger.warning("加载 SEC 公司代码底账失败: %s", e)

    def resolve_ticker_by_cik(self, cik_str: str) -> Optional[str]:
        """根据 10 位或不足 10 位的 CIK 查验对应美股 Ticker."""
        self._load_sec_tickers()
        if not self._cik_to_ticker_cache:
            return None
        cik_norm = cik_str.strip().zfill(10)
        return self._cik_to_ticker_cache.get(cik_norm)

    @staticmethod
    def clean_html_text(raw_html: Optional[str] = None) -> str:
        """剥离 HTML 标签，解码实体字符，清理多余空白为可读纯文本."""
        if not raw_html:
            return ""
        text = str(raw_html)
        text = html.unescape(text)
        # 将换行/段落标签转为清晰符号
        text = re.sub(r"<(?:br|p|div)\s*/?>", " · ", text, flags=re.IGNORECASE)
        # 剥离所有 HTML 标签
        text = re.sub(r"<[^>]+>", " ", text)
        # 压缩多余空白
        text = re.sub(r"\s+", " ", text).strip()
        # 清除前导/尾随的点
        text = text.strip("· ").strip()
        return text

    def parse_sec_filing_event(
        self,
        title: str,
        content: str,
    ) -> Optional[Dict[str, Any]]:
        """深度解析 SEC 官方申报 (8-K, 10-K, 10-Q, 6-K, Form 4 等)."""
        # 匹配标题形式: 8-K - MOBIX LABS, INC (0001855467) (Filer)
        pattern = r"(8-K(?:/A)?|10-K(?:/A)?|10-Q(?:/A)?|6-K(?:/A)?|Form\s+4|SC\s+13[DG](?:/A)?)\s*-\s*([^(]+?)\s*\((\d+)\)"
        m = re.search(pattern, title, re.IGNORECASE)
        if not m:
            # 备选匹配: 包含 8-K 或 10-K 的宽松标题
            if not any(f in title.upper() for f in ["8-K", "10-K", "10-Q", "6-K"]):
                return None
            form_type = "8-K" if "8-K" in title.upper() else "SEC 报告"
            company_raw = title
            cik_raw = ""
        else:
            form_type = m.group(1).upper()
            company_raw = m.group(2).strip()
            cik_raw = m.group(3).strip()

        # 查找上市代码
        ticker = self.resolve_ticker_by_cik(cik_raw) if cik_raw else None

        # 构造实体
        entities: List[str] = []
        if ticker:
            entities.append(f"{company_raw} ({ticker})")
            entities.append(ticker)
        elif company_raw:
            entities.append(company_raw)
        entities.append("美国证监会 (SEC)")

        # 从正文中提取 8-K Items
        items_found = re.findall(r"Item\s+(\d+\.\d+)[:\s]+([^<\n\r·]+)", content, re.IGNORECASE)

        severity = "P2"
        segments = ["公司治理与证券合规"]
        item_zh_list = []

        if items_found:
            for item_num, item_desc in items_found:
                num_clean = item_num.strip()
                if num_clean in SEC_8K_ITEM_MAP:
                    zh_name, item_sev, item_seg = SEC_8K_ITEM_MAP[num_clean]
                    item_zh_list.append(f"Item {num_clean} ({zh_name})")
                    if item_sev == "P0":
                        severity = "P0"
                    elif item_sev == "P1" and severity != "P0":
                        severity = "P1"
                    if item_seg not in segments:
                        segments.append(item_seg)
                else:
                    item_zh_list.append(f"Item {num_clean} ({item_desc.strip()[:20]})")

        # 提炼微观影响买方研判
        company_display = f"{company_raw} ({ticker})" if ticker else company_raw
        if form_type == "8-K":
            if item_zh_list:
                items_str = "、".join(item_zh_list[:3])
                impact = (
                    f"{company_display} 提交 SEC 8-K 重大临时申报：披露 {items_str}；"
                    f"涉及关键经营与公司治理事项，直接影响股东权益与业务预期。"
                )
            else:
                impact = (
                    f"{company_display} 提交 SEC 8-K 官方重大事项申报 (CIK: {cik_raw})；"
                    f"重点披露公司最新重大经营事件与未公开法定事项。"
                )
            category = "State_Policy_Regulatory"
            duration = "中期 1~6 个月"
        elif form_type == "10-K":
            impact = (
                f"{company_display} 正式披露 SEC 年度审计报告 (10-K)：全量财报三表、"
                f"MD&A管理层讨论与审计底稿已发布，构成基本面情景DCF测算与估值校准依据。"
            )
            severity = "P1"
            category = "State_Policy_Regulatory"
            segments = ["年度财务报表底稿", "公司基本面与估值"]
            duration = "长期年度基准"
        elif form_type == "10-Q":
            impact = (
                f"{company_display} 正式披露 SEC 季度报告 (10-Q)：季度营收利润三表底账就绪，"
                f"可供穿透存货周转(DIO)、净现金储备与自由现金流波动。"
            )
            severity = "P1"
            category = "State_Policy_Regulatory"
            segments = ["季度财务数据更新", "现金流与存货周转"]
            duration = "中期 1~3 个月"
        else:
            impact = f"{company_display} 提交 SEC {form_type} 官方信息披露文档 (CIK: {cik_raw})。"
            category = "State_Policy_Regulatory"
            duration = "短期"

        # 整理干净的正文摘要预览
        clean_content = self.clean_html_text(content)

        return {
            "category": category,
            "involved_entities": entities,
            "micro_physical_impact": impact,
            "estimated_duration": duration,
            "affected_business_segments": segments,
            "severity_level": severity,
            "clean_content": clean_content,
        }

    def parse_central_bank_event(
        self,
        title: str,
        content: str,
        source: str,
    ) -> Optional[Dict[str, Any]]:
        """深度解析全球主要中央银行（美联储、日本央行、欧洲央行）法定公报与言论."""
        t_low = title.lower()
        s_low = source.lower()

        # 1. 日本央行 (Bank of Japan / BoJ)
        if "boj" in s_low or "bank of japan" in s_low or "boj" in t_low or "日本银行" in title:
            entities = ["日本央行 (BoJ)", "全球外汇与固定收益市场"]
            segments = ["日本宏观流动性", "日元汇率与套息平仓"]
            severity = "P1"
            category = "CentralBank_Liquidity_FX_Shock"
            duration = "中期 1~3 个月"

            if "monetary policy" in t_low or "statement" in t_low or "货币政策" in title:
                impact = f"日本央行发布货币政策决议公告：{title}；涉及短期基准利率走廊、收益率曲线控制或国债买入指引变动。"
            elif "speech" in t_low or "address" in t_low or "演讲" in title or "讲话" in title:
                impact = f"日本央行审议委员/行长政策演说：{title}；重点阐释对通胀目标持续性与后续加息路径的前瞻指引。"
            elif "accounts" in t_low or "balance" in t_low or "资产负债" in title:
                impact = f"日本央行最新资产负债表与活期账户数据：{title}；反映基础货币投放规模与金融体系超额储备动向。"
                severity = "P2"
            else:
                impact = f"日本央行官方发布重要宏观公告：{title}；关注日元流动性传导与金融市场预期差。"

            return {
                "category": category,
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": duration,
                "affected_business_segments": segments,
                "severity_level": severity,
                "clean_content": self.clean_html_text(content or title),
            }

        # 2. 欧洲央行 (ECB)
        if "ecb" in s_low or "europa.eu" in s_low or "european central bank" in t_low:
            entities = ["欧洲央行 (ECB)", "欧洲银行与债券市场"]
            segments = ["欧元区货币市场", "欧洲宏观流动性"]
            severity = "P1"
            category = "CentralBank_Liquidity_FX_Shock"
            duration = "中期 1~3 个月"

            if "wage tracker" in t_low or "wage" in t_low:
                impact = f"欧洲央行发布劳动力薪资追踪指标：{title}；评估欧元区工资粘性与核心通胀反弹风险。"
            elif "banking data" in t_low or "financial stability" in t_low:
                impact = f"欧洲央行发布银行业及金融稳定性报告：{title}；监测主要系统性银行资产质量与信贷抗风险能力。"
            elif ":" in title and any(w in t_low for w in ["speech", "integrated", "policy", "growth", "money", "stability", "vujčić", "cipollone", "schnabel", "lagarde"]):
                impact = f"欧洲央行执委/官员政策演说：{title}；就欧元区宏观韧性、地缘碎片化及利率周期走向释放关键信号。"
            else:
                impact = f"欧洲央行官方重要公报：{title}；关注欧元区基准利率预期与流动性变动。"

            return {
                "category": category,
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": duration,
                "affected_business_segments": segments,
                "severity_level": severity,
                "clean_content": self.clean_html_text(content or title),
            }

        # 3. 美联储 (Federal Reserve / Fed)
        if "federalreserve" in s_low or "federal reserve" in s_low or "fed" in t_low or "fomc" in t_low:
            entities = ["美联储 (Federal Reserve)", "联邦公开市场委员会 (FOMC)"]
            segments = ["美元流动性", "全球基准无风险利率"]
            severity = "P1"
            category = "CentralBank_Liquidity_FX_Shock"
            duration = "中长期 1~3 个月"

            if "minutes" in t_low:
                impact = f"美联储议息会议纪要发布：{title}；详尽揭示货币政策委员会对通胀轨迹、失业率及政策利率走向的争论。"
            elif "discount rate" in t_low:
                impact = f"美联储贴现率会议记录：{title}；反映对商业银行向贴现窗口借款意愿与银行体系备付金状况的评估。"
            elif "resolution plan" in t_low or "banking" in t_low or "capital" in t_low:
                impact = f"美联储与监管部门银行业规程：{title}；评估大型金融机构处置预案与系统性金融风险防范。"
            else:
                impact = f"美联储官方重要发布：{title}；直接传导至美债收益率曲线与跨资产无风险贴现率。"

            return {
                "category": category,
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": duration,
                "affected_business_segments": segments,
                "severity_level": severity,
                "clean_content": self.clean_html_text(content or title),
            }

        return None

    def parse_corporate_tech_event(
        self,
        title: str,
        content: str,
        source: str,
    ) -> Optional[Dict[str, Any]]:
        """深度解析科技龙头企业官方发布 (NVIDIA, Google, Microsoft, Apple, Dow Jones)."""
        t_low = title.lower()
        s_low = source.lower()

        # 1. 英伟达官方博客 (NVIDIA Blog)
        if "nvidia" in s_low or "nvidia" in t_low:
            entities = ["英伟达 (NVDA)", "先进计算与GPU生态"]
            segments = ["数据中心与AI算力", "半导体生态"]
            severity = "P1"
            category = "Supply_Chain_Chokepoint"
            duration = "中长期 6~12 个月"

            if "geforce now" in t_low or "dlss" in t_low or "game" in t_low:
                impact = f"英伟达发布游戏与云渲染动态：{title}；推动端侧云游戏订阅及图形增强算法普及。"
                severity = "P2"
                segments = ["消费级GPU与云游戏"]
            elif "care" in t_low or "health" in t_low or "medical" in t_low:
                impact = f"英伟达发布医疗与智慧健康技术进展：{title}；基于AI算法赋能临床决策与医学影像。"
                segments = ["医疗健康AI与生命科学"]
            elif "robot" in t_low or "simulation" in t_low or "isaac" in t_low:
                impact = f"英伟达发布具身智能与物理仿真进展：{title}；依托物理AI与虚拟环境加速精密机器人开发。"
                segments = ["具身智能与机器人仿真"]
            elif "opensource" in t_low or "openshell" in t_low or "kubernetes" in t_low:
                impact = f"英伟达推进开源AI基础设施：{title}；增强在万卡算力工厂及异构集群编排调度的核心软件生态。"
                segments = ["算力集群编排与开源生态"]
            else:
                impact = f"英伟达官方发布技术与产品进展：{title}；强化其在先进算力基础设施领域的全栈竞争壁垒。"

            return {
                "category": category,
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": duration,
                "affected_business_segments": segments,
                "severity_level": severity,
                "clean_content": self.clean_html_text(content or title),
            }

        # 2. 谷歌官方博客 (Google Blog)
        if "google" in s_low or "google" in t_low:
            entities = ["谷歌母公司 (Alphabet)", "生成式AI生态"]
            segments = ["云计算基础设施", "企业级AI与搜索生态"]
            impact = f"谷歌官方发布前沿技术与产品动态：{title}；涉及大模型研发、云平台与多模态AI应用落地。"
            return {
                "category": "State_Policy_Regulatory",
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": "长期持续",
                "affected_business_segments": segments,
                "severity_level": "P2",
                "clean_content": self.clean_html_text(content or title),
            }

        # 3. 微软官方博客 (Microsoft Blog)
        if "microsoft" in s_low or "microsoft" in t_low:
            entities = ["微软 (MSFT)", "企业云生态"]
            segments = ["Azure云基础设施", "企业级SaaS与Copilot"]
            impact = f"微软官方披露企业技术生态进展：{title}；涉及 Azure 算力、Copilot 与云办公生产力生态。"
            return {
                "category": "State_Policy_Regulatory",
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": "长期持续",
                "affected_business_segments": segments,
                "severity_level": "P2",
                "clean_content": self.clean_html_text(content or title),
            }

        # 4. 苹果官方新闻室 (Apple Newsroom)
        if "apple" in s_low or "apple" in t_low:
            entities = ["苹果公司 (AAPL)", "全球消费电子供应链"]
            segments = ["高端消费终端", "iOS生态与服务业务"]
            impact = f"苹果官方新闻发布：{title}；涉及终端硬件迭代、供应链合作或数字服务生态进展。"
            return {
                "category": "State_Policy_Regulatory",
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": "中长期 3~6 个月",
                "affected_business_segments": segments,
                "severity_level": "P2",
                "clean_content": self.clean_html_text(content or title),
            }

        # 5. 道琼斯 / 华尔街日报大盘与市场要闻
        if "dj.com" in s_low or "wsj" in s_low or "markets" in s_low:
            entities = ["全球证券交易市场", "买方机构投资者"]
            segments = ["股票与债券交易", "跨资产配置"]
            impact = f"权威财经市场专讯：{title}；关注宏观无风险利率波动、大宗商品供应或标的资产交易情绪变动。"
            return {
                "category": "Other_Macro_Event",
                "involved_entities": entities,
                "micro_physical_impact": impact,
                "estimated_duration": "短期 1~5 个交易日",
                "affected_business_segments": segments,
                "severity_level": "P2",
                "clean_content": self.clean_html_text(content or title),
            }

        return None

    def distill_single_event(
        self,
        title: str,
        content: str,
        source: str = "Official_Feed",
        fallback_category: str = "Other_Macro_Event",
    ) -> Dict[str, Any]:
        """统一对单一事件执行全息因果提取与结构化提纯，绝不返回与标题相同的机械字符串."""
        # 1. 尝试 SEC 官方申报解析
        sec_res = self.parse_sec_filing_event(title, content)
        if sec_res:
            return sec_res

        # 2. 尝试全球央行公报解析
        cb_res = self.parse_central_bank_event(title, content, source)
        if cb_res:
            return cb_res

        # 3. 尝试龙头企业官方技术发布解析
        tech_res = self.parse_corporate_tech_event(title, content, source)
        if tech_res:
            return tech_res

        # 4. 通用保底结构化提取 (杜绝 micro_physical_impact == title)
        clean_content = self.clean_html_text(content or title)
        source_clean = re.sub(r"https?://(?:www\.)?([^/]+).*", r"\1", source)

        # 提取标题中可能存在的公司代码或关键词
        ticker_match = re.findall(r"\b([A-Z]{1,5})\b", title)
        known_us_tickers = {"NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSM", "AMD", "AVGO", "INTC", "PLTR", "SPY", "QQQ"}
        hit_tickers = [t for t in ticker_match if t in known_us_tickers]

        entities = hit_tickers if hit_tickers else [source_clean]
        segments = ["宏观产业与综合业务"]

        # 综合提纯买方微观解读
        if clean_content and len(clean_content) > len(title) and clean_content != title:
            # 采用内容提要作为辅助解读
            summary_snip = clean_content[:100].rstrip("· ")
            impact = f"权威信源 ({source_clean}) 发布关键信息：{title}；核心事实摘要：{summary_snip}。"
        else:
            impact = f"官方信源 ({source_clean}) 发布最新行业与监管动态：{title}；关注相关业务预期与基本面传导影响。"

        return {
            "category": fallback_category,
            "involved_entities": entities,
            "micro_physical_impact": impact,
            "estimated_duration": "中期 1~3 个月",
            "affected_business_segments": segments,
            "severity_level": "P2",
            "clean_content": clean_content,
        }
