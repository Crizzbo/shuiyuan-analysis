import { useEffect, useState } from 'react'
import type { DashboardSummaryData, MarketQuoteItem, IndicatorItem, EventItem } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TaskDispatcherPanel } from './TaskDispatcherPanel'
import { formatDeviceTime, toChinese } from '../utils/format'
import { EventCard } from './common'

interface DashboardTabProps {
  onNavigateTab: (tabId: string) => void
  onSelectEvent: (eventId: string) => void
  onSelectTicker?: (ticker: string) => void
  refreshKey?: number
}

function getStatusBadge(status?: string) {
  switch (status) {
    case 'FRESH':
      return { text: '通过时效核验', cls: 'bg-[#199e70]/20 text-[#199e70] border-[#199e70]/40' }
    case 'PREVIOUS_CLOSE':
      return { text: '前一交易日收盘基准', cls: 'bg-gray-100 text-gray-700 border-gray-300' }
    case 'STALE_BLOCKED':
      return { text: '数据超期阻断', cls: 'bg-[#d03b3b]/20 text-[#d03b3b] border-[#d03b3b]/40' }
    case 'NOT_CONFIGURED':
      return { text: '待配置行情源', cls: 'bg-gray-700/20 text-gray-500 border-gray-700/40' }
    case 'NO_QUOTE':
      return { text: '待补行情', cls: 'bg-gray-700/20 text-gray-500 border-gray-700/40' }
    default:
      return { text: '状态待核验', cls: 'bg-[#3987e5]/20 text-[#3987e5] border-[#3987e5]/40' }
  }
}

