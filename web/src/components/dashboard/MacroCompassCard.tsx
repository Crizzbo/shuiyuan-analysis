import { useState } from 'react'
import type { MarketQuoteItem } from '../../types/api'
import {
  CompassIcon,
  InfoCircleIcon,
  LightBulbIcon,
  TrendUpIcon,
  TrendDownIcon,
} from '../common'

interface BenchmarkIndexItem {
  ticker: string
  nameZh: string
  desc: string
  detail: string
  param_reflection?: string
  market: string
  currency: string
  symbol: string
  change: string
  change_pct: string
  is_up: boolean
  data_status: string
  data_status_zh: string
  formatted_price?: string
  quote: MarketQuoteItem
}

interface MacroGaugeItem {
  id: string
  nameZh: string
  value: string
  role: string
  status: string
  status_code?: string
  tone: 'warning' | 'accent' | 'info' | 'good'
  detail: string
  param_reflection?: string
  data_status?: string
  data_status_zh?: string
}

interface MacroCompassCardProps {
  benchmarkDate?: string
  benchmarkNote?: string
  marketRegime?: any
  benchmarkIndices: BenchmarkIndexItem[]
  macroGauges: MacroGaugeItem[]
  usAD: any
  jpAD: any
  ma: any
  onNavigateTab: (tabId: string) => void
}

