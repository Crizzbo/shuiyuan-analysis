import { useState } from 'react'
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

interface UnifiedPipelineDef {
  id: string
  name: string
  tag: string
  icon: string
  description: string
  primaryTaskId: string
  subTaskIds: string[]
  recommendedSchedule: string
}

const UNIFIED_PIPELINES: UnifiedPipelineDef[] = [
  {
    id: 'MACRO_CORRIDOR',
    name: '宏观基准与流动性走廊',
    tag: 'MACRO',
    icon: '🌐',
    description: '测算 10Y美债收益率、美联储利差、VIX、USD/JPY 及全盘 14,892 只标的 50/200日均线趋势宽度走廊',
    primaryTaskId: 'INDICATOR_UPDATE',
    subTaskIds: ['INDICATOR_UPDATE'],
    recommendedSchedule: '每小时自动计算 / 实时感知',
  },
  {
    id: 'MARKET_QUOTES',
    name: '全盘行情流式入账流水线',
    tag: 'QUOTES_STREAM',
    icon: '📈',
    description: 'Google Sheets 6~298 分片并发拉取、全盘 14,892 只标的实时与收盘行情入账，严格执行当日时效门禁核验',
    primaryTaskId: 'FULL_UNIVERSE_COLLECT',
    subTaskIds: ['FULL_UNIVERSE_COLLECT', 'QUOTE_COLLECT'],
    recommendedSchedule: '盘前与盘中高频流式拉取',
  },
  {
    id: 'EVENT_RADAR',
    name: '权威突发事件雷达流水线',
    tag: 'OFFICIAL_EVENTS',
    icon: '⚡',
    description: 'SEC、JPX、美联储官方披露即时采集与 AI 商业实质提炼，识别受波及上市主体，持久化入 SQLite 数据库',
    primaryTaskId: 'OFFICIAL_NEWS',
    subTaskIds: ['OFFICIAL_NEWS'],
    recommendedSchedule: '每小时脉冲抓取 / SQLite 持久化',
  },
  {
    id: 'SCREENING_PIPELINE',
    name: '全市场时序平账与形态初筛流水线',
    tag: 'SERIES_SCREENING',
    icon: '📊',
    description: '美股/日股收盘历史日 K 线拉取、时序对账平账、0-Token SEPA/VCP 主升浪收敛初筛与阶段形态判定',
    primaryTaskId: 'STOCK_SCREENING',
    subTaskIds: ['US_DAILY', 'JP_DAILY', 'STOCK_SCREENING'],
    recommendedSchedule: '美股 08:00 JST / 日股 07:30 JST / 盘后初筛',
  },
  {
    id: 'FINANCE_AUDIT_MODELS',
    name: '官方三表平账与24大量化模型流水线',
    tag: 'VALUATION_AUDIT',
    icon: '🛡️',
    description: '官方 10-K/有价证券报告书资产负债表刚性平账自检、24 大量化估值模型核算、SHA-256 账本验签与官方补数',
    primaryTaskId: 'FINANCE_CALC',
    subTaskIds: ['FINANCE_CALC', 'LOCAL_AUDIT', 'INCREMENTAL_COLLECT', 'STOCK_DOSSIER_COLLECT'],
    recommendedSchedule: '每 30~60 分钟巡检 / 每日深度核算',
  },
]

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
  const [viewMode, setViewMode] = useState<'streamlined' | 'all'>('streamlined')

  const taskMap = new Map(tasks.map(t => [t.id, t]))

  return (
    <div className="ice-panel rounded-2xl p-5 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-sky-100 gap-3">
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span className="p-1 rounded bg-teal-50 text-teal-600">
              <ShieldCheckIcon className="w-4 h-4" />
            </span>
            生产调度任务矩阵
            <span className="text-xs font-normal text-slate-500">
              ({viewMode === 'streamlined' ? '5 大标准化闭环流水线' : '11 项独立原子任务'})
            </span>
          </h2>
          <p className="text-[11px] text-slate-500">
            {viewMode === 'streamlined'
              ? '业务闭环模式：合并同类项冗余，归并宏观走廊、全盘行情、事件雷达、时序初筛与三表模型 5 大闭环流水线'
              : '底层原子模式：按数据维度独立调度，支持对每一项底层爬虫与核验脚本实施微观控制'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* 模式切换按钮 */}
          <div className="inline-flex rounded-lg p-0.5 bg-slate-100 border border-slate-200 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('streamlined')}
              className={`px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                viewMode === 'streamlined'
                  ? 'bg-white text-sky-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              5 大标准化闭环（推荐）
            </button>
            <button
              type="button"
              onClick={() => setViewMode('all')}
              className={`px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                viewMode === 'all'
                  ? 'bg-white text-sky-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              11 项原子任务
            </button>
          </div>

          <button
            type="button"
            onClick={onToggleRunsHistory}
            className="px-3 py-1 rounded-lg text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 cursor-pointer flex items-center gap-1"
          >
            <span>{showRunsHistory ? '收起执行流水' : '流水记录'}</span>
            {showRunsHistory ? <ChevronUpIcon className="w-3.5 h-3.5" /> : <ChevronDownIcon className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* 视图 1：5 大标准化闭环流水线（推荐） */}
      {viewMode === 'streamlined' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {UNIFIED_PIPELINES.map(pipeline => {
            const matchedTasks = pipeline.subTaskIds
              .map(id => taskMap.get(id))
              .filter((t): t is TaskSchedulerTask => Boolean(t))
            const primaryTask = taskMap.get(pipeline.primaryTaskId) || matchedTasks[0]
            const isAnyRunning = matchedTasks.some(t => runningTaskId === t.id)
            const allEnabled = matchedTasks.every(t => t.enabled !== false)

            return (
              <div
                key={pipeline.id}
                className="ice-block rounded-2xl p-4 flex flex-col justify-between gap-3 shadow-2xs border border-sky-100/80 bg-white/90 hover:border-sky-300 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-2xl p-1.5 rounded-xl bg-sky-50 border border-sky-100">
                        {pipeline.icon}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-sm text-slate-900">{pipeline.name}</h3>
                          <span className="text-[10px] text-sky-700 bg-sky-50 px-2 py-0.5 rounded font-mono font-semibold border border-sky-200">
                            {pipeline.tag}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                          推荐排程：{pipeline.recommendedSchedule}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {primaryTask && (
                        <button
                          type="button"
                          disabled={isAnyRunning}
                          onClick={() => void onRunTask(primaryTask)}
                          className="px-3 py-1.5 rounded-lg text-xs font-bold bg-sky-600 hover:bg-sky-700 text-white shadow-xs cursor-pointer disabled:opacity-50"
                        >
                          {isAnyRunning ? '运行中…' : '执行管线'}
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    {pipeline.description}
                  </p>
                </div>

                {/* 聚合原子任务列表 */}
                <div className="pt-2 border-t border-sky-100/60 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span className="font-medium text-slate-700">包含原子任务 ({matchedTasks.length})</span>
                    <span className="text-[10px]">
                      状态: {allEnabled ? (
                        <span className="text-emerald-700 font-bold">全部就绪开启</span>
                      ) : (
                        <span className="text-amber-700 font-bold">部分暂停</span>
                      )}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    {matchedTasks.map(subTask => (
                      <div
                        key={subTask.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-sky-50/40 border border-sky-100/70 text-xs gap-2"
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="font-semibold text-slate-800 truncate" title={subTask.name}>
                            {subTask.name}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono px-1 rounded bg-white/80 border border-slate-200 shrink-0">
                            {subTask.dimension}
                          </span>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => onConfigureTask(subTask.id)}
                            className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-white hover:bg-slate-50 text-slate-600 border border-slate-200 cursor-pointer"
                          >
                            配置
                          </button>
                          <button
                            type="button"
                            onClick={() => void onToggleSchedule(subTask.id, subTask.enabled ?? true)}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border cursor-pointer ${
                              subTask.enabled !== false
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                                : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                            }`}
                          >
                            {subTask.enabled !== false ? '开启' : '暂停'}
                          </button>
                          <button
                            type="button"
                            disabled={runningTaskId === subTask.id}
                            onClick={() => void onRunTask(subTask)}
                            className="px-2 py-0.5 rounded text-[10px] font-bold bg-white text-sky-700 hover:bg-sky-50 border border-sky-200 cursor-pointer disabled:opacity-50"
                          >
                            {runningTaskId === subTask.id ? '…' : '触发'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 视图 2：11 项底层独立原子任务网格 */}
      {viewMode === 'all' && (
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
      )}

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