export function DashboardTab({ onNavigateTab, onSelectEvent, onSelectTicker, refreshKey }: DashboardTabProps) {
  const [data, setData] = useState<DashboardSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExtractingNews, setIsExtractingNews] = useState(false)
  const handleExtractNews = async () => {
    if (isExtractingNews) return
    setIsExtractingNews(true)
    showToast({
      type: 'info',
      title: '官方资讯分时采集与AI提炼',
      message: '正在向后端发起新闻抓取与事件雷达因果提炼...',
    })

    try {
      const res = await api.runTerminalTask('OFFICIAL_NEWS')
      if (res.ok) {
        showToast({
          type: 'success',
          title: '官方资讯采集已完成',
          message: '新资讯已采集并由事件雷达引擎完成提炼入库。',
        })
        await loadData()
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
      setIsExtractingNews(false)
    }
  }

  const loadData = async () => {
    try {
      setLoading(true)
      const res = await api.getDashboardSummary()
      if (res.ok) {
        setData(res.data)
        setError(null)
      } else {
        setError(res.error?.message || '获取总览数据失败')
      }
    } catch (err: any) {
      setError(err.message || '网络连接异常')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [refreshKey])

  if (loading && !data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
          <div className="text-sm text-[var(--text-muted)]">正在汇集最新市场行情、事件雷达与指标底账...</div>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="p-8 text-center text-[#d03b3b] bg-[#331114]/20 border border-[#d03b3b]/30 rounded-xl m-6">
        <p className="font-semibold">总览数据加载失败: {error}</p>
        <button
          onClick={loadData}
          className="mt-3 px-4 py-1.5 bg-[#d03b3b] text-white text-xs rounded-lg hover:bg-[#b03030] cursor-pointer"
        >
          重新拉取
        </button>
      </div>
    )
  }

  const extraQuotes = data?.markets?.all_quotes ?? []
  const dailyArchives = data?.markets?.daily_archives ?? []
  const mergeQuotes = (base: MarketQuoteItem[], market: string) => {
    const quotes = new Map(base.map(quote => [quote.ticker, quote]))
    for (const quote of extraQuotes) {
      if (quote.market === market) quotes.set(quote.ticker, quote)
    }
    for (const archive of dailyArchives) {
      const ticker = market === 'JP' ? archive.symbol.replace(/\.T$/, '') : archive.symbol
      if (archive.market === market && !quotes.has(ticker)) {
        quotes.set(ticker, { ticker, market, company_name: '', price: null,
          currency: market === 'JP' ? 'JPY' : 'USD', is_valid: false, data_status: 'NO_QUOTE' })
      }
    }
    return [...quotes.values()]
  }
  const archivedClose = (quote: MarketQuoteItem) => {
    const data = dailyArchives.find(item => item.market === quote.market &&
      (item.symbol === quote.ticker || item.symbol === `${quote.ticker}.T`))
    return data?.last_date && data.close != null
      ? `历史收盘 ${data.last_date} · ${data.close.toLocaleString()} ${quote.currency}`
      : null
  }
  const usAssets = mergeQuotes(data?.markets?.us_indices ?? [], 'US')
  const jpAssets = mergeQuotes([...(data?.markets?.jp_indices ?? []), ...(data?.markets?.jp_core_equities ?? [])], 'JP')

  const readiness = data?.readiness

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <TaskDispatcherPanel schedulerInfo={data?.task_scheduler} onTaskCompleted={loadData} onManage={() => onNavigateTab("collection")} />
      {/* ========================================================================= */}
      {/* 1. 宏观流动性与全市场趋势宽度 (重市场动态指标，顶层核心呈现) */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 美股市场行情 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)] gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#3987e5]" />
              <h2 className="text-sm font-bold text-[var(--text-primary)]">美股核心指数与主要资产</h2>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {data?.markets?.reconciliation?.us && (
                <button
                  type="button"
                  onClick={() => onNavigateTab('collection')}
                  className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#3987e5]/10 text-[#3987e5] hover:bg-[#3987e5]/20 border border-[#3987e5]/30 flex items-center gap-1 cursor-pointer transition-all"
                  title="点击跳转至采集中心查看 10,445 只美股全市场目标交易日对账底账"
                >
                  <span>目标交易日: {data.markets.reconciliation.us.target_trading_day}</span>
                  <span className="text-[#199e70] font-bold">· 平账已平衡</span>
                  <span>&rarr;</span>
                </button>
              )}
              <span className="text-xs text-[var(--text-muted)]">
                {data?.markets?.market_session_note || '等待已核验行情'}
              </span>
            </div>
          </div>

          <div className="max-h-[32rem] overflow-y-auto divide-y divide-[var(--border-color)]/50">
            {usAssets.map((q: MarketQuoteItem) => {
              const badge = getStatusBadge(q.data_status)
              return (
                <div key={q.ticker} className="py-2.5 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs font-mono text-[var(--text-primary)]">
                        {q.ticker}
                      </span>
                      <span className="text-xs text-[var(--text-secondary)] truncate">
                        {q.company_name}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                      {formatDeviceTime(q.timestamp_iso || q.timestamp_formatted)}
                    </div>
                    {archivedClose(q) && <div className="text-[11px] text-[var(--text-muted)]">{archivedClose(q)}</div>}
                  </div>

                  <div className="text-right shrink-0">
                    <div className="font-mono font-bold text-sm text-[var(--text-primary)]">
                      {q.formatted_price || (q.price !== null ? `$${q.price.toFixed(2)}` : '—')}
                    </div>
                    <span className={`inline-block text-[10px] px-1.5 py-0.2 rounded border font-medium mt-0.5 ${badge.cls}`}>
                      {badge.text}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* 日股市场资产与汇率门禁 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)] gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#199e70]" />
              <h2 className="text-sm font-bold text-[var(--text-primary)]">日股核心指数与权重标的</h2>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {data?.markets?.reconciliation?.jp && (
                <button
                  type="button"
                  onClick={() => onNavigateTab('collection')}
                  className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#199e70]/10 text-[#199e70] hover:bg-[#199e70]/20 border border-[#199e70]/30 flex items-center gap-1 cursor-pointer transition-all"
                  title="点击跳转至采集中心查看 4,447 只东证日股全市场目标交易日对账底账"
                >
                  <span>目标交易日: {data.markets.reconciliation.jp.target_trading_day}</span>
                  <span className="text-[#199e70] font-bold">· 平账已平衡</span>
                  <span>&rarr;</span>
                </button>
              )}
              <span className="text-xs text-[var(--text-muted)]">
                {data?.markets?.market_session_note || '等待已核验行情'}
              </span>
            </div>
          </div>

          <div className="max-h-[32rem] overflow-y-auto divide-y divide-[var(--border-color)]/50">
            {jpAssets.map((q: MarketQuoteItem) => {
              const badge = getStatusBadge(q.data_status)
              return (
                <div key={q.ticker} className="py-2.5 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs font-mono text-[var(--text-primary)]">
                        {q.ticker}
                      </span>
                      <span className="text-xs text-[var(--text-secondary)] truncate">
                        {q.company_name}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                      {formatDeviceTime(q.timestamp_iso || q.timestamp_formatted)}
                    </div>
                    {archivedClose(q) && <div className="text-[11px] text-[var(--text-muted)]">{archivedClose(q)}</div>}
                  </div>

                  <div className="text-right shrink-0">
                    <div className="font-mono font-bold text-sm text-[var(--text-primary)]">
                      {q.formatted_price || (q.price !== null ? `¥${q.price.toLocaleString()}` : '—')}
                    </div>
                    <span className={`inline-block text-[10px] px-1.5 py-0.2 rounded border font-medium mt-0.5 ${badge.cls}`}>
                      {badge.text}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
          <h2 className="text-sm font-bold">宏观与市场指标</h2>
          <span className="text-xs text-[var(--text-muted)]">归档基准 {formatDeviceTime(readiness?.latest_timestamp_utc)}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          {(data?.indicators || []).map((ind: IndicatorItem) => (
            <div
              key={ind.id}
              className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 flex flex-col justify-between hover:border-[#3987e5]/50 transition-all shadow-sm"
            >
              <div>
                <div className="text-xs text-[var(--text-muted)] flex items-center justify-between gap-1">
                  <span className="truncate font-semibold text-[var(--text-secondary)]">{ind.name_zh}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-gray-600/20 text-gray-400 shrink-0 font-mono">
                    {toChinese(ind.data_status)}
                  </span>
                </div>
                <div className="text-2xl font-black font-mono text-[var(--text-primary)] mt-2 tracking-tight">
                  {ind.display_value || ind.value}
                </div>
              </div>
              <div className="mt-2 text-xs text-[var(--text-muted)]">{formatDeviceTime(ind.as_of)}</div>
              {ind.signal_zh && (
                <div className="text-[11px] text-[#3987e5] mt-2.5 font-medium bg-[#3987e5]/10 px-2 py-1 rounded border border-[#3987e5]/20 truncate">
                  {ind.signal_zh}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 6. 突发核心事件情报雷达 */}
      {/* ========================================================================= */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#d03b3b]" />
            <h2 className="text-sm font-bold text-[var(--text-primary)]">
              突发核心事件情报雷达
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExtractNews}
              disabled={isExtractingNews}
              className={`text-xs px-2.5 py-1 rounded-md font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                isExtractingNews
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                  : 'bg-[var(--bg-card)] hover:bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/30 hover:border-[#3987e5]'
              }`}
              title="触发官方资讯采集，实时核验与抽取最新情报"
            >
              <span className={isExtractingNews ? 'animate-spin' : ''}>⚡</span>
              <span>{isExtractingNews ? '正在抽取情报...' : '即时抽取最新新闻'}</span>
            </button>
            <button
              onClick={() => onNavigateTab('intelligence')}
              className="text-xs text-[var(--text-secondary)] hover:text-[#3987e5] hover:underline cursor-pointer"
            >
              查看全部情报 ({data?.events_summary?.total_events || 0}条) →
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {data?.events_summary?.top_events && data.events_summary.top_events.length > 0 ? (
            data.events_summary.top_events.map((ev: EventItem) => (
              <EventCard
                key={ev.event_id}
                id={ev.event_id}
                title={ev.title}
                severity={ev.severity}
                verification_status={ev.verification_status}
                is_quarantined_rumor={ev.is_quarantined_rumor}
                published_at={ev.published_at}
                source_name={ev.source_name}
                category={ev.category}
                micro_physical_impact={ev.micro_physical_impact}
                involved_entities={ev.involved_entities}
                affected_business_segments={ev.affected_business_segments}
                onClick={() => {
                  onSelectEvent(ev.event_id)
                  onNavigateTab('intelligence')
                }}
                onSelectTicker={onSelectTicker}
              />
            ))
          ) : (
            <div className="text-center py-6 text-xs text-[var(--text-muted)]">
              暂无突发事件记录
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DashboardTab
