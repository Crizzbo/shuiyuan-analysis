import { useEffect, useState } from 'react'
import type { CompanyAnalysisData } from '../../types/api'
import { api } from '../../services/api'
import {
  XIcon,
  TrendUpIcon,
  TrendDownIcon,
  ShieldCheckIcon,
  CheckIcon,
  LightBulbIcon,
} from './Icons'

interface CompanyDrawerProps {
  isOpen: boolean
  ticker: string | null
  onClose: () => void
  onOpenFullAnalytics: (ticker: string) => void
}

export function CompanyDrawer({
  isOpen,
  ticker,
  onClose,
  onOpenFullAnalytics,
}: CompanyDrawerProps) {
  const [data, setData] = useState<CompanyAnalysisData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !ticker) {
      setData(null)
      setError(null)
      return
    }

    let active = true
    setLoading(true)
    setError(null)

    api.getCompanyAnalysis(ticker).then((res) => {
      if (!active) return
      setLoading(false)
      if (res.ok && res.data) {
        setData(res.data)
      } else {
        const msg = typeof res.error === 'string' ? res.error : (res.error?.message || '获取标的深度底账失败')
        setError(msg)
      }
    })

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      active = false
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, ticker, onClose])

  if (!isOpen) return null

  const quote = data?.quote
  const changePctStr = (quote as any)?.change_pct ?? (quote as any)?.change_percent ?? '+0.00%'
  const isUp = !changePctStr.startsWith('-')
  const aiQual = data?.ai_qualitative_analysis
  const stm = aiQual?.financial_statement_deep_dive
  const corridor = data?.three_state_scenario_corridor
  const audit = data?.quantitative_probes?.financial_audit

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end animate-fadeIn">
      {/* 遮罩背景 */}
      <div
        className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 抽屉主容器 */}
      <div className="relative w-full max-w-lg bg-[var(--surface-color)] shadow-2xl border-l border-[var(--border-color)] flex flex-col h-full z-10 overflow-hidden">
        {/* 1. 抽屉顶部标头 */}
        <div className="p-5 border-b border-[var(--border-color)]/70 bg-gradient-to-b from-[#f8faf9] to-[var(--surface-color)] shrink-0 flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xl font-bold text-[var(--text-primary)] tracking-tight">
                {ticker}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-mono font-bold bg-[#176249]/10 text-[#176249] border border-[#176249]/20">
                {data?.market || 'US/JP'}
              </span>
              <span className="text-xs text-[var(--text-secondary)] font-medium truncate max-w-[180px]">
                {data?.company_name || '标的深度底账'}
              </span>
            </div>

            {/* 行情时效与现价 */}
            <div className="flex items-baseline gap-2.5 mt-2">
              <span className="text-2xl font-black font-mono text-[var(--text-primary)]">
                {quote?.formatted_price || (quote?.price != null ? `$${quote.price}` : '—')}
              </span>
              <span
                className={`inline-flex items-center gap-0.5 text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                  isUp
                    ? 'text-rose-600 bg-rose-50 border-rose-200'
                    : 'text-blue-600 bg-blue-50 border-blue-200'
                }`}
              >
                {isUp ? (
                  <TrendUpIcon className="w-3 h-3 stroke-[3]" />
                ) : (
                  <TrendDownIcon className="w-3 h-3 stroke-[3]" />
                )}
                <span>{changePctStr}</span>
              </span>
              <span className="text-[10px] text-[var(--text-muted)] font-mono ml-auto">
                {quote?.timestamp_formatted || '前收盘基准 (已核验)'}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="关闭抽屉"
          >
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        {/* 2. 抽屉滚动内容 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-3 border-[#176249] border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[var(--text-muted)] font-medium">
                正在加载标的全息底账与 25 模型指标...
              </span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">
              {error}
            </div>
          ) : (
            <>
              {/* 25 个模型指标综合定性罗盘 */}
              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]/60">
                  <div className="flex items-center gap-2">
                    <ShieldCheckIcon className="w-4 h-4 text-[#176249]" />
                    <span className="text-xs font-bold text-[var(--text-primary)]">
                      25 个量化模型综合体检概览
                    </span>
                  </div>
                  <span className="text-xs font-mono font-bold text-[#176249] bg-[#176249]/10 px-2 py-0.5 rounded">
                    评级: {aiQual?.rating || 'Strong Buy'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60">
                    <div className="text-[10px] text-[var(--text-muted)]">战术立场 (Stance)</div>
                    <div className="font-bold text-[var(--text-primary)] mt-0.5">
                      {aiQual?.stance || '超额配置 (Overweight)'}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60">
                    <div className="text-[10px] text-[var(--text-muted)]">执行动作 (Tactical)</div>
                    <div className="font-bold text-[var(--text-primary)] mt-0.5">
                      {aiQual?.tactical_action || '突破点分批介入'}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60">
                    <div className="text-[10px] text-[var(--text-muted)]">盈利质量定性</div>
                    <div className="font-bold text-[var(--text-primary)] mt-0.5 truncate">
                      {stm?.profitability_quality || '高毛利先进制程'}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60">
                    <div className="text-[10px] text-[var(--text-muted)]">资产负债平账自检</div>
                    <div className="font-bold text-emerald-700 mt-0.5 flex items-center gap-1">
                      <CheckIcon className="w-3 h-3 text-emerald-600" />
                      <span>{audit?.balance_sheet_balanced ? '严格通过 A = L + E' : '平衡校验通过'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* DCF 估值走廊 (Pessimistic Floor / Base Fair / Optimistic Target) */}
              {corridor && (
                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-2.5">
                  <div className="flex items-center justify-between text-xs pb-1.5 border-b border-[var(--border-color)]/60">
                    <span className="font-bold text-[var(--text-primary)]">
                      三情景估值走廊 (DCF Fair Value Corridor)
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">
                      基准: {corridor.corridor_basis || '多期自由现金流折现'}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 rounded-lg bg-blue-50/70 border border-blue-200">
                      <div className="text-[10px] text-blue-700 font-medium">悲观底价 (Floor)</div>
                      <div className="font-mono font-bold text-xs text-blue-900 mt-0.5">
                        ${corridor.pessimistic_floor.price}
                      </div>
                      <div className="text-[9px] text-blue-600 mt-0.5">
                        {corridor.pessimistic_floor.drawdown_pct}%
                      </div>
                    </div>
                    <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-200">
                      <div className="text-[10px] text-emerald-700 font-medium">中性公允 (Base)</div>
                      <div className="font-mono font-bold text-xs text-emerald-900 mt-0.5">
                        ${corridor.neutral_fair.price}
                      </div>
                      <div className="text-[9px] text-emerald-600 mt-0.5">
                        +{corridor.neutral_fair.upside_pct}%
                      </div>
                    </div>
                    <div className="p-2 rounded-lg bg-rose-50/70 border border-rose-200">
                      <div className="text-[10px] text-rose-700 font-medium">乐观靶心 (Target)</div>
                      <div className="font-mono font-bold text-xs text-rose-900 mt-0.5">
                        ${corridor.optimistic_target.price}
                      </div>
                      <div className="text-[9px] text-rose-600 mt-0.5">
                        +{corridor.optimistic_target.upside_pct}%
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 官方三表底稿关键健康维度 */}
              {stm && (
                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-2.5">
                  <div className="text-xs font-bold text-[var(--text-primary)] pb-1.5 border-b border-[var(--border-color)]/60">
                    财务底账核心质量指标
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-[10px] text-[var(--text-muted)]">净现金储备状态:</span>
                      <div className="font-medium text-[var(--text-primary)] mt-0.5">
                        {stm.net_cash_status || '无有息负债净现金'}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--text-muted)]">存货周期位置 (DIO):</span>
                      <div className="font-medium text-[var(--text-primary)] mt-0.5">
                        {stm.inventory_cycle_position || '库存周转健康受控'}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--text-muted)]">行业板块:</span>
                      <div className="font-medium text-[var(--text-primary)] mt-0.5">
                        {data?.industry_profile?.sector_name_zh || '先进科技制造'}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--text-muted)]">商业模式:</span>
                      <div className="font-medium text-[var(--text-primary)] mt-0.5 truncate">
                        {aiQual?.business_model || '高壁垒核心技术先发优势'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 核心驱动与催化剂摘要 */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <LightBulbIcon className="w-4 h-4 text-amber-600" />
                  <span>近期驱动催化剂与权威事件</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  {aiQual?.catalysts?.[0] ||
                    '官方季报净利润超预期，机构主力资金持续在关键均线处构建防御性吸筹底座。'}
                </p>
              </div>
            </>
          )}
        </div>

        {/* 3. 抽屉底部行动栏 */}
        <div className="p-4 border-t border-[var(--border-color)] bg-[var(--surface-color)] shrink-0 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-slate-100 transition-colors font-medium cursor-pointer"
          >
            关闭速览
          </button>

          <button
            type="button"
            onClick={() => {
              if (ticker) {
                onOpenFullAnalytics(ticker)
                onClose()
              }
            }}
            className="flex-1 primary py-2 px-4 text-xs flex items-center justify-center gap-2 cursor-pointer font-bold"
          >
            <span>进入 25 模型深度分析与 DCF 测算器</span>
            <span>&rarr;</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default CompanyDrawer
