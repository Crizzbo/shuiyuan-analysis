import { useCallback, useEffect, useState } from 'react'
import './App.css'

import { api } from './services/api'
import type { HealthData, PipelineStatusData, LogItem } from './types/api'
import { useSSE } from './hooks/useSSE'
import { Header } from './components/Header'
import { DashboardTab } from './components/DashboardTab'
import { AnalyticsTab } from './components/AnalyticsTab'
import { SystemOpsTab } from './components/SystemOpsTab'
import { CompanyDrawer } from './components/common/CompanyDrawer'
import { ToastContainer } from './components/Toast'

const tabs = [
  { id: 'overview', label: '投资决策总览' },
  { id: 'analytics', label: '标的计算中心' },
  { id: 'system', label: '系统底账运维' },
] as const
type Tab = (typeof tabs)[number]['id']

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [systemSubTab, setSystemSubTab] = useState<'collection' | 'intelligence' | 'settings' | 'logs'>('collection')
  const [health, setHealth] = useState<HealthData | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusData | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [drawerTicker, setDrawerTicker] = useState<string | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
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
        sseConnected={connected}
        onPipelineStarted={() => {
          setSystemSubTab('collection')
          setTab('system')
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
        {tab === 'overview' && (
          <DashboardTab
            refreshKey={refreshKey}
            onNavigateTab={(target) => {
              if (target === 'analytics') {
                setTab('analytics')
              } else if (target === 'collection' || target === 'intelligence' || target === 'settings' || target === 'logs') {
                setSystemSubTab(target)
                setTab('system')
              }
            }}
            onSelectEvent={(eventId) => {
              setSelectedEventId(eventId)
              setSystemSubTab('intelligence')
              setTab('system')
            }}
            onSelectTicker={(ticker) => {
              setSelectedTicker(ticker)
              setDrawerTicker(ticker)
              setIsDrawerOpen(true)
            }}
          />
        )}

        {tab === 'analytics' && (
          <AnalyticsTab refreshKey={refreshKey} initialTicker={selectedTicker} />
        )}

        {tab === 'system' && (
          <SystemOpsTab
            pipelineStatus={pipelineStatus}
            realtimeLogs={realtimeLogs}
            refreshKey={refreshKey}
            defaultSubTab={systemSubTab}
            selectedEventId={selectedEventId}
            onClearSelectedEvent={() => setSelectedEventId(null)}
            onSelectTicker={(ticker) => {
              setSelectedTicker(ticker)
              setDrawerTicker(ticker)
              setIsDrawerOpen(true)
            }}
          />
        )}
      </main>

      {/* 右侧标的全息底账与 25 模型速览抽屉 */}
      <CompanyDrawer
        isOpen={isDrawerOpen}
        ticker={drawerTicker}
        onClose={() => setIsDrawerOpen(false)}
        onOpenFullAnalytics={(t) => {
          setSelectedTicker(t)
          setIsDrawerOpen(false)
          setTab('analytics')
        }}
      />

      <ToastContainer />
    </>
  )
}
