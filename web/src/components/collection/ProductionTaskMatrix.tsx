import type { TaskSchedulerTask } from '../../types/api'
import {
  ShieldCheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '../common'

interface ProductionTaskMatrixProps {
  tasks: TaskSchedulerTask[]
  allRuns: any[]
  runningTaskId: string | null
  showRunsHistory: boolean
  onToggleRunsHistory: () => void
  onConfigureTask: (taskId: string) => void
  onToggleSchedule: (taskId: string, enabled: boolean) => void
  onRunTask: (task: TaskSchedulerTask) => void
}

export function ProductionTaskMatrix({
  tasks,
  allRuns,
  runningTaskId,
  showRunsHistory,
  onToggleRunsHistory,
  onConfigureTask,
  onToggleSchedule,
  onRunTask,
}: ProductionTaskMatrixProps) {
  return (
    <div className="ice-panel rounded-2xl p-5 shadow-xs space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-sky-100">
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span className="p-1 rounded bg-teal-50 text-teal-600">
              <ShieldCheckIcon className="w-4 h-4" />
            </span>
            生产调度任务矩阵 (10 大标准化数据生产流水线)
          </h2>
          <p className="text-[11px] text-slate-500">
            按数据维度独立调度：行情归档、日线对账、舆情抓取、形态初筛、三表核对与账本自检
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleRunsHistory}
            className="px-3 py-1 rounded-lg text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 cursor-pointer flex items-center gap-1"
          >
            <span>{showRunsHistory ? '收起执行流水' : '查看执行流水历史'}</span>
            {showRunsHistory ? <ChevronUpIcon className="w-3.5 h-3.5" /> : <ChevronDownIcon className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* 10 项任务卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {tasks.map(task => (
          <div
            key={task.id}
            className="ice-block rounded-xl p-3.5 flex items-center justify-between gap-3 shadow-2xs"
          >
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-xs text-slate-800 truncate">{task.name}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-50 text-sky-700 border border-sky-200 font-mono">
                  {task.dimension}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">{task.schedule}</div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => onConfigureTask(task.id)}
                className="px-2 py-1 rounded text-[11px] font-medium bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 cursor-pointer"
                title="参数配置"
              >
                配置
              </button>
              <button
                type="button"
                onClick={() => void onToggleSchedule(task.id, task.enabled ?? true)}
                className={`px-2 py-1 rounded text-[11px] font-medium border cursor-pointer ${
                  task.enabled !== false
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                    : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100'
                }`}
                title="切换定时调度"
              >
                {task.enabled !== false ? '已开启' : '已暂停'}
              </button>
              <button
                type="button"
                disabled={runningTaskId === task.id}
                onClick={() => void onRunTask(task)}
                className="px-2.5 py-1 rounded text-[11px] font-bold bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 cursor-pointer disabled:opacity-50"
              >
                {runningTaskId === task.id ? '运行中…' : '立即执行'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 展开任务历史流水 */}
      {showRunsHistory && (
        <div className="pt-2 border-t border-sky-100 space-y-2">
          <div className="text-xs font-bold text-slate-700">最近流水线执行记录:</div>
          <div className="divide-y divide-sky-100 rounded-xl border border-sky-100 bg-white/95 overflow-hidden font-mono text-xs max-h-60 overflow-y-auto">
            {allRuns.length === 0 ? (
              <div className="p-4 text-center text-slate-400">暂无执行流水记录</div>
            ) : (
              allRuns.slice(0, 15).map(run => (
                <div key={run.run_id} className="p-2.5 flex items-center justify-between gap-2 hover:bg-sky-50/50">
                  <div className="space-y-0.5">
                    <div className="font-bold text-slate-800">{run.task}</div>
                    <div className="text-[11px] text-slate-500">{run.created_at} · Run ID: {run.run_id.slice(0, 8)}</div>
                  </div>
                  <div className="text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      run.status === 'SUCCESS' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                    }`}>
                      {run.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
