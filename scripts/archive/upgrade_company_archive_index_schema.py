"""公司档案索引2.0：记录证据路径与缺失状态，移除强制评级和假当前市价。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'schemas/company-archive.schema.json'
    backup=ROOT/'data/audits/drive-deep-analysis-20261012/code-originals/company-archive.schema.json'
    if not backup.exists(): backup.write_bytes(path.read_bytes())
    props={'company_id':{'type':'string','minLength':1},'ticker':{'type':'string','minLength':1},
        'market':{'enum':['US','JP']},'profile_path':{'type':'string','minLength':1},'evidence_path':{'type':'string','minLength':1},
        'research_status':{'enum':['evidence_partial','evidence_missing']},'investment_stance':{'type':'null'},'position_fraction':{'type':'null'}}
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'公司证据档案索引2.0','type':'object','additionalProperties':False,
        'required':['schema_version','title','companies_count','companies'],'properties':{
            'schema_version':{'const':'2.0.0'},'title':{'type':'string'},'companies_count':{'type':'integer','minimum':1},
            'companies':{'type':'array','items':{'type':'object','additionalProperties':False,'required':list(props),'properties':props}}}}
    path.write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__': main()
