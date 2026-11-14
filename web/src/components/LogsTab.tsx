import { useState, useEffect, useMemo } from 'react'
import type { LogItem } from '../types/api'
import { api } from '../services/api'
import { Pagination } from './Pagination'
import { formatDeviceTime } from '../utils/format'

interface LogsTabProps {
  realtimeLogs?: LogItem[]
}

export function LogsTab({ realtimeLogs = [] }: LogsTabProps) {
  const [logs, setLogs] = useState<LogItem[]>([])
  const [levelFilter, setLevelFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 40
  const [loading, setLoading] = useState(true)

  const loadLogs = async () => {
    try {
      setLoading(true)
      const res = await api.getLogs({
        level: levelFilter,
        q: searchQuery.trim() || undefined,
        limit: 150,
      })
      if (res.ok) {
        setLogs(res.data.logs)
      }
    } catch (err) {
      console.error('Failed to load logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setCurrentPage(1)
    loadLogs()
  }, [levelFilter])

  // 合并实时推流日志
  const combinedLogs = useMemo(() => {
    return [...realtimeLogs, ...logs].filter((l, idx, self) => {
      return self.findIndex((item) => item.log_id === l.log_id) === idx
    })
  }, [realtimeLogs, logs])

  const totalItems = combinedLogs.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const pagedLogs = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return combinedLogs.slice(start, start + pageSize)
  }, [combinedLogs, currentPage, pageSize])

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {/* 头部控制栏 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-[var(--text-muted)]">日志级别:</span>
            {[
              { id: 'ALL', label: '全部' },
              { id: 'INFO', label: '信息' },
              { id: 'WARN', label: '预警' },
              { id: 'ERROR', label: '异常' },
            ].map((lvl) => (
              <button
                key={lvl.id}
                onClick={() => setLevelFilter(lvl.id)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                  levelFilter === lvl.id
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--border-color)]'
                }`}
              >
                {lvl.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="搜索日志消息、模块、线程..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadLogs()}
            className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs w-60 focus:outline-none focus:border-[#3987e5]"
          />
          <button
            onClick={loadLogs}
            className="px-3 py-1.5 bg-[#3987e5] text-white rounded-lg text-xs hover:bg-[#2a78d6] cursor-pointer"
          >
            筛选
          </button>
          <button
            onClick={() => {
              setSearchQuery('')
              loadLogs()
            }}
            className="px-2.5 py-1.5 bg-[var(--bg-card)] text-[var(--text-secondary)] rounded-lg text-xs hover:bg-[var(--border-color)] border border-[var(--border-color)] cursor-pointer"
          >
            重置
          </button>
        </div>
      </div>

      {/* 终端风格日志控制台 */}
      <div className="bg-[#090d16] border border-[#27354b] rounded-xl p-4 font-mono text-xs shadow-inner min-h-[500px] max-h-[70vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-gray-800 text-[11px] text-gray-500 mb-2">
          <span>系统运行实时日志流（保留最近 500 条记录）</span>
          <span className="flex items-center gap-1.5 text-[#199e70]">
            <span className="w-2 h-2 rounded-full bg-[#199e70]" />
            实时流同步中
          </span>
        </div>

        {loading && logs.length === 0 ? (
          <div className="text-gray-500 py-8 text-center">正在加载日志流...</div>
        ) : pagedLogs.length === 0 ? (
          <div className="text-gray-500 py-8 text-center">暂无匹配的日志记录</div>
        ) : (
          <div className="space-y-1.5">
            {pagedLogs.map((log) => (
              <div
                key={log.log_id}
                className="flex items-start gap-2.5 py-1 border-b border-gray-800/30 hover:bg-gray-800/20 px-2 rounded leading-relaxed"
              >
                <span className="text-gray-500 shrink-0 text-[11px] font-mono">
                  {formatDeviceTime(log.timestamp)}
                </span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0 ${
                    log.level === 'ERROR'
                      ? 'bg-[#d03b3b]/30 text-[#d03b3b] border border-[#d03b3b]/50'
                      : log.level === 'WARN'
                      ? 'bg-[#c98500]/30 text-[#c98500] border border-[#c98500]/50'
                      : 'bg-[#3987e5]/20 text-[#3987e5]'
                  }`}
                >
                  {log.level}
                </span>
                <span className="text-[#199e70] shrink-0 text-[11px]">[{log.module}]</span>
                <span className="text-gray-200 break-words">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 分页控制 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 shadow-sm">
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalItems}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
        />
      </div>
    </div>
  )
}
