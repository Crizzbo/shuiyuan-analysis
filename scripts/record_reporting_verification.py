"""锁定当前真实解析快照与项目内依赖版本，不修改历史报告记录。"""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.pipeline import digest

directory=ROOT/'third_party/reporting';directory.mkdir(parents=True,exist_ok=True)
records=[]
for name in ['arelle-release','lxml','pymupdf','pandas','financetoolkit','jsonschema']:
    dist=metadata.distribution(name)
    records.append({'name':name,'version':dist.version,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                    'purpose':'本地财报解析/契约校验/计算，不调用行情或财报 API'})
    for file in dist.files or []:
        if str(file).endswith(('LICENSE.md','COPYING','LICENSE.txt')) and '.dist-info/' in str(file):
            source=Path(dist.locate_file(file)).resolve()
            if source.is_relative_to(ROOT):
                # 许可证按原文纯文本保存，避免被知识库 Markdown 链接校验误认为业务引用。
                filename=name+'-'+source.name
                if filename.endswith('.md'):
                    filename=filename[:-3]+'.txt'
                shutil.copyfile(source,directory/filename)
(directory/'dependencies.json').write_text(json.dumps({'dependencies':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with sqlite3.connect(ROOT/'data/financial/reports.sqlite3') as db:
    results=[]
    for report_id in ['intu-2026-10k-v1','sony-2026-20f-v1','nintendo-2026-annual-v1']:
        row=db.execute('SELECT snapshot_path,sha256 FROM reports WHERE report_id=? ORDER BY rowid DESC LIMIT 1',(report_id,)).fetchone()
        raw=(ROOT/row[0]).read_bytes()
        if digest(raw)!=row[1]:
            raise ValueError('报告快照摘要不匹配')
        report=json.loads(raw)
        results.append({'report_id':report_id,'snapshot_path':row[0],'sha256':row[1],
                        'entity_id':report['entity_id'],'fact_count':len(report['facts']),
                        'calculations_computed':sum(x['status']=='computed' for x in report['calculations']),
                        'checks_by_status':{s:sum(x['status']==s for x in report['checks']) for s in ['passed','failed','incomplete']},
                        'parser_issues':report['issues'],'release_status':report['release_status'],
                        'taxonomy_validation':report.get('taxonomy_validation',{'status':'not_run'})})
(ROOT/'data/financial/verification.json').write_text(json.dumps({'schema_version':'1.0.0','reports':results,
  'boundary':'真实财报解析快照；正式 facts 登记见 research-facts-verification.json；不代表六步研究已完成'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
