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
    name: '全球宏观流动性与资金成本走廊',
    tag: '宏观与利率中枢',
    icon: '🌐',
    description: '跟踪 10 年期美债收益率、美联储政策利差、恐慌指数 VIX 及全市场 1.48 万只标的均线宽度，研判大盘系统性风险与资产估值折现锚点。',
    primaryTaskId: 'INDICATOR_UPDATE',
    subTaskIds: ['INDICATOR_UPDATE'],
    recommendedSchedule: '实时感知 · 每小时自动重算',
  },
  {
    id: 'MARKET_QUOTES',
    name: '全市场股票行情实时同步与新鲜度守卫',
    tag: '美日万家行情入账',
    icon: '📈',
    description: '多通道并发同步美股与日股 14,800+ 只标的的实时报价与收盘数据，严密前置拦截过期陈旧行情，确保交易决策依据绝对真实。',
    primaryTaskId: 'FULL_UNIVERSE_COLLECT',
    subTaskIds: ['FULL_UNIVERSE_COLLECT', 'QUOTE_COLLECT'],
    recommendedSchedule: '盘前盘中高频流式同步',
  },
  {
    id: 'EVENT_RADAR',
    name: '权威监管披露与重大投资情报雷达',
    tag: '官方事件穿透',
    icon: '⚡',
    description: '即时抓取 SEC 8-K/10-K、日本东证 (JPX) 及美联储官方权威公报，AI 深度提炼微观商业影响并精准锁定受波及上市公司，隔离市场谣言。',
    primaryTaskId: 'OFFICIAL_NEWS',
    subTaskIds: ['OFFICIAL_NEWS'],
    recommendedSchedule: '全天候脉冲监控 · 权威核验',
  },
  {
    id: 'SCREENING_PIPELINE',
    name: '趋势宽度扫描与主升浪高胜率买点初筛',
    tag: 'SEPA&VCP 选股池',
    icon: '📊',
    description: '基于历史交易日 K 线与量价结构，全自动甄选处于机构主力建仓拉升的第二阶段主升浪、且波动收窄 (VCP) 临近突破的高胜率个股。',
    primaryTaskId: 'STOCK_SCREENING',
    subTaskIds: ['US_DAILY', 'JP_DAILY', 'STOCK_SCREENING'],
    recommendedSchedule: '美股 08:00 / 日股 07:30 / 盘后更新',
  },
  {
    id: 'FINANCE_AUDIT_MODELS',
    name: '官方财报防伪审查与买方深度估值引擎',
    tag: '安全边际与内在价值',
    icon: '🛡️',
    description: '核验官方原始财务报表勾稽平衡，排查财务粉饰风险 (Beneish M-Score)，自动运行多阶段 DCF 与反向折现估值走廊，确立买入安全边际。',
    primaryTaskId: 'FINANCE_CALC',
    subTaskIds: ['FINANCE_CALC', 'LOCAL_AUDIT', 'INCREMENTAL_COLLECT', 'STOCK_DOSSIER_COLLECT'],
    recommendedSchedule: '每日开盘前核算 · 动态微调',
  },
]

const TASK_USER_FACING_MAP: Record<string, { title: string; desc: string }> = {
  QUOTE_COLLECT: { title: '核心监控标的实时报价更新', desc: '更新科技巨头与重点自选池实时价格' },
  FULL_UNIVERSE_COLLECT: { title: '美日全市场万家标的行情同步', desc: '全量同步近 1.5 万家上市公司最新收盘底账' },
  US_DAILY: { title: '美股收盘日线抽取与时序平账', desc: '抽取并校验美股全量历史 OHLCV 日 K 线' },
  JP_DAILY: { title: '日股收盘日线抽取与时序平账', desc: '抽取并校验日股全量历史 OHLCV 日 K 线' },
  OFFICIAL_NEWS: { title: '官方公告与突发投资情报提炼', desc: '解析 SEC、东证与美联储披露中的微观商业实质' },
  STOCK_SCREENING: { title: '全市场主升浪形态与买点发现', desc: '扫描 SEPA 趋势模板与 VCP 收缩临界候选' },
  INDICATOR_UPDATE: { title: '宏观基准利率与市场宽度走廊', desc: '测算美债收益率、利差与全市场均线分布' },
  FINANCE_CALC: { title: '官方三表财务指标与24大量化模型', desc: '核算多阶段DCF、杜邦拆解与资本成本WACC' },
  LOCAL_AUDIT: { title: '本地财报刚性平账与决策账本验签', desc: '执行资产负债表平衡检验与历史预测存证' },
  INCREMENTAL_COLLECT: { title: '官方监管缺失财报定向补数', desc: '扫描缺失 10-K 或日线的标的并建立补数队列' },
  STOCK_DOSSIER_COLLECT: { title: '指定重点标的全维度深度研报生产', desc: '一键拉取并生成指定标的机构买方全息档案' },
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
            生产调度任务矩阵 (投研流水线)
            <span className="text-xs font-normal text-slate-500">
              ({viewMode === 'streamlined' ? '5 大标准化闭环流水线' : '11 项底层原子任务'})
            </span>
          </h2>
          <p className="text-[11px] text-slate-500">
            {viewMode === 'streamlined'
              ? '面向投资决策：将 11 项技术原子调度归并为 5 大闭环业务流水线，实现从宏观风向、行情入账到深度估值的一键生产'
              : '底层原子控制：按数据维度独立调度，支持对每一项底层抓取、日线抽取与审计脚本实施精细化控制'}
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
                    {matchedTasks.map(subTask => {
                      const meta = TASK_USER_FACING_MAP[subTask.id]
                      const displayName = meta?.title || subTask.name
                      return (
                        <div
                          key={subTask.id}
                          className="flex items-center justify-between p-2 rounded-lg bg-sky-50/40 border border-sky-100/70 text-xs gap-2"
                        >
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="font-semibold text-slate-800 truncate" title={displayName}>
                              {displayName}
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
                      )
                    })}
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
          {tasks.map(task => {
            const meta = TASK_USER_FACING_MAP[task.id]
            const displayName = meta?.title || task.name
            const desc = meta?.desc
            return (
              <div
                key={task.id}
                className="ice-block rounded-xl p-3.5 flex items-center justify-between gap-3 shadow-2xs"
              >
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-xs text-slate-800 truncate" title={displayName}>{displayName}</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-50 text-sky-700 border border-sky-200 font-mono">
                      {task.dimension}
                    </span>
                  </div>
                  {desc && <div className="text-[11px] text-slate-600 truncate">{desc}</div>}
                  <div className="text-[10px] text-slate-400 font-mono">{task.schedule}</div>
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
            )
          })}
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
