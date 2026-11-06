"""同步时间契约的中文名称与业务释义；不改写研究历史。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name,key in [('schema-field-meanings.json','meanings'),('schema-field-names.json','names_zh')]:
    p=ROOT/'schemas'/name;s=json.loads(p.read_text(encoding='utf-8'))
    s.update(document_version='1.5.0',schema_version='1.1.0')
    for prefix in ['evidence','source_manifest']:
        if key=='names_zh':
            s[key][prefix+'.published_at']='精确发布时间'
            s[key][prefix+'.published_date']='发布日期'
            s[key][prefix+'.publication_precision']='发布时间精度'
        else:
            s[key][prefix+'.published_at']='原始资料的精确发布时间，必须带时区；1.0.0 不允许为空，1.1.0 在仅日期或未知时填 null，不得补造午夜。'
            s[key][prefix+'.published_date']='官方资料显示的发布日期，或精确发布时间在其原时区内的日期；1.1.0 必须出现键，未知填 null。仅日期不证明该日任意时刻已经可得。'
            s[key][prefix+'.publication_precision']='instant 有已核实的精确时刻；date 仅有日期，published_at 必须 null；unknown 两者均未知且为空。1.1.0 必填，与登记资料版本保持一致。'
    if key=='meanings':
        for prefix in ['research','source_manifest']:
            s[key][prefix+'.schema_version']='数据契约版本，支持 1.0.0 与 1.1.0；新版保留发布日期精度，不表示步骤或软件版本。'
    p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
