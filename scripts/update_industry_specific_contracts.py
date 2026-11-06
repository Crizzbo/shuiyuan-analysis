"""将专属采集规格接入已有指标设计契约；保留旧版，不把设计升级当实测完成。"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    path=ROOT/'knowledge/contracts/metric-definitions.json'
    original=path.read_bytes()
    data=json.loads(original)
    specs={s['parent_metric_id']:s for s in json.loads((ROOT/'knowledge/metrics/industry-specifications.json').read_text(encoding='utf-8'))['specifications']}
    changed=False
    for definition in data['definitions']:
        if definition['metric_id'] not in specs:
            continue
        s=specs[definition['metric_id']]
        ref={'source_path':'knowledge/metrics/industry-specifications.json','locator':'specifications[parent_metric_id='+s['parent_metric_id']+']','source_kind':'project_design'}
        if ref in definition['source_refs']:
            continue
        changed=True
        definition['inputs']=s['required_inputs_zh']
        definition['formula']=s['business_definition_zh'] if s['value_kind']=='scalar' else '按原子字段分别保存；不合并为未经定义的数值；详见行业专属规格及原子字段字典'
        definition['denominator']='按来源和原子字段确定；事件、金额和存量无通用分母'
        definition['comparability_notes']=s['comparability_rules_zh']
        definition['source_requirements']=['发行人年报及经营指标补充表；需要时使用监管原文、客户财报或官方行业统计','按原子字段绑定具体公司分部、单位、期间、时点可得证据；复合项必须分别登记']
        definition['source_refs'].append(ref)
        definition['blocking_reasons']=['已补齐原子采集规格；父驱动仍为多口径容器，须选择证券实际适用原子项及具体单位','缺失原文或口径不匹配的字段继续阻断；真实样本不等于全部驱动完成']
        # 父驱动 context_defined 不能伪装成已统一单位的单一计算指标。
        definition['definition_status']='needs_definition'
    if changed:
        history=ROOT/'knowledge/contracts/history'
        history.mkdir(exist_ok=True)
        backup=history/f'metric-definitions.r{data["revision"]}.json'
        if backup.exists() and backup.read_bytes()!=original:
            raise ValueError('旧知识版本已存在且字节冲突，禁止覆盖')
        if not backup.exists():
            backup.write_bytes(original)
        data['revision']+=1
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    discovery=json.loads((ROOT/'knowledge/metrics/representative-source-discovery.json').read_text(encoding='utf-8'))['sources']
    reps_path=ROOT/'knowledge/metrics/representatives.json'
    reps=json.loads(reps_path.read_text(encoding='utf-8'))
    verification=json.loads((ROOT/'data/financial/industry-specific-verification.json').read_text(encoding='utf-8'))
    samples=json.loads((ROOT/verification['snapshot_path']).read_text(encoding='utf-8'))
    sampled={o['industry_id'] for o in samples['observations']}
    for r in reps['representatives']:
        r['source_discovery_refs']=[{'source_path':'knowledge/metrics/representative-source-discovery.json','locator':'sources.'+r['industry_id']}]
        r['original_review_status']='sample_excerpt_registered_full_driver_review_pending' if r['industry_id'] in sampled else 'pending_full_original_metric_review'
    reps_path.write_text(json.dumps(reps,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    jobs=[]
    input_path=ROOT/'data/financial/industry-driver-input-verification.json'
    input_drivers={}
    if input_path.exists():
        from financial_reporting.industry_inputs import verify_ledger
        input_index=json.loads(input_path.read_text(encoding='utf8'))
        ledger=verify_ledger(json.loads((ROOT/input_index['snapshot_path']).read_text(encoding='utf8')))
        if ledger['observation_snapshot_path']!=verification['snapshot_path']:
            raise ValueError('输入台账未更新到本次观测版本')
        input_drivers={d['parent_metric_id']:d for d in ledger['drivers']}
    for s in specs.values():
        row=next(c for c in samples['coverage'] if c['parent_metric_id']==s['parent_metric_id'])
        jobs.append({'industry_id':s['industry_id'],'representative':next(r['name'] for r in reps['representatives'] if r['industry_id']==s['industry_id']),'parent_metric_id':s['parent_metric_id'],'name_zh':s['name_zh'],'source_candidate_url':discovery[s['industry_id']],'required_inputs_zh':s['required_inputs_zh'],'status':row['status'],'sample_observation_ids':row['observation_ids'],'research_gate':'blocked','next_action_zh':'AI 浏览器打开官方原文，按逐行业字典核验每个必需字段；不披露仅记录该份材料范围内缺口，不推断全部公开来源均缺失'})
        if s['parent_metric_id'] in input_drivers:
            driver=input_drivers[s['parent_metric_id']]
            jobs[-1].update(input_status=driver['input_status'],definition_status=driver['definition_status'],calculation_ready=driver['calculation_ready'],missing_inputs_zh=[slot['name_zh'] for slot in driver['slots'] if slot['status']=='missing'],input_ledger_ref=input_index['snapshot_path'])
    (ROOT/'data/browser-search/industry-specific-jobs.json').write_text(json.dumps({'schema_version':'1.0.0','not_an_automated_collector':True,'jobs':jobs},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'contract_revision':data['revision'],'representatives':len(reps['representatives']),'browser_jobs':len(jobs)},ensure_ascii=False))

if __name__=='__main__':
    main()
