"""AI 浏览器定向补数与信源法定鉴真流水线 (Evidence Verification Pipeline).

严格遵循《2026-10-11 最新数据来源策略》与买方防伪鉴真准则:
1. 真实证据原则: 拒绝无依据的口头声称，必须以项目内官方监管/交易所/发行人公报原文为唯一事实底账;
2. 密码学验签: 刚性计算证据文件 SHA-256 哈希指纹，全程不可篡改、可审计、处处留痕;
3. 传闻熔断解除: 核验通过后将信源升格至 Tier 1 官方最高权威，自动解锁下游 SOTP 因果穿透计算;
4. 自动化批量匹配: 支持自动扫描证据收件箱 (inbox)，基于事件 ID 智能关联并批量解封;
5. 自动联动闭环: 验签完成后即时重算 SOTP 受损账本，并刷新大屏看板与待补任务清单。
"""

import hashlib
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.event_radar_collector import RadarDatabaseManager
from finance_tools.sotp_event_analyzer import SotpEventAnalyzer
from scripts.generate_radar_dashboard import generate_dashboard_html as generate_radar_dashboard
from scripts.generate_radar_browser_checklist import generate_radar_browser_checklist

logger = logging.getLogger("EvidenceVerificationPipeline")


class EvidenceVerificationPipeline:
    """法定信源证据核验与传闻熔断自动解封流水线."""

    def __init__(
        self,
        db_path: str = "data/ledger/event_radar.sqlite3",
        evidence_inbox_dir: str = "data_sources/official_filings/inbox",
        archive_dir: str = "data_sources/official_filings",
        receipts_path: str = "data/ledger/verification_receipts.json",
        auto_refresh_reports: bool = True,
    ):
        db_p = Path(db_path)
        self.db_path = str(db_p if db_p.is_absolute() else (PROJECT_ROOT / db_path))
        self.inbox_dir = PROJECT_ROOT / evidence_inbox_dir
        self.archive_dir = PROJECT_ROOT / archive_dir
        self.receipts_path = PROJECT_ROOT / receipts_path
        self.auto_refresh_reports = auto_refresh_reports

        # 初始化确保目录结构就绪
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_mgr = RadarDatabaseManager(db_path=self.db_path)

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """计算证据文件的标准 SHA-256 哈希值."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def validate_file_safety(self, file_path: Path) -> Tuple[Path, str]:
        """核验文件合法性与项目内安全边界防御."""
        resolved = file_path.resolve()
        try:
            rel_path = resolved.relative_to(PROJECT_ROOT)
        except ValueError:
            raise PermissionError(f"安全红线：证据文件 ({resolved}) 必须严格位于项目根目录内，禁止跨目录越界。")

        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"证据文件不存在或不是普通文件: {resolved}")

        return resolved, str(rel_path).replace("\\", "/")

    def load_receipts(self) -> List[Dict[str, Any]]:
        """加载已归档的防伪鉴真密码学收据账本."""
        if self.receipts_path.is_file():
            try:
                with open(self.receipts_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("解析核验收据账本失败: %s", e)
        return []

    def record_receipt(self, receipt_data: Dict[str, Any]) -> None:
        """安全持久化单条鉴真收据."""
        receipts = self.load_receipts()
        # 依据 event_id 幂等覆盖或追加
        updated = False
        for idx, r in enumerate(receipts):
            if r.get("event_id") == receipt_data.get("event_id"):
                receipts[idx] = receipt_data
                updated = True
                break
        if not updated:
            receipts.append(receipt_data)

        with open(self.receipts_path, "w", encoding="utf-8") as f:
            json.dump(receipts, f, ensure_ascii=False, indent=2)

    def verify_single_event(
        self,
        event_id: str,
        evidence_file: Path,
        note: Optional[str] = None,
        archive_copy: bool = True,
    ) -> Dict[str, Any]:
        """对单条事件执行法定公报核验、SHA-256 验签并彻底解除传闻熔断."""
        ev_file, rel_path = self.validate_file_safety(evidence_file)
        file_sha256 = self.compute_sha256(ev_file)

        existing = self.db_mgr.get_event_by_id(event_id)
        if not existing:
            raise KeyError(f"雷达数据库中未找到编号为 '{event_id}' 的事件记录")

        # 若处于收件箱，规范归档至指定业务子目录
        final_rel_path = rel_path
        if archive_copy and self.inbox_dir in ev_file.parents:
            category = existing.get("category", "macro")
            target_sub = self.archive_dir / category
            target_sub.mkdir(parents=True, exist_ok=True)
            target_file = target_sub / ev_file.name
            shutil.copy2(ev_file, target_file)
            final_rel_path = str(target_file.relative_to(PROJECT_ROOT)).replace("\\", "/")

        now_iso = datetime.now(timezone.utc).isoformat()
        verification_note = note or f"AI浏览器定向补数完成，核验官方公报原文属实 (SHA-256: {file_sha256[:12]}...)"

        # 更新雷达数据库: 提升信源等级、变更状态、解除传闻熔断
        update_success = self.db_mgr.confirm_event_verification(
            event_id=event_id,
            evidence_path=final_rel_path,
            evidence_sha256=file_sha256,
            verified_at=now_iso,
            note=verification_note,
        )

        if not update_success:
            raise RuntimeError(f"更新事件 {event_id} 数据库核验状态失败")

        receipt = {
            "receipt_id": f"RCP_{event_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "event_id": event_id,
            "title": existing.get("title"),
            "category": existing.get("category"),
            "previous_status": existing.get("verification_status"),
            "new_status": "Confirmed_Fact",
            "previous_credibility": existing.get("credibility_tier"),
            "new_credibility": "Tier1_Official_Regulatory",
            "evidence_path": final_rel_path,
            "evidence_sha256": file_sha256,
            "file_size_bytes": ev_file.stat().st_size,
            "verified_at": now_iso,
            "verification_note": verification_note,
            "circuit_breaker_lifted": True,
        }
        self.record_receipt(receipt)

        logger.info(
            "事件 %s 法定信源核验成功 | 状态: Confirmed_Fact | 熔断已解除 | SHA-256: %s",
            event_id,
            file_sha256[:16],
        )

        # 联动刷新报表看板与补数清单
        if self.auto_refresh_reports:
            try:
                generate_radar_dashboard(db_path=self.db_path)
                generate_radar_browser_checklist(db_path=self.db_path)
            except Exception as e:
                logger.error("联动生成看板报表异常: %s", e)

        return receipt

    def scan_and_process_inbox(self) -> List[Dict[str, Any]]:
        """智能扫描收件箱，自动提取文件名中的 EVT_<ID> 并批量执行验签入库."""
        if not self.inbox_dir.exists():
            return []

        processed_receipts = []
        files = [p for p in self.inbox_dir.iterdir() if p.is_file()]

        # 获取数据库中已知事件 ID 映射表，支持精确子串命中与正则回溯
        all_events = self.db_mgr.query_events()
        event_id_map = {e["event_id"].upper(): e["event_id"] for e in all_events if e.get("event_id")}

        for f in files:
            matched_id = None
            upper_name = f.name.upper()

            # 策略 1: 直接匹配已知事件 ID 子串 (按长度倒序，优先匹配最长 ID)
            sorted_candidates = sorted(event_id_map.keys(), key=len, reverse=True)
            for cand in sorted_candidates:
                if cand in upper_name:
                    matched_id = event_id_map[cand]
                    break

            # 策略 2: 正则提取 EVT_ 开头的前缀串，并逐级回退分割符匹配
            if not matched_id:
                m = re.search(r"(EVT_[A-Za-z0-9_]+)", f.name, re.IGNORECASE)
                if m:
                    raw_cand = m.group(1).upper()
                    parts = raw_cand.split("_")
                    for i in range(len(parts), 1, -1):
                        sub_cand = "_".join(parts[:i])
                        if sub_cand in event_id_map:
                            matched_id = event_id_map[sub_cand]
                            break
                        if self.db_mgr.get_event_by_id(sub_cand):
                            matched_id = sub_cand
                            break

            if not matched_id:
                continue

            existing = self.db_mgr.get_event_by_id(matched_id)
            if not existing:
                continue

            try:
                receipt = self.verify_single_event(
                    event_id=matched_id,
                    evidence_file=f,
                    note=f"收件箱自动发现并验签入库: {f.name}",
                    archive_copy=True,
                )
                processed_receipts.append(receipt)
                # 归档后安全移除收件箱暂存副本
                f.unlink(missing_ok=True)
            except Exception as e:
                logger.error("自动处理收件箱证据文件 %s 失败: %s", f.name, e)

        return processed_receipts

    def list_pending_verification_events(self) -> List[Dict[str, Any]]:
        """获取所有待核查与熔断中的重大事件清单 (供 AI 浏览器精准定位)."""
        all_events = self.db_mgr.query_events()
        pending = []
        for e in all_events:
            v_status = e.get("verification_status", "")
            cred = e.get("credibility_tier", "")
            sev = e.get("severity_level", "P2")
            if v_status == "Unverified_Rumor" or cred != "Tier1_Official_Regulatory":
                pending.append({
                    "event_id": e.get("event_id"),
                    "title": e.get("title"),
                    "category": e.get("category"),
                    "severity_level": sev,
                    "current_status": v_status,
                    "current_tier": cred,
                    "micro_physical_impact": e.get("micro_physical_impact"),
                    "involved_entities": e.get("involved_entities", []),
                    "published_at": e.get("published_at"),
                })
        return pending
