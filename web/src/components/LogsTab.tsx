import { useState, useEffect, useMemo } from 'react'
import type { LogItem, LogFileInfo } from '../types/api'
import { api } from '../services/api'
import { Pagination } from './Pagination'
import { formatDeviceTime, toChinese } from '../utils/format'

interface LogsTabProps {
  realtimeLogs?: LogItem[]
  refreshKey?: number
}

const MODULE_PRESETS: Array<{ id: string; label: string; icon: string }> = [
  { id: 'ALL', label: '全部模块', icon: '📋' },
  { id: 'event_radar', label: '事件雷达', icon: '⚡' },
  { id: 'evidence_verification', label: '公报核验', icon: '🛡️' },
  { id: 'terminal_scheduler', label: '任务调度', icon: '⏱️' },
  { id: 'terminal_service', label: '终端服务', icon: '🌐' },
  { id: 'alert_dispatcher', label: '告警分发', icon: '🚨' },
  { id: 'market_quotes', label: '行情归档', icon: '📈' },
  { id: 'pipeline_orchestrator', label: '信息流水线', icon: '🔄' },
]

const MODULE_ZH_MAP: Record<string, string> = {
  event_radar: '事件雷达',
  evidence_verification: '公报核验',
  terminal_scheduler: '任务调度',
  terminal_service: '终端服务',
  alert_dispatcher: '告警分发',
  market_quotes: '行情归档',
  pipeline_orchestrator: '信息流水线',
  screening_engine: '选股初筛',
  audit_ledger: '预测账本审计',
  filing_audit: '三表核对',
  quant_valuation: '量化估值',
  system_core: '系统核心',
}

const MODULE_COLOR_MAP: Record<string, string> = {
  event_radar: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  evidence_verification: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  terminal_scheduler: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  terminal_service: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  alert_dispatcher: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
  market_quotes: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  pipeline_orchestrator: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
  screening_engine: 'bg-teal-500/15 text-teal-400 border-teal-500/30',
  audit_ledger: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
}

