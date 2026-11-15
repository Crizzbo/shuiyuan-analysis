import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { showToast } from './Toast'
import { SettingsIcon } from './common'

interface TaskConfigModalProps {
  isOpen: boolean
  onClose: () => void
  selectedTaskId?: string | null
  onConfigSaved?: () => void
}

export function TaskConfigModal({
  isOpen,
  onClose,
  selectedTaskId,
  onConfigSaved,
}: TaskConfigModalProps) {
  const [fullConfig, setFullConfig] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [activeTaskId, setActiveTaskId] = useState<string>('STOCK_SCREENING')
  const [jsonText, setJsonText] = useState<string>('')
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [isRawJsonMode, setIsRawJsonMode] = useState<boolean>(false)

  const loadConfig = async () => {
    try {
      setLoading(true)
      const res = await api.getTaskConfig()
      if (res.ok && res.data) {
        setFullConfig(res.data)
        const initialTask = selectedTaskId || activeTaskId || 'STOCK_SCREENING'
        setActiveTaskId(initialTask)
        if (res.data.tasks && res.data.tasks[initialTask]) {
          setJsonText(JSON.stringify(res.data.tasks[initialTask], null, 2))
        }
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '加载任务配置失败',
        message: err.message || '网络连接或服务端异常',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      void loadConfig()
    }
  }, [isOpen, selectedTaskId])

  // 当切换选中任务时，同步更新 jsonText
  const handleSelectTask = (taskId: string) => {
    setActiveTaskId(taskId)
    setJsonError(null)
    if (fullConfig?.tasks?.[taskId]) {
      setJsonText(JSON.stringify(fullConfig.tasks[taskId], null, 2))
    }
  }

  // 处理文本域中的 JSON 编辑
  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    setJsonText(text)
    try {
      const parsed = JSON.parse(text)
      setJsonError(null)
      // 同步回 fullConfig 临时状态
      setFullConfig((prev: any) => {
        if (!prev) return prev
        return {
          ...prev,
          tasks: {
            ...prev.tasks,
            [activeTaskId]: parsed,
          },
        }
      })
    } catch (err: any) {
      setJsonError(`JSON 语法格式错误: ${err.message}`)
    }
  }

  // 保存配置到后端 SSOT
  const handleSave = async () => {
    if (jsonError) {
      showToast({
        type: 'error',
        title: '无法保存配置',
        message: '请先修正 JSON 语法格式错误',
      })
      return
    }

    try {
      setSaving(true)
      // 确保当前 activeTask 的 jsonText 得到应用
      const currentTaskConfig = JSON.parse(jsonText)
      const updatedConfig = {
        ...fullConfig,
        updated_at: new Date().toISOString(),
        tasks: {
          ...(fullConfig?.tasks || {}),
          [activeTaskId]: currentTaskConfig,
        },
      }

      const res = await api.updateTaskConfig(updatedConfig)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '任务配置已落盘 (SSOT)',
          message: `[${currentTaskConfig.name_zh || activeTaskId}] 参数已成功保存至 config/terminal_tasks.json`,
        })
        onConfigSaved?.()
        onClose()
      } else {
        showToast({
          type: 'error',
          title: '保存失败',
          message: res.error?.message || '后端拒绝更新配置',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '保存异常',
        message: err.message || '网络或数据序列化异常',
      })
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  const tasksMap = fullConfig?.tasks || {}
  const taskKeys = Object.keys(tasksMap)
  const currentTask = tasksMap[activeTaskId] || {}

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 backdrop-blur-sm p-4">
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in duration-200">
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-color)] bg-[var(--bg-card)]">
          <div className="flex items-center gap-3">
            <SettingsIcon className="w-5 h-5 text-slate-700" />
            <div>
              <h2 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <span>数据运营任务参数配置</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-mono font-medium">
                  config/terminal_tasks.json
                </span>
              </h2>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                配置各数据任务的调度排程、批处理规模、过滤规则与执行阈值。
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-color)] transition-colors cursor-pointer text-base"
          >
            ✕
          </button>
        </div>

        {/* 内容主体：左侧任务列表 + 右侧参数详情与 JSON 编辑器 */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* 左侧任务导航 */}
          <div className="w-full md:w-64 border-r border-[var(--border-color)] bg-[var(--bg-card)]/50 p-3 overflow-y-auto space-y-1.5 shrink-0">
            <div className="text-[11px] font-semibold text-[var(--text-muted)] px-2 py-1 mb-1">
              8 项运营任务清单
            </div>
            {taskKeys.map((k) => {
              const t = tasksMap[k]
              const isSelected = k === activeTaskId
              const isCollection = t.track === 'DATA_COLLECTION'

              return (
                <button
                  key={k}
                  onClick={() => handleSelectTask(k)}
                  className={`w-full text-left p-2.5 rounded-xl transition-all cursor-pointer flex flex-col gap-1 border ${
                    isSelected
                      ? 'bg-[#3987e5]/15 border-[#3987e5] text-[var(--text-primary)] shadow-sm'
                      : 'border-transparent hover:bg-[var(--surface-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold truncate">{t.name_zh || k}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                        isCollection
                          ? 'bg-[#3987e5]/20 text-[#3987e5]'
                          : 'bg-[#199e70]/20 text-[#199e70]'
                      }`}
                    >
                      {isCollection ? '采集轨' : '核对轨'}
                    </span>
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] font-mono truncate">
                    {t.schedule?.display_zh || t.schedule?.cron_expr || '按需'}
                  </div>
                </button>
              )
            })}
          </div>

          {/* 右侧详情与编辑区域 */}
          <div className="flex-1 flex flex-col overflow-y-auto p-5 space-y-4">
            {loading ? (
              <div className="flex-1 flex items-center justify-center p-12">
                <div className="w-6 h-6 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <>
                {/* 任务头信息 */}
                <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-[var(--text-primary)]">
                        {currentTask.name_zh || activeTaskId}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-gray-500/15 text-[var(--text-muted)]">
                        ID: {activeTaskId}
                      </span>
                    </div>
                    <div className="text-xs text-[var(--text-secondary)] mt-1">
                      {currentTask.description_zh}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsRawJsonMode(!isRawJsonMode)}
                      className="px-2.5 py-1 text-xs rounded-lg border border-[var(--border-color)] bg-[var(--surface-color)] hover:border-[#3987e5] text-[var(--text-secondary)] cursor-pointer"
                    >
                      {isRawJsonMode ? '切换结构化视图' : '查看/编辑完整 JSON'}
                    </button>
                  </div>
                </div>

                {/* 结构化参数展示 / 快速调整 */}
                {!isRawJsonMode ? (
                  <div className="space-y-4">
                    {/* 基础运行属性 */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="p-3 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)]/70">
                        <div className="text-[11px] text-[var(--text-muted)] font-medium">执行轨道</div>
                        <div className="text-xs font-semibold text-[var(--text-primary)] mt-0.5">
                          {currentTask.track === 'DATA_COLLECTION'
                            ? '外部增量数据采集 (Track 2)'
                            : '本地核对与同步任务 (Track 1)'}
                        </div>
                      </div>

                      <div className="p-3 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)]/70">
                        <div className="text-[11px] text-[var(--text-muted)] font-medium">调度排程 (Cron)</div>
                        <div className="text-xs font-mono font-semibold text-[var(--text-primary)] mt-0.5">
                          {currentTask.schedule?.display_zh} ({currentTask.schedule?.cron_expr})
                        </div>
                      </div>
                    </div>

                    {/* 核心参数字典 */}
                    <div className="p-4 bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]/80 space-y-3">
                      <div className="text-xs font-bold text-[var(--text-primary)] flex items-center justify-between">
                        <span>业务运行参数 (Runtime Parameters)</span>
                        <span className="text-[10px] text-[var(--text-muted)] font-mono">
                          {Object.keys(currentTask.params || {}).length} 项配置
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {Object.entries(currentTask.params || {}).map(([pkey, pval]) => (
                          <div
                            key={pkey}
                            className="p-2.5 rounded bg-[var(--surface-color)] border border-[var(--border-color)] flex flex-col justify-between"
                          >
                            <span className="text-[11px] text-[var(--text-muted)] font-mono">{pkey}</span>
                            <span className="text-xs font-bold font-mono text-[var(--text-primary)] mt-1">
                              {typeof pval === 'boolean'
                                ? pval
                                  ? 'TRUE'
                                  : 'FALSE'
                                : String(pval)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="text-[11px] text-[var(--text-muted)] italic">
                      提示：点击右上角「查看/编辑完整 JSON」可自由增删字段并调整 Cron 表达式或批次上限。
                    </div>
                  </div>
                ) : (
                  /* 完整 JSON 文本编辑器 */
                  <div className="flex-1 flex flex-col space-y-2">
                    <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                      <span>可直接在此编辑当前任务的 JSON 配置，点击保存即写入任务配置：</span>
                      {jsonError && <span className="text-rose-600 font-medium">{jsonError}</span>}
                    </div>
                    <textarea
                      value={jsonText}
                      onChange={handleJsonChange}
                      rows={14}
                      className={`w-full font-mono text-xs p-3.5 rounded-xl bg-[var(--bg-card)] border focus:outline-none transition-colors leading-relaxed ${
                        jsonError
                          ? 'border-rose-500 text-rose-600'
                          : 'border-[var(--border-color)] text-[var(--text-primary)] focus:border-[#176249]'
                      }`}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* 底部操作栏 */}
        <div className="px-6 py-3.5 border-t border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between">
          <div className="text-xs text-[var(--text-muted)]">
            配置文件: <code className="font-mono text-[var(--text-secondary)]">config/terminal_tasks.json</code>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg border border-[var(--border-color)] text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-color)] cursor-pointer"
            >
              取消
            </button>
            <button
              type="button"
              disabled={saving || !!jsonError || loading}
              onClick={handleSave}
              className="px-5 py-1.5 rounded-lg bg-[#176249] hover:bg-[#14533e] active:scale-95 text-white text-xs font-semibold shadow-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-1.5"
            >
              {saving ? (
                <>
                  <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>正在保存...</span>
                </>
              ) : (
                <span>保存任务配置</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
