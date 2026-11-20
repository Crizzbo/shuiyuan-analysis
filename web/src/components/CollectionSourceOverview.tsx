import type { CollectionOverviewData, MarketReconciliationMap, TaskSchedulerRun } from '../types/api'
import { formatDeviceTime, toChinese } from '../utils/format'

const SOURCE_NAMES: Record<string, string> = {
  yfinance: 'Yahoo Finance', jpx_daily: '东证日刊', jquants: 'J-Quants',
  sec: 'SEC EDGAR', edinet: 'EDINET', issuer_ir: '发行人投资者关系网站',
  alpha_vantage: 'Alpha Vantage', fred_csv: 'FRED 公开 CSV', fred: 'FRED API',
  bls: '美国劳工统计局', boj: '日本银行', estat: '日本 e-Stat',
  tdnet: 'TDnet', rss: '监管与发行人 RSS', gdelt: 'GDELT',
}
const SOURCE_GROUPS = [
  { title: '行情与日线', ids: ['yfinance', 'jpx_daily', 'jquants'] },
  { title: '财报与公司披露', ids: ['sec', 'edinet', 'issuer_ir', 'tdnet', 'alpha_vantage'] },
  { title: '宏观与利率', ids: ['fred_csv', 'fred', 'bls', 'boj', 'estat'] },
  { title: '事件线索', ids: ['rss', 'gdelt'] },
]
const MODE_LABEL = { scheduled: '接入定时任务', available: '可按来源计划执行', disabled: '自动接口停用' }
const EVENT_ROLE = { scheduled: '定时 RSS 范围', candidate: '候选 RSS', radar: '事件雷达配置' }
const count = (value?: number) => value?.toLocaleString('zh-CN') ?? '—'

interface Props {
  overview: CollectionOverviewData | null
  reconciliation: MarketReconciliationMap | null
  checked: boolean
  runs: TaskSchedulerRun[]
  onArchive: () => void
  onAudit: () => void
}

