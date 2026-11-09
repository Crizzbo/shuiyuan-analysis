"""归档本次浏览器下载的PDF的已核对表格；仅本地提取，不自动联网取数。"""
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]

def main():
    pdf='data/browser-search/originals/vz_4q25_fs_013026.pdf'
    page=PdfReader(ROOT/pdf).pages[9].extract_text()
    excerpts=[line for line in page.splitlines() if line.startswith(('Retail postpaid phone  1.02','Retail core prepaid ARPU(4) $ 32.90','(4)  Wireless retail core prepaid ARPU','Unaudited','3 Mos. Ended','12/31/25'))]
    required=['Retail postpaid phone  1.02 %  0.92 %  0.98 %  0.88 %','Retail core prepaid ARPU(4) $ 32.90 $ 32.34 1.7 $ 32.52 $ 32.37 0.5']
    if not all(line in excerpts for line in required): raise ValueError('已核对PDF表格内容变化')
    bindings=[dict(component='vz_total_postpaid_phone_churn_q4',parent_metric_id='telecom_driver_2',
        name_zh='全无线后付费电话季度报告流失率',binding_role='reported_metric',
        limitation_zh='消费者和企业无线合计后付费电话；不是全设备或预付费流失率；断开数和平均连接数未取得',raw_unit='percent',unit='ratio'),
        dict(component='vz_core_prepaid_arpu_q4',parent_metric_id='telecom_driver_1',
        name_zh='核心预付费每连接报告服务收入',binding_role='context_sample',
        limitation_zh='剔除SafeLink的预付费ARPU；不是后付费ARPA，服务收入及平均同群连接数未拆出，不能充当公式分子分母',raw_unit='USD_per_connection',unit='USD_per_connection')]
    observations=[]
    for binding,raw,value,conversion,scope,needle in [
        (bindings[0],'1.02','0.0102','percent_divided_by_100','total_wireless_retail_postpaid_phone',required[0]),
        (bindings[1],'32.90','32.90','identity','core_prepaid_excludes_safelink',required[1])]:
        observations.append(dict(binding,raw_value=raw,value=value,conversion=conversion,
            period_start='2025-10-01',period_end='2025-12-31',period_type='quarterly',scope=scope,
            excerpt_indices=[excerpts.index(needle)]))
    url='https://www.verizon.com/about/file/77271/download?token=r9Yg9nOj'
    source=dict(industry_id='telecom',published_date='2026-01-30',source_url=url,
        locator='官方4Q25财务补充表第10页，Total Wireless Operating and Financial Statistics，3 Mos. Ended 12/31/25列；完整PDF已下载',
        excerpts=excerpts,observations=observations,
        original_document=dict(path=pdf,sha256=hashlib.sha256((ROOT/pdf).read_bytes()).hexdigest(),source_url=url,excerpt_pages=[10]*len(excerpts)))
    outputs={
        'data/browser-search/telecom-reviewed-20261012.json':dict(schema_version='1.0.0',observed_at='2026-10-12T01:37:06Z',archive_kind='manual_browser_visible_excerpt_with_optional_original_pdf',sources=[source]),
        'knowledge/metrics/telecom-reviewed-bindings-20261012.json':dict(schema_version='1.0.0',bindings=bindings),
        'knowledge/metrics/telecom-reviewed-sources-20261012.json':dict(schema_version='1.0.0',sources={'telecom':[url]})}
    for relative,data in outputs.items():
        with (ROOT/relative).open('x',encoding='utf8') as out:
            json.dump(data,out,ensure_ascii=False,indent=2);out.write('\n')
    print('已归档本次官方PDF及两项明确口径观测；脚本不联网')

if __name__=='__main__': main()
