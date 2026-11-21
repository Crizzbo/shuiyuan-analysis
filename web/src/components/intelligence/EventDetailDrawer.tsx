import React from 'react'
import type { EventItem } from '../../types/api'
import { toList, formatSourceName } from '../../utils/format'
import {
  SeverityBadge,
  VerificationBadge,
  EntityPills,
  MicroImpactBox,
} from '../common'

export interface EventDetailDrawerProps {
  activeEvent: EventItem | null
  detailLoading: boolean
  onClose: () => void
  onSelectTicker?: (ticker: string) => void
}

/**
 * 权威事件深度详情抽屉 (Event Detail Drawer)
 * 穿透展示官方信源、时间戳、未核实隔离警示与微观因果传导分析
 */
export const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({
  activeEvent,
  detailLoading,
  onClose,
  onSelectTicker,
}) => {
  if (!activeEvent) return null

  return (
    <div className="lg:col-span-5 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 sticky top-24 max-h-[85vh] overflow-y-auto space-y-5 shadow-sm">
      {/* 头部状态与关闭按钮 */}
      <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <SeverityBadge level={activeEvent.severity} />
          <VerificationBadge status={activeEvent.verification_status} />
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 cursor-pointer transition-colors"
        >
          ✕ 关闭面板
        </button>
      </div>

      {detailLoading ? (
        <div className="py-8 text-center text-xs text-[var(--text-muted)]">加载详情中...</div>
      ) : (
        <>
          <div>
            <h2 className="text-base font-bold text-[var(--text-primary)] leading-snug">
              {activeEvent.title}
            </h2>
            <div className="text-xs text-[var(--text-muted)] mt-2.5 flex flex-wrap items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] font-mono text-[#176249] font-bold">
                发布日期: {activeEvent.published_date || activeEvent.published_at?.slice(0, 10)}
              </span>
              {activeEvent.published_time && (
                <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] font-mono text-[var(--text-secondary)] font-medium">
                  确切时间: {activeEvent.published_time}
                </span>
              )}
              {activeEvent.source_name && (
                <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                  信源: {formatSourceName(activeEvent.source_name)}
                </span>
              )}
              {activeEvent.estimated_duration && (
                <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                  预期影响周期: {activeEvent.estimated_duration}
                </span>
              )}
            </div>
          </div>

          {activeEvent.is_quarantined_rumor && (
            <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-800 space-y-1.5">
              <div className="font-bold text-rose-700 flex items-center gap-1.5">
                <span>未核实传闻已启动安全隔离</span>
              </div>
              <p className="text-[11px] opacity-90 leading-relaxed">
                {activeEvent.verification_note ||
                  '该情报尚未获得上市公司正式公告或权威监管机构核验。为防范虚假信息干扰，系统已对其建立安全隔离，严禁直接输入至估值测算与量化风控中。'}
              </p>
            </div>
          )}

          <div className="space-y-1.5">
            <MicroImpactBox
              impact={activeEvent.micro_physical_impact || '暂无结构化微观业务传导分析'}
              category={activeEvent.category}
              title="业务冲击与微观传导分析"
            />
          </div>

          <div className="space-y-1.5">
            <div className="text-xs font-bold text-[var(--text-primary)]">关联标的与受影响业务</div>
            <div className="flex flex-wrap items-center gap-1.5">
              <EntityPills entities={activeEvent.involved_entities} onSelectTicker={onSelectTicker} />
              {toList(activeEvent.affected_business_segments).map((seg, idx) => (
                <span
                  key={idx}
                  className="text-xs px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200"
                >
                  {seg}
                </span>
              ))}
            </div>
          </div>

          {activeEvent.raw_content && (
            <div className="space-y-1.5">
              <div className="text-xs font-bold text-[var(--text-primary)]">原始情报摘要</div>
              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3 text-[11px] text-[var(--text-muted)] max-h-40 overflow-y-auto leading-relaxed">
                {activeEvent.raw_content}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
