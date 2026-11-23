import React, { useMemo } from 'react'
import type { EventItem, EventsData } from '../../types/api'
import { Pagination } from '../Pagination'
import { toList, getSeverityBadge, getVerificationBadge, formatSourceName, formatCredibilityTier } from '../../utils/format'
import {
  EntityPills,
  MicroImpactBox,
  CalendarIcon,
  ShieldCheckIcon,
  FilterIcon,
  SearchIcon,
  XIcon,
} from '../common'
import { EventDetailDrawer } from './EventDetailDrawer'
import { CardListSkeleton } from '../common/Skeleton'

export interface EventRadarViewProps {
  data: EventsData | null
  loading: boolean
  severityFilter: string
  setSeverityFilter: (s: string) => void
  statusFilter: string
  setStatusFilter: (s: string) => void
  dateFilter: string
  setDateFilter: (d: string) => void
  segmentFilter: string
  setSegmentFilter: (s: string) => void
  searchQuery: string
  setSearchQuery: (q: string) => void
  onSearch: () => void
  currentPage: number
  setCurrentPage: (p: number) => void
  pageSize: number
  activeEvent: EventItem | null
  detailLoading: boolean
  onSelectEvent: (eventId: string) => void
  onCloseDetail: () => void
  onSelectTicker?: (ticker: string) => void
}

const SEVERITY_FILTERS = [
  { id: 'ALL', label: '全部级别' },
  { id: 'P0', label: '极高影响' },
  { id: 'P1', label: '重要关注' },
  { id: 'P2', label: '行业动态' },
  { id: 'P3', label: '常规资讯' },
]

function cleanContentSnippet(raw?: string): string {
  if (!raw) return ''
  let text = raw.replace(/<(?:br|p|div)\s*\/?>/gi, ' · ').replace(/<[^>]+>/g, ' ')
  text = text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
  text = text.replace(/\s+/g, ' ').trim()
  return text.replace(/^[·\s]+/, '').replace(/[·\s]+$/, '')
}

/**
 * 事件雷达全息深度研判子视图 (Event Radar View)
 * 提供双层子菜单分类检索、精准日历筛选、板块切片与事件列表/详情抽屉联动
 */
