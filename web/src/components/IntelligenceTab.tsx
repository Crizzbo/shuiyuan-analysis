import { useState, useEffect, useMemo } from 'react'
import type { EventsData, EventItem } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { Pagination } from './Pagination'
import { formatDeviceTime } from '../utils/format'

interface IntelligenceTabProps {
  selectedEventId?: string | null
  onClearSelectedEvent?: () => void
  refreshKey?: number
}

interface NewsItem {
  title: string
  published_at: string | null
  source: string
}

function toList(val?: string[] | string): string[] {
  if (!val) return []
  if (Array.isArray(val)) return val
  return String(val).split(/\s+/).filter(Boolean)
}

function getSeverityBadge(sev: string) {
  switch (sev) {
    case 'P0':
      return { text: '极高影响', cls: 'bg-[#d03b3b]/20 text-[#d03b3b] border-[#d03b3b]/40' }
    case 'P1':
      return { text: '重要关注', cls: 'bg-[#c98500]/20 text-[#c98500] border-[#c98500]/40' }
    case 'P2':
      return { text: '行业动态', cls: 'bg-[#3987e5]/20 text-[#3987e5] border-[#3987e5]/40' }
    default:
      return { text: '常规资讯', cls: 'bg-gray-600/20 text-gray-400 border-gray-600/30' }
  }
}

function getVerificationBadge(status: string) {
  switch (status) {
    case 'Confirmed_Fact':
      return { text: '官方权威核实', cls: 'bg-[#199e70]/20 text-[#199e70] border-[#199e70]/40' }
    case 'Corroborated_Report':
      return { text: '主流媒体采信', cls: 'bg-[#3987e5]/20 text-[#3987e5] border-[#3987e5]/40' }
    case 'Unverified_Rumor':
      return { text: '待核实传闻隔离', cls: 'bg-[#d03b3b]/20 text-[#d03b3b] border-[#d03b3b]/40' }
    default:
      return { text: '已归档', cls: 'bg-gray-600/20 text-gray-400 border-gray-600/30' }
  }
}

