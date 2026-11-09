"""归档并登记经 AI 浏览器核验的行业原子样本；不联网、不生成投资判断。"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from financial_reporting.industry_specific import register_samples, verify_snapshot

if __name__=='__main__':
    result=register_samples()
    verify_snapshot(result['snapshot_path'])
    output=Path(__file__).resolve().parents[1]/'data/financial/industry-specific-verification.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
