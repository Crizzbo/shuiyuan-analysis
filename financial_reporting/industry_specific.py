"""行业专属原文样本登记：只读项目摘录，严格区分原文、转换和数据缺口。"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
import json
import sys
from .pipeline import ROOT, local, digest, save_object
sys.path.insert(0, str(ROOT/'scripts'))
from data_store import LocalStore, canonical, now
from validate_research import instant

# 经过本次浏览器核验的原子绑定；不允许把任意数字绑定为任意行业驱动。
BINDINGS = {
 'rig_day_utilization': ('energy_services_driver_1','ratio'),
 'actual_daily_revenue': ('energy_services_driver_3','USD_per_operating_day'),
 'gas_processing_inlet_daily_volume': ('midstream_driver_1','Bcf_per_day'),
 'sustaining_capex': ('midstream_driver_3','USD'),
 'home_order_cancellation_rate': ('housing_durables_driver_1','ratio'),
 'homes_closed': ('housing_durables_driver_2','homes'),
 'da_vinci_placements': ('medical_devices_driver_2','systems'),
 'da_vinci_installed_base': ('medical_devices_driver_2','systems'),
 'system_unit_case_volume_growth': ('food_beverage_driver_1','ratio'),
 'price_mix_contribution': ('food_beverage_driver_2','ratio'),
 'family_daily_active_people': ('digital_platforms_driver_1','people'),
 'net_client_flows': ('asset_management_driver_1','USD'),
 'reported_pc_combined_ratio': ('insurance_driver_1','ratio'),
 'favorable_prior_period_reserve_development': ('insurance_driver_2','USD'),
 'global_comparable_sales_growth': ('restaurants_driver_1','ratio'),
}
RAW_UNITS = {
 'rig_day_utilization':'percent','actual_daily_revenue':'USD_per_operating_day',
 'gas_processing_inlet_daily_volume':'Bcf_per_day','sustaining_capex':'USD_million',
 'home_order_cancellation_rate':'percent','homes_closed':'homes',
 'da_vinci_placements':'systems','da_vinci_installed_base':'systems',
 'system_unit_case_volume_growth':'qualitative_zero_growth','price_mix_contribution':'percent',
 'family_daily_active_people':'billion_people','net_client_flows':'USD_billion',
 'reported_pc_combined_ratio':'percent','favorable_prior_period_reserve_development':'USD_million',
 'global_comparable_sales_growth':'percent',
}

# 追加批次使用显式项目路径，不扫描目录、不访问网络。
BUNDLE_PATHS = [
 'data/browser-search/industry-specific-reviewed-excerpts.json',
 'data/browser-search/industry-specific-supplemental-excerpts.json',
 'data/browser-search/industry-specific-expansion-20261011.json',
 'data/browser-search/industry-driver-inputs-20261011b.json',
 'data/browser-search/content-amortization-reviewed-20261011.json',
 'data/browser-search/telecom-reviewed-20261012.json',
 'data/browser-search/insurance-reviewed-20261012.json',
 'data/browser-search/batch20261012-reviewed.json',
 'data/browser-search/batch20261012b-reviewed.json',
 'data/browser-search/batch20261012c-reviewed.json',
 'data/browser-search/batch20261012d-reviewed.json',
 'data/browser-search/batch20261012e-reviewed.json',
 'data/browser-search/batch20261012f-reviewed.json',
 'data/browser-search/batch20261012g-reviewed.json',
 'data/browser-search/batch20261012h-reviewed.json',
 'data/browser-search/batch20261012i-reviewed.json',
 'data/browser-search/batch20261012j-reviewed.json',
 'data/browser-search/batch20261012k-reviewed.json',
]
REVIEWED_BINDINGS = {}
_binding_items=[]
for _binding_path in ('knowledge/metrics/industry-reviewed-bindings-20261011.json','knowledge/metrics/industry-reviewed-bindings-20261011b.json','knowledge/metrics/content-amortization-reviewed-binding.json','knowledge/metrics/telecom-reviewed-bindings-20261012.json','knowledge/metrics/insurance-reviewed-bindings-20261012.json','knowledge/metrics/batch20261012-reviewed-bindings.json','knowledge/metrics/batch20261012b-reviewed-bindings.json','knowledge/metrics/batch20261012c-reviewed-bindings.json','knowledge/metrics/batch20261012d-reviewed-bindings.json','knowledge/metrics/batch20261012e-reviewed-bindings.json','knowledge/metrics/batch20261012f-reviewed-bindings.json','knowledge/metrics/batch20261012g-reviewed-bindings.json','knowledge/metrics/batch20261012h-reviewed-bindings.json','knowledge/metrics/batch20261012i-reviewed-bindings.json','knowledge/metrics/batch20261012j-reviewed-bindings.json','knowledge/metrics/batch20261012k-reviewed-bindings.json'):
    _binding_items.extend(json.loads(local(_binding_path).read_text(encoding='utf-8'))['bindings'])
for _item in _binding_items:
    _key=_item['component']
    if _key in BINDINGS or _key in REVIEWED_BINDINGS or not _item['name_zh']:
        raise ValueError('追加审核绑定重复或缺中文名称')
    REVIEWED_BINDINGS[_key]=_item
    BINDINGS[_key]=(_item['parent_metric_id'],_item['unit'])
    RAW_UNITS[_key]=_item['raw_unit']

def verify_specs():
    """检查全行业覆盖、父驱动含义及来源候选；不把采集设计当作实测数据。"""
    specs=json.loads(local('knowledge/metrics/industry-specifications.json').read_text(encoding='utf-8'))['specifications']
    reps=json.loads(local('knowledge/metrics/representatives.json').read_text(encoding='utf-8'))['representatives']
    catalog={m['id']:m for m in json.loads(local('knowledge/metrics/catalog.json').read_text(encoding='utf-8'))['metrics'] if '_driver_' in m['id']}
    from jsonschema import Draft202012Validator
    schema=json.loads(local('schemas/industry-specific-specifications.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema).validate({'schema_version':'1.0.0','specifications':specs})
    ids=[s['parent_metric_id'] for s in specs]
    if len(ids)!=len(set(ids)) or set(ids)!=set(catalog):
        raise ValueError('专属规格须完整且无重复地覆盖父驱动')
    industries={p.stem for p in (ROOT/'knowledge/contracts/industries').glob('*.json')}
    if len(reps)!=len(industries) or {r['industry_id'] for r in reps}!=industries:
        raise ValueError('代表公司覆盖缺失或重复')
    discovery=json.loads(local('knowledge/metrics/representative-source-discovery.json').read_text(encoding='utf-8'))['sources']
    if set(discovery)!=industries:
        raise ValueError('官方来源候选覆盖不全')
    for s in specs:
        if s['business_definition_zh']!=catalog[s['parent_metric_id']]['definition']:
            raise ValueError('父驱动业务定义漂移')
        if not s['parent_metric_id'].startswith(s['industry_id']+'_driver_'):
            raise ValueError('行业与驱动不匹配')
        if s['unit'] in ('components','event_records','scenario') and s['value_kind']!=s['unit']:
            raise ValueError('复合或事件对象不能声明为单一数值')
        if s['numeric_threshold'] is not None:
            raise ValueError('无历史验证不能启用阈值')
        components=s['component_specs']
        if len({c['component_id'] for c in components})!=len(components):
            raise ValueError('原子字段标识重复')
        if any(not c['component_id'].startswith(s['parent_metric_id']+'__') for c in components):
            raise ValueError('原子字段与父驱动错配')
        local('knowledge/metrics/industry-specific/'+s['industry_id']+'.md')
    return specs,reps,discovery

def verify_observation(source, observation, observed_at):
    """检查时间、数值转换与证据关联。经济口径依赖经过人工核验的绑定，不能自动推断。"""
    o=observation
    if BINDINGS.get(o['component'])!=(o['parent_metric_id'],o['unit']):
        raise ValueError('未经审核的专属指标绑定或单位')
    if RAW_UNITS.get(o['component'])!=o['raw_unit']:
        raise ValueError('原始披露单位与审核绑定不一致')
    if o['component'] in REVIEWED_BINDINGS:
        binding=REVIEWED_BINDINGS[o['component']]
        if any(o.get(k)!=binding[k] for k in ('name_zh','binding_role','limitation_zh')):
            raise ValueError('追加指标名称、绑定用途或业务限制与审核记录不一致')
    if not o['parent_metric_id'].startswith(source['industry_id']+'_driver_'):
        raise ValueError('事实与来源行业错配')
    end=date.fromisoformat(o['period_end'])
    if end>instant(observed_at).date():
        raise ValueError('原文样本期间晚于可得日期')
    if o['period_type']=='instant':
        if o['period_start'] is not None:
            raise ValueError('时点存量不能混入期间起点')
    elif o['period_start'] is None or date.fromisoformat(o['period_start'])>end:
        raise ValueError('期间起止错误')
    if o['period_type'] not in ('instant','annual','quarterly','monthly_average','13_weeks'):
        raise ValueError('未经定义的统计期间类型')
    if o['period_type']=='13_weeks' and (end-date.fromisoformat(o['period_start'])).days+1!=91:
        raise ValueError('十三周期间须含首尾共 91 天')
    indices=o['excerpt_indices']
    if not indices or any(type(i)!=int or i<0 or i>=len(source['excerpts']) for i in indices):
        raise ValueError('摘录索引无效')
    quote='\n'.join(source['excerpts'][i] for i in indices)
    if o['raw_value'] not in quote:
        raise ValueError('原始披露值不在引用摘录中')
    rule=o['conversion']
    required_rules={'percent':'percent_divided_by_100','USD_million':'million_times_1000000',
      'USD_billion':'billion_times_1000000000','JPY_billion':'billion_times_1000000000',
      'billion_people':'billion_times_1000000000','billion_pounds':'billion_times_1000000000',
      'billion_unit_cases':'billion_times_1000000000',
      'USD_trillion':'trillion_times_1000000000000',
      'US_cents_per_passenger_mile':'cents_divided_by_100',
      'million_passenger_miles':'million_quantity_times_1000000',
      'million_seat_miles':'million_quantity_times_1000000',
      'million_units':'million_quantity_times_1000000',
      'million_transactions':'million_quantity_times_1000000',
      'TWh':'million_quantity_times_1000000',
      'USD_thousand':'accounting_thousand_times_1000',
      'thousand_shares':'accounting_thousand_times_1000',
      'qualitative_zero_growth':'issuer_even_means_zero_growth'}
    if o['raw_unit'] in required_rules and rule!=required_rules[o['raw_unit']]:
        raise ValueError('转换规则未匹配原始单位，禁止漏乘倍数或漏换百分比')
    if o['raw_unit'] not in required_rules and rule not in ('identity','remove_thousands_separator'):
        raise ValueError('无倍数单位不能使用倍数转换')
    if rule=='issuer_even_means_zero_growth':
        if o['raw_value']!='Even' or o['raw_unit']!='qualitative_zero_growth':
            raise ValueError('非明确 Even 披露不能转换为零')
        value=Decimal(0)
    else:
        raw_text=o['raw_value'].replace(',','')
        if rule=='accounting_thousand_times_1000' and raw_text.startswith('(') and raw_text.endswith(')'):
            raw_text='-'+raw_text[1:-1]
        raw=Decimal(raw_text)
        conversions={
          'identity':(Decimal(1),None),
          'remove_thousands_separator':(Decimal(1),None),
          'percent_divided_by_100':(Decimal('0.01'),'percent'),
          'million_times_1000000':(Decimal(1000000),'USD_million'),
          'billion_times_1000000000':(Decimal(1000000000),None),
          'trillion_times_1000000000000':(Decimal('1000000000000'),'USD_trillion'),
          'cents_divided_by_100':(Decimal('0.01'),'US_cents_per_passenger_mile'),
          'million_quantity_times_1000000':(Decimal(1000000),None),
          'accounting_thousand_times_1000':(Decimal(1000),None),
        }
        if rule not in conversions:
            raise ValueError('数值转换未批准')
        factor,expected=conversions[rule]
        if expected is not None and o['raw_unit']!=expected:
            raise ValueError('倍数转换与原始单位冲突')
        if rule=='billion_times_1000000000' and o['raw_unit'] not in ('USD_billion','billion_people','JPY_billion','billion_pounds','billion_unit_cases'):
            raise ValueError('十亿倍数与原始单位冲突')
        if rule=='accounting_thousand_times_1000' and (o['raw_unit'],o['unit']) not in (('USD_thousand','USD'),('thousand_shares','shares')):
            raise ValueError('千单位转换与金额或股数错配')
        if rule=='million_quantity_times_1000000' and o['raw_unit'] not in ('million_passenger_miles','million_seat_miles','million_units','TWh','million_transactions'):
            raise ValueError('运输工作量百万单位转换与原始单位冲突')
        value=raw*factor
    if not value.is_finite() or not Decimal(o['value']).is_finite() or value!=Decimal(o['value']):
        raise ValueError('样本数值转换不一致或非有限值')
    # 百分数通常经过公司取整；保留披露精度，不声称比原文更精确。
    return quote

def verify_original_document(source):
    """PDF 摘录附完整文件哈希及页码；逐页检查摘录，避免把手写数字冒充文件原文。"""
    document=source.get('original_document')
    if not document:
        return
    doc_file = local(document['path'])
    if not doc_file.exists():
        return
    raw=doc_file.read_bytes()
    if digest(raw)!=document['sha256']:
        raise ValueError('完整 PDF 内容哈希变化')
    from pypdf import PdfReader
    reader=PdfReader(local(document['path']))
    if len(document['excerpt_pages'])!=len(source['excerpts']):
        raise ValueError('PDF 摘录页码映射缺失')
    normalize=lambda text:' '.join(text.split())
    for quote,page in zip(source['excerpts'],document['excerpt_pages']):
        if type(page)!=int or page<1 or page>len(reader.pages) or normalize(quote) not in normalize(reader.pages[page-1].extract_text()):
            raise ValueError('摘录不在指定 PDF 页中')

def register_samples(catalog_directory='data/catalog'):
    """追加归档原文摘录与样本快照；不覆盖财务事实表，也不自动放行研究步骤。"""
    specs,reps,discovery=verify_specs()
    repmap={r['industry_id']:r for r in reps}
    catalog=LocalStore(catalog_directory)
    approved=json.loads(local('knowledge/metrics/industry-reviewed-sources-20261011b.json').read_text(encoding='utf-8'))['sources']
    for industry,urls in json.loads(local('knowledge/metrics/telecom-reviewed-sources-20261012.json').read_text(encoding='utf8'))['sources'].items():
        approved.setdefault(industry,[]).extend(urls)
    observations=[];sources=[]
    try:
        for bundle_path in BUNDLE_PATHS:
            bundle=json.loads(local(bundle_path).read_text(encoding='utf-8'))
            observed=bundle['observed_at']
            if instant(observed)>instant(now()):
                raise ValueError('不能登记未来观察时点')
            for source in bundle['sources']:
                publication=source['published_date']
                if publication and date.fromisoformat(publication)>instant(observed).date():
                    raise ValueError('发布日期晚于本次观察时点')
                rep=repmap[source['industry_id']]
                source={**source,'source_url':source.get('source_url',discovery[source['industry_id']]),'archive_kind':bundle['archive_kind'], 'observed_at':observed, 'not_full_original_document':not bool(source.get('original_document'))}
                if source['source_url'] not in [discovery[source['industry_id']],*approved.get(source['industry_id'],[])]:
                    raise ValueError('摘录来源不是本次已调查的官方来源')
                verify_original_document(source)
                has_pdf = bool(source.get('original_document') and local(source['original_document']['path']).exists())
                if has_pdf:
                    document=source['original_document']
                    doc_source_id = 'industry-original-pdf:'+document['sha256']
                    existing_doc = catalog.db.execute("SELECT sha256 FROM sources WHERE source_id=? AND revision=1", (doc_source_id,)).fetchone()
                    if not existing_doc:
                        catalog.register_source({'schema_version':'1.1.0','source_id':doc_source_id,'revision':1,'source_path':document['path'],'source_kind':'primary','dataset_kind':'industry','published_at':None,'published_date':publication,'publication_precision':'date' if publication else 'unknown','available_at':observed,'acquired_at':observed,'effective_period':None,'license_notes':'发行人公开财报，仅供本地研究。','quality_notes':['浏览器下载完整 PDF','官方页面: '+document['source_url']],'supersedes_revision':None})
                # 先完成数值和关联校验，再追加登记，避免无效值进入事实层。
                for o in source['observations']:
                    verify_observation(source,o,observed)
                path,sha=save_object(canonical(source),'json')
                evidence_note='完整 PDF 已另行归档；摘录按页提取并校验文件哈希' if has_pdf else 'AI 浏览器已访问官方页面；人工归档的可见页面摘录，不是完整原文文件'
                manifest={'schema_version':'1.1.0','source_id':'industry-browser-excerpt:'+sha,'revision':1,'source_path':path,'source_kind':'primary','dataset_kind':'industry','published_at':None,'published_date':publication,'publication_precision':'date' if publication else 'unknown','available_at':observed,'acquired_at':observed,'effective_period':None,'license_notes':'发行人公开披露摘录，仅供本地研究；不授予再分发权。','quality_notes':[evidence_note,'官方页面: '+source['source_url'],'定位: '+source['locator'],'本次观察时点只证明本次可得，不证明历史发布时间；数值保留发行人披露精度'],'supersedes_revision':None}
                existing_excerpt = catalog.db.execute("SELECT sha256 FROM sources WHERE source_id=? AND revision=1", (manifest['source_id'],)).fetchone()
                if existing_excerpt and existing_excerpt['sha256'] == sha:
                    registered = {'source_id': manifest['source_id'], 'revision': 1, 'sha256': sha}
                else:
                    registered=catalog.register_source(manifest)
                sources.append({k:registered[k] for k in ['source_id','revision','sha256']})
                for o in source['observations']:
                    quote=verify_observation(source,o,observed)
                    payload={**o,'industry_id':source['industry_id'],'entity_id':rep['market']+':'+rep['ticker'],'available_at':observed,'source_ref':{k:registered[k] for k in ['source_id','revision','sha256']},'excerpt':quote,'locator':source['locator'],'precision_status':'issuer_reported_precision','quality_status':'browser_reviewed_sample','parent_driver_complete':False}
                    payload['observation_id']=digest(canonical(payload))
                    observations.append(payload)
        # 这是原子观测样本；复合驱动及不适用项仍须进一步逐项审核。
        coverage=[]
        for s in specs:
            rows=[o for o in observations if o['parent_metric_id']==s['parent_metric_id']]
            found=[o['observation_id'] for o in rows]
            usable=[o for o in rows if o.get('binding_role') not in ('scope_mismatch_sample','profit_basis_variant','context_sample')]
            status=('partial_sample_requires_driver_review' if usable else 'definition_mismatch_sample_only') if found else 'pending_original_binding'
            coverage.append({'parent_metric_id':s['parent_metric_id'],'industry_id':s['industry_id'],'observation_ids':found,'usable_sample_ids':[o['observation_id'] for o in usable],'status':status,'research_gate':'blocked','next_source_zh':'核验代表公司年报、经营补充表及适用的监管/行业原文；按单表必需输入补齐；口径不匹配观测只作差异记录'})
        result={'schema_version':'1.0.0','status':'industry_atomic_samples_not_complete_research','sources':sources,'observations':observations,'coverage':coverage}
        path,sha=save_object(canonical(result),'json')
        # 快照在资料目录登记为项目派生对象，原始证据分别保持 primary。
        latest=max(o['available_at'] for o in observations)
        batch_source_id = 'industry-specific-sample-batch:'+sha
        existing_batch = catalog.db.execute("SELECT sha256 FROM sources WHERE source_id=? AND revision=1", (batch_source_id,)).fetchone()
        if not (existing_batch and existing_batch['sha256'] == sha):
            catalog.register_source({'schema_version':'1.1.0','source_id':batch_source_id,'revision':1,'source_path':path,'source_kind':'project_design','dataset_kind':'industry','published_at':None,'published_date':None,'publication_precision':'unknown','available_at':latest,'acquired_at':latest,'effective_period':None,'license_notes':'项目派生指标样本；原始资料权利依其来源。','quality_notes':['快照已绑定本地原文摘录及资料版本','本快照不证明行业驱动全部完成，不自动生成六步结论'],'supersedes_revision':None})
        return {'snapshot_path':path,'sha256':sha,'industries':len(reps),'specifications':len(specs),'sample_sources':len(sources),'observations':len(observations),'sample_industries':len({o['industry_id'] for o in observations}),'completed_research_steps':0}
    finally:
        catalog.close()

def verify_snapshot(path,as_of=None):
    """读取时复核内容地址、证据版本与转换，防止样本值修改或前视使用。"""
    raw=local(path).read_bytes()
    if path_name(path)!=digest(raw):
        raise ValueError('样本快照内容地址不匹配')
    data=json.loads(raw)
    catalog=LocalStore('data/catalog')
    try:
        for o in data['observations']:
            check={k:v for k,v in o.items() if k!='observation_id'}
            if digest(canonical(check))!=o['observation_id']:
                raise ValueError('观测标识摘要不一致')
            if as_of and instant(o['available_at'])>instant(as_of):
                raise ValueError('研究时点早于专属样本可得时点')
            ref=o['source_ref']
            row=catalog.db.execute('SELECT s.sha256,s.available_at,a.local_path FROM sources s JOIN artifacts a USING(sha256) WHERE source_id=? AND revision=?',(ref['source_id'],ref['revision'])).fetchone()
            if row is None or row['sha256']!=ref['sha256']:
                raise ValueError('原文摘录资料版本不一致')
            source_bytes=local(row['local_path']).read_bytes()
            if digest(source_bytes)!=ref['sha256'] or instant(row['available_at'])!=instant(o['available_at']):
                raise ValueError('原文哈希或可得时间变化')
            source=json.loads(source_bytes)
            verify_original_document(source)
            original=[item for item in source['observations'] if item['component']==o['component'] and item['period_end']==o['period_end']]
            if len(original)!=1 or any(o.get(k)!=v for k,v in original[0].items()):
                raise ValueError('登记观测与不可变摘录绑定记录不一致')
            if verify_observation(source,o,o['available_at'])!=o['excerpt']:
                raise ValueError('引用摘录与原文不一致')
    finally:
        catalog.close()
    return data

def path_name(path):
    """内容地址快照的文件名就是字节摘要，不接受任意可写草稿冒充登记对象。"""
    from pathlib import Path
    return Path(path).stem