export function IntelligenceTab({ selectedEventId, onClearSelectedEvent, refreshKey }: IntelligenceTabProps) {
  // 原生视图切换：事件雷达深度研判 vs 官方来源资讯流水
  const [activeView, setActiveView] = useState<'radar' | 'news'>('radar')

  // 1. 事件雷达相关状态
  const [data, setData] = useState<EventsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [dateFilter, setDateFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10
  const [activeEvent, setActiveEvent] = useState<EventItem | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)

  // 2. 官方来源资讯相关状态
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [newsLoading, setNewsLoading] = useState(false)
  const [newsSourceFilter, setNewsSourceFilter] = useState('ALL')
  const [newsSearch, setNewsSearch] = useState('')
  const [newsPage, setNewsPage] = useState(1)
  const newsPageSize = 12

  const handleExtractNews = async () => {
    if (isExtracting) return
    setIsExtracting(true)
    showToast({
      type: 'info',
      title: '官方资讯分时采集',
      message: '正在向后端发起新闻与突发情报即时抽取...',
    })

    try {
      const res = await api.runTerminalTask('OFFICIAL_NEWS')
      if (res.ok) {
        showToast({
          type: 'success',
          title: '官方资讯采集已完成',
          message: '最新官方公告与新闻已归档入库。',
        })
        await Promise.all([loadEvents(), loadNews()])
      } else {
        showToast({
          type: 'error',
          title: '提交采集失败',
          message: res.error?.message || '未能完成事件雷达脉冲采集',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或服务调用异常',
      })
    } finally {
      setIsExtracting(false)
    }
  }

  const loadEvents = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (severityFilter !== 'ALL') params.severity = severityFilter
      if (statusFilter !== 'ALL') params.verification_status = statusFilter
      if (dateFilter !== 'ALL') params.date = dateFilter
      if (searchQuery.trim()) params.q = searchQuery.trim()

      const res = await api.getEvents(params)
      if (res.ok) {
        setData(res.data)
      }
    } catch (err) {
      console.error('Failed to load events:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadNews = async () => {
    try {
      setNewsLoading(true)
      const res = await api.getTerminalNews()
      if (res.ok && res.data?.items) {
        setNewsItems(res.data.items)
      }
    } catch (err) {
      console.error('Failed to load terminal news:', err)
    } finally {
      setNewsLoading(false)
    }
  }

  const loadEventDetail = async (eventId: string) => {
    try {
      setDetailLoading(true)
      const res = await api.getEventDetail(eventId)
      if (res.ok) {
        setActiveEvent(res.data)
      }
    } catch (err) {
      console.error('Failed to load event detail:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    setCurrentPage(1)
    void loadEvents()
  }, [severityFilter, statusFilter, dateFilter, refreshKey])

  useEffect(() => {
    void loadNews()
  }, [refreshKey])

  useEffect(() => {
    if (selectedEventId) {
      void loadEventDetail(selectedEventId)
      setActiveView('radar')
    }
  }, [selectedEventId])

  const allEvents = data?.events || []
  const totalItems = allEvents.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const pagedEvents = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return allEvents.slice(start, start + pageSize)
  }, [allEvents, currentPage, pageSize])

  const sevCounts = data?.severity_counts || {}
  const verCounts = data?.verification_counts || {}
  const availableDates = data?.available_dates || []
  const dateCounts = data?.date_counts || {}

  const severityFilters = [
    { id: 'ALL', label: '全部级别' },
    { id: 'P0', label: '极高影响' },
    { id: 'P1', label: '重要关注' },
    { id: 'P2', label: '行业动态' },
    { id: 'P3', label: '常规资讯' },
  ]

  // 资讯流过滤与分页
  const availableSources = useMemo(() => {
    const set = new Set<string>()
    newsItems.forEach((n) => {
      if (n.source) set.add(n.source)
    })
    return Array.from(set)
  }, [newsItems])

  const filteredNews = useMemo(() => {
    return newsItems.filter((n) => {
      if (newsSourceFilter !== 'ALL' && n.source !== newsSourceFilter) return false
      if (newsSearch.trim()) {
        const q = newsSearch.trim().toLowerCase()
        if (!n.title.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [newsItems, newsSourceFilter, newsSearch])

  const totalNewsPages = Math.max(1, Math.ceil(filteredNews.length / newsPageSize))
  const pagedNews = useMemo(() => {
    const start = (newsPage - 1) * newsPageSize
    return filteredNews.slice(start, start + newsPageSize)
  }, [filteredNews, newsPage, newsPageSize])

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6">
      {/* 头部统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-[var(--text-muted)]">事件库总收录</div>
          <div className="text-xl font-bold font-mono text-[var(--text-primary)] mt-1">
            {data?.total_events ?? '—'}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-[#d03b3b] font-medium">极高影响事件</div>
          <div className="text-xl font-bold font-mono text-[#d03b3b] mt-1">
            {sevCounts.P0 ?? 0}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-[#c98500] font-medium">重要关注事件</div>
          <div className="text-xl font-bold font-mono text-[#c98500] mt-1">
            {sevCounts.P1 ?? 0}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-[#3987e5] font-medium">行业动态情报</div>
          <div className="text-xl font-bold font-mono text-[#3987e5] mt-1">
            {sevCounts.P2 ?? 0}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-gray-400">常规资讯</div>
          <div className="text-xl font-bold font-mono text-gray-400 mt-1">
            {sevCounts.P3 ?? 0}
          </div>
        </div>
        <div className="bg-[#331114]/20 border border-[#d03b3b]/30 rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-[#d03b3b] font-medium">传闻风险隔离</div>
          <div className="text-xl font-bold font-mono text-[#d03b3b] mt-1">
            {verCounts.Unverified_Rumor ?? 0}
          </div>
        </div>
      </div>

      {/* 原生内嵌双模块切换器 (拒绝新建外部页面，直接在事件情报内切换) */}
      <div className="flex items-center justify-between gap-3 bg-[var(--surface-color)] border border-[var(--border-color)] p-2 rounded-xl shadow-sm">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveView('radar')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeView === 'radar'
                ? 'bg-[#3987e5] text-white shadow'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
            }`}
          >
            <span>🎯 权威事件雷达与深度商业影响研判</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/20">
              {data?.total_events ?? 0}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveView('news')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeView === 'news'
                ? 'bg-[#3987e5] text-white shadow'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
            }`}
          >
            <span>📰 官方监管与交易所资讯流 (分时采集底账)</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/20">
              {newsItems.length}
            </span>
          </button>
        </div>

        {/* 右侧：手动即时抽取按钮 */}
        <button
          type="button"
          onClick={handleExtractNews}
          disabled={isExtracting}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-all shadow-sm ${
            isExtracting
              ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
              : 'bg-[#3987e5] hover:bg-[#2b74cf] text-white'
          }`}
          title="触发官方资讯采集，实时核验与抽取最新情报"
        >
          <span className={isExtracting ? 'animate-spin' : ''}>⚡</span>
          <span>{isExtracting ? '抽取中...' : '即时抽取官方资讯'}</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* 视图一：事件雷达全息深度研判与商业影响 */}
      {/* ========================================================================= */}
      {activeView === 'radar' && (
        <div className="space-y-6">
          {/* 按日期归档与历史时间线控制台 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 space-y-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#199e70]" />
                <h2 className="text-xs font-bold text-[var(--text-primary)]">
                  按日期归档时间线 (Date Archive & Timeline)
                </h2>
                <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-medium flex items-center gap-1">
                  <span>↓</span>
                  <span>严格按时间降序（最新在前）</span>
                </span>
                <span className="text-xs text-[var(--text-muted)] font-mono">
                  已收录 {availableDates.length} 个历史日期 · 共 {data?.total_events ?? 0} 篇情报底账
                </span>
              </div>

              {/* 日期精确选择下拉框 */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-[var(--text-muted)]">精确归档日期:</span>
                <select
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                  className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-[#3987e5] cursor-pointer font-bold"
                >
                  <option value="ALL">全部历史日期 ({data?.total_events ?? 0} 篇)</option>
                  {availableDates.map((d) => (
                    <option key={d} value={d}>
                      {d} 归档 ({dateCounts[d] ?? 0} 篇)
                    </option>
                  ))}
                </select>
                {dateFilter !== 'ALL' && (
                  <button
                    type="button"
                    onClick={() => setDateFilter('ALL')}
                    className="text-xs text-[#3987e5] hover:underline cursor-pointer"
                  >
                    重置全量 ✕
                  </button>
                )}
              </div>
            </div>

            {/* 快捷日期切档药丸列表 */}
            <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-[var(--border-color)]/50 text-xs">
              <span className="text-[11px] text-[var(--text-muted)] mr-1">快捷切档:</span>
              <button
                type="button"
                onClick={() => setDateFilter('ALL')}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer ${
                  dateFilter === 'ALL'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:border-[#3987e5]'
                }`}
              >
                全部 ({data?.total_events ?? 0})
              </button>
              {availableDates.slice(0, 10).map((d) => (
                <button
                  type="button"
                  key={d}
                  onClick={() => setDateFilter(d)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                    dateFilter === d
                      ? 'bg-[#199e70] text-white shadow-sm'
                      : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:border-[#199e70]'
                  }`}
                >
                  <span>{d}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      dateFilter === d
                        ? 'bg-white/20 text-white'
                        : 'bg-[var(--surface-color)] text-[var(--text-muted)]'
                    }`}
                  >
                    {dateCounts[d] ?? 0}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* 筛选与搜索 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              {/* 级别筛选 */}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-[var(--text-muted)]">影响级别:</span>
                {severityFilters.map((f) => (
                  <button
                    type="button"
                    key={f.id}
                    onClick={() => setSeverityFilter(f.id)}
                    className={`px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                      severityFilter === f.id
                        ? 'bg-[#3987e5] text-white shadow-sm'
                        : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--border-color)]'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* 核验状态筛选 */}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-[var(--text-muted)]">核验状态:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-[#3987e5] cursor-pointer"
                >
                  <option value="ALL">全部状态</option>
                  <option value="Confirmed_Fact">官方权威核实</option>
                  <option value="Corroborated_Report">主流媒体采信</option>
                  <option value="Unverified_Rumor">待核实传闻隔离</option>
                </select>
              </div>
            </div>

            {/* 关键字搜索 */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="搜索关联公司、行业板块、事件标题..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadEvents()}
                className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs w-60 focus:outline-none focus:border-[#3987e5]"
              />
              <button
                type="button"
                onClick={loadEvents}
                className="px-3 py-1.5 bg-[#3987e5] text-white rounded-lg text-xs hover:bg-[#2a78d6] cursor-pointer"
              >
                搜索
              </button>
            </div>
          </div>

          {/* 主界面：左侧事件列表 + 右侧事件详情抽屉 */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className={`space-y-3 ${activeEvent ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
              {loading ? (
                <div className="text-center py-12 text-xs text-[var(--text-muted)] bg-[var(--surface-color)] rounded-xl border border-[var(--border-color)]">
                  正在调取数据库最新情报底账...
                </div>
              ) : pagedEvents.length > 0 ? (
                <>
                  {pagedEvents.map((ev) => {
                    const sBadge = getSeverityBadge(ev.severity)
                    const vBadge = getVerificationBadge(ev.verification_status)

                    return (
                      <div
                        key={ev.event_id}
                        onClick={() => loadEventDetail(ev.event_id)}
                        className={`bg-[var(--surface-color)] border rounded-xl p-4 cursor-pointer transition-all ${
                          activeEvent?.event_id === ev.event_id
                            ? 'border-[#3987e5] ring-1 ring-[#3987e5]/50'
                            : 'border-[var(--border-color)] hover:border-[#3987e5]/50'
                        }`}
                      >
                        {/* 顶部状态与信息行 */}
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3">
                            <span className={`px-2 py-0.5 rounded text-xs font-bold shrink-0 border ${sBadge.cls}`}>
                              {sBadge.text}
                            </span>
                            <div>
                              <h3 className="text-sm font-semibold text-[var(--text-primary)] hover:text-[#3987e5]">
                                {ev.title}
                              </h3>
                              <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-[var(--text-muted)]">
                                {/* 独立的日期与时间一级字段 */}
                                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px] font-mono">
                                  <span className="text-[#3987e5] font-bold">
                                    📅 {ev.published_date || ev.published_at?.slice(0, 10)}
                                  </span>
                                  {ev.published_time && (
                                    <span className="text-[var(--text-secondary)] font-medium">
                                      🕒 {ev.published_time}
                                    </span>
                                  )}
                                </div>
                                <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px]">
                                  信源: {ev.source_name}
                                </span>
                                <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px]">
                                  可信度: {ev.credibility_tier}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* 状态徽章 */}
                          <div className="shrink-0">
                            {ev.is_quarantined_rumor ? (
                              <span className="px-2 py-0.5 rounded text-[11px] bg-[#d03b3b]/20 text-[#d03b3b] border border-[#d03b3b]/40 font-semibold flex items-center gap-1">
                                ⚠ 传闻隔离
                              </span>
                            ) : (
                              <span className={`px-2 py-0.5 rounded text-[11px] border font-medium ${vBadge.cls}`}>
                                {vBadge.text}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* 关联主体信息 */}
                        {toList(ev.involved_entities).length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-2.5 border-t border-[var(--border-color)]/50">
                            <span className="text-[11px] text-[var(--text-muted)] mr-1">关联主体:</span>
                            {toList(ev.involved_entities).map((ent, idx) => (
                              <span
                                key={idx}
                                className="text-[11px] px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] font-mono font-medium"
                              >
                                {ent}
                              </span>
                            ))}
                          </div>
                        )}
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
              <div className="lg:col-span-5 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 sticky top-24 max-h-[85vh] overflow-y-auto space-y-5 shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
                  <div className="flex items-center gap-2">
                    <span className={`font-bold text-xs px-2 py-0.5 rounded border ${getSeverityBadge(activeEvent.severity).cls}`}>
                      {getSeverityBadge(activeEvent.severity).text}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded border ${getVerificationBadge(activeEvent.verification_status).cls}`}>
                      {getVerificationBadge(activeEvent.verification_status).text}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveEvent(null)
                      onClearSelectedEvent?.()
                    }}
                    className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 cursor-pointer"
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
                        <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] font-mono text-[#3987e5] font-bold">
                          📅 发布日期: {activeEvent.published_date || activeEvent.published_at?.slice(0, 10)}
                        </span>
                        {activeEvent.published_time && (
                          <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] font-mono text-[var(--text-secondary)] font-medium">
                            🕒 确切时间: {activeEvent.published_time}
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                          信源: {activeEvent.source_name}
                        </span>
                        {activeEvent.estimated_duration && (
                          <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                            预期影响周期: {activeEvent.estimated_duration}
                          </span>
                        )}
                      </div>
                    </div>

                    {activeEvent.is_quarantined_rumor && (
                      <div className="bg-[#331114]/30 border border-[#d03b3b]/50 rounded-lg p-3 text-xs text-[#fce8e8] space-y-1.5">
                        <div className="font-bold text-[#d03b3b] flex items-center gap-1.5">
                          <span>⚠ 未核实传闻已启动安全隔离</span>
                        </div>
                        <p className="text-[11px] opacity-90 leading-relaxed">
                          {activeEvent.verification_note ||
                            '该情报尚未获得上市公司正式公告或权威监管机构核验。为防范虚假信息干扰，系统已对其建立安全隔离，严禁直接输入至估值测算与量化风控中。'}
                        </p>
                      </div>
                    )}

                    <div className="space-y-1.5">
                      <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#199e70]" />
                        业务冲击与微观传导分析
                      </div>
                      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3.5 text-xs text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
                        {activeEvent.micro_physical_impact || '暂无结构化微观业务传导分析'}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-xs font-bold text-[var(--text-primary)]">关联标的与受影响业务</div>
                      <div className="flex flex-wrap gap-1.5">
                        {toList(activeEvent.involved_entities).map((e, idx) => (
                          <span
                            key={idx}
                            className="text-xs px-2.5 py-1 rounded bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/20 font-mono font-medium"
                          >
                            {e}
                          </span>
                        ))}
                        {toList(activeEvent.affected_business_segments).map((seg, idx) => (
                          <span
                            key={idx}
                            className="text-xs px-2.5 py-1 rounded bg-[#199e70]/10 text-[#199e70] border border-[#199e70]/20"
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
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 视图二：官方监管与交易所资讯流 (分时采集底账) */}
      {/* ========================================================================= */}
      {activeView === 'news' && (
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                官方监管机构与交易所资讯流
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                覆盖 SEC、东京证券交易所 (JPX)、美联储 (FED) 及官方通讯社权威公开信源。
              </p>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30">
              共收录 {newsItems.length} 条官方资讯底账
            </span>
          </div>

          {/* 筛选与搜索工具栏 */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-[var(--text-muted)] mr-1">信源筛选:</span>
              <button
                type="button"
                onClick={() => setNewsSourceFilter('ALL')}
                className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                  newsSourceFilter === 'ALL'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                全部信源 ({newsItems.length})
              </button>
              {availableSources.map((s) => (
                <button
                  type="button"
                  key={s}
                  onClick={() => setNewsSourceFilter(s)}
                  className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                    newsSourceFilter === s
                      ? 'bg-[#3987e5] text-white shadow-sm'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="搜索资讯标题关键字..."
                value={newsSearch}
                onChange={(e) => {
                  setNewsSearch(e.target.value)
                  setNewsPage(1)
                }}
                className="text-xs bg-[var(--surface-color)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 w-60 focus:outline-none focus:border-[#3987e5]"
              />
            </div>
          </div>

          {/* 资讯流水表格列表 */}
          {newsLoading ? (
            <div className="p-8 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
              正在检索官方资讯流...
            </div>
          ) : pagedNews.length > 0 ? (
            <div className="space-y-2.5">
              {pagedNews.map((item, idx) => (
                <div
                  key={`${item.source}-${idx}`}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/40 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 transition-all shadow-sm"
                >
                  <div className="space-y-1 min-w-0">
                    <h4 className="text-xs font-bold text-[var(--text-primary)] hover:text-[#3987e5] leading-relaxed">
                      {item.title}
                    </h4>
                    <div className="flex flex-wrap items-center gap-2 text-[10px] text-[var(--text-muted)] font-mono">
                      <span>🕒 发布时间: {item.published_at ? formatDeviceTime(item.published_at) : '发布时间未标注'}</span>
                    </div>
                  </div>

                  <span className="text-[10px] px-2.5 py-1 rounded bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/25 font-semibold shrink-0">
                    {item.source}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-[var(--text-muted)] bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]">
              暂无匹配的官方来源资讯。点击右上角“即时抽取官方资讯”触发分时采集。
            </div>
          )}

          {/* 资讯分页器 */}
          {filteredNews.length > newsPageSize && (
            <div className="pt-2">
              <Pagination
                currentPage={newsPage}
                totalPages={totalNewsPages}
                totalItems={filteredNews.length}
                pageSize={newsPageSize}
                onPageChange={setNewsPage}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default IntelligenceTab