function getStatusBadge(status?: string) {
  switch (status) {
    case 'FRESH':
      return { text: '盘中实时', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' }
    case 'PREVIOUS_CLOSE':
      return { text: '前收盘基准', cls: 'bg-slate-100 text-slate-700 border-slate-200' }
    case 'STALE_BLOCKED':
      return { text: '前收盘基准', cls: 'bg-slate-100 text-slate-700 border-slate-200' }
    case 'NOT_CONFIGURED':
      return { text: '待配置源', cls: 'bg-slate-100 text-slate-500 border-slate-200' }
    case 'NO_QUOTE':
      return { text: '待补行情', cls: 'bg-slate-100 text-slate-500 border-slate-200' }
    default:
      return { text: '前收盘基准', cls: 'bg-slate-100 text-slate-500 border-slate-200' }
  }
}

export function MacroCompassCard({
  benchmarkDate,
  benchmarkNote,
  marketRegime,
  benchmarkIndices,
  macroGauges,
  usAD,
  jpAD,
  ma,
  onNavigateTab,
}: MacroCompassCardProps) {
  const [activeTooltipTicker, setActiveTooltipTicker] = useState<string | null>(null)
  const [activeMacroTooltipId, setActiveMacroTooltipId] = useState<string | null>(null)

  return (
    <div className="ice-panel rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0284c7] via-[#0369a1] to-[#082f49] border border-[#38bdf8]/40 flex items-center justify-center text-white shadow-xs shrink-0 relative overflow-hidden">
            <CompassIcon className="w-5 h-5 text-sky-200" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                全球双市场宏观罗盘与大盘体温研判
              </h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/20 font-mono">
                美日跨市宏观
              </span>
            </div>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              美股与日股核心宏观流动性、波动率指数 (VIX) 与大盘情绪跨市场定价锚
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-mono">
            基准: {benchmarkDate || '2026-11-14'} ({benchmarkNote || '前收盘基准'})
          </span>
        </div>
      </div>

      {/* 买方顶层定性结论条 */}
      <div className="bg-[var(--bg-card)] rounded-xl p-3.5 border border-[var(--border-color)]/60 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[var(--text-primary)]">
              大盘定性：{marketRegime?.regime_title || '高息中枢定价约束 · 结构性主升浪分化扩散'}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-amber-50 text-amber-700 border border-amber-200">
              {marketRegime?.regime_status_zh || '波动警戒 (VIX 28.18)'}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab('intelligence')}
            className="text-xs text-slate-700 hover:text-slate-900 hover:underline cursor-pointer flex items-center gap-1 font-medium"
          >
            <span>驱动事件雷达</span>
            <span>&rarr;</span>
          </button>
        </div>
        <div className="flex items-start gap-1.5 text-xs text-slate-700 font-medium">
          <LightBulbIcon className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
          <span>策略指引：{marketRegime?.strategy_guidance || '全市场涨跌比处于 1.8 偏多顺风区间，但宏观利率锚高位压制估值倍数；仓位上限维持 3-4 成精选布局，聚焦通过 SEPA 严筛的 VCP 紧绷收缩标的。'}</span>
        </div>
        <div className="text-[11px] text-[var(--text-muted)] font-mono pt-1 border-t border-[var(--border-color)]/40 flex flex-wrap gap-x-4 gap-y-1">
          <span>美股涨跌比 (ADR): {marketRegime?.adr_us || `${usAD.ad_ratio} (中位数 ${usAD.median_return_pct})`}</span>
          <span>日股涨跌比 (ADR): {marketRegime?.adr_jp || `${jpAD.ad_ratio} (中位数 ${jpAD.median_return_pct})`}</span>
          <span>52周净新高: {marketRegime?.net_highs_52w || `+${ma.high_low.net_expansion} 席`}</span>
        </div>
      </div>

      {/* 双市场核心基准卡片阵列 */}
      <div className="space-y-3 pt-1">
        <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
          <div className="flex items-center gap-1.5">
            <span>双市场核心基准指数 (Benchmark Indices)</span>
            <span className="text-[11px] text-[var(--text-muted)] font-normal hidden sm:inline">
              · 点击右上角感叹号图标聚焦查看详细图表说明
            </span>
          </div>
          <span className="text-[11px] text-[var(--text-muted)] font-normal">每日逐笔收盘核验为准</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {benchmarkIndices.map((idx, index) => {
            const q = idx.quote
            const badge = getStatusBadge(idx.data_status || q?.data_status)
            const isUp = idx.is_up ?? true
            const chgPct = idx.change_pct || '+0.00%'

            const alignClass = (index % 4 === 0)
              ? 'left-0 sm:left-0'
              : (index % 4 === 3)
              ? 'right-0 sm:right-0'
              : 'right-0 sm:left-1/2 sm:-translate-x-1/2'

            return (
              <div
                key={idx.ticker}
                className={`ice-block ${isUp ? 'flame-surge' : 'frost-crystal'} rounded-xl p-3.5 flex flex-col justify-between transition-all group relative`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                      {idx.ticker}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <span className={`text-[9px] px-1.5 py-0.2 rounded border font-medium ${badge.cls}`}>
                        {idx.data_status_zh || badge.text}
                      </span>

                      <div
                        className="relative"
                        onMouseEnter={() => setActiveTooltipTicker(idx.ticker)}
                        onMouseLeave={() => setActiveTooltipTicker(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title={`${idx.nameZh} 详细说明`}
                          aria-label={`${idx.nameZh} 详细说明`}
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveTooltipTicker(activeTooltipTicker === idx.ticker ? null : idx.ticker)
                          }}
                          onFocus={() => setActiveTooltipTicker(idx.ticker)}
                          onBlur={() => setActiveTooltipTicker(null)}
                          className={`w-4 h-4 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                            activeTooltipTicker === idx.ticker
                              ? 'bg-slate-700 text-white shadow-sm'
                              : 'bg-[var(--surface-color)] hover:bg-slate-200 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                          }`}
                        >
                          <InfoCircleIcon className="w-3 h-3" />
                        </button>

                        {activeTooltipTicker === idx.ticker && (
                          <div
                            className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-white border border-slate-200 shadow-xl z-50 pointer-events-auto opacity-100 transition-all duration-200 ${alignClass}`}
                            onMouseEnter={() => setActiveTooltipTicker(idx.ticker)}
                            onMouseLeave={() => setActiveTooltipTicker(null)}
                          >
                            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 mb-1.5">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span className="font-mono font-bold text-xs text-slate-800">
                                  {idx.ticker}
                                </span>
                                <span className="text-[11px] text-slate-700 font-medium truncate">
                                  {idx.nameZh}
                                </span>
                              </div>
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium shrink-0">
                                {idx.desc}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-600 leading-relaxed">
                              {idx.detail}
                            </p>
                            {idx.param_reflection && (
                              <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-100 text-[10px] text-slate-600 leading-relaxed">
                                <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                                {idx.param_reflection}
                              </div>
                            )}
                            <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                              <span>市场: {idx.market}</span>
                              <span>货币: {idx.currency}</span>
                              <span>时效: {idx.data_status_zh || badge.text}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] text-[var(--text-muted)] truncate mt-1">
                    {idx.nameZh}
                  </div>

                  <div className="text-lg font-black font-mono mt-1.5 tracking-tight truncate">
                    {idx.formatted_price || q?.formatted_price || (q?.price != null ? `${idx.symbol}${q.price}` : '—')}
                  </div>

                  <div className="flex items-center gap-1 mt-1 text-[11px] font-mono font-bold">
                    <span className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded border ${
                      isUp ? 'flame-badge font-black' : 'frost-badge font-bold'
                    }`}>
                      {isUp ? <TrendUpIcon className="w-2.5 h-2.5 stroke-[3] text-rose-600" /> : <TrendDownIcon className="w-2.5 h-2.5 stroke-[3] text-blue-600" />}
                      <span>{chgPct}</span>
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 宏观流动性与恐慌舵手指标 */}
      <div className="space-y-2.5 pt-2 border-t border-[var(--border-color)]/50">
        <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
          <div className="flex items-center gap-1.5">
            <span>宏观流动性、无风险利率与恐慌情绪指标 (Macro Liquidity & Volatility)</span>
            <span className="text-[11px] text-[var(--text-muted)] font-normal hidden sm:inline">
              · 点击右上角感叹号图标展开宏观影响解析
            </span>
          </div>
          <span className="text-[11px] text-[var(--text-muted)] font-mono font-normal">系统重要性锚点</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {macroGauges.map((g, index) => {
            const alignClass = (index % 6 === 0)
              ? 'left-0'
              : (index % 6 === 5)
              ? 'right-0'
              : 'right-0 sm:left-1/2 sm:-translate-x-1/2'

            return (
              <div
                key={g.id}
                className="ice-block rounded-xl p-2.5 flex flex-col justify-between hover:border-sky-300 transition-all relative group shadow-2xs"
              >
                <div>
                  <div className="flex items-center justify-between gap-1">
                    <div className="text-[10px] text-[var(--text-muted)] truncate font-medium">
                      {g.nameZh}
                    </div>

                    <div
                      className="relative shrink-0"
                      onMouseEnter={() => setActiveMacroTooltipId(g.id)}
                      onMouseLeave={() => setActiveMacroTooltipId(null)}
                    >
                      <button
                        type="button"
                        tabIndex={0}
                        title={`${g.nameZh} 详细说明`}
                        aria-label={`${g.nameZh} 详细说明`}
                        onClick={(e) => {
                          e.stopPropagation()
                          setActiveMacroTooltipId(activeMacroTooltipId === g.id ? null : g.id)
                        }}
                        onFocus={() => setActiveMacroTooltipId(g.id)}
                        onBlur={() => setActiveMacroTooltipId(null)}
                        className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                          activeMacroTooltipId === g.id
                            ? 'bg-[#176249] text-white shadow-sm'
                            : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                        }`}
                      >
                        <InfoCircleIcon className="w-2.5 h-2.5" />
                      </button>

                      {activeMacroTooltipId === g.id && (
                        <div
                          className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 ${alignClass}`}
                          onMouseEnter={() => setActiveMacroTooltipId(g.id)}
                          onMouseLeave={() => setActiveMacroTooltipId(null)}
                        >
                          <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                                {g.id}
                              </span>
                              <span className="text-[11px] text-[var(--text-secondary)] font-medium truncate">
                                {g.nameZh}
                              </span>
                            </div>
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium shrink-0">
                              {g.role}
                            </span>
                          </div>
                          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                            {g.detail}
                          </p>
                          {g.param_reflection && (
                            <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                              <span className="font-semibold text-[#176249]">【参数读数反映情况】：</span>
                              {g.param_reflection}
                            </div>
                          )}
                          <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                            <span>当前读数: <strong className="text-[var(--text-primary)]">{g.value}</strong></span>
                            <span>状态: <span className={
                              g.tone === 'warning' ? 'text-amber-500 font-semibold' :
                              g.tone === 'good' ? 'text-[#176249] font-semibold' :
                              'text-slate-700 font-semibold'
                            }>{g.status}</span></span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-base font-black font-mono text-[var(--text-primary)] mt-1 tracking-tight">
                    {g.value}
                  </div>
                </div>

                <div className="mt-1.5 flex items-center justify-between gap-1 pt-1 border-t border-[var(--border-color)]/40">
                  <span className="text-[9px] text-[var(--text-muted)] font-mono truncate">{g.id}</span>
                  <span className={`text-[9px] px-1 py-0.2 rounded font-medium border ${
                    g.tone === 'warning' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                    g.tone === 'good' ? 'text-emerald-700 bg-emerald-50 border-emerald-200' :
                    'text-slate-700 bg-slate-100 border-slate-200'
                  }`}>
                    {g.status}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
