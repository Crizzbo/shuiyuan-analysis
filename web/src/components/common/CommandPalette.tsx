import React, { useEffect, useRef, useState, useMemo } from 'react'
import { api } from '../../services/api'
import type { CandidateItem, EventItem } from '../../types/api'
import {
  SearchIcon,
  XIcon,
  CornerDownLeftIcon,
  CompassIcon,
  TargetIcon,
  DatabaseIcon,
  BarChartIcon,
  SettingsIcon,
  LayersIcon,
  RefreshIcon,
} from './Icons'

export interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onNavigateTab: (tabId: string) => void
  onSelectTicker: (ticker: string) => void
  onSelectEvent: (eventId: string) => void
  onTriggerPipeline: () => void
  onRefreshData: () => void
}

interface PaletteActionItem {
  id: string
  type: 'action'
  label: string
  subtext: string
  shortcut?: string
  icon: React.ReactNode
  perform: () => void
}

interface PaletteCandidateItem {
  id: string
  type: 'candidate'
  ticker: string
  name: string
  market: string
  price: number | null
  currency: string
  readiness?: string
  vcp_code?: string | null
  perform: () => void
}

interface PaletteEventItem {
  id: string
  type: 'event'
  eventId: string
  title: string
  severity: string
  publishedAt: string
  perform: () => void
}

type PaletteItem = PaletteActionItem | PaletteCandidateItem | PaletteEventItem

