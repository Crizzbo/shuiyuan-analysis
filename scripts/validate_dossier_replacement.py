"""发布前验证完整替换集、JSON证据及PDF摘要；失败绝不删除旧云盘文件。"""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.evidence_dossiers import validate_dossier
from financial_reporting.pipeline import local

def main():
    manifest=json.loads(local('reports/replacements/drive-20261012/manifest.json').read_text(encoding='utf8'))
    inventory=json.loads(local('data/audits/drive-deep-analysis-20261012/inventory.json').read_text(encoding='utf8'))['files']
    if not manifest['complete_replacement_set'] or {r['old_file_id'] for r in manifest['files']}!={r['id'] for r in inventory}:
        raise ValueError('替换范围不完整')
    for item in manifest['files']:
        for path_key,hash_key in [('json_path','json_sha256'),('pdf_path','pdf_sha256')]:
            if hashlib.sha256(local(item[path_key]).read_bytes()).hexdigest()!=item[hash_key]: raise ValueError('发布文件发生变化')
        data=json.loads(local(item['json_path']).read_text(encoding='utf8'))
        validate_dossier(data)
        if data['symbol']!=item['symbol'] or data['market']!=item['market'] or len(data['facts'])!=item['facts_count']:
            raise ValueError('发布身份或事实数不一致')
    result={'validated_files':len(manifest['files']),'with_verified_facts':manifest['with_verified_facts'],'verified':True,
        'manifest_sha256':hashlib.sha256(local('reports/replacements/drive-20261012/manifest.json').read_bytes()).hexdigest()}
    local('reports/replacements/drive-20261012').joinpath('preflight.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
