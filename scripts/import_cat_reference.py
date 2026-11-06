"""在用户明确授权后，将四份指定参考资料原样复制入项目；不启动外部项目。"""
import csv
import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FILES = {
 'marks_notes.txt':'docs/投资最重要的事_学习笔记.md',
 'industry_cycle_notes.txt':'docs/第8章_景气度_精读笔记.md',
 'intu_research.txt':'docs/财捷INTU深入分析_20260814.md',
 'sp500_reference.csv':'docs/标普500全量资料库_20260820.csv',
}

def main():
    source_root = Path(r'C:\Users\shared_user\Desktop\猫哥的股票交易指南').resolve()
    dest = ROOT/'knowledge/sources/cat_reference'
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    for name, relative in FILES.items():
        source = (source_root/relative).resolve()
        if not source.is_relative_to(source_root):
            raise ValueError('来源目录越界')
        data = source.read_bytes()
        target = dest/name
        if target.exists() and target.read_bytes() != data:
            raise ValueError('导入副本已有不同内容，须新建版本')
        target.write_bytes(data)
        records.append({'local_path':target.relative_to(ROOT).as_posix(), 'origin_relative_path':relative,
            'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data),
            'source_kind':'secondary', 'available_at':None, 'published_at':None,
            'review_status':'reference_only_pending_primary_verification'})
    rows = list(csv.DictReader(io.StringIO((dest/'sp500_reference.csv').read_text(encoding='utf-8-sig'))))
    sectors = {}
    for row in rows:
        sectors[row.get('行业','')] = sectors.get(row.get('行业',''),0)+1
    manifest = {'manifest_kind':'reference_import_inventory_not_source_manifest',
        'acquired_at':datetime.now(timezone.utc).isoformat(),
        'origin_directory_label':'用户授权的猫哥股票交易指南目录', 'files':records,
        'csv_rows':len(rows),'csv_columns':list(rows[0]) if rows else [], 'sector_row_counts':sectors,
        'limitations':['行数不是独立公司数，可能含同公司不同证券',
            '日期来自文件名或报告文本，不等于已核实的 published_at/available_at',
            '现价、分析师目标价及旧折现结果均未核验，不能据此完成 S4 或进行历史回测',
            '此清单不是 source-manifest.schema 实例，实际观测需按资料治理接口登记']}
    (dest/'import-inventory.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Copied {len(records)} reference files, SHA256 verified; CSV {len(rows)} rows.')

if __name__ == '__main__':
    main()
