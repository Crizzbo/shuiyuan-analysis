import { useState } from 'react'
import type { EventItem } from '../../types/api'
import {
  FilterIcon,
  ZapIcon,
  InfoCircleIcon,
  EventCard,
} from '../common'

interface SepaFunnelAndSentimentCardProps {
  funnel: any
  sentiment: any
  eventsSummary: any
  isExtractingNews: boolean
  onExtractNews: () => void
  onSelectEvent: (eventId: string) => void
  onNavigateTab: (tabId: string) => void
  onSelectTicker?: (ticker: string) => void
}

export function SepaFunnelAndSentimentCard({
  funnel,
  sentiment,
  eventsSummary,
  isExtractingNews,
  onExtractNews,
  onSelectEvent,
  onNavigateTab,
  onSelectTicker,
}: SepaFunnelAndSentimentCardProps) {
  const [activeSentimentTooltipId, setActiveSentimentTooltipId] = useState<string | null>(null)

  return (
    <div className="lg:col-span-4 space-y-5">
      {/* 1. SEPA 主升浪趋势形态统计漏斗 */}
      <div className="ice-panel rounded-xl p-4 shadow-sm space-y-3.5">
        <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
          <div className="flex items-center gap-2">
            <FilterIcon className="w-4 h-4 text-[#176249]" />
            <h3 className="text-xs font-bold text-[var(--text-primary)]">
              SEPA 主升浪选股统计漏斗
            </h3>
          </div>
          <span className="text-[10px] text-[var(--text-muted)] font-mono">趋势模板与形态收缩</span>
        </div>

        {/* 漏斗 5 阶层 */}
        <div className="space-y-2">
          {[
            { stage: '全盘标的池扫描', count: funnel.total_screened, pct: '100%', barW: '100%' },
            { stage: '站上 200 日牛熊线', count: funnel.stage_1_base_building, pct: '25.7%', barW: '75%' },
            { stage: '第二阶段主升浪结构', count: funnel.stage_2_trend_aligned, pct: '7.5%', barW: '50%' },
            { stage: '高相对强度 (RS ≥ 80)', count: funnel.stage_3_near_high, pct: '3.2%', barW: '32%' },
            { stage: 'VCP 临界突破候选', count: funnel.stage_4_vcp_candidates, pct: '0.12%', barW: '18%' },
          ].map((f, i) => (
            <div key={f.stage} className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
                    i === 4 ? 'bg-gradient-to-r from-amber-500 to-rose-600 text-white shadow-xs' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {i + 1}
                  </span>
                  <span className={`font-medium ${i === 4 ? 'text-rose-600 font-bold' : 'text-[var(--text-secondary)]'}`}>
                    {f.stage}
                  </span>
                </div>
                <span className="font-mono font-bold text-[var(--text-primary)]">
                  {f.count.toLocaleString()} 家 <span className="text-[var(--text-muted)] text-[10px]">({f.pct})</span>
                </span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    i === 4
                      ? 'bg-gradient-to-r from-amber-500 to-rose-600'
                      : i === 0
                      ? 'bg-slate-300'
                      : i === 1
                      ? 'bg-[#176249]/40'
                      : i === 2
                      ? 'bg-[#176249]/70'
                      : 'bg-[#176249]'
                  }`}
                  style={{ width: f.barW }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* 顶尖 VCP 突破候选个股卡片直达 */}
        <div className="space-y-2 pt-2 border-t border-[var(--border-color)]/60">
          <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
            <span>临界突破 VCP 精选标的 ({funnel.top_candidates.length}席)</span>
            <span className="text-[10px] text-[#176249] font-medium">点击进入分析 &rarr;</span>
          </div>
          <div className="space-y-2">
            {funnel.top_candidates.map((c: any) => (
              <div
                key={c.ticker}
                onClick={() => {
                  onSelectTicker?.(c.ticker)
                  onNavigateTab('analytics')
                }}
                className="ice-block flame-surge rounded-xl p-3 cursor-pointer transition-all flex items-center justify-between gap-3 group shadow-xs hover:shadow-md"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                      {c.ticker}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/25">
                      {c.vcp_contraction_stages}次收缩 VCP
                    </span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-medium truncate">
                      {c.name_zh}
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-muted)] truncate mt-1">
                    催化: {c.catalyst_driver}
                  </p>
                </div>

                <div className="text-right shrink-0 font-mono">
                  <div className="font-bold text-xs text-[var(--text-primary)]">
                    {c.price}
                  </div>
                  <div className={`text-[10px] font-bold ${c.chg_pct?.startsWith('-') ? 'text-blue-600' : 'text-rose-600'}`}>
                    {c.chg_pct}
                  </div>
                  <div className="text-[9px] text-[var(--text-muted)] mt-0.5">
                    突破线: {c.pivot_price}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 2. 宏观资金能级与期权市场情绪 */}
      <div className="ice-panel rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]/60">
          <div className="flex items-center gap-2">
            <ZapIcon className="w-4 h-4 text-slate-700" />
            <h3 className="text-xs font-bold text-[var(--text-primary)]">
              宏观资金能级与期权情绪
            </h3>
          </div>
          <span className="text-[10px] text-[var(--text-muted)] font-mono">流动性与期权 PCR</span>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {[
            {
              id: 'fg',
              title: 'Fear & Greed 恐慌贪婪',
              value: sentiment.fear_greed_score,
              sub: sentiment.fear_greed_gauge,
              valColor: 'text-rose-600',
              detail: 'CNN 综合恐慌与贪婪指数（0-100）。综合市场动量、股票价格强度、避险需求与垃圾债利差。读数在 60-75 为健康贪婪蓄势，> 80 触发极度狂热警惕，< 25 为极端恐慌买点。',
              param_reflection: '读数处于 60-75 温和贪婪区，反映市场情绪向上扩张且未见 80 以上非理性狂热，风险收益比适宜。',
            },
            {
              id: 'pcr',
              title: '期权看跌/看涨比 (PCR)',
              value: sentiment.put_call_ratio,
              sub: sentiment.put_call_signal,
              valColor: 'text-blue-600',
              detail: '全市场看跌期权 (Put) 与看涨期权 (Call) 总成交量之比。PCR < 0.70 表明市场看多投机亢奋，0.70 - 0.90 为健康防御中性区间，> 1.0 表明对冲买盘沉重。',
              param_reflection: 'PCR 0.70-0.90 处于健康中性区间，反映机构下行对冲买盘适度，认购期权未出现极端投机泡沫。',
            },
            {
              id: 'inflow',
              title: '主力机构资金净流入',
              value: sentiment.institutional_net_inflow_str,
              sub: '净买入防御权重',
              valColor: 'text-rose-600',
              detail: '基于交易所大单宗数 (Block Trades) 资金流向监测的大机构主力买方净流入。反映聪明钱 (Smart Money) 在核心权重指数及龙头防御板块的战略建仓意愿。',
              param_reflection: '大额主力资金净流入呈现正向，反映顶级机构做市商与公募基金在核心蓝筹资产上正在持续吸筹建仓。',
            },
            {
              id: 'volume',
              title: '市场成交量能倍率',
              value: `${sentiment.volume_expansion_ratio}x`,
              sub: sentiment.volume_verdict,
              valColor: 'text-[var(--text-primary)]',
              detail: '全市场当日总成交额相对 50 日均量 (50-Day Moving Average Volume) 的倍率。倍率在 1.1x - 1.3x 之间伴随指数上涨，代表机构资金真实介入的健康放量主升浪。',
              param_reflection: '量能倍率在 1.1x-1.3x 伴随指数收阳，反映增量资金进场接力，突破具备充足的量能置信度。',
            },
          ].map((item, index) => {
            const alignClass = (index % 2 === 0) ? 'left-0' : 'right-0'

            return (
              <div
                key={item.id}
                className="ice-block rounded-xl p-2.5 text-center relative group shadow-2xs hover:border-sky-300 transition-all"
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <div className="text-[10px] text-[var(--text-muted)] truncate font-medium text-left">
                    {item.title}
                  </div>

                  {/* 感叹号浮层 */}
                  <div
                    className="relative shrink-0"
                    onMouseEnter={() => setActiveSentimentTooltipId(item.id)}
                    onMouseLeave={() => setActiveSentimentTooltipId(null)}
                  >
                    <button
                      type="button"
                      tabIndex={0}
                      title={`${item.title} 详细说明`}
                      aria-label={`${item.title} 详细说明`}
                      onClick={(e) => {
                        e.stopPropagation()
                        setActiveSentimentTooltipId(activeSentimentTooltipId === item.id ? null : item.id)
                      }}
                      onFocus={() => setActiveSentimentTooltipId(item.id)}
                      onBlur={() => setActiveSentimentTooltipId(null)}
                      className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                        activeSentimentTooltipId === item.id
                          ? 'bg-[#176249] text-white border-[#176249]'
                          : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                      }`}
                    >
                      <InfoCircleIcon className="w-2.5 h-2.5" />
                    </button>

                    {activeSentimentTooltipId === item.id && (
                      <div
                        className={`absolute top-full mt-2 w-60 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                        onMouseEnter={() => setActiveSentimentTooltipId(item.id)}
                        onMouseLeave={() => setActiveSentimentTooltipId(null)}
                      >
                        <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                          <span className="font-bold text-xs text-[var(--text-primary)]">
                            {item.title}
                          </span>
                        </div>
                        <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                          {item.detail}
                        </p>
                        {item.param_reflection && (
                          <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                            <span className="font-semibold text-[#176249]">【参数反映情况】：</span>
                            {item.param_reflection}
                          </div>
                        )}
                        <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                          <span>读数: <strong className="text-[var(--text-primary)]">{item.value}</strong></span>
                          <span>定性: <span className="text-[#176249] font-semibold">{item.sub}</span></span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className={`text-lg font-black font-mono ${item.valColor} mt-0.5`}>
                  {item.value}
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 font-medium truncate">
                  {item.sub}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 3. 权威事件情报雷达 */}
      <div className="ice-panel rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <h3 className="text-xs font-bold text-[var(--text-primary)]">
              权威事件雷达 ({eventsSummary?.total_events || 0}篇)
            </h3>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={onExtractNews}
              disabled={isExtractingNews}
              className="text-[10px] px-2 py-0.5 rounded bg-[var(--bg-card)] hover:bg-slate-100 text-slate-700 border border-slate-200 hover:text-[#176249] hover:border-[#176249]/40 cursor-pointer transition-all flex items-center gap-1"
              title="即时核验与抽取官方最新公报"
            >
              <ZapIcon className={`w-3 h-3 text-slate-600 ${isExtractingNews ? 'animate-spin' : ''}`} />
              <span>{isExtractingNews ? '抽取中...' : '即时抽取'}</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigateTab('intelligence')}
              className="text-[10px] text-[var(--text-secondary)] hover:text-[#176249] hover:underline cursor-pointer"
            >
              全部 &rarr;
            </button>
          </div>
        </div>

        <div className="space-y-2.5">
          {eventsSummary?.top_events && eventsSummary.top_events.length > 0 ? (
            eventsSummary.top_events.slice(0, 4).map((ev: EventItem) => (
              <EventCard
                key={ev.event_id}
                id={ev.event_id}
                title={ev.title}
                severity={ev.severity}
                verification_status={ev.verification_status}
                is_quarantined_rumor={ev.is_quarantined_rumor}
                published_at={ev.published_at}
                source_name={ev.source_name}
                category={ev.category}
                micro_physical_impact={ev.micro_physical_impact}
                involved_entities={ev.involved_entities}
                affected_business_segments={ev.affected_business_segments}
                compact={true}
                onClick={() => {
                  onSelectEvent(ev.event_id)
                  onNavigateTab('intelligence')
                }}
                onSelectTicker={onSelectTicker}
              />
            ))
          ) : (
            <div className="text-center py-6 text-xs text-[var(--text-muted)]">
              暂无权威事件记录
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
