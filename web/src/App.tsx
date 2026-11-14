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
  const [health, setHealth] = useState<HealthData | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusData | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [realtimeLogs, setRealtimeLogs] = useState<LogItem[]>([])
  const [refreshKey, setRefreshKey] = useState(0)

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
        pipelineStatus={pipelineStatus}
        sseConnected={connected}
        onPipelineStatusChange={setPipelineStatus}
        onPipelineStarted={() => {
          setTab('collection')
        }}
      />
      <div className="site-header">
        <nav className="container main-nav" aria-label="主导航">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
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
              setTab('intelligence')
            }}
          />
        )}

        {tab === 'intelligence' && (
          <IntelligenceTab
            selectedEventId={selectedEventId}
            onClearSelectedEvent={() => setSelectedEventId(null)}
            refreshKey={refreshKey}
          />
        )}

        {tab === 'collection' && (
          <CollectionTab pipelineStatus={pipelineStatus} />
        )}

        {tab === 'analytics' && (
          <AnalyticsTab refreshKey={refreshKey} />
        )}

        {tab === 'logs' && (
          <LogsTab realtimeLogs={realtimeLogs} />
        )}

        {tab === 'settings' && (
          <SettingsTab />
        )}
      </main>
      <ToastContainer />
    </>
  )
}
