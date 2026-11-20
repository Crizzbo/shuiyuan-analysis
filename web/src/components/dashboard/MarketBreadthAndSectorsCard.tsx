import { useState } from 'react'
import {
  BarChartIcon,
  InfoCircleIcon,
  TrendUpIcon,
  TrendDownIcon,
} from '../common'

interface MarketBreadthAndSectorsCardProps {
  usAD: any
  jpAD: any
  histogram: any[]
  sectors: any[]
  ma: any
}

export function MarketBreadthAndSectorsCard({
  usAD,
  jpAD,
  histogram,
  sectors,
  ma,
}: MarketBreadthAndSectorsCardProps) {
  const [activeMaTooltipId, setActiveMaTooltipId] = useState<string | null>(null)
  const [activeExpansionTooltip, setActiveExpansionTooltip] = useState(false)

  return (
    <div className="space-y-5">
      {/* 2. 全市场每日股票涨跌分布统计 (Market Advance-Decline Breadth & Return Histogram) */}
      <div className="ice-panel rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
          <div className="flex items-center gap-2.5">
            <BarChartIcon className="w-5 h-5 text-slate-700" />
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                全市场每日股票涨跌分布统计
              </h2>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                覆盖美股 (SEC 10,000+ 家) 与日股 (东证 4,400+ 家) 全量上市主体的客观日线涨跌广度与收益区间直方图
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
            <span>全市场中位数涨幅:</span>
            <div className="flex items-center gap-1.5 font-bold">
              <span className={`px-2 py-0.5 rounded border ${
                !usAD.median_return_pct.startsWith('-') ? 'text-rose-600 bg-rose-50 border-rose-200' : 'text-blue-600 bg-blue-50 border-blue-200'
              }`}>
                美股 {usAD.median_return_pct}
              </span>
              <span className={`px-2 py-0.5 rounded border ${
                !jpAD.median_return_pct.startsWith('-') ? 'text-rose-600 bg-rose-50 border-rose-200' : 'text-blue-600 bg-blue-50 border-blue-200'
              }`}>
                日股 {jpAD.median_return_pct}
              </span>
            </div>
          </div>
        </div>

        {/* 双市场涨跌数量与比例进度条 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 美股 ADR */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 shadow-sm">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[10px] font-bold">US</span>
                <span>美股全市场涨跌统计 (10,000+ 标的)</span>
              </span>
              <span className={`font-mono font-bold ${usAD.ad_ratio >= 1.0 ? 'text-rose-600' : 'text-blue-600'}`}>
                涨跌比: {usAD.ad_ratio}
              </span>
            </div>
            {/* 比例条 (红涨蓝跌) */}
            <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden flex">
              <div
                style={{ width: `${usAD.advancers_pct}%` }}
                className="bg-rose-500 h-full transition-all"
                title={`上涨: ${usAD.advancers} 家 (${usAD.advancers_pct}%)`}
              />
              <div
                style={{ width: `${100 - usAD.advancers_pct - usAD.decliners_pct}%` }}
                className="bg-slate-300 h-full transition-all"
                title={`平盘: ${usAD.unchanged} 家`}
              />
              <div
                style={{ width: `${usAD.decliners_pct}%` }}
                className="bg-blue-500 h-full transition-all"
                title={`下跌: ${usAD.decliners} 家 (${usAD.decliners_pct}%)`}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] pt-0.5">
              <span className="text-rose-600 font-semibold inline-flex items-center gap-1">
                <TrendUpIcon className="w-2.5 h-2.5 stroke-[3] text-rose-600" />
                <span>上涨 {usAD.advancers.toLocaleString()} ({usAD.advancers_pct}%)</span>
              </span>
              <span className="text-slate-400">━ 平盘 {usAD.unchanged.toLocaleString()}</span>
              <span className="text-blue-600 font-semibold inline-flex items-center gap-1">
                <TrendDownIcon className="w-2.5 h-2.5 stroke-[3] text-blue-600" />
                <span>下跌 {usAD.decliners.toLocaleString()} ({usAD.decliners_pct}%)</span>
              </span>
            </div>
            <div className="text-[10px] text-[var(--text-secondary)] bg-[var(--surface-color)] px-2.5 py-1 rounded border border-[var(--border-color)]/50 flex justify-between">
              <span>定性：{usAD.regime}</span>
              <span className="font-mono">中位数涨幅: {usAD.median_return_pct}</span>
            </div>
          </div>

          {/* 日股 ADR */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 shadow-sm">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[10px] font-bold">JP</span>
                <span>东证全市场涨跌统计 (4,400+ 标的)</span>
              </span>
              <span className={`font-mono font-bold ${jpAD.ad_ratio >= 1.0 ? 'text-rose-600' : 'text-blue-600'}`}>
                涨跌比: {jpAD.ad_ratio}
              </span>
            </div>
            {/* 比例条 (红涨蓝跌) */}
            <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden flex">
              <div
                style={{ width: `${jpAD.advancers_pct}%` }}
                className="bg-rose-500 h-full transition-all"
                title={`上涨: ${jpAD.advancers} 家 (${jpAD.advancers_pct}%)`}
              />
              <div
                style={{ width: `${100 - jpAD.advancers_pct - jpAD.decliners_pct}%` }}
                className="bg-slate-300 h-full transition-all"
                title={`平盘: ${jpAD.unchanged} 家`}
              />
              <div
                style={{ width: `${jpAD.decliners_pct}%` }}
                className="bg-blue-500 h-full transition-all"
                title={`下跌: ${jpAD.decliners} 家 (${jpAD.decliners_pct}%)`}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] pt-0.5">
              <span className="text-rose-600 font-semibold inline-flex items-center gap-1">
                <TrendUpIcon className="w-2.5 h-2.5 stroke-[3] text-rose-600" />
                <span>上涨 {jpAD.advancers.toLocaleString()} ({jpAD.advancers_pct}%)</span>
              </span>
              <span className="text-slate-400">━ 平盘 {jpAD.unchanged.toLocaleString()}</span>
              <span className="text-blue-600 font-semibold inline-flex items-center gap-1">
                <TrendDownIcon className="w-2.5 h-2.5 stroke-[3] text-blue-600" />
                <span>下跌 {jpAD.decliners.toLocaleString()} ({jpAD.decliners_pct}%)</span>
              </span>
            </div>
            <div className="text-[10px] text-[var(--text-secondary)] bg-[var(--surface-color)] px-2.5 py-1 rounded border border-[var(--border-color)]/50 flex justify-between">
              <span>定性：{jpAD.regime}</span>
              <span className="font-mono">中位数涨幅: {jpAD.median_return_pct}</span>
            </div>
          </div>
        </div>

        {/* 7-分档每日涨跌分布直方图 */}
        <div className="space-y-2 pt-2 border-t border-[var(--border-color)]/50">
          <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
            <span>全市场个股每日收益率分布直方图 (Return Distribution Histogram)</span>
            <span className="text-[11px] text-[var(--text-muted)] font-mono font-normal">
              多头倾斜偏度 (Skewness: Positive)
            </span>
          </div>
          <div className="grid grid-cols-7 gap-2 pt-1">
            {histogram.map((bucket) => {
              const isUp = bucket.tone === 'up'
              const barColor = isUp ? 'bg-rose-500' : 'bg-blue-500'
              const textColor = isUp ? 'text-rose-600' : 'text-blue-600'
              return (
                <div
                  key={bucket.range}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 flex flex-col justify-between items-center text-center hover:border-slate-300 transition-all"
                >
                  <div className="text-[10px] text-[var(--text-muted)] font-mono font-semibold truncate w-full">
                    {bucket.range}
                  </div>
                  <div className="w-full flex items-end justify-center h-16 py-1">
                    <div
                      className={`w-4/5 rounded-t-md transition-all duration-500 ${barColor}`}
                      style={{ height: `${Math.max(12, Math.min(100, bucket.pct * 2.5))}%` }}
                      title={`${bucket.range}: ${bucket.count} 家 (${bucket.pct}%)`}
                    />
                  </div>
                  <div className="w-full pt-1 border-t border-[var(--border-color)]/40">
                    <div className={`text-xs font-mono font-black ${textColor}`}>
                      {bucket.pct}%
                    </div>
                    <div className="text-[9px] text-[var(--text-muted)] font-mono truncate">
                      {bucket.count.toLocaleString()} 家
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* 3. GICS 全行业板块收益与成交动量天梯榜 (Sector Performance Ladder) */}
      <div className="ice-panel rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
          <div className="flex items-center gap-2.5">
            <BarChartIcon className="w-5 h-5 text-slate-700" />
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                GICS 全行业板块收益与成交动量天梯榜
              </h2>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                从科技算力到防御公共事业，按当日涨跌幅与成交量能倍率排序的行业胜负手结构
              </p>
            </div>
          </div>
          <span className="text-xs text-[var(--text-muted)] font-mono">
            共收录 9 大核心 GICS 产业集群
          </span>
        </div>

        <div className="space-y-2">
          {sectors.map((sec) => (
            <div
              key={sec.id}
              className={`ice-block ${sec.is_up ? 'flame-surge' : 'frost-crystal'} rounded-xl px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-3 transition-all shadow-2xs`}
            >
              {/* 左：排名与板块名称 */}
              <div className="flex items-center gap-3 min-w-[200px]">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono ${
                  sec.strength_rank <= 3
                    ? 'bg-[#176249] text-white'
                    : 'bg-[var(--surface-color)] text-[var(--text-muted)] border border-[var(--border-color)]'
                }`}>
                  {sec.strength_rank}
                </span>
                <div>
                  <div className="text-xs font-bold text-[var(--text-primary)]">
                    {sec.name_zh}
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] font-mono">
                    领涨龙头: <span className="text-[var(--text-secondary)] font-semibold">{sec.top_driver}</span>
                  </div>
                </div>
              </div>

              {/* 中：上涨个股比例微进度条 */}
              <div className="hidden md:flex items-center gap-2 min-w-[150px]">
                <span className="text-[10px] text-[var(--text-muted)] font-mono shrink-0">上涨率:</span>
                <div className="w-24 bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-rose-500 h-full rounded-full"
                    style={{ width: `${sec.advancers_pct}%` }}
                  />
                </div>
                <span className="text-[10px] text-[var(--text-secondary)] font-mono">
                  {sec.advancers_pct}%
                </span>
              </div>

              {/* 右：成交量倍率与涨跌幅 (红涨蓝跌) */}
              <div className="flex items-center gap-4 text-right">
                <div className="text-right">
                  <div className="text-[9px] text-[var(--text-muted)]">量能倍率</div>
                  <div className="text-xs font-mono font-semibold text-[var(--text-primary)]">
                    {sec.volume_ratio}x
                  </div>
                </div>
                <div className="min-w-[80px] text-right">
                  <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-black font-mono border ${
                    sec.is_up ? 'flame-badge font-black' : 'frost-badge font-bold'
                  }`}>
                    {sec.return_formatted}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. 市场多周期均线渗透与 52 周新高净扩展 (MA Penetration & High-Low Index) */}
      <div className="ice-panel rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
          <div className="flex items-center gap-2.5">
            <BarChartIcon className="w-5 h-5 text-emerald-500" />
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                全市场多周期均线渗透与 52 周新高净扩展
              </h2>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                全市场 20/50/150/200 日关键均线站上率与创 52 周新高/新低多空力量对照
              </p>
            </div>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 font-semibold">
            {ma.high_low.regime}
          </span>
        </div>

        {/* 四大均线渗透条 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              id: 'ma20',
              title: '20 日均线渗透率',
              pct: ma.above_20d_pct,
              role: '短期爆发冲刺力',
              detail: '全市场站上 20 日均线的个股比例。衡量超短期市场爆发动量与日内冲刺力，渗透率超过 70% 表明短线极度亢奋，需注意技术性超买回踩。',
              param_reflection: '站上20日线标的占比反映超短线进攻动量，当前读数处于中高位反映短期买方情绪处于健康爆发通道。',
            },
            {
              id: 'ma50',
              title: '50 日均线渗透率',
              pct: ma.above_50d_pct,
              role: '中期波段生命线',
              detail: '全市场站上 50 日移动平均线的个股比例。50日线是公募与对冲基金主力的核心加仓成本防线，站上率 > 50% 是判定中级波段牛市顺风环境的基础契约。',
              param_reflection: '站上50日线标的占比超 50%，反映主流公募基金与对冲基金正在波段加仓，主升浪获得中期机构底仓支撑。',
            },
            {
              id: 'ma150',
              title: '150 日均线渗透率',
              pct: ma.above_150d_pct,
              role: '趋势形态确立线',
              detail: '全市场站上 150 日中长期移动平均线的个股比例。米纳尔维尼 SEPA 趋势模板核心过滤条件，表明标的经历充分筑底后正式进入第二阶段主升浪结构。',
              param_reflection: '站上150日线标的占比突破 60%，反映全市场已有超六成股票完成筑底并确立第二阶段中长期上升通道。',
            },
            {
              id: 'ma200',
              title: '200 日均线渗透率',
              pct: ma.above_200d_pct,
              role: '长期牛熊分水岭',
              detail: '全市场站上 200 日长期移动平均线的个股比例。全球机构投资者公认的宏观牛熊分水岭，> 50% 意味着全市场广度处于牛市健康扩张期，个股突破成功率显著提高。',
              param_reflection: '全市场站上200日长期牛熊线标的比例超 60%，反映全盘牛市广度健康坚实，非少数巨头虚胖拉升。',
            },
          ].map((item, index) => {
            const alignClass = (index === 0)
              ? 'left-0'
              : (index === 3)
              ? 'right-0'
              : 'right-0 sm:left-1/2 sm:-translate-x-1/2'

            return (
              <div
                key={item.id}
                className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 space-y-2 relative group shadow-sm hover:border-slate-300 transition-all"
              >
                <div className="flex items-center justify-between gap-1">
                  <div className="text-[11px] text-[var(--text-muted)] font-medium truncate">
                    {item.title}
                  </div>

                  {/* 感叹号详细说明浮层 */}
                  <div
                    className="relative shrink-0"
                    onMouseEnter={() => setActiveMaTooltipId(item.id)}
                    onMouseLeave={() => setActiveMaTooltipId(null)}
                  >
                    <button
                      type="button"
                      tabIndex={0}
                      title={`${item.title} 详细说明`}
                      aria-label={`${item.title} 详细说明`}
                      onClick={(e) => {
                        e.stopPropagation()
                        setActiveMaTooltipId(activeMaTooltipId === item.id ? null : item.id)
                      }}
                      onFocus={() => setActiveMaTooltipId(item.id)}
                      onBlur={() => setActiveMaTooltipId(null)}
                      className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                        activeMaTooltipId === item.id
                          ? 'bg-[#176249] text-white border-[#176249]'
                          : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                      }`}
                    >
                      <InfoCircleIcon className="w-2.5 h-2.5" />
                    </button>

                    {activeMaTooltipId === item.id && (
                      <div
                        className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 ${alignClass}`}
                        onMouseEnter={() => setActiveMaTooltipId(item.id)}
                        onMouseLeave={() => setActiveMaTooltipId(null)}
                      >
                        <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                          <span className="font-bold text-xs text-[var(--text-primary)]">
                            {item.title}
                          </span>
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium shrink-0">
                            {item.role}
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
                          <span>当前渗透率: <strong className="text-[var(--text-primary)]">{item.pct}%</strong></span>
                          <span>基准: <span className={item.pct >= 50 ? 'text-[#176249] font-semibold' : 'text-amber-500 font-semibold'}>{item.pct >= 50 ? '多头优势' : '空头承压'}</span></span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-xl font-black font-mono text-[var(--text-primary)]">
                  {item.pct}%
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      item.pct >= 50 ? 'bg-[#176249]' : 'bg-amber-500'
                    }`}
                    style={{ width: `${item.pct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* 52周新高净扩展指标 */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <TrendUpIcon className="w-5 h-5 text-rose-500" />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-[var(--text-primary)]">
                  52 周新高 vs 52 周新低净扩展 (Net New Highs)
                </span>

                <div
                  className="relative"
                  onMouseEnter={() => setActiveExpansionTooltip(true)}
                  onMouseLeave={() => setActiveExpansionTooltip(false)}
                >
                  <button
                    type="button"
                    tabIndex={0}
                    title="52周新高净扩展指标详细说明"
                    aria-label="52周新高净扩展指标详细说明"
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveExpansionTooltip(!activeExpansionTooltip)
                    }}
                    onFocus={() => setActiveExpansionTooltip(true)}
                    onBlur={() => setActiveExpansionTooltip(false)}
                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                      activeExpansionTooltip
                        ? 'bg-[#176249] text-white shadow-sm'
                        : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                    }`}
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>

                  {activeExpansionTooltip && (
                    <div
                      className="absolute top-full mt-2 left-0 w-72 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                      onMouseEnter={() => setActiveExpansionTooltip(true)}
                      onMouseLeave={() => setActiveExpansionTooltip(false)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-[var(--text-primary)]">
                          52 周新高净扩展
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-50 text-rose-600 border border-rose-200 font-medium shrink-0">
                          多头广度指标
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        新高持续压制新低，表明牛市趋势内部流动性宽裕，假跌风险低。
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-[#176249]">【参数反映情况】：</span>
                        当前净扩展为 +{ma.high_low.net_expansion} 席（52周新高 {ma.high_low.new_52w_highs} 席 vs 52周新低 {ma.high_low.new_52w_lows} 席），新高持续处于净主导地位，反映市场整体赚钱效应充沛，属于典型多头进攻浪潮。
                      </div>
                      <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                        <span>统计范围: 双市场全量</span>
                        <span>净差: +{ma.high_low.net_expansion}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                双市场广度指标 · 新高 vs 新低净差监测
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 font-mono">
            <div className="text-center">
              <div className="text-[9px] text-[var(--text-muted)]">52周新高</div>
              <div className="text-sm font-black text-rose-600">+{ma.high_low.new_52w_highs} 席</div>
            </div>
            <div className="text-center">
              <div className="text-[9px] text-[var(--text-muted)]">52周新低</div>
              <div className="text-sm font-black text-blue-600">-{ma.high_low.new_52w_lows} 席</div>
            </div>
            <div className="text-center pl-3 border-l border-[var(--border-color)]">
              <div className="text-[9px] text-[var(--text-muted)]">净扩展指数</div>
              <div className="text-base font-black text-rose-600">+{ma.high_low.net_expansion} 席</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
