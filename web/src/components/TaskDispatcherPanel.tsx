import { useState } from 'react'
import { api } from '../services/api'
import type { TaskSchedulerInfo } from '../types/api'
import { showToast } from './Toast'

interface Props {
  schedulerInfo?: TaskSchedulerInfo | null
  onTaskCompleted: () => Promise<void>
  onManage: () => void
}

export function TaskDispatcherPanel({ schedulerInfo, onTaskCompleted, onManage }: Props) {
  const [busy, setBusy] = useState(false)
  const active = schedulerInfo?.active_runs ?? []
  const automatic = schedulerInfo?.automatic_enabled ?? false

  async function submit(action: 'start' | 'automatic') {
    setBusy(true)
    try {
      const result = action === 'start' ? await api.startTerminalBatch() : await api.setTerminalAutomatic(!automatic)
      if (!result.ok) {
        showToast({ type: 'error', title: '操作失败', message: result.error?.message || '调度服务不可用' })
        return
      }
      showToast({
        type: 'success',
        title: action === 'start' ? '已提交本地核对与数据采集' : '已更新自动调度',
        message: action === 'start' && 'run_id' in result.data ? `运行编号 ${result.data.run_id.slice(0, 8)}` : '',
      })
      await onTaskCompleted()
    } catch (error) {
      showToast({ type: 'error', title: '操作失败', message: error instanceof Error ? error.message : '无法连接调度服务' })
    } finally {
      setBusy(false)
    }
  }

  return <section aria-label="任务控制" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border-color)] bg-[var(--surface-color)] px-4 py-2 text-sm">
    <div className="flex flex-wrap items-center gap-3">
      <button type="button" disabled={busy || !schedulerInfo} onClick={() => void submit('start')}
        className="rounded-md bg-[#176249] px-3 py-1 text-white disabled:opacity-50">启动</button>
      <button type="button" role="switch" aria-checked={automatic} aria-label="自动调度总开关"
        disabled={busy || !schedulerInfo?.automatic_available} onClick={() => void submit('automatic')}
        className="rounded-md border border-[var(--border-color)] px-3 py-1 disabled:opacity-50">
        自动调度{automatic ? '已开' : '已关'}
      </button>
      <span className="text-xs text-[var(--text-muted)]">
        {schedulerInfo ? `本地任务 ${active.filter(run => schedulerInfo.tasks.find(task => task.id === run.task)?.track === 'local').length} 项 · 采集 ${active.filter(run => schedulerInfo.tasks.find(task => task.id === run.task)?.track === 'collection').length} 项进行中` : '等待调度服务'}
      </span>
    </div>
    <button type="button" className="text-xs text-[var(--accent)]" onClick={onManage}>管理任务 →</button>
  </section>
}
