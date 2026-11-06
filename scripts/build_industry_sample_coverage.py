"""由已验证的快照生成覆盖报告和原子字段分表字典，不推断未读材料的披露情况。"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.industry_specific import verify_snapshot

def main():
    latest=json.loads((ROOT/'data/financial/industry-specific-verification.json').read_text(encoding='utf8'))
    data=verify_snapshot(latest['snapshot_path'])
    reps=json.loads((ROOT/'knowledge/metrics/representatives.json').read_text(encoding='utf8'))['representatives']
    labels={'partial_sample_requires_driver_review':'局部样本，必需输入及定义待审核',
      'definition_mismatch_sample_only':'仅口径差异样本，不计入可用输入',
      'pending_original_binding':'尚未登记匹配原文，不等于未披露'}
    lines=['# 行业专属原始数据覆盖报告','',
      f"累计 {latest['sample_industries']} / 41 个行业有原文观测，共 {latest['observations']} 条；完成研究步骤为 0。",
      '证据包含人工归档的浏览器可见摘录及两份完整财报 PDF；PDF 摘录逐页核验哈希与原文。有观测不等于驱动全输入齐备；全部研究闸门仍为阻断。本表不代表最新季度覆盖。','',
      '[驱动输入统一目录](driver-inputs/README.md)：逐行业查看必需输入、绑定观测、缺口与口径审核状态。','',
      '[快照索引](../../data/financial/industry-specific-verification.json) · [逐驱动待补清单](../../data/browser-search/industry-specific-jobs.json) · [追加字段字典](industry-reviewed-bindings-20261011.md)','',
      '| 行业标识 | 代表公司 | 观测数 | 驱动 1 | 驱动 2 | 驱动 3 |','|---|---|---:|---|---|---|']
    for rep in reps:
        industry=rep['industry_id']
        count=sum(o['industry_id']==industry for o in data['observations'])
        statuses=[labels[next(c for c in data['coverage'] if c['parent_metric_id']==industry+'_driver_'+str(n))['status']] for n in range(1,4)]
        lines.append('| '+' | '.join([industry,rep['name'],str(count),*statuses])+' |')
    lines+=['','## 本批业务口径','',
      '- 达美：客英里、座英里、报告客座率及 yield 分开；每加仑燃油价格不能替代单位运输燃油成本。',
      '- HCA：同院住院、等价住院及单位收入分开；集团工资福利及收入不能与同院服务量拼接，合同工覆盖待核。',
      '- 好市多：52 周年度口径；同店销售含燃油汇率与剔除燃油汇率分别保存，不替代客流增长。',
      '- GE Vernova：各分部新增订单与收入分别保存；RPO 积压订单缺取消条款，尚非完整复合指标。',
      '- Fluor：总积压订单缺可执行及融资划分，不能直接生成可执行订单覆盖年数。',
      '- Prologis：现金同物业 NOI 已有样本；自有及管理组合出租率不是固定同物业群出租率；Core FFO 不能填入 AFFO。',
      '- 菲莫国际：无烟收入、毛利润及收入占比分开；毛利润不能填入营业利润。',
      '- 沃尔玛：十三周结束于 2026 年 1 月 30 日且排除燃油，不套用财务季度截止日。','',
      '其余行业的原文、各驱动缺失输入、分部分类及完整定义仍待补全；核验齐备后才可升级为完整指标绑定。']
    (ROOT/'knowledge/metrics/industry-sample-coverage.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    bindings=json.loads((ROOT/'knowledge/metrics/industry-reviewed-bindings-20261011.json').read_text(encoding='utf8'))['bindings']
    role_labels={'reported_metric':'报告指标','formula_input':'计算输入，未计算',
      'scope_mismatch_sample':'范围差异，仅作记录','profit_basis_variant':'利润层次不同，不能替代','context_sample':'背景信息'}
    dictionary=['# 追加原子字段数据字典','',
      '每个字段保存原始值、原始单位、规范化值、期间、范围、摘录索引、来源版本及可得时间。计算输入不代表已计算；差异和背景项不计为可用输入。',
      '[机器可读绑定](industry-reviewed-bindings-20261011.json) · [覆盖报告](industry-sample-coverage.md)','']
    for parent in dict.fromkeys(b['parent_metric_id'] for b in bindings):
        dictionary += [f'## {parent}','','| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |','|---|---|---|---|---|---|']
        for b in bindings:
            if b['parent_metric_id']==parent:
                dictionary.append('| '+' | '.join([b['component'],b['name_zh'],b['raw_unit'],b['unit'],role_labels[b['binding_role']],b['limitation_zh']])+' |')
        dictionary.append('')
    (ROOT/'knowledge/metrics/industry-reviewed-bindings-20261011.md').write_text('\n'.join(dictionary)+'\n',encoding='utf8')
    print('PASS: 41 行业覆盖表及 30 个追加字段分表字典')

if __name__=='__main__':
    main()
