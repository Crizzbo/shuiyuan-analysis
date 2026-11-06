"""把带正式来源映射的指标观测追加到六步研究新修订；保持待审核状态。"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from financial_reporting.pipeline import local,digest
from data_store import LocalStore,now,destination
from validate_research import validate
from financial_reporting.industry_mapping import verify_mapping

def attach(mapping_path,research_id,output):
    mapping=json.loads(local(mapping_path).read_text(encoding='utf-8'))
    verify_mapping(mapping)
    c=LocalStore()
    try:
        record=c.get_research(research_id)
        if record['subject']['company_id']!=mapping['entity_id']:raise ValueError('映射公司与研究不同')
        if any(s['status']!='pending' for s in record['steps']):raise ValueError('已经开展的研究须按失效重审流程接入，禁止自动改写判断')
        timestamp=now();record.update(revision=record['revision']+1,as_of=mapping['as_of'],recorded_at=timestamp)
        record['observations']=mapping['observations'];record['evidence']=mapping['evidence'];record['calculations']=[]
        links=dict(mapping['source_map'])
        eid='mapping-execution-'+digest(local(mapping_path).read_bytes())
        # 计算执行记录为项目材料，不冒充原始公司事实；原始证据仍独立绑定。
        source={'schema_version':'1.1.0','source_id':eid,'revision':1,'source_path':mapping_path,'source_kind':'project_design',
          'dataset_kind':'research_material','published_at':timestamp,'published_date':timestamp[:10],'publication_precision':'instant',
          'available_at':timestamp,'acquired_at':timestamp,'effective_period':None,'license_notes':'项目内计算执行记录',
          'quality_notes':['记录输入正式登记标识、公式、开源库版本及观测输出；不充当公司原始事实。'],'supersedes_revision':None}
        c.register_source(source)
        record['evidence'].append({'id':eid,'source_path':mapping_path,'locator':'mapping_results / observations / calculation_refs / lineage',
          'source_kind':'project_design','published_at':timestamp,'published_date':timestamp[:10],'publication_precision':'instant',
          'available_at':timestamp,'acquired_at':timestamp,'excerpt_or_summary':'正式财务事实映射执行结果，含指标值、计算材料及来源版本。',
          'limitations':['执行核对不表示公司分类复核、阈值验证或六步完成。']})
        links[eid]={'source_id':eid,'revision':1}
        # 当前计算以正式科目事实为输入，raw facts 没有冒充行业 observation。
        for obs in record['observations']:
            record['calculations'].append({'id':'calc-'+obs['id'],'method':'financial_fact_industry_mapping','method_version':'1.0.0',
              'implementation_path':'financial_reporting/industry_mapping.py','input_observation_refs':[],'assumption_refs':[],
              'outputs':[obs['value']],'verification_status':'unchecked','verification_evidence_refs':[eid]})
        # 执行证明进入新研究的截止时点，避免把刚形成的项目材料放进更早研究。
        from validate_research import instant
        if instant(record['as_of'])<instant(timestamp):record['as_of']=timestamp
        for step in record['steps']:
            step['updated_at']=timestamp
            step['notes'].append('已接入 '+str(len(record['observations']))+' 项财务指标观测；必需行业指标缺口：'+','.join(mapping['missing_required_metric_ids']))
        validate(record)
        target=destination(output);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as out:out.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        with target.with_suffix('.sources.json').open('x',encoding='utf-8') as out:out.write(json.dumps(links,ensure_ascii=False,indent=2)+'\n')
        return c.save_research(record,links)
    finally:c.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mapping');p.add_argument('--research-id',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(attach(a.mapping,a.research_id,a.output),ensure_ascii=False,indent=2))
