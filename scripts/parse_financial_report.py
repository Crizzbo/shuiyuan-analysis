"""本地原始财报转标准事实并追加至财务 staging；不联网、不读取密钥。"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from financial_reporting.pipeline import local, run, store, metric_batch

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('--metric-output',help='导出软件年度营业利润率输入，项目内新文件')
    parser.add_argument('--period-end')
    parser.add_argument('--as-of')
    parser.add_argument('--validate-taxonomy',action='store_true',help='使用官方本地分类标准及 Arelle 完整离线校验')
    args=parser.parse_args()
    report=run(json.loads(local(args.plan).read_text(encoding='utf-8')),full_taxonomy=args.validate_taxonomy)
    summary=store(report)
    if args.metric_output:
        batch=metric_batch(report,args.period_end,args.as_of)
        target=local(args.metric_output)
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as out:
            out.write(json.dumps(batch,ensure_ascii=False,indent=2)+'\n')
        summary['metric_output']=args.metric_output
    print(json.dumps({k:v for k,v in summary.items() if k!='checks'}|{'checks_by_status':{s:sum(c['status']==s for c in summary['checks']) for s in ['passed','failed','incomplete']}},ensure_ascii=False,indent=2))
