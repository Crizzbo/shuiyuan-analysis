"""真实三公司行业候选样板及全行业缺口清单；不自动确认行业归类。"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from financial_reporting.industry_mapping import map_industry,BINDINGS,SPECIAL
from financial_reporting.pipeline import save_object
from data_store import now
index=[]
for entity,industry,end,scope in [('US:INTU:CIK896878','software','2026-07-31','consolidated'),
 ('JP:6758:CIK313838','hardware','2026-03-31','consolidated_continuing'),('JP:7974','media_entertainment','2026-03-31','consolidated')]:
    r=map_industry(entity,industry,end,now(),scope)
    path,sha=save_object(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2).encode(),'json')
    index.append({'entity_id':entity,'industry_candidate':industry,'snapshot_path':path,'sha256':sha,
                  'computed':len(r['observations']),'missing_required_metric_ids':r['missing_required_metric_ids']})
coverage=[]
for p in sorted((ROOT/'knowledge/contracts/industries').glob('*.json')):
    industry=json.loads(p.read_text(encoding='utf-8'))
    coverage.append({'industry_id':p.stem,'bound_shared_metric_ids':[] if p.stem in SPECIAL else list(BINDINGS),
                     'blocked_required_metric_ids':industry['required_metric_ids'],
                     'reason':'专门口径未审核' if p.stem in SPECIAL else '行业驱动字段绑定与原始输入尚不完整'})
(ROOT/'data/financial/industry-mapping-verification.json').write_text(json.dumps({'examples':index,'industry_coverage':coverage},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(index,ensure_ascii=False,indent=2))
