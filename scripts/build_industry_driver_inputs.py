"""输出统一目录和逐行业输入表；缺口来自原始规格，不宣称所有公开材料未披露。"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.industry_inputs import register_ledger, verify_ledger
from financial_reporting.industry_specific import verify_snapshot

def main():
    latest=json.loads((ROOT/'data/financial/industry-specific-verification.json').read_text(encoding='utf8'))
    index=register_ledger(latest['snapshot_path'])
    (ROOT/'data/financial/industry-driver-input-verification.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    ledger=verify_ledger(json.loads((ROOT/index['snapshot_path']).read_text(encoding='utf8')))
    observations=verify_snapshot(latest['snapshot_path'])['observations']
    byid={o['observation_id']:o for o in observations}
    reps=json.loads((ROOT/'knowledge/metrics/representatives.json').read_text(encoding='utf8'))['representatives']
    labels={'input_complete':'必需输入已齐备','partial_inputs':'部分必需输入已绑定','pending_input_binding':'必需输入尚未绑定'}
    directory=ROOT/'knowledge/metrics/driver-inputs';directory.mkdir(exist_ok=True)
    overview=['# 行业驱动输入统一目录','',f"覆盖 41 个行业、123 个驱动。必需输入齐备 {index['input_complete']} 项，其中选定口径可计算 {index['calculation_ready']} 项；部分绑定 {index['partial_inputs']} 项，其余 {index['pending_input_binding']} 项待绑定。",'','输入齐备仅针对表内所选公司、产品、范围和期间，不表示最新季度覆盖、全部商业模式覆盖或六步研究完成。尚未绑定不等于所有来源均未披露；口径差异、背景数值不计入必需输入。', '', '[机器可读台账索引](../../../data/financial/industry-driver-input-verification.json) · [绑定方案](../industry-input-binding-plans.json) · [说明书](../../../docs/industry-driver-inputs.md)','', '| 行业及分表 | 代表公司 | 驱动 1 | 驱动 2 | 驱动 3 |','|---|---|---|---|---|']
    for rep in reps:
        industry=rep['industry_id'];drivers=[d for d in ledger['drivers'] if d['industry_id']==industry]
        overview.append('| '+' | '.join([f'[{industry}]({industry}.md)',rep['name'],*[labels[d['input_status']] for d in drivers]])+' |')
        lines=[f'# {industry} 行业驱动输入表','',f"代表公司：{rep['name']}（{rep['market']}:{rep['ticker']}）。",'', '[统一目录](README.md) · [原始行业字典](../industry-specific/'+industry+'.md)','']
        for d in drivers:
            lines += [f"## {d['parent_metric_id']} — {d['name_zh']}",'',d['business_definition_zh'],'',f"选用口径：{d['selected_variant_zh']}。输入状态：{labels[d['input_status']]}。定义状态：{d['definition_status']}。",'','| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |','|---|---|---|---|---|']
            for slot in d['slots']:
                obs='；'.join(b['component']+' / '+b['unit']+('（范围元数据）' if b['kind']=='scope_metadata' else '（期间元数据）' if b['kind']=='period_metadata' else '') for b in slot['bindings']) or '待补'
                refs='；'.join(b['source_ref']['source_id']+' r'+str(b['source_ref']['revision']) for b in slot['bindings']) or '无匹配证据'
                lines.append('| '+' | '.join([slot['slot_id'],slot['name_zh'],'已绑定' if slot['status']=='bound' else '缺失',obs,refs])+' |')
            lines+=['','限制：'+'；'.join(d['limitations_zh'])+'。','', '| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |','|---|---|---|---|---|']
            for identifier in d['related_observation_ids']:
                o=byid[identifier]
                lines.append('| '+' | '.join([o.get('name_zh',o['component']),o['raw_value']+' '+o['raw_unit'],o['value']+' '+o['unit'],str(o['period_start'])+' 至 '+o['period_end']+' / '+o['scope'],o.get('binding_role','早期审核样本')+'；'+o.get('limitation_zh','完整定义待核')])+' |')
            lines+=['','研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。','']
        (directory/(industry+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf8')
    (directory/'README.md').write_text('\n'.join(overview)+'\n',encoding='utf8')
    print(json.dumps(index,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
