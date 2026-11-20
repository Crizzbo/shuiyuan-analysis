import type { CompanyAnalysisData } from '../../types/api'
import { EventCard } from '../common'

interface EventImpactStreamCardProps {
  eventsAnalysis: CompanyAnalysisData['events_analysis']
}

export function EventImpactStreamCard({ eventsAnalysis }: EventImpactStreamCardProps) {
  return (
    <div id="sec-radar" className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-slate-400" />
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            重要事件与业务影响 (Event Radar Impact)
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
            已匹配 {eventsAnalysis?.matched_count ?? eventsAnalysis?.total_events_count ?? 0} 篇权威事件
          </span>
          {eventsAnalysis?.sotp_impact?.estimated_enterprise_value_delta_pct !== undefined && (
            <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${
              eventsAnalysis.sotp_impact.estimated_enterprise_value_delta_pct >= 0
                ? 'bg-rose-50 text-rose-700 border-rose-200'
                : 'bg-blue-50 text-blue-700 border-blue-200'
            }`}>
              企业价值预估变动: {eventsAnalysis.sotp_impact.estimated_enterprise_value_delta_pct > 0 ? '+' : ''}
              {eventsAnalysis.sotp_impact.estimated_enterprise_value_delta_pct.toFixed(2)}%
            </span>
          )}
        </div>
      </div>

      {/* SOTP 分部因果冲击矩阵 */}
      {eventsAnalysis?.sotp_impact?.segment_impacts && eventsAnalysis.sotp_impact.segment_impacts.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span>SOTP 业务分部因果冲击测算 (SOTP Business Segment Sensitivity)</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {eventsAnalysis.sotp_impact.segment_impacts.map((seg: any, sIdx: number) => (
              <div key={sIdx} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-[var(--text-primary)]">{seg.segment_name}</span>
                  <div className="flex items-center gap-2 text-[10px] font-mono">
                    <span className={seg.revenue_impact_pct >= 0 ? 'text-rose-600' : 'text-blue-600'}>
                      营收冲击: {seg.revenue_impact_pct >= 0 ? '+' : ''}{seg.revenue_impact_pct.toFixed(1)}%
                    </span>
                    <span className={seg.margin_impact_bps >= 0 ? 'text-rose-600' : 'text-blue-600'}>
                      利润率: {seg.margin_impact_bps >= 0 ? '+' : ''}{seg.margin_impact_bps} bps
                    </span>
                  </div>
                </div>
                <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                  {seg.qualitative_summary}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 关联事件明细流 */}
      {eventsAnalysis?.recent_events && eventsAnalysis.recent_events.length > 0 ? (
        <div className="space-y-2.5">
          <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span>近期高关联突发事件与微观业务传导</span>
          </div>
          <div className="space-y-2">
            {eventsAnalysis.recent_events.map((evt) => (
              <EventCard
                key={evt.event_id}
                id={evt.event_id}
                title={evt.title}
                severity={evt.severity}
                verification_status={evt.verification_status}
                published_at={evt.published_at}
                micro_physical_impact={evt.micro_physical_impact}
                involved_entities={evt.involved_entities}
                affected_business_segments={evt.affected_business_segments}
                compact
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="p-6 text-center text-xs text-[var(--text-muted)] bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]">
          未检测到针对当前标的的重大突发舆情或隔离事件，宏观与产业链传导保持平稳。
        </div>
      )}
    </div>
  )
}