const PINNED_TICKERS = [
  { ticker: 'NVDA', name: 'NVIDIA Corporation', market: 'US', currency: 'USD' },
  { ticker: 'AAPL', name: 'Apple Inc.', market: 'US', currency: 'USD' },
  { ticker: 'MSFT', name: 'Microsoft Corporation', market: 'US', currency: 'USD' },
  { ticker: 'VRT', name: 'Vertiv Holdings Co', market: 'US', currency: 'USD' },
  { ticker: '6758', name: 'Sony Group Corp (ソニーグループ)', market: 'JP', currency: 'JPY' },
  { ticker: '7203', name: 'Toyota Motor Corp (トヨタ自動車)', market: 'JP', currency: 'JPY' },
]

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigateTab,
  onSelectTicker,
  onSelectEvent,
  onTriggerPipeline,
  onRefreshData,
}) => {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [candidateResults, setCandidateResults] = useState<CandidateItem[]>([])
  const [eventResults, setEventResults] = useState<EventItem[]>([])

  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // 基础系统操作指令
  const systemActions: PaletteActionItem[] = useMemo(
    () => [
      {
        id: 'action-dashboard',
        type: 'action',
        label: '总览仪表盘 (Dashboard)',
        subtext: '大盘双市场罗盘、行业天梯、涨跌分布直方图与宏观指标',
        shortcut: '1',
        icon: <CompassIcon className="w-4 h-4 text-sky-600" />,
        perform: () => {
          onNavigateTab('dashboard')
          onClose()
        },
      },
      {
        id: 'action-intelligence',
        type: 'action',
        label: '事件情报库 (Intelligence)',
        subtext: '官方资讯流水雷达、突发事件穿透与买方舆情质检',
        shortcut: '2',
        icon: <TargetIcon className="w-4 h-4 text-amber-600" />,
        perform: () => {
          onNavigateTab('intelligence')
          onClose()
        },
      },
      {
        id: 'action-collection',
        type: 'action',
        label: '采集中心 (Data Operations)',
        subtext: '美日全市场数据采集调度、时效对账与 AI 浏览器补数',
        shortcut: '3',
        icon: <DatabaseIcon className="w-4 h-4 text-cyan-600" />,
        perform: () => {
          onNavigateTab('collection')
          onClose()
        },
      },
      {
        id: 'action-analytics',
        type: 'action',
        label: '计算分析 (Valuation Cockpit)',
        subtext: '买方估值走廊、25 项核心量化模型与官方三表深度底稿',
        shortcut: '4',
        icon: <BarChartIcon className="w-4 h-4 text-emerald-600" />,
        perform: () => {
          onNavigateTab('analytics')
          onClose()
        },
      },
      {
        id: 'action-logs',
        type: 'action',
        label: '系统日志 (System Logs)',
        subtext: 'SSE 实时推流、各模块任务流水与异常排查追踪',
        shortcut: '5',
        icon: <LayersIcon className="w-4 h-4 text-indigo-600" />,
        perform: () => {
          onNavigateTab('logs')
          onClose()
        },
      },
      {
        id: 'action-settings',
        type: 'action',
        label: '合规审计 (Compliance & Rules)',
        subtext: '全盘知识库契约、平账规则、时效门禁与架构四层巡检',
        shortcut: '6',
        icon: <SettingsIcon className="w-4 h-4 text-slate-600" />,
        perform: () => {
          onNavigateTab('settings')
          onClose()
        },
      },
      {
        id: 'action-trigger-pipeline',
        type: 'action',
        label: '立即触发数据采集流水线',
        subtext: '调度盘前/盘中自动化补数与状态对账任务',
        shortcut: '↵ Run',
        icon: <DatabaseIcon className="w-4 h-4 text-rose-600" />,
        perform: () => {
          onTriggerPipeline()
          onClose()
        },
      },
      {
        id: 'action-refresh-data',
        type: 'action',
        label: '全盘数据即时刷新',
        subtext: '同步最新行情时间戳与系统健康检查状态',
        shortcut: 'R',
        icon: <RefreshIcon className="w-4 h-4 text-sky-600" />,
        perform: () => {
          onRefreshData()
          onClose()
        },
      },
    ],
    [onNavigateTab, onClose, onTriggerPipeline, onRefreshData]
  )

  // 窗口打开时自动聚焦并清空
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setCandidateResults([])
      setEventResults([])
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // 异步搜索逻辑（防抖）
  useEffect(() => {
    if (!isOpen) return
    const trimmed = query.trim()
    if (!trimmed) {
      setCandidateResults([])
      setEventResults([])
      setLoading(false)
      return
    }

    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const [candRes, eventRes] = await Promise.all([
          api.getAnalyticsCandidates('ALL', 8, 1, trimmed),
          api.getEvents({ q: trimmed, limit: 5 }),
        ])
        if (candRes.ok && candRes.data.candidates) {
          setCandidateResults(candRes.data.candidates)
        }
        if (eventRes.ok && eventRes.data.events) {
          setEventResults(eventRes.data.events)
        }
      } catch {
        // 容错降级
      } finally {
        setLoading(false)
      }
    }, 180)

    return () => clearTimeout(timer)
  }, [query, isOpen])

  // 构造最终扁平列表
  const flatItems: PaletteItem[] = useMemo(() => {
    const trimmed = query.trim().toLowerCase()

    // 1. 过滤系统操作
    const filteredActions = systemActions.filter(
      (act) =>
        act.label.toLowerCase().includes(trimmed) ||
        act.subtext.toLowerCase().includes(trimmed) ||
        (act.shortcut && act.shortcut.toLowerCase() === trimmed)
    )

    // 2. 标的资产项
    let candidateItems: PaletteCandidateItem[] = []
    if (trimmed) {
      candidateItems = candidateResults.map((cand) => ({
        id: `cand-${cand.ticker}`,
        type: 'candidate',
        ticker: cand.ticker,
        name: cand.company_name,
        market: cand.market,
        price: cand.latest_price,
        currency: cand.currency,
        readiness: cand.readiness_status,
        vcp_code: cand.vcp_code,
        perform: () => {
          onSelectTicker(cand.ticker)
          onClose()
        },
      }))
    } else {
      // 空搜索时展示置顶龙头
      candidateItems = PINNED_TICKERS.map((pin) => ({
        id: `pinned-${pin.ticker}`,
        type: 'candidate',
        ticker: pin.ticker,
        name: pin.name,
        market: pin.market,
        price: null,
        currency: pin.currency,
        perform: () => {
          onSelectTicker(pin.ticker)
          onClose()
        },
      }))
    }

    // 3. 事件项
    const eventItems: PaletteEventItem[] = eventResults.map((ev) => ({
      id: `ev-${ev.event_id}`,
      type: 'event',
      eventId: ev.event_id,
      title: ev.title,
      severity: ev.severity,
      publishedAt: ev.published_at_iso || ev.published_at,
      perform: () => {
        onSelectEvent(ev.event_id)
        onClose()
      },
    }))

    return [...filteredActions, ...candidateItems, ...eventItems]
  }, [query, systemActions, candidateResults, eventResults, onSelectTicker, onSelectEvent, onClose])

  // 重置索引保护
  useEffect(() => {
    setSelectedIndex(0)
  }, [flatItems.length])

  // 键盘操作拦截
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (flatItems.length > 0 ? (prev + 1) % flatItems.length : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (flatItems.length > 0 ? (prev - 1 + flatItems.length) % flatItems.length : 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (flatItems[selectedIndex]) {
        flatItems[selectedIndex].perform()
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    }
  }

  // 滚动可视区域居中
  useEffect(() => {
    if (!listRef.current) return
    const el = listRef.current.querySelector(`[data-index="${selectedIndex}"]`) as HTMLElement | null
    if (el) {
      el.scrollIntoView({ block: 'nearest' })
    }
  }, [selectedIndex])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-sky-950/40 backdrop-blur-sm transition-all"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-[rgba(240,248,255,0.96)] border border-sky-300/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-150"
        style={{
          boxShadow:
            'inset 0 1.5px 2px rgba(255, 255, 255, 0.95), inset 0 -1.5px 2px rgba(186, 230, 253, 0.3), 0 25px 50px -12px rgba(12, 74, 110, 0.35)',
        }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* 顶部搜索输入框 */}
        <div className="flex items-center px-4 py-3.5 border-b border-sky-200/80 bg-white/70 gap-3">
          <SearchIcon className="w-5 h-5 text-sky-600 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="全盘检索代码、公司名称、重大事件或输入指令 (如 NVDA, 苹果, 7203, 1~6)..."
            className="flex-1 bg-transparent border-0 outline-none text-sm text-[var(--text-primary)] placeholder-sky-900/40 font-medium"
          />
          {loading && (
            <span className="text-xs text-sky-600 animate-pulse flex items-center gap-1 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-600 animate-ping" />
              检索中
            </span>
          )}
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="p-1 rounded-md text-sky-700/60 hover:text-sky-900 hover:bg-sky-100 transition-colors"
            >
              <XIcon className="w-3.5 h-3.5" />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[10px] font-mono px-2 py-0.5 rounded bg-sky-100 text-sky-700 border border-sky-200/80 shadow-2xs">
            ESC
          </kbd>
        </div>

        {/* 候选结果滚动列表 */}
        <div ref={listRef} className="max-h-[380px] overflow-y-auto p-2">
          {flatItems.length === 0 ? (
            <div className="py-12 text-center text-xs text-[var(--text-muted)]">
              未找到与 &quot;{query}&quot; 匹配的标的、事件或系统指令
            </div>
          ) : (
            flatItems.map((item, idx) => {
              const isSelected = idx === selectedIndex
              const prevItem = flatItems[idx - 1]
              const isFirstOfGroup = !prevItem || prevItem.type !== item.type

              const groupLabels: Record<string, string> = {
                action: '功能指令与页面导航',
                candidate: query ? '标的资产池匹配 (全盘万家企业)' : '核心龙头标的直达 (美股 / 日股)',
                event: '突发事件情报雷达',
              }

              return (
                <React.Fragment key={item.id}>
                  {isFirstOfGroup && (
                    <div className="px-3 pt-2.5 pb-1 text-[10px] font-bold text-sky-800/80 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-1 h-3 rounded-full bg-sky-500" />
                      <span>{groupLabels[item.type]}</span>
                    </div>
                  )}

                  {item.type === 'action' && (
                    <div
                      data-index={idx}
                      onClick={() => item.perform()}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex items-center justify-between px-3.5 py-2 rounded-xl cursor-pointer transition-all my-0.5 ${
                        isSelected
                          ? 'bg-sky-500/15 border-l-4 border-sky-600 pl-2.5 shadow-2xs'
                          : 'hover:bg-sky-50/70 border-l-4 border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-7 h-7 rounded-lg bg-sky-100/80 border border-sky-200/80 flex items-center justify-center shrink-0">
                          {item.icon}
                        </div>
                        <div className="truncate">
                          <div className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-2">
                            <span>{item.label}</span>
                          </div>
                          <div className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
                            {item.subtext}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {item.shortcut && (
                          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-sky-200 text-sky-800 shadow-2xs">
                            {item.shortcut}
                          </kbd>
                        )}
                        {isSelected && <CornerDownLeftIcon className="w-3.5 h-3.5 text-sky-600" />}
                      </div>
                    </div>
                  )}

                  {item.type === 'candidate' && (
                    <div
                      data-index={idx}
                      onClick={() => item.perform()}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex items-center justify-between px-3.5 py-2 rounded-xl cursor-pointer transition-all my-0.5 ${
                        isSelected
                          ? 'bg-sky-500/15 border-l-4 border-sky-600 pl-2.5 shadow-2xs'
                          : 'hover:bg-sky-50/70 border-l-4 border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex flex-col items-center justify-center shrink-0 font-mono font-bold text-xs text-emerald-800">
                          <span>{item.ticker.slice(0, 4)}</span>
                        </div>
                        <div className="truncate">
                          <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-2">
                            <span className="font-mono text-sky-950 font-black">{item.ticker}</span>
                            <span
                              className={`text-[9px] px-1.5 py-0.2 rounded font-bold ${
                                item.market === 'US'
                                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                  : 'bg-red-50 text-red-700 border border-red-200'
                              }`}
                            >
                              {item.market}
                            </span>
                            {item.vcp_code && (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200 font-mono font-semibold">
                                VCP临界
                              </span>
                            )}
                            <span className="text-[11px] font-normal text-[var(--text-secondary)] truncate">
                              {item.name}
                            </span>
                          </div>
                          <div className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
                            {item.readiness ? `底账: ${item.readiness}` : '点击穿透至计算分析工作台与 DCF 走廊'}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {item.price !== null && (
                          <div className="text-right font-mono">
                            <span className="text-xs font-bold text-[var(--text-primary)]">
                              {item.price.toFixed(2)}
                            </span>
                            <span className="text-[10px] text-[var(--text-muted)] ml-1">
                              {item.currency}
                            </span>
                          </div>
                        )}
                        {isSelected && <CornerDownLeftIcon className="w-3.5 h-3.5 text-sky-600" />}
                      </div>
                    </div>
                  )}

                  {item.type === 'event' && (
                    <div
                      data-index={idx}
                      onClick={() => item.perform()}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex items-center justify-between px-3.5 py-2 rounded-xl cursor-pointer transition-all my-0.5 ${
                        isSelected
                          ? 'bg-amber-500/15 border-l-4 border-amber-600 pl-2.5 shadow-2xs'
                          : 'hover:bg-amber-50/70 border-l-4 border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
                          <TargetIcon className="w-3.5 h-3.5 text-amber-600" />
                        </div>
                        <div className="truncate">
                          <div className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-2">
                            <span className="truncate">{item.title}</span>
                            <span
                              className={`text-[9px] px-1.5 py-0.2 rounded font-bold font-mono ${
                                item.severity === 'P0'
                                  ? 'bg-red-100 text-red-800 border border-red-300'
                                  : 'bg-amber-100 text-amber-800 border border-amber-200'
                              }`}
                            >
                              {item.severity}
                            </span>
                          </div>
                          <div className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
                            {item.publishedAt ? `发布: ${item.publishedAt}` : '点击穿透查看事件影响与因果雷达'}
                          </div>
                        </div>
                      </div>
                      {isSelected && <CornerDownLeftIcon className="w-3.5 h-3.5 text-amber-600 shrink-0" />}
                    </div>
                  )}
                </React.Fragment>
              )
            })
          )}
        </div>

        {/* 底部键盘快捷键提示 */}
        <div className="px-4 py-2.5 bg-sky-100/60 border-t border-sky-200/70 flex items-center justify-between text-[11px] text-[var(--text-muted)] font-mono">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white text-sky-800 border border-sky-200">↑↓</kbd>
              <span>导航</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white text-sky-800 border border-sky-200">↵</kbd>
              <span>执行/直达</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white text-sky-800 border border-sky-200">1~6</kbd>
              <span>切屏</span>
            </span>
          </div>
          <div className="text-[10px] text-sky-800 font-sans">
            按 <kbd className="px-1 py-0.2 rounded bg-white border border-sky-200">ESC</kbd> 退出
          </div>
        </div>
      </div>
    </div>
  )
}
