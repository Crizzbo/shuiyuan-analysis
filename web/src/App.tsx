import { useCallback, useEffect, useState } from 'react'
import './App.css'

import { api } from './services/api'
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
import { CommandPalette } from './components/common/CommandPalette'

const tabs = [
  { id: 'dashboard', label: '总览' },
  { id: 'intelligence', label: '事件情报' },
  { id: 'collection', label: '采集中心' },
  { id: 'analytics', label: '计算分析' },
  { id: 'logs', label: '系统日志' },
  { id: 'settings', label: '合规审计' },
] as const
type Tab = (typeof tabs)[number]['id']

export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('shuiyuan_theme')
      if (saved === 'dark' || saved === 'light') return saved
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
    }
    return 'light'
  })
  const [health, setHealth] = useState<HealthData | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusData | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [realtimeLogs, setRealtimeLogs] = useState<LogItem[]>([])
  const [refreshKey, setRefreshKey] = useState(0)
  const [isPaletteOpen, setIsPaletteOpen] = useState(false)

  // 极夜暗黑交易模式与 DOM/本地缓存双向挂载
  useEffect(() => {
    const isDark = theme === 'dark'
    document.documentElement.classList.toggle('dark', isDark)
    document.body.classList.toggle('dark', isDark)
    localStorage.setItem('shuiyuan_theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  const refreshHealth = useCallback(async () => {
    const [status, healthResponse] = await Promise.all([
      api.getPipelineStatus(),
      api.getHealth(),
    ])
    if (status.ok) setPipelineStatus(status.data)
    if (healthResponse.ok) setHealth(healthResponse.data)
  }, [])

  useEffect(() => {
    void refreshHealth()
  }, [refreshHealth])

  // 全局键盘快捷键监听 (Cmd+K / Ctrl+K 以及 1~6 快捷切屏)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // 1. Cmd+K / Ctrl+K 切换命令面板
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setIsPaletteOpen((prev) => !prev)
        return
      }

      // 如果当前聚焦在输入框内，不拦截单键数字快捷键
      const activeTagName = (document.activeElement?.tagName || '').toLowerCase()
      if (activeTagName === 'input' || activeTagName === 'textarea' || activeTagName === 'select') {
        return
      }

      // 2. 纯数字键 1~6 快速切换标签页 (当命令面板未打开时)
      if (!isPaletteOpen && ['1', '2', '3', '4', '5', '6'].includes(e.key)) {
        const targetTabMap: Record<string, Tab> = {
          '1': 'dashboard',
          '2': 'intelligence',
          '3': 'collection',
          '4': 'analytics',
          '5': 'logs',
          '6': 'settings',
        }
        const targetTab = targetTabMap[e.key]
        if (targetTab) {
          e.preventDefault()
          setTab(targetTab)
        }
      }
    }

    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [isPaletteOpen])

  const { connected } = useSSE({
    onPipelineStatus: setPipelineStatus,
    onSnapshot: () => {
      setRefreshKey((key) => key + 1)
      void refreshHealth()
    },
    onLogEntry: (log) => setRealtimeLogs((previous) => [log, ...previous].slice(0, 100)),
    onCollectionUpdate: () => setRefreshKey((key) => key + 1),
  })

  return (
    <>
      <Header
        health={health}
        sseConnected={connected}
        theme={theme}
        onToggleTheme={toggleTheme}
        onPipelineStarted={() => {
          setTab('collection')
        }}
        onOpenCommandPalette={() => setIsPaletteOpen(true)}
      />
      <div className="site-header">
        <nav className="container main-nav" aria-label="主导航">
          {tabs.map((item, index) => (
            <button
              key={item.id}
              type="button"
              aria-current={tab === item.id ? 'page' : undefined}
              onClick={() => setTab(item.id)}
              title={`按 ${index + 1} 快速切换`}
            >
              <span>{item.label}</span>
              <span className="ml-1.5 text-[10px] font-mono opacity-50 font-normal">
                {index + 1}
              </span>
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
              setTab('intelligence')
            }}
            onSelectTicker={(ticker) => {
              setSelectedTicker(ticker)
              setTab('analytics')
            }}
          />
        )}

        {tab === 'intelligence' && (
          <IntelligenceTab
            selectedEventId={selectedEventId}
            onClearSelectedEvent={() => setSelectedEventId(null)}
            refreshKey={refreshKey}
            onSelectTicker={(ticker) => {
              setSelectedTicker(ticker)
              setTab('analytics')
            }}
          />
        )}

        {tab === 'collection' && (
          <CollectionTab pipelineStatus={pipelineStatus} refreshKey={refreshKey} onAudit={() => setTab('settings')}
            onNavigateToAnalytics={(ticker) => {
              setSelectedTicker(ticker)
              setTab('analytics')
            }}
          />
        )}

        {tab === 'analytics' && (
          <AnalyticsTab refreshKey={refreshKey} initialTicker={selectedTicker} />
        )}

        {tab === 'logs' && (
          <LogsTab realtimeLogs={realtimeLogs} refreshKey={refreshKey} />
        )}

        {tab === 'settings' && (
          <SettingsTab />
        )}
      </main>

      {/* 全局 Cmd+K 命令面板与万家资产池秒级检索中枢 */}
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        onNavigateTab={(targetTab) => {
          if (tabs.some((t) => t.id === targetTab)) {
            setTab(targetTab as Tab)
          }
        }}
        onSelectTicker={(ticker) => {
          setSelectedTicker(ticker)
          setTab('analytics')
        }}
        onSelectEvent={(eventId) => {
          setSelectedEventId(eventId)
          setTab('intelligence')
        }}
        onTriggerPipeline={() => {
          setTab('collection')
          void api.startPipeline('local_audit_sync', 'ALL')
        }}
        onRefreshData={() => {
          setRefreshKey((k) => k + 1)
          void refreshHealth()
        }}
      />

      <ToastContainer />
    </>
  )
}