export function CollectionSourceOverview({ overview, reconciliation, checked, runs, onArchive, onAudit }: Props) {
  const readiness = overview?.readiness
  const latest = (task: string) => runs.find(run => run.task === task)
  const macro = latest('INDICATOR_UPDATE')
  const events = latest('OFFICIAL_NEWS')
  const audit = runs.find(run => run.task === 'LOCAL_AUDIT' && run.finished_at)
  const sources = overview?.source_catalog
  const groups = SOURCE_GROUPS.map(group => ({
    ...group, sources: sources?.filter(source => group.ids.includes(source.id)) ?? [],
  }))
  const other = sources?.filter(source => !SOURCE_GROUPS.some(group => group.ids.includes(source.id))) ?? []

  return (
    <section className="ice-panel rounded-2xl p-5 space-y-4" aria-labelledby="collection-sources-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 id="collection-sources-heading" className="text-xl font-bold text-slate-900">数据采集状态</h1>
          <p className="mt-1 text-sm text-slate-600">按市场核对目标交易日，再查看三表、宏观、事件和底账验签。</p>
        </div>
        <button type="button" onClick={onArchive} className="rounded-lg border border-sky-200 px-3 py-1.5 text-sm font-medium text-sky-800">查看归档明细</button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {(['us', 'jp'] as const).map(market => {
          const data = reconciliation?.[market]
          const metrics = [
            ['有效日线', data?.matched_count],
            ['无成交', data?.no_trade_count],
            ['待补', data?.pending_count],
            ['未映射', data?.unmapped_count],
            ['错误', data?.error_count],
          ] as const
          return (
            <article key={market} className="rounded-xl border border-sky-100 bg-white/85 p-4">
              <div className="flex justify-between gap-2">
                <h2 className="text-sm font-bold text-slate-900">{market === 'us' ? '美股日线' : '日股日线'}</h2>
                <span className="text-xs text-slate-600">目标交易日 {data?.target_trading_day ?? '—'}</span>
              </div>
              <div className="mt-2 text-sm text-slate-700">
                {data ? <>已覆盖 <strong>{data.coverage_rate_pct}%</strong> · 标的总数 {count(data.universe_count)}</> : checked ? '暂未取得对账结果' : '正在读取对账结果…'}
              </div>
              <dl className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
                {metrics.map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs text-slate-500">{label}</dt>
                    <dd className="font-mono text-sm font-semibold tabular-nums text-slate-900">{count(value)}</dd>
                  </div>
                ))}
              </dl>
              {data && <p className="mt-3 text-xs text-slate-600">
                计数{data.is_balanced ? '平衡' : '有差额'} · 差额 {count(data.balance_diff)} · 核对时间 {formatDeviceTime(data.as_of)}
              </p>}
            </article>
          )
        })}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <article className="rounded-lg border border-sky-100 bg-white/75 p-3">
          <h2 className="text-sm font-semibold text-slate-900">行情快照</h2>
          <p className="mt-1 text-sm text-slate-700">{readiness ? `最近归档批次 ${count(readiness.total_completed_count)} 个标的` : '暂无批次信息'}</p>
          <p className="mt-1 text-xs text-slate-500">{formatDeviceTime(readiness?.latest_timestamp_utc)}</p>
        </article>
        <article className="rounded-lg border border-sky-100 bg-white/75 p-3">
          <h2 className="text-sm font-semibold text-slate-900">官方财报</h2>
          <p className="mt-1 text-sm text-slate-700">SEC 原档 {count(overview?.lifecycle_tiers.sec_official_files)} 份</p>
          <p className="mt-1 text-xs text-slate-500">原文补数队列 {count(overview?.replenishment_queue.total_pending)} 项</p>
        </article>
        {([{ title: '宏观指标更新', run: macro }, { title: '官方资讯采集', run: events }]).map(({ title, run }) => (
          <article key={title} className="min-w-0 rounded-lg border border-sky-100 bg-white/75 p-3">
            <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
            <p className="mt-1 text-sm text-slate-700">{run ? toChinese(run.status) : '暂无运行记录'}</p>
            {run && <p className="mt-1 text-xs text-slate-500">{formatDeviceTime(run.finished_at ?? run.created_at)}</p>}
            {run?.result?.message && <p className="mt-1 text-xs text-slate-600 break-words">{run.result.message}</p>}
          </article>
        ))}
        <article className="rounded-lg border border-sky-100 bg-white/75 p-3">
          <h2 className="text-sm font-semibold text-slate-900">最近本地核验</h2>
          <p className="mt-1 text-sm text-slate-700">{audit ? toChinese(audit.status) : '暂无核验记录'}</p>
          {audit && <p className="mt-1 text-xs text-slate-500">{formatDeviceTime(audit.finished_at)}</p>}
          <button type="button" onClick={onAudit} className="mt-1 text-xs font-medium text-sky-800 underline">查看合规审计</button>
        </article>
      </div>
      <details className="rounded-lg border border-sky-100 bg-white/75 p-3 text-sm">
        <summary className="cursor-pointer font-semibold text-slate-800">数据来源目录{sources && ` · ${sources.length} 个配置来源`}</summary>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {([...groups, ...(other.length ? [{ title: '其他配置来源', sources: other }] : [])]).map(group => (
            <div key={group.title}>
              <h3 className="font-medium text-slate-900">{group.title}</h3>
              {group.sources.map(source => (
                <div key={source.id} className="flex justify-between gap-2 border-b border-sky-50 py-1 text-xs text-slate-700">
                  <span>
                    {SOURCE_NAMES[source.id] ?? source.id}
                    {source.trust === 'primary' && <small className="ml-1 text-slate-500">原始来源</small>}
                  </span>
                  <span>{MODE_LABEL[source.mode]}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
        {!!overview?.event_sources?.length && (
          <details className="mt-3 border-t border-sky-100 pt-2 text-xs">
            <summary className="cursor-pointer font-medium text-slate-900">资讯与事件雷达配置明细</summary>
            <ul className="mt-2 grid gap-1 md:grid-cols-2">
              {overview.event_sources.map(source => (
                <li key={`${source.role}-${source.name}`} className="flex justify-between gap-2 text-slate-700">
                  <span>{source.name}</span>
                  <span className="shrink-0">{EVENT_ROLE[source.role]}{source.priority && ` · ${toChinese(source.priority)}`}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
        <div className="mt-3 border-t border-sky-100 pt-2">
          <h3 className="font-medium text-slate-900">授权导入与本地原档</h3>
          <ul className="mt-1 space-y-1 text-xs text-slate-700">
            <li>Google Finance 专用 Sheets · 宿主授权导入行情快照</li>
            <li>SEC／JPX 标的目录 · 本地证券池与覆盖分母</li>
            <li>SEC CompanyFacts、JPX／发行人披露 · 本地原档与浏览器核验补数</li>
            <li>本地市场与宏观归档 · 供计算与历史对账读取</li>
          </ul>
        </div>
        {!sources && <p className="mt-1 text-xs text-slate-600">暂未取得来源配置。</p>}
      </details>
    </section>
  )
}
