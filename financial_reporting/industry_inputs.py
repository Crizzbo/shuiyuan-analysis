"""逐驱动输入台账：人工明确选用字段，验证证据、范围和期间，不以字段相似度猜测绑定。"""
from __future__ import annotations
import json
from .pipeline import local, save_object, digest
from .industry_specific import verify_snapshot
import sys
from .pipeline import ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from data_store import canonical, LocalStore

PLAN_PATH='knowledge/metrics/industry-input-binding-plans.json'

def validate_binding_plans(data, specs):
    """独立结构契约及业务约束；归档旧方案与当前方案执行同一校验。"""
    from jsonschema import Draft202012Validator, FormatChecker
    schema=json.loads(local('schemas/industry-input-binding-plans.schema.json').read_text(encoding='utf8'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    known={s['parent_metric_id']:s for s in specs}
    seen=set()
    for plan in data['plans']:
        parent=plan['parent_metric_id']
        if parent in seen or parent not in known:
            raise ValueError('绑定方案父驱动重复或未知')
        seen.add(parent)
        start,end=plan['period_start'],plan['period_end']
        if start is not None and (end is None or start>end):
            raise ValueError('绑定方案期间倒置')
        if set(plan['slots'])-set(known[parent]['required_inputs_zh']):
            raise ValueError('绑定方案输入名称与原始规格不一致')
    return data

def build_ledger(snapshot_path,plan_path=PLAN_PATH):
    """读取不可变观测与人工绑定方案，为全部 123 个驱动生成输入槽位和明确缺口。"""
    snapshot=verify_snapshot(snapshot_path)
    specs=json.loads(local('knowledge/metrics/industry-specifications.json').read_text(encoding='utf8'))['specifications']
    plans=validate_binding_plans(json.loads(local(plan_path).read_text(encoding='utf8')), specs)['plans']
    if len({p['parent_metric_id'] for p in plans})!=len(plans):
        raise ValueError('绑定方案父驱动重复')
    planmap={p['parent_metric_id']:p for p in plans}
    if set(planmap)-{s['parent_metric_id'] for s in specs}:
        raise ValueError('绑定方案存在未知驱动')
    bycomponent={}
    for observation in snapshot['observations']:
        bycomponent.setdefault(observation['component'],[]).append(observation)
    drivers=[]
    for spec in specs:
        parent=spec['parent_metric_id'];plan=planmap.get(parent,{})
        supplied=plan.get('slots',{})
        if set(supplied)-set(spec['required_inputs_zh']):
            raise ValueError('绑定方案输入名称与原始规格不一致')
        slots=[];paired=[]
        for index,name in enumerate(spec['required_inputs_zh'],1):
            bindings=[]
            for binding in supplied.get(name,[]):
                # 期间与范围必须匹配；期末时点存量指标（无 period_start）允许与同截止期成对。
                rows=[o for o in bycomponent.get(binding['component'],[]) if (o['period_start']==plan['period_start'] or ((o['period_start'] is None or plan['period_start'] is None) and o['period_end']==plan['period_end'])) and o['period_end']==plan['period_end'] and o['scope']==binding['scope']]
                if len(rows)!=1: raise ValueError('选用输入必须唯一匹配公司范围和期间')
                o=rows[0]
                if o['parent_metric_id']!=parent or o['unit']!=binding['unit']:
                    raise ValueError('输入跨父驱动或单位错配')
                # EPS 加权股数可用于同名槽位，但绝不能替代期初期末实际股数。
                weighted_eps_input=(parent=='software_driver_3' and name=='加权稀释股数' and o['component'] in ('ddog_weighted_diluted_eps_shares','ddog_weighted_diluted_eps_shares_2024') and binding['kind']=='numeric')
                if o.get('binding_role') in ('scope_mismatch_sample','profit_basis_variant','context_sample') and not weighted_eps_input:
                    raise ValueError('范围差异、利润层次差异和背景项不能作驱动输入')
                if binding['kind'] not in ('numeric','scope_metadata','period_metadata'):
                    raise ValueError('未知输入绑定类型')
                if binding['kind']=='numeric': paired.append(o)
                bindings.append({'component':o['component'],'kind':binding['kind'],'scope':o['scope'],'unit':o['unit'],'observation_id':o['observation_id'],'source_ref':o['source_ref'],'available_at':o['available_at']})
            slots.append({'slot_id':parent+'__input_'+str(index),'name_zh':name,'status':'bound' if bindings else 'missing','bindings':bindings})
        # 复合不同产品不能直接求和。只对方案声明的同范围公式检查分子分母。
        if plan.get('requires_same_scope') and len({(o['entity_id'],o['scope'],o['period_start'],o['period_end'],o['period_type']) for o in paired})>1:
            raise ValueError('分子分母公司、范围或期间不一致')
        missing=[s['slot_id'] for s in slots if s['status']=='missing']
        status='input_complete' if not missing else 'partial_inputs' if any(s['bindings'] for s in slots) else 'pending_input_binding'
        related=[o for o in snapshot['observations'] if o['parent_metric_id']==parent]
        drivers.append({'parent_metric_id':parent,'industry_id':spec['industry_id'],'name_zh':spec['name_zh'],'business_definition_zh':spec['business_definition_zh'],'selected_variant_zh':plan.get('selected_variant_zh','尚未选择经过审核的公司具体口径'),'period_start':plan.get('period_start'),'period_end':plan.get('period_end'),'slots':slots,'missing_slot_ids':missing,'input_status':status,'definition_status':'company_variant_reviewed' if plan.get('definition_reviewed') else 'definition_review_pending','calculation_ready':status=='input_complete' and bool(plan.get('definition_reviewed')),'research_gate':'blocked','related_observation_ids':[o['observation_id'] for o in related],'limitations_zh':plan.get('limitations_zh',['尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露'])})
    return {'schema_version':'1.0.0','observation_snapshot_path':snapshot_path,'observation_snapshot_sha256':digest(local(snapshot_path).read_bytes()),'binding_plan_path':plan_path,'binding_plan_sha256':digest(local(plan_path).read_bytes()),'drivers':drivers}

def verify_ledger(data):
    """重建台账并逐字段比较，拒绝人为放行、换期、替换来源或把代理量填入缺失槽位。"""
    from jsonschema import Draft202012Validator
    Draft202012Validator(json.loads(local('schemas/industry-driver-inputs.schema.json').read_text(encoding='utf8'))).validate(data)
    raw=local(data['binding_plan_path']).read_bytes()
    if digest(raw)!=data['binding_plan_sha256']:
        raise ValueError('绑定方案哈希变化')
    store=LocalStore('data/catalog')
    try:
        row=store.db.execute('SELECT sha256 FROM sources WHERE source_id=? AND revision=1',('industry-input-plan:'+data['binding_plan_sha256'],)).fetchone()
        if row is None or row['sha256']!=data['binding_plan_sha256']:
            raise ValueError('绑定方案未登记为审核版本')
    finally: store.close()
    if data!=build_ledger(data['observation_snapshot_path'],data['binding_plan_path']):
        raise ValueError('台账与已审核绑定方案或不可变证据不一致')
    return data

def register_ledger(snapshot_path):
    """追加台账及绑定方案为项目设计资料；只更新最新索引，不覆写旧证据。"""
    build_ledger(snapshot_path)  # 校验方案后才登记，避免无效方案进入批准版本目录。
    observation=verify_snapshot(snapshot_path)
    latest=max(o['available_at'] for o in observation['observations'])
    store=LocalStore('data/catalog')
    try:
        plan_path,plan_sha=save_object(local(PLAN_PATH).read_bytes(),'json')
        def register(stored,hash_value,prefix):
            source_id = prefix + hash_value
            existing = store.db.execute("SELECT sha256 FROM sources WHERE source_id=? AND revision=1", (source_id,)).fetchone()
            if existing and existing["sha256"] == hash_value:
                return
            store.register_source({'schema_version':'1.1.0','source_id':source_id,'revision':1,'source_path':stored,'source_kind':'project_design','dataset_kind':'industry','published_at':None,'published_date':None,'publication_precision':'unknown','available_at':latest,'acquired_at':latest,'effective_period':None,'license_notes':'项目输入设计及派生台账。','quality_notes':['输入齐备不等于研究结论完成；全部研究闸门仍阻断'],'supersedes_revision':None})
        register(plan_path,plan_sha,'industry-input-plan:')
        data=verify_ledger(build_ledger(snapshot_path,plan_path))
        path,sha=save_object(canonical(data),'json')
        register(path,sha,'industry-driver-input-ledger:')
    finally: store.close()
    return {'schema_version':'1.0.0','snapshot_path':path,'sha256':sha,'drivers':len(data['drivers']),'input_complete':sum(d['input_status']=='input_complete' for d in data['drivers']),'calculation_ready':sum(d['calculation_ready'] for d in data['drivers']),'partial_inputs':sum(d['input_status']=='partial_inputs' for d in data['drivers']),'pending_input_binding':sum(d['input_status']=='pending_input_binding' for d in data['drivers'])}