export const EventRadarView: React.FC<EventRadarViewProps> = ({
  data,
  loading,
  severityFilter,
  setSeverityFilter,
  statusFilter,
  setStatusFilter,
  dateFilter,
  setDateFilter,
  segmentFilter,
  setSegmentFilter,
  searchQuery,
  setSearchQuery,
  onSearch,
  currentPage,
  setCurrentPage,
  pageSize,
  activeEvent,
  detailLoading,
  onSelectEvent,
  onCloseDetail,
  onSelectTicker,
}) => {
  const eventsList = data?.events
  const allEvents = useMemo(() => eventsList || [], [eventsList])
  const sevCounts = data?.severity_counts || {}
  const availableDates = data?.available_dates || []
  const dateCounts = data?.date_counts || {}

  // 提取业务分部
  const availableSegments = useMemo(() => {
    const set = new Set<string>()
    allEvents.forEach((ev) => {
      toList(ev.affected_business_segments).forEach((s) => {
        const clean = String(s).trim()
        if (clean && clean !== 'General' && clean !== '通用' && clean !== '通用产业') {
          set.add(clean)
        }
      })
    })
    return Array.from(set).sort()
  }, [allEvents])

  // 分部过滤
  const filteredEvents = useMemo(() => {
    if (segmentFilter === 'ALL') return allEvents
    return allEvents.filter((ev) =>
      toList(ev.affected_business_segments).includes(segmentFilter)
    )
  }, [allEvents, segmentFilter])

  const totalItems = filteredEvents.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const pagedEvents = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredEvents.slice(start, start + pageSize)
  }, [filteredEvents, currentPage, pageSize])

  return (
    <div className="space-y-6">
      {/* 综合情报控制台 (双层子菜单架构) */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 space-y-3.5 shadow-sm">
        {/* 子菜单一级：影响级别分类导航项 */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]/60">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-[var(--text-muted)] font-semibold text-xs mr-1 shrink-0">情报分类:</span>
            {SEVERITY_FILTERS.map((f) => (
              <button
                type="button"
                key={f.id}
                onClick={() => setSeverityFilter(f.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  severityFilter === f.id
                    ? 'bg-[#176249] text-white shadow-sm'
                    : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-[var(--text-primary)] border border-transparent hover:border-slate-200 dark:hover:border-slate-700'
                }`}
              >
                <span>{f.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    severityFilter === f.id
                      ? 'bg-white/20 text-white'
                      : 'bg-[var(--surface-color)] text-[var(--text-muted)]'
                  }`}
                >
                  {f.id === 'ALL' ? (data?.total_events ?? 0) : (sevCounts[f.id] ?? 0)}
                </span>
              </button>
            ))}
          </div>

          {/* 右侧：总览与已收录统计 */}
          <div className="text-xs text-[var(--text-muted)] font-mono flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#176249] animate-pulse" />
            <span>收录 {availableDates.length} 个历史日期 · 共 {data?.total_events ?? 0} 篇权威事件</span>
          </div>
        </div>

        {/* 子菜单二级：日历精准筛选 + 核验状态 + 可扩展维度 (业务板块) + 搜索框 */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            {/* 1. 日历筛选 (Calendar Picker) */}
            <div className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)] font-medium flex items-center gap-1">
                <CalendarIcon className="w-3.5 h-3.5 text-slate-600" />
                <span>日历筛选:</span>
              </span>
              <div className="relative inline-flex items-center">
                <input
                  type="date"
                  value={dateFilter === 'ALL' ? '' : dateFilter}
                  min={availableDates[availableDates.length - 1]}
                  max={availableDates[0]}
                  onChange={(e) => setDateFilter(e.target.value || 'ALL')}
                  className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] hover:border-slate-300 rounded-lg px-2.5 py-1 text-xs font-mono focus:outline-none focus:border-[#176249] cursor-pointer"
                  title="点击日历选择历史日期进行归档精准筛选"
                />
                {dateFilter !== 'ALL' && (
                  <button
                    type="button"
                    onClick={() => setDateFilter('ALL')}
                    className="ml-1.5 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white text-[11px] cursor-pointer transition-all flex items-center gap-1"
                    title="清除日历筛选，恢复查看全部日期"
                  >
                    <span>{dateFilter} ({dateCounts[dateFilter] ?? 0}篇)</span>
                    <XIcon className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* 2. 核验状态子菜单下拉 */}
            <div className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)] font-medium flex items-center gap-1">
                <ShieldCheckIcon className="w-3.5 h-3.5 text-[#176249]" />
                <span>核验状态:</span>
              </span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] hover:border-slate-300 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-[#176249] cursor-pointer"
              >
                <option value="ALL">全部核验状态</option>
                <option value="Confirmed_Fact">官方权威核实</option>
                <option value="Corroborated_Report">主流媒体采信</option>
                <option value="Unverified_Rumor">待核实传闻隔离</option>
              </select>
            </div>

            {/* 3. 子菜单扩展性槽位 (支持按业务板块快速扩展) */}
            <div className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)] font-medium flex items-center gap-1">
                <FilterIcon className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                <span>业务板块:</span>
              </span>
              <select
                value={segmentFilter}
                onChange={(e) => setSegmentFilter(e.target.value)}
                className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] hover:border-slate-300 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-[#176249] cursor-pointer"
              >
                <option value="ALL">全部业务分部</option>
                {availableSegments.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* 搜索框 */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="text"
                placeholder="搜索关联公司、行业板块、事件标题..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onSearch()}
                className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg pl-8 pr-3 py-1.5 text-xs w-56 sm:w-64 focus:outline-none focus:border-[#176249] hover:border-slate-300"
              />
              <SearchIcon className="w-3.5 h-3.5 text-[var(--text-muted)] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
            <button
              type="button"
              onClick={onSearch}
              className="px-3 py-1.5 bg-[#176249] hover:bg-[#124e3a] text-white rounded-lg text-xs font-semibold cursor-pointer transition-all shadow-sm flex items-center gap-1"
            >
              <SearchIcon className="w-3.5 h-3.5" />
              <span>搜索</span>
            </button>
          </div>
        </div>
      </div>

      {/* 主界面：左侧事件列表 + 右侧事件详情抽屉 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className={`space-y-3 ${activeEvent ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          {loading ? (
            <CardListSkeleton count={4} />
          ) : pagedEvents.length > 0 ? (
            <>
              {pagedEvents.map((ev) => {
                const sBadge = getSeverityBadge(ev.severity)
                const vBadge = getVerificationBadge(ev.verification_status)

                return (
                  <div
                    key={ev.event_id}
                    onClick={() => {
                      onSelectEvent(ev.event_id)
                      if (typeof window !== 'undefined' && window.innerWidth < 1024) {
                        setTimeout(() => {
                          document.getElementById('event-detail-drawer')?.scrollIntoView({ behavior: 'smooth' })
                        }, 150)
                      }
                    }}
                    className={`bg-[var(--surface-color)] border rounded-xl p-4 cursor-pointer transition-all ${
                      activeEvent?.event_id === ev.event_id
                        ? 'border-[#176249] ring-1 ring-[#176249]/50'
                        : 'border-[var(--border-color)] hover:border-[#176249]/50'
                    }`}
                  >
                    {/* 顶部状态与信息行 */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold shrink-0 border ${sBadge.cls}`}>
                          {sBadge.text}
                        </span>
                        <div>
                          <h3 className="text-sm font-semibold text-[var(--text-primary)] hover:text-[#176249]">
                            {ev.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-[var(--text-muted)]">
                            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px] font-mono">
                              <span className="text-[#176249] font-bold">
                                {ev.published_date || ev.published_at?.slice(0, 10)}
                              </span>
                              {ev.published_time && (
                                <span className="text-[var(--text-secondary)] font-medium">
                                  {ev.published_time}
                                </span>
                              )}
                            </div>
                            {ev.source_name && (
                              <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px]">
                                信源: {formatSourceName(ev.source_name)}
                              </span>
                            )}
                            {(() => {
                              const cred = formatCredibilityTier(ev.credibility_tier)
                              return cred.text ? (
                                <span className={`px-2 py-0.5 rounded border text-[11px] font-medium ${cred.cls}`}>
                                  {cred.text}
                                </span>
                              ) : null
                            })()}
                          </div>
                        </div>
                      </div>

                      {/* 状态徽章 */}
                      <div className="shrink-0">
                        {ev.is_quarantined_rumor ? (
                          <span className="px-2 py-0.5 rounded text-[11px] bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50 font-semibold flex items-center gap-1">
                            传闻隔离
                          </span>
                        ) : (
                          <span className={`px-2 py-0.5 rounded text-[11px] border font-medium ${vBadge.cls}`}>
                            {vBadge.text}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 微观物理与买方研判解读 */}
                    {ev.micro_physical_impact && (
                      <MicroImpactBox
                        impact={ev.micro_physical_impact}
                        category={ev.category}
                        title="买方微观研判与传导影响"
                      />
                    )}

                    {/* 原始情报与披露事实摘要预览 */}
                    {(ev.clean_content || ev.raw_content) && (
                      <div className="mt-2.5 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]/70 text-xs text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-[var(--text-muted)] mr-1.5 shrink-0">
                          📄 事实概要:
                        </span>
                        <span className="line-clamp-2">
                          {ev.clean_content || cleanContentSnippet(ev.raw_content)}
                        </span>
                      </div>
                    )}

                    {/* 底部关联主体与受影响分部 */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-2.5 border-t border-[var(--border-color)]/50">
                      <div className="flex flex-wrap items-center gap-1.5">
                        {toList(ev.involved_entities).length > 0 && (
                          <>
                            <span className="text-[11px] text-[var(--text-muted)] mr-1">关联主体:</span>
                            <EntityPills entities={ev.involved_entities} onSelectTicker={onSelectTicker} />
                          </>
                        )}
                      </div>
                      {toList(ev.affected_business_segments).length > 0 && (
                        <div className="flex flex-wrap items-center gap-1">
                          {toList(ev.affected_business_segments).slice(0, 3).map((seg, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 font-medium"
                            >
                              {seg}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}

              <div className="pt-2">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  totalItems={totalItems}
                  pageSize={pageSize}
                  onPageChange={setCurrentPage}
                />
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-xs text-[var(--text-muted)] bg-[var(--surface-color)] rounded-xl border border-[var(--border-color)]">
              未找到匹配条件的事件记录
            </div>
          )}
        </div>

        {/* 右侧抽屉：详情面板 */}
        {activeEvent && (
          <EventDetailDrawer
            activeEvent={activeEvent}
            detailLoading={detailLoading}
            onClose={onCloseDetail}
            onSelectTicker={onSelectTicker}
          />
        )}
      </div>
    </div>
  )
}
