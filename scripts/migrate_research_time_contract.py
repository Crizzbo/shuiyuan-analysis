"""显式升级研究时间契约：输出新修订；旧研究及已完成判断不自动覆盖或认可。"""
import argparse,copy,json
from data_store import now
from validate_knowledge_structure import ROOT,local_file
from validate_research import validate,load

def migrate(record,timestamp=None):
    validate(record)
    if record['schema_version']!='1.0.0':raise ValueError('只迁移 1.0.0，避免重复增加修订')
    if record['invalidation_events']:
        raise ValueError('含失效事件的研究须结合事件历史人工迁移；本入口不改写事件')
    result=copy.deepcopy(record);timestamp=timestamp or now()
    result.update(schema_version='1.1.0',revision=record['revision']+1,recorded_at=timestamp)
    from validate_research import instant
    for e in result['evidence']:
        e.update(publication_precision='instant',published_date=instant(e['published_at']).date().isoformat())
    for step in result['steps']:
        if step['status']!='pending':
            step.update(version=step['version']+1,status='invalidated',updated_at=timestamp)
            step['notes'].append('时间契约升级；原输出仅为历史，须重审后按原流程重新完成。')
    for step in result['steps']:
        for dep in step['inputs']['dependencies']:
            dep['version']=result['steps'][int(dep['step_id'][1:])-1]['version']
    validate(result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output');a=p.parse_args()
    result=migrate(load(local_file(ROOT,a.input)))
    from data_store import destination
    target=destination(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as out:out.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':a.output,'revision':result['revision'],'schema_version':result['schema_version']},ensure_ascii=False))
