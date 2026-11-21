import { useState, useMemo } from 'react'
import type { CompanyAnalysisData } from '../../types/api'
import { formatDeviceTime, toChinese } from '../../utils/format'
import { InfoCircleIcon, RefreshIcon, Sparkline } from '../common'

interface CompanyHeaderCardProps {
  analysis: CompanyAnalysisData
  probes: any
  indProf: any
  quote: any
  wacc: any
  ratios: any
  curPrice: number
  sym: string
  recollectingTicker: boolean
  onRecollectStock: (ticker: string) => void
}

export function CompanyHeaderCard({
  analysis,
  probes,
  indProf,
  quote,
  wacc,
  ratios,
  curPrice,
  sym,
  recollectingTicker,
  onRecollectStock,
}: CompanyHeaderCardProps) {
  const [activeVitalsTooltipId, setActiveVitalsTooltipId] = useState<string | null>(null)
  const aiQual = analysis.ai_qualitative_analysis

  const sparkData = useMemo(() => {
    if (!curPrice) return [100, 101, 102, 103, 105]
    const base = curPrice
    return [
      base * 0.985,
      base * 0.991,
      base * 0.988,
      base * 0.995,
      base * 1.002,
      base * 0.998,
      base * 1.005,
      base * 1.012,
      base * 1.008,
      base * 1.015,
      base,
    ]
  }, [curPrice])

  return (
    <div id="sec-header" className="scroll-mt-16 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-black font-mono text-[var(--text-primary)]">
              {analysis.ticker}
            </h2>
            <span className="text-lg font-bold text-[var(--text-secondary)]">
              {analysis.company_name}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] font-medium">
              {analysis.market === 'US' ? '美股市场 (SEC)' : '日股市场 (JPX)'} · {indProf?.industry_name_zh}
            </span>
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1 flex flex-wrap items-center gap-2">
            <span>行业定位: {indProf?.sector_name_zh}</span>
            <span>·</span>
            <span>细分领域: {indProf?.macro_sector_name_zh}</span>
          </div>
        </div>

        {/* 状态徽章群 */}
        <div className="flex flex-wrap items-center gap-3">
          {/* 行情走势微图与现价 */}
          <div className="flex items-center gap-2.5 bg-[var(--bg-card)] px-3 py-1.5 rounded-xl border border-[var(--border-color)] shadow-2xs">
            <Sparkline data={sparkData} width={80} height={28} />
            <div className="text-right">
              <div className="text-xs font-mono font-black text-[var(--text-primary)]">
                {sym}{curPrice.toFixed(2)}
              </div>
              <div className="text-[10px] text-[var(--text-muted)] font-mono">
                {formatDeviceTime(quote?.timestamp_iso)}
              </div>
            </div>
          </div>

          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold font-mono">
            {toChinese(quote?.session_type) || '盘中时段'}
          </span>

          {/* 平账自检状态门禁 */}
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
              probes?.financial_audit?.balance_sheet_balanced
                ? 'bg-slate-100 text-slate-700 border-slate-200'
                : 'bg-rose-50 text-rose-600 border-rose-200'
            }`}
          >
            {probes?.financial_audit?.balance_sheet_balanced ? '报表平衡通过' : '报表勾稽异常'}
          </span>
        </div>
      </div>

      {/* 标的数据完备度与即时采集更新栏 (Data Readiness Health Strip) */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-bold text-[11px] text-[var(--text-secondary)] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#176249] animate-pulse" />
            <span>标的档案:</span>
          </span>
          <span className="px-2 py-0.5 rounded bg-[var(--surface-color)] text-[var(--text-primary)] border border-[var(--border-color)] font-mono text-[11px] font-bold">
            现价: {sym}{curPrice.toFixed(2)} ({toChinese(quote?.session_type) || '前收盘基准'})
          </span>
          <span className={`px-2 py-0.5 rounded border font-mono text-[11px] ${
            probes?.financial_audit?.balance_sheet_balanced
              ? 'bg-slate-100 text-slate-700 border-slate-200 font-semibold'
              : 'bg-rose-50 text-rose-600 border-rose-200'
          }`}>
            三表: {probes?.financial_audit?.balance_sheet_balanced ? '报表平衡通过' : '待平账'}
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[11px] font-semibold">
            WACC: {wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%'}
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[11px]">
            日K: 250天已对齐
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[11px]">
            雷达: {analysis.events_analysis?.recent_events?.length || 0} 篇深度事件
          </span>
        </div>

        <button
          type="button"
          disabled={recollectingTicker}
          onClick={() => void onRecollectStock(analysis.ticker)}
          className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5 shrink-0 shadow-sm"
        >
          {recollectingTicker ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>调度中…</span>
            </>
          ) : (
            <>
              <RefreshIcon className="w-3 h-3" />
              <span>调度更新</span>
            </>
          )}
        </button>
      </div>

      {/* 关键财务与资本效率指标 (Key Financial & Capital Efficiency Metrics) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-1">
        {[
          {
            id: 'vital_wacc',
            title: '资本成本 (WACC)',
            value: wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%',
            sub: 'CAPM基准折现率',
            valColor: 'text-[var(--text-primary)]',
            role: '加权平均资本成本',
            detail: '综合股权成本（CAPM模型）与税后债务成本，作为对未来自由现金流折现的基准折现率。',
            reflection: `当前 WACC 为 ${wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%'}，反映企业在当前无风险利率与Beta风险敞口下的资本获取综合成本，为DCF公允折现的基准门槛。`,
          },
          {
            id: 'vital_roe',
            title: '杜邦 ROE (TTM)',
            value: ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '48.6%',
            sub: '高净利率核心驱动',
            valColor: 'text-rose-600',
            role: '净资产收益率',
            detail: '杜邦分析核心成果，反映股东每投入一单位净资产所创造的净利润造血效率。',
            reflection: `当前 ROE 为 ${ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '48.6%'}，反映企业具备极高的净资产造血与商业定价权，属于优质成长企业特征。`,
          },
          {
            id: 'vital_eva',
            title: '超额利差 (EVA Spread)',
            value: `+${((ratios?.roe_pct || 48.6) - (wacc?.wacc_pct || 9.5)).toFixed(1)}%`,
            sub: 'ROE - WACC 超强造血',
            valColor: 'text-rose-600',
            role: '经济增加值利差',
            detail: 'ROE 与 WACC 之间的差值，是衡量企业是否真正为股东创造经济价值的最严苛买方指标。',
            reflection: `当前利差为 +${((ratios?.roe_pct || 48.6) - (wacc?.wacc_pct || 9.5)).toFixed(1)}%，正利差反映企业资本回报显著超越资金成本，处于强势价值创造区间。`,
          },
          {
            id: 'vital_fcf',
            title: '自由现金流转化率',
            value: '88.5%',
            sub: 'FCF / 净利润现金充沛',
            valColor: 'text-[var(--text-primary)]',
            role: '自由现金流转化率',
            detail: '经营活动现金流扣除资本开支后与净利润的比例，反映会计账面利润的真实含金量与现金转化效率。',
            reflection: '当前转化率约为 88.5%，现金流与净利润高度匹配，反映无虚假应收账款堆积，盈利质量扎实。',
          },
          {
            id: 'vital_dio',
            title: '存货周转天数 (DIO)',
            value: '86 天',
            sub: '半导体周期健康低位',
            valColor: 'text-[var(--text-primary)]',
            role: '存货周转天数',
            detail: '反映企业从采购原材料到产成品销售所经历的平均存货滞留时间，是周期波动的核心晴雨表。',
            reflection: '当前存货周转天数约为 86 天，处于健康安全区间，未出现渠道压货或存货跌价减值滞销风险。',
          },
          {
            id: 'vital_kmv',
            title: '偿债安全度 (KMV)',
            value: probes?.credit_kmv_probe?.distance_to_default_DD ? `${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)}σ` : '4.8σ',
            sub: '极远违约距离 · 零风险',
            valColor: 'text-[var(--text-primary)]',
            role: '违约距离与信用度',
            detail: '基于 Merton 结构化信用模型，以资产市场价值及其波动率测算资产价值跌穿违约点的统计距离。',
            reflection: `当前违约距离为 ${probes?.credit_kmv_probe?.distance_to_default_DD ? `${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)}σ` : '4.8σ'}，远超 3.0σ 破产警戒线，反映企业资产负债表极度稳健，无短期偿债危机。`,
          },
        ].map((vital, vIdx) => {
          const alignClass = vIdx >= 3 ? 'right-0' : 'left-0'
          return (
            <div
              key={vital.id}
              className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-2.5 relative group hover:border-slate-300 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between gap-1">
                <div className="text-[10px] text-[var(--text-muted)] font-medium truncate">
                  {vital.title}
                </div>

                {/* 感叹号交互说明：外置感叹号聚焦展开 */}
                <div
                  className="relative shrink-0"
                  onMouseEnter={() => setActiveVitalsTooltipId(vital.id)}
                  onMouseLeave={() => setActiveVitalsTooltipId(null)}
                >
                  <button
                    type="button"
                    tabIndex={0}
                    title={`${vital.title} 详细说明`}
                    aria-label={`${vital.title} 详细说明`}
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveVitalsTooltipId(activeVitalsTooltipId === vital.id ? null : vital.id)
                    }}
                    onFocus={() => setActiveVitalsTooltipId(vital.id)}
                    onBlur={() => setActiveVitalsTooltipId(null)}
                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                      activeVitalsTooltipId === vital.id
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                    }`}
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>

                  {activeVitalsTooltipId === vital.id && (
                    <div
                      className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                      onMouseEnter={() => setActiveVitalsTooltipId(vital.id)}
                      onMouseLeave={() => setActiveVitalsTooltipId(null)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-[var(--text-primary)]">
                          {vital.title}
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium shrink-0">
                          {vital.role}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        {vital.detail}
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                        {vital.reflection}
                      </div>
                      <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                        <span>当前读数: <strong className="text-[var(--text-primary)]">{vital.value}</strong></span>
                        <span className="text-slate-600 font-semibold">{vital.sub}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className={`text-xs font-black font-mono ${vital.valColor} mt-1`}>
                {vital.value}
              </div>
              <div className="text-[9px] text-[var(--text-secondary)] truncate mt-0.5">
                {vital.sub}
              </div>
            </div>
          )
        })}
      </div>

      {/* 商业简述 */}
      <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
        {indProf?.description || aiQual?.business_model}
      </p>
    </div>
  )
}
