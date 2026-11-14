import { useCallback, useEffect, useState, useMemo } from 'react'
import './App.css'

import { api as terminalApi } from './services/api'
import type { HealthData, PipelineStatusData, LogItem } from './types/api'
import { useSSE } from './hooks/useSSE'
import { Header } from './components/Header'
import { DashboardTab } from './components/DashboardTab'
import { IntelligenceTab } from './components/IntelligenceTab'
import { CollectionTab } from './components/CollectionTab'
import { AnalyticsTab } from './components/AnalyticsTab'
import { LogsTab } from './components/LogsTab'
import { SettingsTab } from './components/SettingsTab'
import { ToastContainer } from './components/Toast'
import { Pagination } from './components/Pagination'
import { formatDeviceTime, toChinese } from './utils/format'

type Run = {
  run_id: string
  task: string
  status: string
  trigger: string
  created_at: string
  result: null | {
    message: string
    items?: { id: string; status: string; result_path?: string; message?: string }[]
  }
}
type Task = { id: string; name: string; schedule: string; enabled: boolean }
type Jobs = { tasks: Task[]; runs: Run[]; scheduled: boolean }
type News = { title: string; published_at: string | null; source: string }
type MarketArchive = { symbol: string; market: string; count: number; last_date: string | null; archived_at: string }


async function api<T>(path: string, body?: Record<string, unknown>): Promise<T> {
  const response = await fetch(
    path,
    body
      ? {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }
      : undefined
  )
  const result = await response.json()
  if (!response.ok || !result.ok) throw new Error(result.error?.message || '请求失败')
  return result.data
}

const tabs = [
  { id: 'dashboard', label: '总览' },
  { id: 'intelligence', label: '事件情报' },
  { id: 'collection', label: '采集中心' },
  { id: 'analytics', label: '计算分析' },
  { id: 'logs', label: '系统日志' },
  { id: 'settings', label: '系统设置' },
] as const
type Tab = (typeof tabs)[number]['id']

