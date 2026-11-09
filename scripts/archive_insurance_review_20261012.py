"""登记本次浏览器已核对的Chubb原表；不联网、不根据总额反推拆分。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    rows=[('cb_pc_loss_ratio_q4','财险赔付及理赔费用率','54.3','0.543'),
        ('cb_pc_acquisition_ratio_q4','财险保单获取成本率','18.9','0.189'),
        ('cb_pc_admin_ratio_q4','财险管理费用率','8.0','0.080'),
        ('cb_pc_combined_ratio_q4','财险综合成本率','81.2','0.812')]
    limitation='集团财险、剔除寿险；包含大灾、前期准备金发展及作物衍生品已实现损益调整；仅2025Q4报告精度'
    bindings=[dict(component=c,parent_metric_id='insurance_driver_1',name_zh=n,binding_role='reported_metric',
        limitation_zh=limitation,raw_unit='percent',unit='ratio') for c,n,raw,value in rows]
    excerpts=['Summary Consolidated Financial Data (Unaudited); Three Months Ended December 31 2025 2024; Year Ended December 31 2025 2024',
        'Loss and loss expense ratio 54.3% 59.4% 59.1% 60.4%',
        'Policy acquisition cost ratio 18.9% 18.4% 18.6% 18.1%',
        'Administrative expense ratio 8.0% 7.9% 8.0% 8.1%',
        'P&C combined ratio 81.2% 85.7% 85.7% 86.6%',
        'P&C combined ratio is the sum of the loss and loss expense ratio, acquisition cost ratio and the administrative expense ratio excluding the life business and including the realized gains and losses on the crop derivatives, as noted above.']
    observations=[dict(b,raw_value=row[2],value=row[3],conversion='percent_divided_by_100',
        scope='group_pc_excludes_life_includes_cats_ppd_crop_derivatives',period_start='2025-10-01',period_end='2025-12-31',
        period_type='quarterly',excerpt_indices=[0,i+1,5]) for i,(b,row) in enumerate(zip(bindings,rows))]
    outputs={
        'knowledge/metrics/insurance-reviewed-bindings-20261012.json':dict(schema_version='1.0.0',bindings=bindings),
        'data/browser-search/insurance-reviewed-20261012.json':dict(schema_version='1.0.0',observed_at='2026-10-12T01:41:00Z',
            archive_kind='manual_browser_visible_excerpt',not_full_original_document=True,
            sources=[dict(industry_id='insurance',published_date='2026-02-03',
                source_url='https://investors.chubb.com/News--Events/news/news-details/2026/Chubb-Reports-Fourth-Quarter/default.aspx',
                locator='Summary Consolidated Financial Data: P&C combined ratio rows, first numeric column Q4 2025; Regulation G combined-ratio definition',
                excerpts=excerpts,observations=observations)])}
    for relative,data in outputs.items():
        with (ROOT/relative).open('x',encoding='utf8') as out:
            json.dump(data,out,ensure_ascii=False,indent=2);out.write('\n')

if __name__=='__main__': main()
