"""把原文核验后的财务事实登记进正式资料目录；不生成六步结论或投资判断。"""
import json
import sys
from pathlib import Path
from .pipeline import ROOT,local,digest,run,store
sys.path.insert(0,str(ROOT/'scripts'))
from data_store import LocalStore,canonical,now
from validate_research import instant

DDL='''CREATE TABLE IF NOT EXISTS financial_facts(
 registration_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, report_id TEXT NOT NULL,
 fact_id TEXT NOT NULL, available_at TEXT NOT NULL, payload_json TEXT NOT NULL,
 original_source_id TEXT NOT NULL, original_revision INTEGER NOT NULL,
 evidence_source_id TEXT NOT NULL, evidence_revision INTEGER NOT NULL,
 registered_at TEXT NOT NULL,
 FOREIGN KEY(original_source_id,original_revision) REFERENCES sources(source_id,revision),
 FOREIGN KEY(evidence_source_id,evidence_revision) REFERENCES sources(source_id,revision));
 CREATE INDEX IF NOT EXISTS financial_facts_asof ON financial_facts(entity_id,available_at);'''

def initialize(catalog):
    catalog.db.executescript(DDL)
    for action in ['UPDATE','DELETE']:
        catalog.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_financial_facts_{action.lower()} BEFORE {action} ON financial_facts BEGIN SELECT RAISE(ABORT,'append-only financial facts'); END")

def source_manifest(report,path,sha,derived=False):
    """不把 PDF 文本页当作独立发布来源；日期及首次可得时点继承原文。"""
    a=report['artifact']; browser=a['browser_receipt']
    return {'schema_version':'1.1.0','source_id':'financial:'+report['report_id']+':'+sha,
      'revision':1,'source_path':path,'source_kind':'primary','dataset_kind':'financial',
      'published_at':a['published_at'],'available_at':a['available_at'],'acquired_at':a['acquired_at'],
      'published_date':browser.get('published_date'),'publication_precision':browser['publication_precision'],
      'effective_period':None,'supersedes_revision':None,
      'license_notes':'公开披露原文，仅供本地研究；不授予再分发权。',
      'quality_notes':['原文 SHA-256: '+a['sha256'],
        '从原始 ZIP/PDF 派生的证据文本，必须同时引用原文版本' if derived else 'AI 浏览器核对发行人或监管原文',
        '首次观察时点用于 as-of；比较年度不是当年的首次发布版本。']}

def verify_payload(catalog,payload,as_of=None):
    """每次读取核对全部证据及执行材料；篡改或前视数据立即阻断。"""
    identity=payload['registration_id']
    if digest(canonical({k:v for k,v in payload.items() if k!='registration_id'}))!=identity:
        raise ValueError('正式事实登记摘要不匹配')
    if payload['fact']['source']['sha256']!=payload['evidence_source']['sha256']:
        raise ValueError('事实与登记证据摘要不一致')
    for key in ['original_source','evidence_source']:
        link=payload[key]
        row=catalog.db.execute('SELECT s.sha256,s.available_at,a.local_path FROM sources s JOIN artifacts a USING(sha256) WHERE source_id=? AND revision=?',
                              (link['source_id'],link['revision'])).fetchone()
        if row is None or row['sha256']!=link['sha256'] or digest(local(row['local_path']).read_bytes())!=link['sha256']:
            raise ValueError('正式资料版本或归档摘要不一致')
        if instant(row['available_at'])!=instant(payload['fact']['source']['available_at']):
            raise ValueError('事实与登记来源可得时点不一致')
    for key in ['report_ref','plan_ref','implementation_ref']:
        ref=payload[key]
        if digest(local(ref['path']).read_bytes())!=ref['sha256']:
            raise ValueError('正式事实执行材料摘要变化')
    tax=payload['taxonomy_validation']
    if tax.get('status')=='passed' and local(tax['snapshot_path']).exists() and digest(local(tax['snapshot_path']).read_bytes())!=tax['sha256']:
        raise ValueError('分类标准校验日志被修改')
    fact=payload['fact']
    evidence=catalog.db.execute('SELECT a.local_path FROM sources s JOIN artifacts a USING(sha256) WHERE source_id=? AND revision=?',
                             (payload['evidence_source']['source_id'],payload['evidence_source']['revision'])).fetchone()
    if fact['source']['excerpt'] not in local(evidence['local_path']).read_text(encoding='utf-8'):
        raise ValueError('事实摘录不在登记证据中')
    if as_of is not None and instant(fact['source']['available_at'])>instant(as_of):
        raise ValueError('研究时点早于事实可得时点')