export function LogsTab({ realtimeLogs = [], refreshKey }: LogsTabProps) {
  const [logs, setLogs] = useState<LogItem[]>([])
  const [levelFilter, setLevelFilter] = useState('ALL')
  const [moduleFilter, setModuleFilter] = useState('ALL')
  const [availableModules, setAvailableModules] = useState<string[]>([])
  const [logFiles, setLogFiles] = useState<LogFileInfo[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 40
  const [loading, setLoading] = useState(true)

  const loadLogs = async () => {
    try {
      setLoading(true)
      const res = await api.getLogs({
        level: levelFilter,
        module: moduleFilter !== 'ALL' ? moduleFilter : undefined,
        q: appliedQuery || undefined,
        limit: 500,
      })
      if (res.ok) {
        setLogs(res.data.logs)
        if (res.data.available_modules) {
          setAvailableModules(res.data.available_modules)
        }
        if (res.data.log_files) {
          setLogFiles(res.data.log_files)
        }
      }
    } catch (err) {
      console.error('Failed to load logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setCurrentPage(1)
    void loadLogs()
  }, [levelFilter, moduleFilter, appliedQuery])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadLogs(), 250)
    return () => window.clearTimeout(timer)
  }, [refreshKey])

  // 合并实时推流日志
  const combinedLogs = useMemo(() => {
    const query = appliedQuery.toLowerCase()
    const entries = new Map([...logs, ...realtimeLogs].map(log => [log.log_id, log]))
    return [...entries.values()]
      .filter(log => {
        const matchLevel = levelFilter === 'ALL' || log.level === levelFilter
        const matchModule = moduleFilter === 'ALL' || log.module?.toLowerCase() === moduleFilter.toLowerCase()
        const matchQuery = !query || [log.message, log.module, log.run_id, log.task].some(value => value?.toLowerCase().includes(query))
        return matchLevel && matchModule && matchQuery
      })
      .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
  }, [realtimeLogs, logs, levelFilter, moduleFilter, appliedQuery])

  const totalItems = combinedLogs.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const pagedLogs = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return combinedLogs.slice(start, start + pageSize)
  }, [combinedLogs, currentPage, pageSize])

  // 计算模块合集：预置模块 + 后端动态发现模块
  const allModuleOptions = useMemo(() => {
    const seen = new Set(MODULE_PRESETS.map(m => m.id))
    const extra = availableModules
      .filter(m => !seen.has(m))
      .map(m => ({ id: m, label: MODULE_ZH_MAP[m] || m, icon: '📦' }))
    return [...MODULE_PRESETS, ...extra]
  }, [availableModules])

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-5">
      {/* 1. 物理专属落盘日志文件状态总览 */}
      {logFiles.length > 0 && (
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-[var(--border-color)]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#199e70]" />
              <h3 className="text-xs font-bold text-[var(--text-primary)]">
                物理专属日志文件落盘体系 (data/logs/ · 10MB 自动轮转)
              </h3>
            </div>
            <span className="text-[11px] text-[var(--text-muted)] font-mono">
              共挂载 {logFiles.length} 个专属分流通道
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
            {logFiles.map((f) => (
              <div
                key={f.filename}
                className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/40 rounded-lg p-2.5 flex flex-col justify-between transition-all"
                title={`物理文件路径: ${f.path}`}
              >
                <div className="text-[11px] font-bold font-mono text-[var(--text-primary)] truncate">
                  {f.filename}
                </div>
                <div className="flex items-center justify-between mt-1.5 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">{f.size_formatted}</span>
                  <span className={`px-1.5 py-0.2 rounded font-medium ${f.exists ? 'bg-[#199e70]/15 text-[#199e70]' : 'bg-gray-700/20 text-gray-500'}`}>
                    {f.exists ? '落盘正常' : '待初始化'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2. 头部过滤控制栏 (级别 + 专属模块 + 检索) */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 space-y-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* 日志级别筛选 */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-[var(--text-muted)] font-medium">日志级别:</span>
            {[
              { id: 'ALL', label: '全部级别' },
              { id: 'INFO', label: '信息' },
              { id: 'WARN', label: '预警' },
              { id: 'ERROR', label: '异常' },
            ].map((lvl) => (
              <button
                type="button"
                key={lvl.id}
                onClick={() => setLevelFilter(lvl.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  levelFilter === lvl.id
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--border-color)]'
                }`}
              >
                {lvl.label}
              </button>
            ))}
          </div>

          {/* 关键字搜索框 */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="搜索日志消息、模块、线程或运行编号..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && setAppliedQuery(searchQuery.trim())}
              className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs w-64 focus:outline-none focus:border-[#3987e5]"
            />
            <button
              type="button"
              onClick={() => setAppliedQuery(searchQuery.trim())}
              className="px-3 py-1.5 bg-[#3987e5] text-white rounded-lg text-xs hover:bg-[#2a78d6] cursor-pointer"
            >
              筛选
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setAppliedQuery('')
                setLevelFilter('ALL')
                setModuleFilter('ALL')
              }}
              className="px-2.5 py-1.5 bg-[var(--bg-card)] text-[var(--text-secondary)] rounded-lg text-xs hover:bg-[var(--border-color)] border border-[var(--border-color)] cursor-pointer"
            >
              重置
            </button>
          </div>
        </div>

        {/* 专属模块 (Module) 快捷切档药丸 */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-[var(--border-color)]/60 text-xs">
          <span className="text-[11px] text-[var(--text-muted)] mr-1">专属模块:</span>
          {allModuleOptions.map((mod) => (
            <button
              type="button"
              key={mod.id}
              onClick={() => setModuleFilter(mod.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer flex items-center gap-1 ${
                moduleFilter === mod.id
                  ? 'bg-[#199e70] text-white shadow-sm'
                  : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:border-[#199e70]'
              }`}
            >
              <span>{mod.icon}</span>
              <span>{mod.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 3. 终端风格控制台日志流水 */}
      <div className="bg-[#090d16] border border-[#27354b] rounded-xl p-4 font-mono text-xs shadow-inner min-h-[500px] max-h-[70vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-gray-800 text-[11px] text-gray-500 mb-2">
          <span>系统运行日志（共收录 {combinedLogs.length} 条记录）</span>
          <span className="flex items-center gap-1.5 text-[#199e70]">
            <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
            SSE 实时推流已就绪
          </span>
        </div>

        {loading && logs.length === 0 ? (
          <div className="text-gray-500 py-12 text-center flex items-center justify-center gap-2">
            <span className="w-3.5 h-3.5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
            正在调取各专属模块日志审计流...
          </div>
        ) : pagedLogs.length === 0 ? (
          <div className="text-gray-500 py-12 text-center">
            暂无匹配条件的日志记录
          </div>
        ) : (
          <div className="space-y-1.5">
            {pagedLogs.map((log) => {
              const modCls = MODULE_COLOR_MAP[log.module] || 'bg-gray-700/20 text-gray-400 border-gray-700/30'
              return (
                <div
                  key={log.log_id}
                  className="flex items-start gap-2.5 py-1 border-b border-gray-800/30 hover:bg-gray-800/20 px-2 rounded leading-relaxed transition-colors"
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
                    {{ INFO: '信息', WARN: '预警', ERROR: '异常' }[log.level] ?? log.level}
                  </span>
                  {/* 模块标签：支持点击快速切档到该模块 */}
                  <button
                    type="button"
                    onClick={() => setModuleFilter(log.module)}
                    className={`px-1.5 py-0.2 rounded text-[10px] font-semibold border shrink-0 cursor-pointer hover:opacity-80 transition-opacity ${modCls}`}
                    title={`点击仅查看 ${MODULE_ZH_MAP[log.module] || log.module} 模块专属日志`}
                  >
                    {log.task ? toChinese(log.task) : (MODULE_ZH_MAP[log.module] || log.module)}
                  </button>
                  <span className="min-w-0 text-gray-200 break-words flex-1">
                    {log.status && <span className="text-gray-400 font-semibold">{toChinese(log.status)} · </span>}
                    {log.message}
                    {log.run_id && (
                      <button
                        type="button"
                        className="ml-2 text-sky-400 hover:text-sky-300 underline font-mono text-[10px]"
                        title={`点击筛选该运行批次: ${log.run_id}`}
                        onClick={() => {
                          setSearchQuery(log.run_id!)
                          setAppliedQuery(log.run_id!)
                        }}
                      >
                        运行 {log.run_id.slice(0, 8)}
                      </button>
                    )}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 4. 分页控制 */}
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
