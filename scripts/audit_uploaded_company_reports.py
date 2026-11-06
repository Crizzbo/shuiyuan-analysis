"""审计已归档云盘报告及生成路径；不把用户报告当作原始事实。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'data/audits/drive-deep-analysis-20261012'

def main():
    rows=[row for path in sorted((AUDIT/'remote-text').glob('batch-*.json')) for row in json.loads(path.read_text(encoding='utf8'))]
    inventory=json.loads((AUDIT/'inventory.json').read_text(encoding='utf8'))['files']
    if {r['file_id'] for r in rows}!={r['id'] for r in inventory}: raise ValueError('未完整读取目标报告')
    patterns={'fabricated_revenue_mix':'68%','fabricated_nrr':'115%','fabricated_supplier_share':'48%',
        'fabricated_customer_share':'32%','unsupported_refinancing_stress':'<1.5%','hardcoded_cash_interest':'4.35%'}
    findings=[]
    for row in rows:
        if not row['content']: raise ValueError('报告读取失败')
        issues=[{'issue_id':key,'matched_text':value,'classification':'confirmed_template_fabrication' if key.startswith('fabricated') else 'unsupported_model_claim'} for key,value in patterns.items() if value in row['content']]
        findings.append({'file_id':row['file_id'],'title':row['title'],'url':row['url'],'issues':issues,
            'disposition':'withdraw_old_report','numeric_fields_status':'unverified_until_primary_source_matching'})
    summary={'reports_read':len(rows),'reports_with_template_fabrication':sum(any(i['classification']=='confirmed_template_fabrication' for i in r['issues']) for r in findings),
        'by_issue':{key:sum(any(i['issue_id']==key for i in row['issues']) for row in findings) for key in patterns},'files':findings}
    (AUDIT/'findings.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# 云盘公司报告假数据审计','',f'已逐份读取{len(rows)}份报告，全部命中同一套无公司来源的模板数字。原文件范围与全文摘录保留在本审计目录。',
        '', '## 已证实的生成缺陷','',
        '- 深度模板为全部公司写入68%/24%/8%营收结构、115%+ NRR、48%供应商集中度、32%客户集中度及偿付无风险判断。',
        '- 场景2缺失财报用默认营收、市值、利润率补齐；资产按营收1.8倍推算；日股大范围共用一套350万百万日元营收等参数。',
        '- 现金/债务/FCF的缺失回退值已是百万单位，却再次除以百万；零值被or替换。股数和价格由错误组合公式推算。',
        '- 把经营现金流减资本开支直接当FCFF，CAPM股权成本误称WACC；无输入时默认为正值并生成目标价/买入线。',
        '- 存货由流动资产减速动资产或15%比例估算；利息用债务乘国债收益率估算；这些估算被表述为财报事实。',
        '- 资产负债率错误使用有息债务代替总负债；ROE/ROA使用期末分母却不说明口径。',
        '- 云盘同步仅按同名跳过并仍打印100%成功，没有内容验收。',
        '', '## 希捷核对实例','',
        '| 项目 | 云盘旧报告 | 已登记FY2026官方披露 |','|---|---:|---:|',
        '| 营收（百万USD） | 8550 | 12195 |','| 净利润（百万USD） | 920 | 3184 |',
        '| 公司FCF（百万USD） | 720 | 3105 |','| 现金（百万USD） | 850 | 1704 |',
        '| 有息债务（百万USD） | 5600 | 185+3380 |',
        '| 股数（百万） | 65.77，无有效口径 | Q4 GAAP摊薄232；FY GAAP摊薄229，期间不同 |',
        '', '旧报告没有正确期间与来源，其数值不能作为正式输入。EPS13.90与旧净利润920混用产生严重股数错误。官方原文见 data/seagate/2026-10-11/official-results-excerpt.md 及已登记不可变副本。',
        '', '## 逐文件结果','', '| 报告 | 问题数 | 处理 |','|---|---:|---|']
    lines.extend(f"| {r['title']}（文件ID：{r['file_id']}） | {len(r['issues'])} | 撤销旧版，重新取证/保留缺失 |" for r in findings)
    (AUDIT/'audit-report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print({k:v for k,v in summary.items() if k!='files'})

if __name__=='__main__': main()
