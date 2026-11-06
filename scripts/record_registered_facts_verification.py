"""核对正式事实，并生成可复现验收索引；不修改历史资料或事实。"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.registry import read_as_of,registered_metric_batch
from data_store import now
from finance_tools.metric_pipeline import run_batch
as_of=now()
rows=[]
for entity in ['US:INTU:CIK896878','JP:6758:CIK313838','JP:7974']:
    facts=read_as_of(entity,as_of)
    rows.append({'entity_id':entity,'fact_count':len(facts),'report_refs':list({p['report_ref']['sha256']:p['report_ref'] for p in facts}.values()),
                 'registration_ids':[p['registration_id'] for p in facts]})
batch=registered_metric_batch('US:INTU:CIK896878','2026-07-31',as_of)
result=run_batch(batch)
data={'schema_version':'1.0.0','query_as_of':as_of,'reports':rows,'active_fact_count':sum(r['fact_count'] for r in rows),
 'before_first_observation_count':len(read_as_of('JP:7974','2026-07-07T00:00:00+09:00')),
 'registered_calculation':result,
 'boundary':'正式报表事实 source_verified；不等于六步判断、行业指标全覆盖或审计意见'}
(ROOT/'data/financial/research-facts-verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in data.items() if k not in ['reports','registered_calculation']},ensure_ascii=False,indent=2))