def register(plan_path,catalog_directory='data/catalog'):
    """调用解析和完整 DTS 校验后登记；重述/实现变更形成新快照，不覆盖旧事实。"""
    from jsonschema import Draft202012Validator,FormatChecker
    plan_bytes=local(plan_path).read_bytes();plan=json.loads(plan_bytes)
    report=run(plan)
    if not report['facts'] or report['issues'] or any(f['status']!='extracted' for f in report['facts']) or any(c['status']=='failed' for c in report['checks']):
        raise ValueError('解析异常、事实冲突或勾稽失败，禁止正式登记')
    # 保存实现与配置的不可变副本，升级代码不导致历史无法读取。
    from .pipeline import save_object
    plan_copy,plan_sha=save_object(plan_bytes,'json')
    impl_copy,impl_sha=save_object(Path(__file__).with_name('pipeline.py').read_bytes(),'txt')
    schema=json.loads(local('schemas/registered-financial-fact.schema.json').read_text(encoding='utf-8'))
    catalog=LocalStore(catalog_directory)
    try:
        initialize(catalog)
        from .taxonomy import validation_fingerprint,validate_dts
        fingerprint=validation_fingerprint() if plan['format']=='inline_zip' else None
        # 相同原文、配置、解析实现与分类标准环境只登记一次。
        candidates=[]
        for row in catalog.db.execute('SELECT payload_json FROM financial_facts WHERE entity_id=? AND report_id=?',(report['entity_id'],report['report_id'])):
            old=json.loads(row[0])
            if (old['plan_ref']['sha256']==plan_sha and old['implementation_ref']['sha256']==impl_sha
                and old['original_source']['sha256']==report['artifact']['sha256']
                and old['taxonomy_validation'].get('validation_fingerprint')==fingerprint):
                verify_payload(catalog,old)
                candidates.append(old)
        if candidates and {p['fact']['id'] for p in candidates}=={f['id'] for f in report['facts']}:
            return {'report_id':report['report_id'],'report_ref':{'snapshot_path':candidates[0]['report_ref']['path']},
              'registered_fact_count':len(candidates),'registration_ids':[p['registration_id'] for p in candidates],
              'taxonomy_validation':candidates[0]['taxonomy_validation'],'idempotent':True}
        if plan['format']=='inline_zip':
            _,report['taxonomy_validation']=validate_dts(plan)
            if report['taxonomy_validation']['status']!='passed':
                raise ValueError('完整 DTS 校验未通过，禁止正式登记')
            report['missing_capabilities']=[]
        ref=store(report)
        a=report['artifact']
        original=catalog.register_source(source_manifest(report,a['source_path'],a['sha256']))
        derived={}
        for f in report['facts']:
            s=f['source']
            if digest(local(s['path']).read_bytes())!=s['sha256'] or s['excerpt'] not in local(s['path']).read_text(encoding='utf-8'):
                raise ValueError('事实证据摘要或摘录错误')
            if s['sha256'] not in derived:
                derived[s['sha256']]=catalog.register_source(source_manifest(report,s['path'],s['sha256'],True))
        registrations=[]
        with catalog.transaction():
            for f in report['facts']:
                d=derived[f['source']['sha256']]
                payload={'schema_version':'1.0.0','entity_id':report['entity_id'],'report_id':report['report_id'],
                  'fact':f,'quality_status':'source_verified','report_ref':{'path':ref['snapshot_path'],'sha256':ref['sha256']},
                  'plan_ref':{'path':plan_copy,'sha256':plan_sha},'implementation_ref':{'path':impl_copy,'sha256':impl_sha},
                  'original_source':{k:original[k] for k in ['source_id','revision','sha256']},
                  'evidence_source':{k:d[k] for k in ['source_id','revision','sha256']},
                  'taxonomy_validation':report['taxonomy_validation']}
                payload['registration_id']=digest(canonical(payload))
                Draft202012Validator(schema,format_checker=FormatChecker()).validate(payload)
                verify_payload(catalog,payload)
                encoded=canonical(payload).decode()
                existing=catalog.db.execute('SELECT payload_json FROM financial_facts WHERE registration_id=?',(payload['registration_id'],)).fetchone()
                if existing and existing[0]!=encoded:
                    raise ValueError('同一正式事实不能覆盖')
                catalog.db.execute('INSERT OR IGNORE INTO financial_facts VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (payload['registration_id'],report['entity_id'],report['report_id'],f['id'],f['source']['available_at'],encoded,
                   original['source_id'],1,d['source_id'],1,now()))
                registrations.append(payload['registration_id'])
        return {'report_id':report['report_id'],'report_ref':ref,'registered_fact_count':len(registrations),
                'registration_ids':registrations,'taxonomy_validation':report['taxonomy_validation']}
    finally:
        catalog.close()

def read_as_of(entity_id,as_of,catalog_directory='data/catalog',include_history=False):
    """返回指定研究时点已经可得的版本；不自动把旧报告比较列当成原始当期值。"""
    catalog=LocalStore(catalog_directory)
    try:
        initialize(catalog)
        results=[]
        for row in catalog.db.execute('SELECT * FROM financial_facts WHERE entity_id=? ORDER BY rowid',(entity_id,)):
            if instant(row['available_at'])>instant(as_of):
                continue
            payload=json.loads(row['payload_json'])
            identity=payload.pop('registration_id')
            if digest(canonical(payload))!=identity or identity!=row['registration_id']:
                raise ValueError('正式事实登记摘要不匹配')
            payload['registration_id']=identity
            verify_payload(catalog,payload,as_of)
            results.append(payload)
        if include_history:
            return results
        latest={p['report_id']:p['report_ref']['sha256'] for p in results}
        return [p for p in results if p['report_ref']['sha256']==latest[p['report_id']]]
    finally:
        catalog.close()

def registered_metric_batch(entity_id,period_end,as_of,catalog_directory='data/catalog'):
    """正式事实复用已有软件行业利润率工具；多个披露版本需显式选择，不能混算。"""
    from .pipeline import metric_batch
    selected=[p for p in read_as_of(entity_id,as_of,catalog_directory)
              if p['fact']['field'] in ('revenue','operating_income') and p['fact']['period']['end']==period_end
              and p['fact']['period']['basis']=='annual']
    if len(selected)!=2 or len({p['report_ref']['sha256'] for p in selected})!=1:
        raise ValueError('缺少唯一同报告的收入与营业利润正式事实')
    report=json.loads(local(selected[0]['report_ref']['path']).read_text(encoding='utf-8'))
    return metric_batch(report,period_end,as_of)
