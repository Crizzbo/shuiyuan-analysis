import { useState, useEffect } from 'react'
import type { PipelineStatusData, LogItem } from '../types/api'
import { CollectionTab } from './CollectionTab'
import { IntelligenceTab } from './IntelligenceTab'
import { SettingsTab } from './SettingsTab'
import { LogsTab } from './LogsTab'

interface SystemOpsTabProps {
  pipelineStatus: PipelineStatusData | null
  realtimeLogs: LogItem[]
  refreshKey?: number
  defaultSubTab?: 'collection' | 'intelligence' | 'settings' | 'logs'
  selectedEventId?: string | null
  onClearSelectedEvent?: () => void
  onSelectTicker?: (ticker: string) => void
}

type SubTab = 'collection' | 'intelligence' | 'settings' | 'logs'

export function SystemOpsTab({
  pipelineStatus,
  realtimeLogs,
  refreshKey,
  defaultSubTab = 'collection',
  selectedEventId,
  onClearSelectedEvent,
  onSelectTicker,
}: SystemOpsTabProps) {
  const [subTab, setSubTab] = useState<SubTab>(defaultSubTab)

  useEffect(() => {
    if (defaultSubTab) {
      setSubTab(defaultSubTab)
    }
  }, [defaultSubTab])

  return (
    <div className="space-y-4">
      {/* 运维中心二级纯文本导航栏 */}
      <div className="bg-[var(--surface-color)] border-b border-[var(--border-color)] px-6 py-2 shadow-xs">
        <div className="container max-w-[1600px] flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[var(--text-primary)] mr-2">
              系统底账与运维管理
            </span>
            <div className="flex items-center gap-1.5">
              {[
                { id: 'collection', label: '数据采集与调度' },
                { id: 'intelligence', label: '权威事件与舆情' },
                { id: 'settings', label: '投研合规与防伪账本' },
                { id: 'logs', label: '系统运行日志' },
              ].map((item) => {
                const active = subTab === item.id
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSubTab(item.id as SubTab)}
                    className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all cursor-pointer ${
                      active
                        ? 'bg-[#176249] text-white shadow-xs'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-100'
                    }`}
                  >
                    {item.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="text-[11px] font-mono text-[var(--text-muted)] hidden sm:block">
            密码学防伪时间链条 · 本地零污染沙箱
          </div>
        </div>
      </div>

      {/* 子视图挂载 */}
      <div>
        {subTab === 'collection' && (
          <CollectionTab pipelineStatus={pipelineStatus} refreshKey={refreshKey} />
        )}
        {subTab === 'intelligence' && (
          <IntelligenceTab
            selectedEventId={selectedEventId}
            onClearSelectedEvent={onClearSelectedEvent}
            refreshKey={refreshKey}
            onSelectTicker={onSelectTicker}
          />
        )}
        {subTab === 'settings' && <SettingsTab />}
        {subTab === 'logs' && (
          <LogsTab realtimeLogs={realtimeLogs} refreshKey={refreshKey} />
        )}
      </div>
    </div>
  )
}
export default SystemOpsTab
