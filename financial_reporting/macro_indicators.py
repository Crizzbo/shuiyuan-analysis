"""宏观经济指标登记与快照生成：支持美债、汇率、就业率与通胀等四大支柱，离线校验防前视。"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
import json
import sys
from .pipeline import ROOT, local, digest, save_object
sys.path.insert(0, str(ROOT / 'scripts'))
from data_store import LocalStore, canonical, now
from validate_research import instant

MACRO_BUNDLE_PATHS = [
    'data/browser-search/macro-reviewed-20261012.json',
]

def verify_macro_specs():
    """检查宏观指标规格目录与传导矩阵的合法性，不接受未定义指标。"""
    catalog_path = local('knowledge/macro/catalog.json')
    catalog_doc = json.loads(catalog_path.read_text(encoding='utf-8'))
    schema_path = local('schemas/macro-catalog.schema.json')
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    from jsonschema import Draft202012Validator
    Draft202012Validator(schema).validate(catalog_doc)
    indicators = catalog_doc['indicators']
    ind_ids = [i['id'] for i in indicators]
    if len(ind_ids) != len(set(ind_ids)):
        raise ValueError('宏观指标 ID 存在重复')
    
    # 验证传导矩阵
    trans_path = local('knowledge/macro/transmission_matrix.json')
    trans_doc = json.loads(trans_path.read_text(encoding='utf-8'))
    trans_schema = json.loads(local('schemas/macro-transmission.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(trans_schema).validate(trans_doc)
    for t in trans_doc['transmissions']:
        if t['macro_indicator_id'] not in ind_ids:
            raise ValueError(f"传导矩阵引用未知宏观指标: {t['macro_indicator_id']}")
    return {i['id']: i for i in indicators}, trans_doc['transmissions']

def verify_macro_observation(source, o, observed):
    """单条宏观观测数据校验：数值转换、引用摘录、单位匹配。"""
    for key in ('indicator_id', 'period_end', 'raw_value', 'raw_unit', 'value', 'unit', 'conversion', 'release_status'):
        if key not in o:
            raise ValueError(f'宏观观测项缺失必需字段: {key}')
    if not o.get('excerpt_indices'):
        raise ValueError('宏观观测项必须指定有效摘录索引')
    quote = ' '.join(source['excerpts'][i] for i in o['excerpt_indices'])
    if o['raw_value'] not in quote:
        raise ValueError(f"原始披露值 {o['raw_value']} 不在引用摘录中")
    
    rule = o['conversion']
    if rule == 'percent_divided_by_100':
        if o['raw_unit'] != 'percent' or o['unit'] != 'ratio':
            raise ValueError('百分比转换单位不匹配')
        val = Decimal(o['raw_value'].replace(',', '')) * Decimal('0.01')
    elif rule == 'identity':
        val = Decimal(o['raw_value'].replace(',', ''))
    else:
        raise ValueError(f'未批准的宏观转换规则: {rule}')
    
    if not val.is_finite() or Decimal(o['value']) != val:
        raise ValueError('数值计算转换不一致')
    return quote

def register_macro_samples(catalog_directory='data/catalog', as_of=None):
    """归档宏观经济观测样本与快照；遵循 LocalStore 机制，严格防时间前视。"""
    spec_map, transmissions = verify_macro_specs()
    catalog = LocalStore(catalog_directory)
    try:
        observations = []
        for bundle_path in MACRO_BUNDLE_PATHS:
            bundle = json.loads(local(bundle_path).read_text(encoding='utf-8'))
            observed = bundle['observed_at']
            if instant(observed) > instant(now()):
                raise ValueError('不能登记未来宏观观察时点')
            for source in bundle['sources']:
                publication = source.get('published_date')
                if publication and date.fromisoformat(publication) > instant(observed).date():
                    raise ValueError('宏观发布日期晚于本次观察时点')
                source_payload = {
                    **source,
                    'archive_kind': bundle['archive_kind'],
                    'observed_at': observed,
                    'not_full_original_document': True
                }
                # 校验指标
                for o in source['observations']:
                    if o['indicator_id'] not in spec_map:
                        raise ValueError(f"未知宏观指标标识: {o['indicator_id']}")
                    verify_macro_observation(source, o, observed)
                
                path, sha = save_object(canonical(source_payload), 'json')
                manifest = {
                    'schema_version': '1.1.0',
                    'source_id': 'macro-browser-excerpt:' + sha,
                    'revision': 1,
                    'source_path': path,
                    'source_kind': 'primary',
                    'dataset_kind': 'market',
                    'published_at': None,
                    'published_date': publication,
                    'publication_precision': 'date' if publication else 'unknown',
                    'available_at': observed,
                    'acquired_at': observed,
                    'effective_period': None,
                    'license_notes': '公开官方宏观数据摘录（美联储/财政部/BLS），仅供本地研究。',
                    'quality_notes': [
                        '官方页面: ' + source['source_url'],
                        '定位: ' + source['locator'],
                        '数值保留发行机构披露精度'
                    ],
                    'supersedes_revision': None
                }
                registered = catalog.register_source(manifest)
                for o in source['observations']:
                    quote = verify_macro_observation(source, o, observed)
                    payload = {
                        'indicator_id': o['indicator_id'],
                        'published_date': source['published_date'],
                        'period_end': o['period_end'],
                        'raw_value': o['raw_value'],
                        'raw_unit': o['raw_unit'],
                        'value': o['value'],
                        'unit': o['unit'],
                        'release_status': o['release_status'],
                        'source_url': source['source_url'],
                        'locator': source['locator'],
                        'available_at': observed,
                        'excerpt': quote,
                        'source_ref': {k: registered[k] for k in ('source_id', 'revision', 'sha256')}
                    }
                    payload['observation_id'] = digest(canonical(payload))
                    observations.append(payload)
                    
        latest_avail = max(o['available_at'] for o in observations)
        cutoff = as_of or latest_avail
        snapshot_payload = {
            'schema_version': '1.0.0',
            'as_of': cutoff,
            'observations': observations
        }
        # 先做自身哈希校验与快照存储
        raw_snap = canonical(snapshot_payload)
        sha = digest(raw_snap)
        snapshot_payload['snapshot_id'] = sha
        final_snap_raw = canonical(snapshot_payload)
        final_sha = digest(final_snap_raw)
        snapshot_path, _ = save_object(final_snap_raw, 'json')
        
        # 验证 Schema
        snapshot_schema = json.loads(local('schemas/macro-snapshot.schema.json').read_text(encoding='utf-8'))
        from jsonschema import Draft202012Validator
        Draft202012Validator(snapshot_schema).validate(snapshot_payload)

        latest_avail = max(o['available_at'] for o in observations)
        catalog.register_source({
            'schema_version': '1.1.0',
            'source_id': 'macro-snapshot-batch:' + final_sha,
            'revision': 1,
            'source_path': snapshot_path,
            'source_kind': 'project_design',
            'dataset_kind': 'market',
            'published_at': None,
            'published_date': None,
            'publication_precision': 'unknown',
            'available_at': latest_avail,
            'acquired_at': latest_avail,
            'effective_period': None,
            'license_notes': '项目派生宏观快照；原始数据依其来源。',
            'quality_notes': ['快照已绑定官方披露摘录与版本', '防前视截面数据'],
            'supersedes_revision': None
        })
        
        index_manifest = {
            'schema_version': '1.0.0',
            'snapshot_path': snapshot_path,
            'sha256': final_sha,
            'indicators_count': len(spec_map),
            'observations_count': len(observations),
            'transmissions_count': len(transmissions)
        }
        (ROOT / 'data/financial/macro-verification.json').write_text(
            json.dumps(index_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )
        return index_manifest
    finally:
        catalog.close()

def verify_macro_snapshot(snapshot_path, as_of=None):
    """只读校验宏观快照：完整性与时间防前视。"""
    raw = local(snapshot_path).read_bytes()
    data = json.loads(raw.decode('utf-8'))
    check = {k: v for k, v in data.items() if k != 'snapshot_id'}
    if digest(canonical(check)) != data.get('snapshot_id'):
        raise ValueError('宏观快照数据摘要不一致')
    if as_of and instant(data['as_of']) > instant(as_of):
        raise ValueError('快照时点超出指定时点')
    return data
