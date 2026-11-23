# -*- coding: utf-8 -*-
"""存量事件雷达数据库全息买方研判与微观因果提纯补全脚本.

用途：
对 data/ledger/event_radar.sqlite3 数据库中的历史事件进行全息扫描与重新提炼：
1. 识别 8-K / 10-K / 10-Q 等官方文件，提取 Item 并生成结构化中文买方解读；
2. 关联 CIK -> 真实上市 Ticker，赋予即时下钻与 DCF 估值穿透能力；
3. 提取央行/科技巨头公报事实，杜绝 micro_physical_impact == title 机械文字；
4. 保证更新操作具备幂等性与事务原子性。
"""

import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.events_and_verification.event_distillation_engine import EventDistillationEngine


def enrich_event_radar_database(db_path: Path) -> int:
    if not db_path.exists():
        print(f"[跳过] 数据库不存在: {db_path}")
        return 0

    engine = EventDistillationEngine(ROOT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute("SELECT * FROM radar_events").fetchall()
    updated_count = 0

    for r in rows:
        row_d = dict(r)
        event_id = row_d["event_id"]
        title = row_d.get("title", "")
        raw_content = row_d.get("raw_content", "") or ""
        source = row_d.get("source_name", "") or ""
        curr_impact = row_d.get("micro_physical_impact", "")

        # 如果没有提炼过，或与标题相同，或者标题包含 8-K 却未解析 items
        needs_enrich = False
        if not curr_impact or curr_impact == title:
            needs_enrich = True
        elif "8-K" in title and "Item" not in curr_impact:
            needs_enrich = True

        if needs_enrich:
            distilled = engine.distill_single_event(
                title=title,
                content=raw_content,
                source=source,
                fallback_category=row_d.get("category", "Other_Macro_Event"),
            )
            new_impact = distilled["micro_physical_impact"]
            new_entities = json.dumps(distilled["involved_entities"], ensure_ascii=False)
            new_segments = json.dumps(distilled["affected_business_segments"], ensure_ascii=False)
            new_severity = distilled["severity_level"]
            new_duration = distilled["estimated_duration"]
            new_category = distilled["category"]

            cur.execute(
                """
                UPDATE radar_events
                SET micro_physical_impact = ?,
                    involved_entities = ?,
                    affected_business_segments = ?,
                    severity_level = ?,
                    estimated_duration = ?,
                    category = ?
                WHERE event_id = ?
                """,
                (new_impact, new_entities, new_segments, new_severity, new_duration, new_category, event_id),
            )
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"[完成] 扫描 {len(rows)} 条事件，已全息提纯并更新 {updated_count} 条事件研判解读！")
    return updated_count


if __name__ == "__main__":
    db_file = ROOT / "data" / "ledger" / "event_radar.sqlite3"
    enrich_event_radar_database(db_file)
