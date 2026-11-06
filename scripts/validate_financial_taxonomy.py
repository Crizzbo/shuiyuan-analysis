"""完整分类标准校验入口：只读项目内官方包和财报；不联网。"""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from financial_reporting.pipeline import local
from financial_reporting.taxonomy import validate_dts
if __name__=='__main__':
    result,summary=validate_dts(json.loads(local(sys.argv[1]).read_text(encoding='utf-8')))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='passed' else 1)
