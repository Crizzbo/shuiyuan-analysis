"""行业与指标口径契约的离线结构及引用检查；不判断经济结论真假。"""
import argparse
import hashlib
from validate_research import load, check_schema, structural, need
from validate_knowledge_structure import ROOT, local_file

DIMENSIONS = {'lifecycle','supply_demand','earnings','credit','sentiment','pricing'}

def validate(data, kind):
    schema_path = 'schemas/industry-knowledge.schema.json' if kind == 'industry' else 'schemas/metric-definition.schema.json'
    schema = load(ROOT/schema_path)
    check_schema(schema,schema)
    structural(data,schema,schema)
    catalog = {m['id']:m for m in load(ROOT/'knowledge/metrics/catalog.json')['metrics']}
    models = {m['id'] for m in load(ROOT/'knowledge/taxonomy/business_models.json')['models']}
    def sources(items):
        for item in items:
            local_file(ROOT,item['source_path'])
    if kind == 'industry':
        industries = {n['id']:n for n in load(ROOT/'knowledge/taxonomy/industries.json')['nodes'] if n['level']=='industry'}
        need(data['industry_id'] in industries,'行业必须为 industry 节点')
        need(set(data['business_model_ids']) <= models and data['business_model_ids'],'商业模式未登记或为空')
        need(set(data['required_metric_ids']) <= set(catalog) and data['required_metric_ids'],'行业指标未登记或为空')
        need({d['dimension_id'] for d in data['dimensions']} == DIMENSIONS,'六维度缺失或重复')
        need(data['research_gate']['required_steps'] == ['S1','S2','S3','S4','S5','S6'],'真实研究步骤不可跳过或乱序')
        for d in data['dimensions']:
            need(set(d['required_metric_ids']) <= set(catalog),'维度指标未登记')
        for route in data['valuation_routes']:
            need(route['business_model_ids'] and set(route['business_model_ids']) <= set(data['business_model_ids']), '估值模式不属于该行业候选模式')
        sources(data['source_refs'])
        if data['external_reference_status'] == 'project_copy_reviewed':
            need(any(s['source_path'].startswith('knowledge/sources/cat_reference/') for s in data['source_refs']), '声称已核对猫哥资料但无项目内副本引用')
    else:
        entries = data['definitions']
        need(len({m['metric_id'] for m in entries}) == len(entries),'指标口径重复')
        for m in entries:
            need(m['metric_id'] in catalog,'口径指标未登记')
            need(m['unit'] == catalog[m['metric_id']]['unit'],'口径单位与原指标字典冲突')
            sources(m['source_refs'])
            if m['definition_status'] == 'specified':
                need(m['formula'] is not None and m['inputs'] and m['denominator'] is not None, '已定义口径缺公式、输入或分母说明')
                need(m['unit'] != 'context_defined' and not m['blocking_reasons'],'已定义口径仍有单位或阻断缺口')
            else:
                need(m['blocking_reasons'],'未定义口径必须记录阻断原因')

def validate_all():
    metric_data = load(ROOT/'knowledge/contracts/metric-definitions.json')
    validate(metric_data,'metrics')
    catalog_ids = {m['id'] for m in load(ROOT/'knowledge/metrics/catalog.json')['metrics']}
    need({m['metric_id'] for m in metric_data['definitions']} == catalog_ids,'指标契约覆盖不完整')
    profiles = list((ROOT/'knowledge/contracts/industries').glob('*.json'))
    expected = {n['id'] for n in load(ROOT/'knowledge/taxonomy/industries.json')['nodes'] if n['level']=='industry'}
    seen = []
    for p in profiles:
        data = load(p)
        validate(data,'industry')
        need(p.stem == data['industry_id'],'行业文件名与 ID 不一致')
        seen.append(data['industry_id'])
    need(set(seen) == expected and len(seen)==len(expected),'行业契约覆盖不完整')
    sample = load(ROOT/'examples/industry-software.design.json')
    validate(sample,'industry')
    need(sample == load(ROOT/'knowledge/contracts/industries/software.json'),'软件样板与知识档案不一致')
    inv = ROOT/'knowledge/sources/cat_reference/import-inventory.json'
    if inv.is_file():
        for row in load(inv)['files']:
            path = local_file(ROOT,row['local_path'])
            need(hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],'参考副本哈希不符')
    print(f'PASS: {len(profiles)} industry design profiles, {len(catalog_ids)} metric specifications, software sample and reference hashes.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file',nargs='?')
    parser.add_argument('--kind',choices=['industry','metrics'],default='industry')
    args = parser.parse_args()
    if args.file:
        validate(load(local_file(ROOT,args.file)),args.kind)
        print('PASS: design structure and references; not empirical validation.')
    else:
        validate_all()
