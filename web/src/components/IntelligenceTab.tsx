import { useState, useEffect, useMemo } from 'react'
import type { EventsData, EventItem } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { Pagination } from './Pagination'
import { toList, getSeverityBadge, getVerificationBadge, formatSourceName, formatCredibilityTier } from '../utils/format'
import {
  SeverityBadge,
  VerificationBadge,
  EntityPills,
  MicroImpactBox,
  EventCard,
  TargetIcon,
  NewspaperIcon,
  ZapIcon,
  BrainIcon,
  CalendarIcon,
  ShieldCheckIcon,
  FilterIcon,
  SearchIcon,
  XIcon,
} from './common'

interface IntelligenceTabProps {
  selectedEventId?: string | null
  onClearSelectedEvent?: () => void
  refreshKey?: number
  onSelectTicker?: (ticker: string) => void
}

interface NewsItem {
  title: string
  published_at: string | null
  source: string
  category?: string
  severity?: string
  involved_entities?: string[]
  micro_physical_impact?: string
  is_distilled?: boolean
}

// 使用 format.ts 统一导出的 toList, getSeverityBadge, getVerificationBadge 单一事实来源 (SSOT)

export function IntelligenceTab({ selectedEventId, onClearSelectedEvent, refreshKey, onSelectTicker }: IntelligenceTabProps) {
  const [isDistilling, setIsDistilling] = useState(false)
  // 原生视图切换：事件雷达深度研判 vs 官方来源资讯流水
  const [activeView, setActiveView] = useState<'radar' | 'news'>('radar')

  // 1. 事件雷达相关状态
  const [data, setData] = useState<EventsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [dateFilter, setDateFilter] = useState('ALL')
  const [segmentFilter, setSegmentFilter] = useState('ALL')
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
  const [newsCategoryFilter, setNewsCategoryFilter] = useState('ALL')
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

  const handleDistillNews = async () => {
    if (isDistilling) return
    setIsDistilling(true)
    showToast({
      type: 'info',
      title: '新闻AI提炼与因果分析',
      message: '正在对已入库资讯进行实体提取、级别判定与微观业务传导分析...',
    })

    try {
      const res = await api.distillEvents()
      if (res.ok) {
        const stats = res.data
        const newCount = (stats as any).cycle_result?.summarized ?? (stats as any).summarized ?? 0
        showToast({
          type: 'success',
          title: '因果分析提炼完成',
          message: `新提炼 ${newCount} 篇情报，共收录 ${stats.total_events || 0} 篇权威事件。`,
        })
        await Promise.all([loadEvents(), loadNews()])
      } else {
        showToast({
          type: 'error',
          title: '提炼失败',
          message: res.error?.message || '未能完成新闻提炼',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或服务调用异常',
      })
    } finally {
      setIsDistilling(false)
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

  useEffect(() => {
    setCurrentPage(1)
  }, [segmentFilter])

  const allEvents = data?.events || []
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

  const availableCategories = useMemo(() => {
    const counts: Record<string, number> = {}
    newsItems.forEach((n) => {
      if (n.category) counts[n.category] = (counts[n.category] || 0) + 1
    })
    return counts
  }, [newsItems])

  const filteredNews = useMemo(() => {
    return newsItems.filter((n) => {
      if (newsSourceFilter !== 'ALL' && n.source !== newsSourceFilter) return false
      if (newsCategoryFilter !== 'ALL' && n.category !== newsCategoryFilter) return false
      if (newsSearch.trim()) {
        const q = newsSearch.trim().toLowerCase()
        const text = `${n.title} ${n.category || ''} ${n.micro_physical_impact || ''}`.toLowerCase()
        if (!text.includes(q)) return false
      }
      return true
    })
  }, [newsItems, newsSourceFilter, newsCategoryFilter, newsSearch])

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
            <TargetIcon className="w-4 h-4" />
            <span>权威事件雷达</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-white/20">
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
            <NewspaperIcon className="w-4 h-4" />
            <span>官方资讯流水</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-white/20">
              {newsItems.length}
            </span>
          </button>
        </div>

        {/* 右侧：手动即时抽取与提炼按钮 */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExtractNews}
            disabled={isExtracting}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-all shadow-sm ${
              isExtracting
                ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                : 'bg-[var(--bg-card)] hover:bg-[var(--border-color)] text-[var(--text-primary)] border border-[var(--border-color)]'
            }`}
            title="触发官方资讯采集，实时核验与拉取最新公开资讯"
          >
            <ZapIcon className={`w-4 h-4 text-amber-500 ${isExtracting ? 'animate-spin' : ''}`} />
            <span>{isExtracting ? '采集拉取中...' : '即时拉取官方资讯'}</span>
          </button>

          <button
            type="button"
            onClick={handleDistillNews}
            disabled={isDistilling}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-all shadow-sm ${
              isDistilling
                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30'
                : 'bg-[#199e70] hover:bg-[#15805c] text-white'
            }`}
            title="对已入库资讯进行自动化实体识别、严重级别分类与微观传导提炼"
          >
            <BrainIcon className={`w-4 h-4 text-white ${isDistilling ? 'animate-spin' : ''}`} />
            <span>{isDistilling ? '提炼研判中...' : 'AI提炼与因果分析'}</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 视图一：事件雷达全息深度研判与商业影响 */}
      {/* ========================================================================= */}
      {activeView === 'radar' && (
        <div className="space-y-6">
          {/* 综合情报控制台 (上下合并为统一子菜单架构，集成日历精准筛选与可扩展板块维度) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 space-y-3.5 shadow-sm">
            {/* 子菜单一级：影响级别分类导航项 */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]/60">
              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <span className="text-[var(--text-muted)] font-semibold text-xs mr-1 shrink-0">情报分类:</span>
                {severityFilters.map((f) => (
                  <button
                    type="button"
                    key={f.id}
                    onClick={() => setSeverityFilter(f.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                      severityFilter === f.id
                        ? 'bg-[#3987e5] text-white shadow-sm'
                        : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--border-color)] hover:text-[var(--text-primary)]'
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
                <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
                <span>收录 {availableDates.length} 个历史日期 · 共 {data?.total_events ?? 0} 篇权威事件</span>
              </div>
            </div>

            {/* 子菜单二级：日历精准筛选 + 核验状态 + 可扩展维度 (业务板块) + 搜索框 */}
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-3">
                {/* 1. 日历筛选 (Calendar Picker) */}
                <div className="flex items-center gap-1.5">
                  <span className="text-[var(--text-muted)] font-medium flex items-center gap-1">
                    <CalendarIcon className="w-3.5 h-3.5 text-[#3987e5]" />
                    <span>日历筛选:</span>
                  </span>
                  <div className="relative inline-flex items-center">
                    <input
                      type="date"
                      value={dateFilter === 'ALL' ? '' : dateFilter}
                      min={availableDates[availableDates.length - 1]}
                      max={availableDates[0]}
                      onChange={(e) => setDateFilter(e.target.value || 'ALL')}
                      className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] hover:border-[#3987e5] rounded-lg px-2.5 py-1 text-xs font-mono focus:outline-none focus:border-[#3987e5] cursor-pointer"
                      title="点击日历选择历史日期进行归档精准筛选"
                    />
                    {dateFilter !== 'ALL' && (
                      <button
                        type="button"
                        onClick={() => setDateFilter('ALL')}
                        className="ml-1.5 px-2 py-0.5 rounded bg-gray-700/20 hover:bg-gray-700/40 text-[var(--text-muted)] hover:text-white text-[11px] cursor-pointer transition-all flex items-center gap-1"
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
                    <ShieldCheckIcon className="w-3.5 h-3.5 text-emerald-500" />
                    <span>核验状态:</span>
                  </span>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] hover:border-[#3987e5] rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-[#3987e5] cursor-pointer"
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
                    className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] hover:border-[#3987e5] rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-[#3987e5] cursor-pointer"
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
                    onKeyDown={(e) => e.key === 'Enter' && loadEvents()}
                    className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg pl-8 pr-3 py-1.5 text-xs w-56 sm:w-64 focus:outline-none focus:border-[#3987e5]"
                  />
                  <SearchIcon className="w-3.5 h-3.5 text-[var(--text-muted)] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
                <button
                  type="button"
                  onClick={loadEvents}
                  className="px-3 py-1.5 bg-[#3987e5] hover:bg-[#2a78d6] text-white rounded-lg text-xs font-semibold cursor-pointer transition-all shadow-sm flex items-center gap-1"
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
                <div className="text-center py-12 text-xs text-[var(--text-muted)] bg-[var(--surface-color)] rounded-xl border border-[var(--border-color)]">
                  正在调取数据库最新权威事件...
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
                                {ev.source_name && (
                                  <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px]">
                                    信源: {formatSourceName(ev.source_name)}
                                  </span>
                                )}
                                {(() => {
                                  const cred = formatCredibilityTier(ev.credibility_tier);
                                  return cred.text ? (
                                    <span className={`px-2 py-0.5 rounded border text-[11px] font-medium ${cred.cls}`}>
                                      {cred.text}
                                    </span>
                                  ) : null;
                                })()}
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
                            <EntityPills entities={ev.involved_entities} onSelectTicker={onSelectTicker} />
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
                    <SeverityBadge level={activeEvent.severity} />
                    <VerificationBadge status={activeEvent.verification_status} />
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
                      <MicroImpactBox
                        impact={activeEvent.micro_physical_impact || '暂无结构化微观业务传导分析'}
                        category={activeEvent.category}
                        title="⚡ 业务冲击与微观传导分析"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-xs font-bold text-[var(--text-primary)]">关联标的与受影响业务</div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <EntityPills entities={activeEvent.involved_entities} onSelectTicker={onSelectTicker} />
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
      {/* 视图二：官方监管与交易所资讯流 (官方资讯流水) */}
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
              共收录 {newsItems.length} 条资讯
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
                  {formatSourceName(s)}
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

          {/* 主题分类筛选药丸 */}
          {Object.keys(availableCategories).length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
              <span className="text-[11px] text-[var(--text-muted)] mr-1">主题分类:</span>
              <button
                type="button"
                onClick={() => setNewsCategoryFilter('ALL')}
                className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                  newsCategoryFilter === 'ALL'
                    ? 'bg-[#199e70] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                全部类别 ({newsItems.length})
              </button>
              {Object.entries(availableCategories).map(([cat, count]) => (
                <button
                  type="button"
                  key={cat}
                  onClick={() => setNewsCategoryFilter(cat)}
                  className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all flex items-center gap-1 ${
                    newsCategoryFilter === cat
                      ? 'bg-[#199e70] text-white shadow-sm'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--surface-color)] border border-[var(--border-color)]'
                  }`}
                >
                  <span>{cat}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${newsCategoryFilter === cat ? 'bg-white/20' : 'bg-gray-700/20 text-gray-400'}`}>
                    {count}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* 资讯流水表格列表 */}
          {newsLoading ? (
            <div className="p-8 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
              正在检索官方资讯流...
            </div>
          ) : pagedNews.length > 0 ? (
            <div className="space-y-2.5">
              {pagedNews.map((item, idx) => (
                <EventCard
                  key={`${item.source}-${idx}`}
                  title={item.title}
                  severity={item.severity}
                  published_at={item.published_at || undefined}
                  source_name={item.source}
                  category={item.category}
                  micro_physical_impact={item.micro_physical_impact}
                  involved_entities={item.involved_entities}
                  is_distilled={item.is_distilled}
                  onSelectTicker={onSelectTicker}
                  onViewRadarDetail={() => {
                    const matched = (data?.events || []).find((e) => e.title === item.title)
                    if (matched) {
                      void loadEventDetail(matched.event_id)
                      setActiveView('radar')
                    }
                  }}
                />
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
