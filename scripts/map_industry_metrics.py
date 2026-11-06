"""正式事实映射行业观测；输出新内容快照，不修改原研究。"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from financial_reporting.industry_mapping import map_industry
from financial_reporting.pipeline import save_object
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ['entity','industry','period-end','as-of']:p.add_argument('--'+field,required=True)
    p.add_argument('--scope',default='consolidated');p.add_argument('--report-id')
    a=p.parse_args();r=map_industry(a.entity,a.industry,a.period_end,a.as_of,a.scope,a.report_id)
    path,sha=save_object(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False).encode(),'json')
    print(json.dumps({'snapshot_path':path,'sha256':sha,'computed':len(r['observations']),
                     'missing_required_metric_ids':r['missing_required_metric_ids'],'industry_gate_status':r['industry_gate_status']},ensure_ascii=False,indent=2))
