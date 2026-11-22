import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AutomatedValuationData, CompanyAnalysisData } from '../../types/api'
import { InfoCircleIcon } from '../common'

interface DcfValuationCorridorCardProps {
  activeValuation: AutomatedValuationData | null | undefined
  analysis: CompanyAnalysisData
  curPrice: number
  sym: string
  customDiscountRate: number
  customTerminalGrowth: number
  customGrowthRates: string
  customBeta: number
  tuning: boolean
  showSensitivity: boolean
  setShowSensitivity: (show: boolean) => void
  setCustomDiscountRate: (v: number) => void
  setCustomTerminalGrowth: (v: number) => void
  setCustomGrowthRates: (v: string) => void
  setCustomBeta: (v: number) => void
  onApplySensitivity: (e: FormEvent) => void
  onResetSensitivity: () => void
}

export function DcfValuationCorridorCard({
  activeValuation,
  analysis,
  curPrice,
  sym,
  customDiscountRate,
  customTerminalGrowth,
  customGrowthRates,
  customBeta,
  tuning,
  showSensitivity,
  setShowSensitivity,
  setCustomDiscountRate,
  setCustomTerminalGrowth,
  setCustomGrowthRates,
  setCustomBeta,
  onApplySensitivity,
  onResetSensitivity,
}: DcfValuationCorridorCardProps) {
  const [activeScenarioTooltip, setActiveScenarioTooltip] = useState<'floor' | 'base' | 'opt' | null>(null)

  const facts = activeValuation?.underlying_facts
  const corridor = activeValuation?.valuation_corridor
  const wacc = activeValuation?.capital_cost_wacc
  const ratios = activeValuation?.profitability_ratios
  const mos = corridor?.margin_of_safety_pct ?? 0

  if (!activeValuation || !corridor) {
    if (analysis?.asset_category === 'Broad_Or_Sector_ETF') {
      return (
        <div id="sec-dcf" className="rounded-xl border border-purple-200 bg-purple-50/60 p-5 text-xs text-purple-900 space-y-2 shadow-sm">
          <div className="flex items-center gap-2 font-bold text-sm text-purple-950">
            <span>💡</span>
            <span>【多资产自适应说明】ETF 采用成分股聚合穿透估值模型</span>
          </div>
          <p className="leading-relaxed text-purple-800">
            标的 [{analysis.ticker}] 属于全球核心指数/行业主题 ETF 资产，其公允价值由底层成分股集合净值 (NAV) 与费率跟踪误差决定。单体企业多阶段自由现金流折现 (DCF) 模型已自适应切换至上方的《ETF 穿透深度分析》面板（包含前十大权重成分股穿透分布与宏观降息敏感度分析）。
          </p>
        </div>
      )
    }
    if (analysis?.asset_category === 'Gold_And_Commodity') {
      return (
        <div id="sec-dcf" className="rounded-xl border border-amber-200 bg-amber-50/60 p-5 text-xs text-amber-900 space-y-2 shadow-sm">
          <div className="flex items-center gap-2 font-bold text-sm text-amber-950">
            <span>💡</span>
            <span>【多资产自适应说明】贵金属采用真实利率与实物储备定价模型</span>
          </div>
          <p className="leading-relaxed text-amber-800">
            标的 [{analysis.ticker}] 属于实物黄金/贵金属大宗商品资产，不适用企业自由现金流贴现。其公允区间由上方的《黄金与特级贵金属宏观穿透分析》承载（涵盖 10 年期 TIPS 真实利率负向弹性、全球金银比与伦敦金库实物交割标准）。
          </p>
        </div>
      )
    }
    if (analysis?.automated_valuation_issue) {
      return (
        <div id="sec-dcf" className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-4 text-xs text-[var(--text-muted)] space-y-1 shadow-sm">
          <div className="font-semibold text-[var(--text-secondary)]">自动估值状态提示</div>
          <div>{analysis.automated_valuation_issue}</div>
        </div>
      )
    }
    return null
  }

  return (
    <div id="sec-dcf" className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-[var(--border-color)]">
        <div>
          <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>多阶段 DCF 内在价值走廊与估值区间</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
              官方财报数据代入
            </span>
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            基于 SEC/JPX 官方三表现金流、WACC 资本成本折现率与 FRED 10Y 美债基准
          </p>
        </div>
        <span
          className={`text-xs px-3 py-1 rounded-full font-bold border font-mono ${
            mos >= 0
              ? 'bg-blue-50 text-blue-600 border-blue-200'
              : 'bg-rose-50 text-rose-600 border-rose-200'
          }`}
        >
          {mos >= 0 ? `安全边际 +${mos.toFixed(1)}% (折价区间)` : `估值溢价 ${Math.abs(mos).toFixed(1)}% (溢价区间)`}
        </span>
      </div>

      {/* 顶层估值研判与投资逻辑 */}
      <div className="p-3.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex items-start gap-3 transition-all">
        <div className="p-1 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)] text-slate-700 shrink-0 mt-0.5">
          <InfoCircleIcon className="w-4 h-4 text-slate-700" />
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <div className="font-bold text-xs text-[var(--text-primary)]">
              估值研判与投资逻辑
            </div>
            <span className={`text-[10px] px-2 py-0.2 rounded-full font-mono font-bold ${
              mos >= 20
                ? 'bg-blue-50 text-blue-600 border border-blue-200'
                : mos >= 0
                ? 'bg-blue-50 text-blue-600 border border-blue-200'
                : mos >= -30
                ? 'bg-rose-50 text-rose-600 border border-rose-200'
                : 'bg-rose-50 text-rose-600 border border-rose-200'
            }`}>
              {mos >= 20
                ? '【估值研判：具备较高安全边际】'
                : mos >= 0
                ? '【估值研判：处于公允价值中枢区间】'
                : mos >= -30
                ? '【估值研判：估值温和偏高 · 缺乏安全边际】'
                : '【估值研判：现价处于历史高位溢价区间】'}
            </span>
          </div>
          <div className="text-xs text-[var(--text-secondary)] leading-relaxed">
            {corridor.valuation_verdict}
          </div>
        </div>
      </div>

      {/* 内在价值估值区间标尺 */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[var(--text-primary)]">
              内在价值估值区间标尺 (Valuation Range)
            </span>
            <span className="text-[10px] text-[var(--text-muted)]">
              现价 vs 保守底价 / 中性公允 / 乐观靶心
            </span>
          </div>
          <span className={`px-2 py-0.5 rounded font-mono font-bold text-[11px] ${
            mos >= 0 ? 'text-blue-600 bg-blue-50 border border-blue-200' : 'text-rose-600 bg-rose-50 border border-rose-200'
          }`}>
            {mos >= 0 ? `安全边际 +${mos.toFixed(1)}%` : `估值溢价 ${Math.abs(mos).toFixed(1)}%`}
          </span>
        </div>

        {/* 标尺轨道图 (自适应动态归一化刻度) */}
        {(() => {
          const pFloor = corridor.conservative_floor.value_per_share
          const pBase = corridor.base_fair_value.value_per_share
          const pOpt = corridor.optimistic_target.value_per_share
          const min = Math.min(pFloor, curPrice) * 0.85
          const max = Math.max(pOpt, curPrice) * 1.15
          const span = Math.max(1, max - min)
          const clamp = (val: number) => Math.max(5, Math.min(95, ((val - min) / span) * 100))
          const curPos = clamp(curPrice)
          const floorPos = clamp(pFloor)
          const basePos = clamp(pBase)
          const optPos = clamp(pOpt)

          return (
            <div className="pt-7 pb-6 px-3">
              <div className="relative w-full h-3 rounded-full bg-slate-200 overflow-visible">
                {/* 保守到中性区间 (安全边际区 - 蓝) */}
                <div
                  className="absolute top-0 h-3 rounded-l-full bg-blue-100"
                  style={{ left: `${floorPos}%`, width: `${Math.max(0, basePos - floorPos)}%` }}
                />
                {/* 中性到乐观区间 (溢价区 - 红) */}
                <div
                  className="absolute top-0 h-3 rounded-r-full bg-rose-100"
                  style={{ left: `${basePos}%`, width: `${Math.max(0, optPos - basePos)}%` }}
                />

                {/* 保守标记 (蓝色底线) */}
                <div className="absolute top-0 -mt-1 w-0.5 h-5 bg-blue-500 -translate-x-1/2" style={{ left: `${floorPos}%` }}>
                  <div className="absolute top-5 -translate-x-1/2 text-[10px] font-mono text-blue-600 whitespace-nowrap">
                    <div>底线 {sym}{pFloor.toFixed(1)}</div>
                  </div>
                </div>

                {/* 中性公允标记 (中性深灰) */}
                <div className="absolute top-0 -mt-1.5 w-1 h-6 bg-slate-800 -translate-x-1/2" style={{ left: `${basePos}%` }}>
                  <div className="absolute top-6 -translate-x-1/2 text-[10px] font-mono font-bold text-slate-800 whitespace-nowrap">
                    <div>公允 {sym}{pBase.toFixed(1)}</div>
                  </div>
                </div>

                {/* 乐观靶心标记 (红色靶心) */}
                <div className="absolute top-0 -mt-1 w-0.5 h-5 bg-rose-500 -translate-x-1/2" style={{ left: `${optPos}%` }}>
                  <div className="absolute top-5 -translate-x-1/2 text-[10px] font-mono text-rose-600 whitespace-nowrap">
                    <div>靶心 {sym}{pOpt.toFixed(1)}</div>
                  </div>
                </div>

                {/* 当前现价指示游标 (统一红涨蓝跌) */}
                <div className="absolute top-0 -mt-7 -translate-x-1/2 flex flex-col items-center z-10" style={{ left: `${curPos}%` }}>
                  <div className={`px-2 py-0.5 rounded font-bold font-mono text-[10px] shadow-sm flex items-center gap-1 whitespace-nowrap ${
                    mos < 0 ? 'bg-rose-600 text-white' : 'bg-blue-600 text-white'
                  }`}>
                    <span>现价</span>
                    <span>{sym}{curPrice.toFixed(2)}</span>
                  </div>
                  <div className={`w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[5px] ${
                    mos < 0 ? 'border-t-rose-600' : 'border-t-blue-600'
                  }`} />
                  <div className={`w-0.5 h-7 ${mos < 0 ? 'bg-rose-600/70' : 'bg-blue-600/70'}`} />
                </div>
              </div>

              {/* 标尺底部三大决策分区说明 */}
              <div className="flex items-center justify-between text-[9px] font-mono text-[var(--text-muted)] pt-8 border-t border-[var(--border-color)]/30 mt-4">
                <span className="text-blue-600 font-semibold flex items-center gap-1">
                  <span>◀ 深度价值区间 (具备安全边际)</span>
                </span>
                <span className="text-slate-700 font-semibold">
                  ● 基本面公允中枢
                </span>
                <span className="text-rose-600 font-semibold flex items-center gap-1">
                  <span>景气溢价区间 (估值偏高) ▶</span>
                </span>
              </div>
            </div>
          )
        })()}
      </div>

      {/* 三态情景估值卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 保守底价 */}
        <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between relative group shadow-sm">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-600">保守底价</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200 font-semibold font-mono">
                  {(corridor.conservative_floor as any).scenario_tag || '严苛防御'}
                </span>

                {/* 感叹号详细说明浮层 */}
                <div
                  className="relative"
                  onMouseEnter={() => setActiveScenarioTooltip('floor')}
                  onMouseLeave={() => setActiveScenarioTooltip(null)}
                >
                  <button
                    type="button"
                    tabIndex={0}
                    title="保守底价情景推演说明"
                    aria-label="保守底价情景推演说明"
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveScenarioTooltip(activeScenarioTooltip === 'floor' ? null : 'floor')
                    }}
                    onFocus={() => setActiveScenarioTooltip('floor')}
                    onBlur={() => setActiveScenarioTooltip(null)}
                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                      activeScenarioTooltip === 'floor'
                        ? 'bg-slate-800 text-white border-slate-800'
                        : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                    }`}
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>

                  {activeScenarioTooltip === 'floor' && (
                    <div
                      className="absolute top-full mt-2 left-0 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                      onMouseEnter={() => setActiveScenarioTooltip('floor')}
                      onMouseLeave={() => setActiveScenarioTooltip(null)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-blue-600">
                          保守底价情景推演
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-50 text-blue-600 border border-blue-200 font-medium">
                          {(corridor.conservative_floor as any).scenario_tag || '严苛防御'}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        {corridor.conservative_floor.description}
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-slate-800">【核心参数反映情况】：</span>
                        折现率设定为 {corridor.conservative_floor.discount_rate_pct}% 与 永续增长率设定为 {corridor.conservative_floor.terminal_growth_pct}%，反映在宏观紧缩与下游资本开支削减下的压力测试支撑底价，由账面净现金和稳态现金流托底。
                      </div>
                      <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                        <div>折现率: {corridor.conservative_floor.discount_rate_pct}% | 永续: {corridor.conservative_floor.terminal_growth_pct}%</div>
                        <div>前3年预测增长: {corridor.conservative_floor.growth_rates_pct.join('%, ')}%</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="text-2xl font-black font-mono text-[var(--text-primary)] mt-2.5">
              {sym}{corridor.conservative_floor.value_per_share.toFixed(2)}
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] space-y-0.5">
            <div>折现率：{corridor.conservative_floor.discount_rate_pct}%</div>
            <div>永续增长率：{corridor.conservative_floor.terminal_growth_pct}%</div>
            <div>预测增长：{corridor.conservative_floor.growth_rates_pct.join('%, ')}%</div>
          </div>
        </div>

        {/* 中性公允价 (核心估值中枢) */}
        <div className="p-4 rounded-xl border-2 border-[#176249] bg-[var(--surface-color)] shadow-sm flex flex-col justify-between relative group">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#176249]">中性公允价</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-semibold font-mono">
                  {(corridor.base_fair_value as any).scenario_tag || '公允基准'}
                </span>

                {/* 感叹号详细说明浮层 */}
                <div
                  className="relative"
                  onMouseEnter={() => setActiveScenarioTooltip('base')}
                  onMouseLeave={() => setActiveScenarioTooltip(null)}
                >
                  <button
                    type="button"
                    tabIndex={0}
                    title="中性公允价情景推演说明"
                    aria-label="中性公允价情景推演说明"
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveScenarioTooltip(activeScenarioTooltip === 'base' ? null : 'base')
                    }}
                    onFocus={() => setActiveScenarioTooltip('base')}
                    onBlur={() => setActiveScenarioTooltip(null)}
                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                      activeScenarioTooltip === 'base'
                        ? 'bg-[#176249] text-white border-[#176249]'
                        : 'bg-[var(--surface-color)] hover:bg-[#176249]/20 text-[var(--text-muted)] hover:text-[#176249] border border-[var(--border-color)]'
                    }`}
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>

                  {activeScenarioTooltip === 'base' && (
                    <div
                      className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                      onMouseEnter={() => setActiveScenarioTooltip('base')}
                      onMouseLeave={() => setActiveScenarioTooltip(null)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-[#176249]">
                          中性公允价推演 (估值中枢)
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                          {(corridor.base_fair_value as any).scenario_tag || '公允基准'}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        {corridor.base_fair_value.description}
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-slate-800">【核心参数反映情况】：</span>
                        基准折现率 {corridor.base_fair_value.discount_rate_pct}% 对应行业标准加权资本成本，永续增速 {corridor.base_fair_value.terminal_growth_pct}% 锚定全球长期名义 GDP 增速，反映基于当前三表底账和稳态护城河的内生真实价值。
                      </div>
                      <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                        <div>WACC 折现率: {corridor.base_fair_value.discount_rate_pct}% | 永续: {corridor.base_fair_value.terminal_growth_pct}%</div>
                        <div>前3年预测增长: {corridor.base_fair_value.growth_rates_pct.join('%, ')}%</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="text-2xl font-black font-mono text-[var(--text-primary)] mt-2.5">
              {sym}{corridor.base_fair_value.value_per_share.toFixed(2)}
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] space-y-0.5">
            <div>WACC 折现率：{corridor.base_fair_value.discount_rate_pct}%</div>
            <div>永续增长率：{corridor.base_fair_value.terminal_growth_pct}%</div>
            <div>预测增长：{corridor.base_fair_value.growth_rates_pct.join('%, ')}%</div>
            {corridor.base_fair_value.forecast && (
              <details className="mt-1.5 text-[11px]">
                <summary className="cursor-pointer text-slate-700 hover:text-slate-900 font-medium">查看 3 年期折现明细</summary>
                <ul className="mt-1 pl-2 space-y-0.5 text-[var(--text-muted)] font-mono">
                  {corridor.base_fair_value.forecast.map(row => (
                    <li key={row.year}>第 {row.year} 年 FCF: {sym}{(row.cash_flow / 1e9).toFixed(2)}B (现值: {sym}{(row.present_value / 1e9).toFixed(2)}B)</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        </div>

        {/* 乐观靶心价 */}
        <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between relative group shadow-sm">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-rose-600">乐观靶心价</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 font-semibold font-mono">
                  {(corridor.optimistic_target as any).scenario_tag || '景气爆发'}
                </span>

                {/* 感叹号详细说明浮层 */}
                <div
                  className="relative"
                  onMouseEnter={() => setActiveScenarioTooltip('opt')}
                  onMouseLeave={() => setActiveScenarioTooltip(null)}
                >
                  <button
                    type="button"
                    tabIndex={0}
                    title="乐观靶心价情景推演说明"
                    aria-label="乐观靶心价情景推演说明"
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveScenarioTooltip(activeScenarioTooltip === 'opt' ? null : 'opt')
                    }}
                    onFocus={() => setActiveScenarioTooltip('opt')}
                    onBlur={() => setActiveScenarioTooltip(null)}
                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-rose-500 ${
                      activeScenarioTooltip === 'opt'
                        ? 'bg-rose-500 text-white border-rose-500'
                        : 'bg-[var(--surface-color)] hover:bg-rose-50 text-[var(--text-muted)] hover:text-rose-500 border border-[var(--border-color)]'
                    }`}
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>

                  {activeScenarioTooltip === 'opt' && (
                    <div
                      className="absolute top-full mt-2 right-0 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                      onMouseEnter={() => setActiveScenarioTooltip('opt')}
                      onMouseLeave={() => setActiveScenarioTooltip(null)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-rose-600">
                          乐观靶心价推演
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-50 text-rose-600 border border-rose-200 font-medium">
                          {(corridor.optimistic_target as any).scenario_tag || '景气爆发'}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        {corridor.optimistic_target.description}
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-slate-800">【核心参数反映情况】：</span>
                        折现率设定为 {corridor.optimistic_target.discount_rate_pct}%，永续增速设定为 {corridor.optimistic_target.terminal_growth_pct}%，前3年增速提升至 {corridor.optimistic_target.growth_rates_pct.join('%, ')}%，反映核心业务景气放量情景下的估值上限。
                      </div>
                      <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                        <div>折现率: {corridor.optimistic_target.discount_rate_pct}% | 永续: {corridor.optimistic_target.terminal_growth_pct}%</div>
                        <div>前3年预测增长: {corridor.optimistic_target.growth_rates_pct.join('%, ')}%</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="text-2xl font-black font-mono text-rose-600 mt-2.5">
              {sym}{corridor.optimistic_target.value_per_share.toFixed(2)}
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] space-y-0.5">
            <div>折现率：{corridor.optimistic_target.discount_rate_pct}%</div>
            <div>永续增长率：{corridor.optimistic_target.terminal_growth_pct}%</div>
            <div>预测增长：{corridor.optimistic_target.growth_rates_pct.join('%, ')}%</div>
          </div>
        </div>
      </div>

      {/* 敏感性动态微调折叠面板 */}
      <div className="pt-2 border-t border-[var(--border-color)]">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-[var(--text-primary)]">
              情景敏感性参数动态校准与压力测试
            </div>
            <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
              支持在官方财报自动代入的基础上，微调折现率与逐年增长率进行敏感性压力测试
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowSensitivity(!showSensitivity)}
            className="px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[#176249] hover:border-[#176249] cursor-pointer"
          >
            {showSensitivity ? '收起微调面板 ▲' : '展开敏感性微调 ▼'}
          </button>
        </div>

        {showSensitivity && (
          <form onSubmit={onApplySensitivity} className="mt-3.5 p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3.5">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <label className="flex flex-col gap-1">
                <span className="text-[var(--text-secondary)] font-medium">基准折现率 WACC (%)</span>
                <input
                  type="number"
                  step="0.1"
                  min="4"
                  max="20"
                  value={customDiscountRate}
                  onChange={e => setCustomDiscountRate(Number(e.target.value))}
                  className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-[var(--text-secondary)] font-medium">永续增长率 (%)</span>
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="5"
                  value={customTerminalGrowth}
                  onChange={e => setCustomTerminalGrowth(Number(e.target.value))}
                  className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-[var(--text-secondary)] font-medium">前3年逐年增长率 (%)</span>
                <input
                  type="text"
                  value={customGrowthRates}
                  onChange={e => setCustomGrowthRates(e.target.value)}
                  placeholder="例如: 18, 14, 10"
                  className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-[var(--text-secondary)] font-medium">标的 Beta 系数</span>
                <input
                  type="number"
                  step="0.05"
                  min="0.5"
                  max="3"
                  value={customBeta}
                  onChange={e => setCustomBeta(Number(e.target.value))}
                  className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                />
              </label>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={tuning}
                className="px-3.5 py-1.5 rounded-md bg-[#176249] hover:bg-[#124e3a] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all shadow-sm"
              >
                {tuning ? '重新测算中…' : '应用微调并重新测算估值走廊'}
              </button>
              <button
                type="button"
                onClick={onResetSensitivity}
                className="px-2.5 py-1.5 rounded-md border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
              >
                恢复官方原始基准
              </button>
            </div>
          </form>
        )}
      </div>

      {/* WACC 资本成本与杜邦分析两列横排 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
        {/* WACC 资本成本 */}
        <div className="p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
            <span className="text-xs font-bold text-[var(--text-primary)]">
              加权平均资本成本 (WACC)
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-100 text-slate-700">
              CAPM 模型
            </span>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">WACC 综合折现率</span>
              <span className="font-mono font-bold text-[var(--text-primary)]">
                {wacc?.wacc_pct}%
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">股权成本 (Cost of Equity)</span>
              <span className="font-mono">{wacc?.cost_of_equity_pct}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">税后债务成本 (Debt Cost)</span>
              <span className="font-mono">{wacc?.after_tax_cost_of_debt_pct}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">股权 / 债务权重</span>
              <span className="font-mono">{wacc?.equity_weight_pct}% / {wacc?.debt_weight_pct}%</span>
            </div>
          </div>
        </div>

        {/* 杜邦分析与盈利质量 */}
        <div className="p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
            <span className="text-xs font-bold text-[var(--text-primary)]">
              杜邦分析与盈利质量透视
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-100 text-slate-700">
              官方三表披露
            </span>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">净资产收益率 (ROE)</span>
              <span className="font-mono font-bold text-[#176249]">
                {ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '—'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">总资产收益率 (ROA)</span>
              <span className="font-mono">{ratios?.roa_pct != null ? `${ratios.roa_pct}%` : '—'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">营业利润率 (Operating Margin)</span>
              <span className="font-mono">{ratios?.operating_margin_pct != null ? `${ratios.operating_margin_pct}%` : '—'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">现金流转化率 (FCF / NI)</span>
              <span className="font-mono">{ratios?.fcf_conversion_pct != null ? `${ratios.fcf_conversion_pct}%` : '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 官方财报核心数据明细卡片 */}
      {facts && (
        <div id="sec-financials" className="scroll-mt-16 pt-2 border-t border-[var(--border-color)]">
          <div className="text-xs font-bold text-[var(--text-primary)] mb-2.5">
            官方财报核心数据 (官方原档: {facts.source_filing})
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[10px] text-[var(--text-muted)]">自由现金流 (FCF)</div>
              <div className="font-mono font-bold text-xs mt-1 text-[var(--text-primary)]">
                {facts.free_cash_flow_formatted}
              </div>
            </div>
            <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[10px] text-[var(--text-muted)]">稀释总股数</div>
              <div className="font-mono font-bold text-xs mt-1 text-[var(--text-primary)]">
                {facts.shares_formatted}
              </div>
            </div>
            <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[10px] text-[var(--text-muted)]">现金储备 / 有息负债</div>
              <div className="font-mono font-bold text-xs mt-1 text-[var(--text-primary)] truncate">
                {facts.cash_formatted} / {facts.debt_formatted}
              </div>
            </div>
            <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[10px] text-[var(--text-muted)]">净现金状态</div>
              <div className="font-medium text-xs mt-1 text-slate-800">
                {facts.net_cash_status}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
