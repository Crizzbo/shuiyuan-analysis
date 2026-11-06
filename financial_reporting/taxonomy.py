"""完整 DTS 的离线 Arelle 校验；官方标准包需先经浏览器归档，缺依赖即阻断。"""
import json
from pathlib import Path
import shutil
import zipfile
from .pipeline import ROOT,local,digest,save_object

def validation_fingerprint():
    """校验环境固定；插件代码变化不可静默沿用旧校验结果。"""
    from importlib.metadata import version
    lock=json.loads(local('third_party/reporting/edgar-transform.json').read_text(encoding='utf-8'))
    for path,sha in lock['files'].items():
        if digest(local(path).read_bytes())!=sha:
            raise ValueError('SEC 转换插件摘要不一致')
    manifest=json.loads(local('data/taxonomies/manifest.json').read_text(encoding='utf-8'))
    for package in manifest['packages']:
        if digest(local(package['path']).read_bytes())!=package['sha256']:
            raise ValueError('分类标准包摘要变化')
    return digest(json.dumps({'packages':manifest,'plugin':lock,'arelle_version':version('arelle-release'),
                    'implementation_sha256':digest(Path(__file__).read_bytes())},sort_keys=True).encode())

def safe_member(name):
    """归档路径不允许覆盖、目录穿越或 Windows 特殊路径。"""
    path=Path(name)
    if name.startswith('/') or path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name:
        raise ValueError('ZIP 成员越界')
    return path

def prepare_cache(manifest):
    cache=local('data/taxonomies/cache')
    # Arelle 内置的 XBRL/W3C 基础 schema 来自已固定的项目内开源依赖。
    import arelle
    bundled=Path(arelle.__file__).parent/'resources/cache'
    if not bundled.resolve().is_relative_to(ROOT):
        raise ValueError('Arelle 依赖不在项目内')
    shutil.copytree(bundled,cache,dirs_exist_ok=True)
    for package in manifest['packages']:
        raw=local(package['path']).read_bytes()
        if digest(raw)!=package['sha256']:
            raise ValueError('分类标准包摘要错误')
        with zipfile.ZipFile(local(package['path'])) as z:
            if sum(i.file_size for i in z.infolist())>500*1024*1024:
                raise ValueError('分类标准包展开过大')
            for i in z.infolist():
                safe_member(i.filename)
                if i.is_dir() or not i.filename.endswith(('.xsd','.xml','.json')):
                    continue
                parts=i.filename.split('/')
                if package['id']=='us-gaap-2026':
                    suffix='xbrl.fasb.org/us-gaap/2026/'+'/'.join(parts[1:])
                elif package['id']=='srt-2026':
                    suffix='xbrl.fasb.org/srt/2026/'+'/'.join(parts[1:])
                elif package['id']=='sec-2026':
                    suffix='/'.join(parts[1:])
                else:
                    raise ValueError('未审核的分类标准包布局')
                for protocol in ['http','https']:
                    target=(cache/protocol/suffix).resolve()
                    if not target.is_relative_to(cache):
                        raise ValueError('分类标准输出越界')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(z.read(i))
    return cache

def validate_dts(plan):
    """调用完整 Arelle 会话加载 schema、linkbase、维度及计算关系，不跳过 DTS。"""
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions
    manifest=json.loads(local('data/taxonomies/manifest.json').read_text(encoding='utf-8'))
    fingerprint=validation_fingerprint()
    cache=prepare_cache(manifest)
    receipt=json.loads(local(plan['receipt_path']).read_text(encoding='utf-8'))
    artifact=receipt['artifact']
    archive=local(artifact['source_path'])
    if digest(archive.read_bytes())!=plan['expected_sha256'] or artifact['sha256']!=plan['expected_sha256']:
        raise ValueError('财报归档哈希不匹配')
    if artifact['browser_receipt']['entity_id']!=plan['entity_id']:
        raise ValueError('财报与公司身份不一致')
    target=local('data/taxonomies/filings/'+plan['expected_sha256'])
    target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for i in z.infolist():
            p=safe_member(i.filename)
            if i.is_dir() or p.suffix.lower() not in ['.htm','.html','.xml','.xsd']:
                continue
            if i.file_size>50*1024*1024:
                raise ValueError('财报成员过大')
            dest=(target/p).resolve()
            if not dest.is_relative_to(target):
                raise ValueError('财报成员越界')
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(z.read(i))
    options=RuntimeOptions(entrypointFile=str(target/safe_member(plan['member'])),
             internetConnectivity='offline',cacheDirectory=str(cache),disablePersistentConfig=True,
             keepOpen=True,validate=True,calcs='xbrl21',plugins=str(local('.venv/vendor/EDGAR/transform')),
             logFile='logToBuffer',logLevel='info',logPropagate=False)
    with Session() as session:
        session.run(options)
        logs=json.loads(session.get_logs('json'))
        models=session.get_models()
        model=models[0] if models else None
        errors=list(model.errors) if model else ['no_model']
        # 某些加载/插件异常只出现在日志，不可因 model.errors 为空而误判通过。
        errors.extend('log:'+entry.get('code','unknown') for entry in logs.get('log',[])
                      if entry.get('level','').lower() in ('error','critical','fatal') and entry.get('code') not in errors)
        result={'schema_version':'1.0.0','report_id':plan['id'],'original_sha256':artifact['sha256'],
          'status':'passed' if model is not None and not errors else 'blocked',
          'errors':errors,'logs':logs,'dts_document_count':len(model.urlDocs) if model else 0,
          'fact_count':len(model.facts) if model else 0,'concept_count':len(model.qnameConcepts) if model else 0,
          'mode':'offline_full_dts_xbrl21_calculations','package_refs':manifest['packages'],
          'validation_fingerprint':fingerprint,
          'implementation_sha256':digest(Path(__file__).read_bytes())}
    path,sha=save_object(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2).encode(),'json')
    return result,{'snapshot_path':path,'sha256':sha,'status':result['status'],'errors':errors,
                   'dts_document_count':result['dts_document_count'],'fact_count':result['fact_count'],
                   'validation_fingerprint':fingerprint}
