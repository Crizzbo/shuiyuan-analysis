"""把正式财报证据接入真实六步待分析草稿；不生成行业判断或自动完成步骤。"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from financial_reporting.registry import read_as_of
from data_store import LocalStore,now
from validate_research import validate

def build():
    target=ROOT/'data/financial/research-drafts/intu-2026-evidence-v1.json'
    if target.exists():
        # 明确读取已有修订，禁止用新的观察时刻覆盖旧输入。
        record=json.loads(target.read_text(encoding='utf-8'))
        mapping=json.loads(target.with_suffix('.sources.json').read_text(encoding='utf-8'))
        catalog=LocalStore()
        try:print(json.dumps(catalog.save_research(record,mapping),ensure_ascii=False,indent=2))
        finally:catalog.close()
        return
    timestamp=now()
    facts=read_as_of('US:INTU:CIK896878',timestamp)
    if not facts:raise ValueError('缺正式 Intuit 财报事实')
    record=json.loads((ROOT/'knowledge/templates/research.pending.json').read_text(encoding='utf-8'))
    record.update(schema_version='1.1.0',research_id='intu-2026-financial-evidence-draft',revision=1,
                  is_fictional=False,as_of=timestamp,recorded_at=timestamp)
    record['subject'].update(company_id='US:INTU:CIK896878',security_ids=['US:INTU'],classification_status='unreviewed')
    segment=record['subject']['segments'][0]
    segment.update(name='公司整体临时分析范围',subindustry_description='软件/订阅为原有计算绑定的待审核分类占位；真实分部及商业模式需另行取证。')
    record.update(evidence=[],observations=[],claims=[],calculations=[])
    mapping={}
    catalog=LocalStore()
    try:
        # 合并相同证据文本，保留事实节点定位；以 sources 正式版本绑定原文。
        for p in facts:
            f=p['fact']
            if f['period']['end']!='2026-07-31' or f['period']['basis']!='annual' or f['field'] not in ('revenue','operating_income'):
                continue
            link=p['evidence_source'];s=f['source'];eid='registered-'+f['id']
            source=json.loads(catalog.db.execute('SELECT manifest_json FROM sources WHERE source_id=? AND revision=?',
                                                (link['source_id'],link['revision'])).fetchone()[0])
            record['evidence'].append({'id':eid,'source_path':s['path'],'locator':s['locator'],'source_kind':s['kind'],
              'published_at':s['published_at'],'published_date':source['published_date'],'publication_precision':source['publication_precision'],
              'available_at':s['available_at'],'acquired_at':source['acquired_at'],'excerpt_or_summary':s['excerpt'],
              'limitations':['来自已登记财报的派生原文证据；原 ZIP 版本及解析执行材料由正式事实登记追溯。',
                              '仅核实发布日期，研究可得时点采用本项目首次实际观察；行业分类及六步分析未完成。']})
            mapping[eid]={k:link[k] for k in ['source_id','revision']}
        if len(record['evidence'])!=2:raise ValueError('缺唯一年度收入与营业利润证据')
        for step in record['steps']:
            step.update(updated_at=timestamp)
            step['notes']=['已接入正式财报证据；尚未开始本步骤分析。']
        validate(record)
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as out:out.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        mapping_path=target.with_suffix('.sources.json')
        with mapping_path.open('x',encoding='utf-8') as out:out.write(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
        result=catalog.save_research(record,mapping)
        print(json.dumps(result|{'input_path':target.relative_to(ROOT).as_posix(),'evidence_count':len(record['evidence'])},ensure_ascii=False,indent=2))
    finally:catalog.close()

if __name__=='__main__':build()
