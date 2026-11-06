"""固定官方 SEC 转换插件提交、文件摘要及许可证；不加载外部项目。"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
repo=ROOT/'.venv/vendor/EDGAR'
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
record={'repository':'https://github.com/Arelle/EDGAR','commit':commit,'plugin':'.venv/vendor/EDGAR/transform',
 'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo/'transform').rglob('*.py'))}}
directory=ROOT/'third_party/reporting'
(directory/'edgar-transform.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(directory/'EDGAR-LICENSE.txt').write_bytes((repo/'LICENSE').read_bytes())
if (repo/'COPYRIGHT.md').exists():(directory/'EDGAR-COPYRIGHT.txt').write_bytes((repo/'COPYRIGHT.md').read_bytes())
