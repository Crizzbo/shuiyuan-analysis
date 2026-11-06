"""经完整校验后登记正式财务事实；使用现有追加式资料目录。"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from financial_reporting.registry import register,read_as_of,registered_metric_batch
from financial_reporting.pipeline import local
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',nargs='?');p.add_argument('--entity');p.add_argument('--as-of')
    p.add_argument('--metric-output');p.add_argument('--period-end')
    a=p.parse_args()
    if a.entity:
        if not a.as_of:p.error('查询须指定 --as-of')
        if a.metric_output:
            if not a.period_end:p.error('指标导出须指定 --period-end')
            batch=registered_metric_batch(a.entity,a.period_end,a.as_of)
            with local(a.metric_output).open('x',encoding='utf-8') as out:
                out.write(json.dumps(batch,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({'metric_output':a.metric_output},ensure_ascii=False))
        else:
            print(json.dumps(read_as_of(a.entity,a.as_of),ensure_ascii=False,indent=2))
    else:
        if not a.plan:p.error('须提供解析配置')
        r=register(a.plan)
        print(json.dumps({k:v for k,v in r.items() if k not in ['registration_ids','report_ref']}|{'snapshot_path':r['report_ref']['snapshot_path']},ensure_ascii=False,indent=2))
