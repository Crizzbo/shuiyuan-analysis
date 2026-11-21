import { useState, useEffect } from 'react'
import type { EventsData, EventItem, TerminalNewsItem } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { ZapIcon, BrainIcon } from './common'
import { EventRadarView } from './intelligence/EventRadarView'
import { OfficialNewsStream } from './intelligence/OfficialNewsStream'

export interface IntelligenceTabProps {
  selectedEventId?: string | null
  onClearSelectedEvent?: () => void
  refreshKey?: number
  onSelectTicker?: (ticker: string) => void
}

/**
 * 事件情报总控工作台 (Intelligence Tab)
 * 双模式驱动：权威事件雷达 (Event Radar) + 官方资讯流水 (Official News Stream)
 * 严格践行 pstack 极简架构与原子解耦准则
 */
export function IntelligenceTab({
  selectedEventId,
  onClearSelectedEvent,
  refreshKey,
  onSelectTicker,
}: IntelligenceTabProps) {
  const [isDistilling, setIsDistilling] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
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

  // 2. 官方资讯流水状态
  const [newsItems, setNewsItems] = useState<TerminalNewsItem[]>([])
  const [newsLoading, setNewsLoading] = useState(false)

  // 官方资讯即时抽取
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
    } catch (err: unknown) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err instanceof Error ? err.message : '网络连接或服务调用异常',
      })
    } finally {
      setIsExtracting(false)
    }
  }

  // 触发资讯 AI 因果提炼
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
        const newCount =
          typeof stats.cycle_result === 'object' && stats.cycle_result !== null && 'summarized' in stats.cycle_result
            ? Number((stats.cycle_result as Record<string, unknown>).summarized)
            : 0
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
    } catch (err: unknown) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err instanceof Error ? err.message : '网络连接或服务调用异常',
      })
    } finally {
      setIsDistilling(false)
    }
  }

  const loadEvents = async () => {
    try {
      setLoading(true)
      const params: { severity?: string; verification_status?: string; date?: string; q?: string } = {}
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

  const sevCounts = data?.severity_counts || {}
  const verCounts = data?.verification_counts || {}

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-6">
      {/* 头部统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-[var(--text-muted)]">事件库总收录</div>
          <div className="text-xl font-bold font-mono text-[var(--text-primary)] mt-1">
            {data?.total_events ?? '—'}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-rose-600 font-medium">极高影响事件</div>
          <div className="text-xl font-bold font-mono text-rose-600 mt-1">
            {sevCounts.P0 ?? 0}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-amber-600 font-medium">重要关注事件</div>
          <div className="text-xl font-bold font-mono text-amber-600 mt-1">
            {sevCounts.P1 ?? 0}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-slate-700 font-medium">行业动态情报</div>
          <div className="text-xl font-bold font-mono text-slate-700 mt-1">
            {sevCounts.P2 ?? 0}
          </div>
        </div>
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-slate-500">常规资讯</div>
          <div className="text-xl font-bold font-mono text-slate-500 mt-1">
            {sevCounts.P3 ?? 0}
          </div>
        </div>
        <div className="bg-rose-50/50 border border-rose-200 rounded-xl p-3 text-center shadow-sm">
          <div className="text-xs text-rose-700 font-medium">传闻风险隔离</div>
          <div className="text-xl font-bold font-mono text-rose-700 mt-1">
            {verCounts.Unverified_Rumor ?? 0}
          </div>
        </div>
      </div>

      {/* 原生内嵌双模块切换器 */}
      <div className="flex items-center justify-between gap-3 bg-[var(--surface-color)] border border-[var(--border-color)] p-2 rounded-xl shadow-sm">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveView('radar')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeView === 'radar'
                ? 'bg-[#176249] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
            }`}
          >
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
                ? 'bg-[#176249] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
            }`}
          >
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
                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                : 'bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-primary)] border border-[var(--border-color)]'
            }`}
            title="触发官方资讯采集，实时核验与拉取最新公开资讯"
          >
            <ZapIcon className={`w-4 h-4 text-amber-600 ${isExtracting ? 'animate-spin' : ''}`} />
            <span>{isExtracting ? '采集拉取中...' : '即时拉取官方资讯'}</span>
          </button>

          <button
            type="button"
            onClick={handleDistillNews}
            disabled={isDistilling}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-all shadow-sm ${
              isDistilling
                ? 'bg-[#176249]/10 text-[#176249] border border-[#176249]/30'
                : 'bg-[#176249] hover:bg-[#124e3a] text-white'
            }`}
            title="对已入库资讯进行自动化实体识别、严重级别分类与微观传导提炼"
          >
            <BrainIcon className={`w-4 h-4 text-white ${isDistilling ? 'animate-spin' : ''}`} />
            <span>{isDistilling ? '提炼研判中...' : '智能提炼与因果分析'}</span>
          </button>
        </div>
      </div>

      {/* 视图一：事件雷达深度研判 */}
      {activeView === 'radar' && (
        <EventRadarView
          data={data}
          loading={loading}
          severityFilter={severityFilter}
          setSeverityFilter={setSeverityFilter}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          dateFilter={dateFilter}
          setDateFilter={setDateFilter}
          segmentFilter={segmentFilter}
          setSegmentFilter={setSegmentFilter}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onSearch={loadEvents}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          pageSize={pageSize}
          activeEvent={activeEvent}
          detailLoading={detailLoading}
          onSelectEvent={loadEventDetail}
          onCloseDetail={() => {
            setActiveEvent(null)
            onClearSelectedEvent?.()
          }}
          onSelectTicker={onSelectTicker}
        />
      )}

      {/* 视图二：官方资讯流水 */}
      {activeView === 'news' && (
        <OfficialNewsStream
          newsItems={newsItems}
          newsLoading={newsLoading}
          onSelectTicker={onSelectTicker}
          onViewRadarDetail={(title) => {
            const matched = (data?.events || []).find((e) => e.title === title)
            if (matched) {
              void loadEventDetail(matched.event_id)
              setActiveView('radar')
            }
          }}
        />
      )}
    </div>
  )
}

export default IntelligenceTab