export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [collectionView, setCollectionView] = useState<'overview' | 'jobs' | 'archives'>('overview')
  const [intelligenceView, setIntelligenceView] = useState<'radar' | 'news'>('radar')
  const [health, setHealth] = useState<HealthData | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusData | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [realtimeLogs, setRealtimeLogs] = useState<LogItem[]>([])
  const [refreshKey, setRefreshKey] = useState(0)
  const [jobs, setJobs] = useState<Jobs | null>(null)
  const [news, setNews] = useState<News[]>([])
  const [newsError, setNewsError] = useState('')
  const [newsPage, setNewsPage] = useState(1)
  const newsPageSize = 10
  const [marketArchives, setMarketArchives] = useState<MarketArchive[]>([])
  const [marketError, setMarketError] = useState('')
  const [archivePage, setArchivePage] = useState(1)
  const archivePageSize = 12
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [pending, setPending] = useState<string | null>(null)

  const refreshHealth = useCallback(async () => {
    const [status, healthResponse] = await Promise.all([
      terminalApi.getPipelineStatus(),
      terminalApi.getHealth(),
    ])
    if (status.ok) setPipelineStatus(status.data)
    if (healthResponse.ok) setHealth(healthResponse.data)
  }, [])

  useEffect(() => {
    void refreshHealth()
  }, [refreshHealth])

  const { connected } = useSSE({
    onPipelineStatus: setPipelineStatus,
    onSnapshot: () => {
      setRefreshKey((key) => key + 1)
      void refreshHealth()
    },
    onLogEntry: (log) => setRealtimeLogs((previous) => [log, ...previous].slice(0, 100)),
    onCollectionUpdate: () => setRefreshKey((key) => key + 1),
  })

  useEffect(() => {
    if (tab !== 'collection' || collectionView !== 'jobs') return
    let active = true
    async function loadJobs() {
      try {
        const next = await api<Jobs>('/api/terminal/tasks')
        if (active) {
          setJobs(next)
          setError('')
        }
      } catch (cause) {
        if (active) setError((cause as Error).message)
      }
    }
    void loadJobs()
    const timer = window.setInterval(loadJobs, 4000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [tab, collectionView])

  useEffect(() => {
    if (tab !== 'intelligence' || intelligenceView !== 'news') return
    let active = true
    api<{ items: News[] }>('/api/terminal/news')
      .then((result) => {
        if (active) {
          setNews(result.items)
          setNewsError('')
        }
      })
      .catch((cause) => {
        if (active) setNewsError(cause.message)
      })
    return () => {
      active = false
    }
  }, [tab, intelligenceView])

  useEffect(() => {
    if (tab !== 'collection' || collectionView !== 'archives') return
    let active = true
    api<{ items: MarketArchive[] }>('/api/terminal/market-archives')
      .then((result) => {
        if (active) {
          setMarketArchives(result.items)
          setMarketError('')
        }
      })
      .catch((cause) => {
        if (active) setMarketError(cause.message)
      })
    return () => {
      active = false
    }
  }, [tab, collectionView])

  async function command(task: Task, schedule = false) {
    setPending(task.id)
    setNotice('')
    try {
      if (schedule) {
        await api('/api/terminal/tasks/schedule', { task: task.id, enabled: !task.enabled })
        setNotice(`${task.name}定时触发已${task.enabled ? '关闭' : '开启'}`)
      } else {
        const result = await api<{ run_id: string }>('/api/terminal/tasks/run', { task: task.id })
        setNotice(`已提交 ${task.name} · ${result.run_id.slice(0, 8)}`)
      }
      setJobs(await api('/api/terminal/tasks'))
    } catch (cause) {
      setNotice((cause as Error).message)
    } finally {
      setPending(null)
    }
  }

  const runs = jobs?.runs ?? []

  // News pagination
  const pagedNews = useMemo(() => {
    const start = (newsPage - 1) * newsPageSize
    return news.slice(start, start + newsPageSize)
  }, [news, newsPage, newsPageSize])

  // Archive pagination
  const pagedArchives = useMemo(() => {
    const start = (archivePage - 1) * archivePageSize
    return marketArchives.slice(start, start + archivePageSize)
  }, [marketArchives, archivePage, archivePageSize])

  return (
    <>
      <Header
        health={health}
        pipelineStatus={pipelineStatus}
        sseConnected={connected}
        onPipelineStatusChange={setPipelineStatus}
        onPipelineStarted={() => {
          setCollectionView('overview')
          setTab('collection')
        }}
      />
      <div className="site-header">
        <nav className="container main-nav" aria-label="主导航">
          {tabs.map((item) => (
            <button
              key={item.id}
              aria-current={tab === item.id ? 'page' : undefined}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
      <main>
        {tab === 'dashboard' && (
          <DashboardTab
            refreshKey={refreshKey}
            onNavigateTab={(id) => {
              if (tabs.some((item) => item.id === id)) setTab(id as Tab)
            }}
            onSelectEvent={(id) => {
              setSelectedEventId(id)
              setIntelligenceView('radar')
            }}
          />
        )}

        {tab === 'intelligence' && (
          <>
            <Subnav
              options={[
                ['radar', '事件雷达'],
                ['news', '官方来源资讯'],
              ]}
              value={intelligenceView}
              onChange={setIntelligenceView}
            />
            {intelligenceView === 'radar' ? (
              <IntelligenceTab
                selectedEventId={selectedEventId}
                onClearSelectedEvent={() => setSelectedEventId(null)}
                refreshKey={refreshKey}
              />
            ) : (
              <div className="container">
                <section className="panel">
                  <div className="flex items-center justify-between mb-4">
                    <h2>官方来源资讯</h2>
                    <span className="text-xs text-[var(--text-muted)]">共 {news.length} 条资讯</span>
                  </div>
                  {newsError && (
                    <p className="error" role="alert">
                      {newsError}
                    </p>
                  )}
                  {!news.length && !newsError && <p className="muted">暂无本轮资讯归档。</p>}
                  <div className="rows">
                    {pagedNews.map((item, i) => (
                      <div className="row" key={`${item.source}-${i}`}>
                        <div>
                          <strong>{item.title}</strong>
                          <p>
                            {item.published_at ? formatDeviceTime(item.published_at) : '发布时间未提供'} ·{' '}
                            {item.source}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {news.length > newsPageSize && (
                    <div className="mt-4 pt-3 border-t border-[var(--border-color)]">
                      <Pagination
                        currentPage={newsPage}
                        totalPages={Math.ceil(news.length / newsPageSize)}
                        totalItems={news.length}
                        pageSize={newsPageSize}
                        onPageChange={setNewsPage}
                      />
                    </div>
                  )}
                </section>
              </div>
            )}
          </>
        )}

        {tab === 'collection' && (
          <>
            <Subnav
              options={[
                ['overview', '采集概览'],
                ['jobs', '定时任务'],
                ['archives', '日线归档'],
              ]}
              value={collectionView}
              onChange={setCollectionView}
            />
            {collectionView === 'overview' && <CollectionTab pipelineStatus={pipelineStatus} />}
            <div className="container">
              {collectionView === 'archives' && (
                <section className="panel">
                  <div className="flex items-center justify-between mb-4">
                    <h2>最近一批日线归档</h2>
                    <span className="text-xs text-[var(--text-muted)]">
                      共收录 {marketArchives.length} 个标的行情
                    </span>
                  </div>
                  {marketError && (
                    <p className="error" role="alert">
                      {marketError}
                    </p>
                  )}
                  {!marketArchives.length && !marketError && (
                    <p className="muted">暂无日线归档。可在任务页运行美股或日股采集。</p>
                  )}
                  <div className="rows">
                    {pagedArchives.map((item) => (
                      <div className="row" key={item.symbol}>
                        <div>
                          <strong>
                            {item.symbol} · {item.market}
                          </strong>
                          <p>归档时间 {formatDeviceTime(item.archived_at)}</p>
                        </div>
                        <div>
                          <strong>{item.count} 个交易日</strong>
                          <p>最后交易日 {item.last_date ?? '未知'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {marketArchives.length > archivePageSize && (
                    <div className="mt-4 pt-3 border-t border-[var(--border-color)]">
                      <Pagination
                        currentPage={archivePage}
                        totalPages={Math.ceil(marketArchives.length / archivePageSize)}
                        totalItems={marketArchives.length}
                        pageSize={archivePageSize}
                        onPageChange={setArchivePage}
                      />
                    </div>
                  )}
                </section>
              )}

              {collectionView === 'jobs' && (
                <>
                  {error && (
                    <p className="error" role="alert">
                      {error}
                    </p>
                  )}
                  <section className="panel">
                    <div className="section-head">
                      <h2>任务计划</h2>
                      <span className="muted">{jobs?.scheduled ? '定时运行中' : '定时未启用'}</span>
                    </div>
                    <div className="rows">
                      {jobs?.tasks.map((task) => (
                        <div className="row" key={task.id}>
                          <div>
                            <strong>{task.name}</strong>
                            <p>
                              {task.schedule}
                              {task.id !== 'LOCAL_AUDIT' &&
                                (task.enabled ? ' · 已开启' : ' · 已关闭')}
                            </p>
                          </div>
                          <div className="actions">
                            {task.id !== 'LOCAL_AUDIT' && (
                              <button
                                disabled={pending !== null || !jobs?.scheduled}
                                onClick={() => void command(task, true)}
                              >
                                {task.enabled ? '停用定时' : '启用定时'}
                              </button>
                            )}
                            <button
                              disabled={pending !== null}
                              onClick={() => void command(task)}
                            >
                              运行
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    {notice && (
                      <p className="muted" role="status">
                        {notice}
                      </p>
                    )}
                  </section>
                  <section className="panel">
                    <h2>运行记录</h2>
                    <RunList runs={runs} tasks={jobs?.tasks ?? []} />
                  </section>
                </>
              )}
            </div>
          </>
        )}

        {/* 计算分析直接挂载全新数千家企业左侧索引 + 右侧全功能诊断与内嵌DCF/WACC估值走廊 */}
        {tab === 'analytics' && <AnalyticsTab refreshKey={refreshKey} />}

        {tab === 'logs' && <LogsTab realtimeLogs={realtimeLogs} />}
        {tab === 'settings' && <SettingsTab />}
      </main>
      <ToastContainer />
    </>
  )
}

function Subnav<T extends string>({
  options,
  value,
  onChange,
}: {
  options: [T, string][]
  value: T
  onChange: (next: T) => void
}) {
  return (
    <div className="container subnav" role="group" aria-label="页面视图">
      {options.map(([id, label]) => (
        <button
          key={id}
          type="button"
          aria-pressed={id === value}
          onClick={() => onChange(id)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function RunList({ runs, tasks }: { runs: Run[]; tasks: Task[] }) {
  const [page, setPage] = useState(1)
  const pageSize = 10
  const totalPages = Math.max(1, Math.ceil(runs.length / pageSize))
  const pagedRuns = runs.slice((page - 1) * pageSize, page * pageSize)

  return (
    <div className="rows">
      {runs.length ? (
        <>
          {pagedRuns.map((run) => (
            <div className="run" key={run.run_id}>
              <div className="row">
                <div>
                  <strong>{tasks.find((task) => task.id === run.task)?.name ?? run.task}</strong>
                  <p>
                    {formatDeviceTime(run.created_at)} ·{' '}
                    {run.trigger === 'scheduled' ? '定时' : '手动'}
                    {run.result?.message ? ` · ${run.result.message}` : ''}
                  </p>
                </div>
                <span className={`badge ${run.status.toLowerCase()}`}>
                  {toChinese(run.status)}
                </span>
              </div>
              {!!run.result?.items?.length && (
                <details>
                  <summary>归档明细</summary>
                  <ul>
                    {run.result.items.map((item) => (
                      <li key={item.id}>
                        {item.id} · {toChinese(item.status)}{' '}
                        {item.result_path && <code>{item.result_path}</code>} {item.message}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))}
          {runs.length > pageSize && (
            <div className="pt-2">
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                totalItems={runs.length}
                pageSize={pageSize}
                onPageChange={setPage}
              />
            </div>
          )}
        </>
      ) : (
        <p className="muted">暂无运行记录。</p>
      )}
    </div>
  )
}
