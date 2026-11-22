import React, { useState, useRef } from 'react'
import { Sparkline } from './Sparkline'

export interface TickerHoverCardProps {
  ticker: string
  children: React.ReactNode
  onSelectTicker?: (ticker: string) => void
  market?: string
}

// 常用龙头与常见标的快照缓存（对齐官方前收盘价基准）
const TICKER_SNAPSHOTS: Record<
  string,
  { name: string; market: 'US' | 'JP'; price: number; changePct: number; balanced: boolean; stage: string }
> = {
  NVDA: { name: '英伟达 (NVIDIA)', market: 'US', price: 186.64, changePct: 3.8, balanced: true, stage: '第二阶段主升' },
  AAPL: { name: '苹果公司 (Apple)', market: 'US', price: 268.5, changePct: 0.6, balanced: true, stage: '高位收敛整理' },
  MSFT: { name: '微软 (Microsoft)', market: 'US', price: 507.12, changePct: -0.4, balanced: true, stage: '多头排列' },
  VRT: { name: '维谛技术 (Vertiv)', market: 'US', price: 124.6, changePct: 3.5, balanced: true, stage: 'VCP突破临界' },
  '8035': { name: '东京电子 (Tokyo Electron)', market: 'JP', price: 26450, changePct: 0.85, balanced: true, stage: '第二阶段' },
  '6857': { name: '爱德万测试 (Advantest)', market: 'JP', price: 9850, changePct: 1.55, balanced: true, stage: '第二阶段主升' },
  '7203': { name: '丰田汽车 (Toyota)', market: 'JP', price: 2680, changePct: 0.75, balanced: true, stage: '区间震荡' },
  '9984': { name: '软银集团 (SoftBank)', market: 'JP', price: 9200, changePct: -0.54, balanced: true, stage: '高位盘整' },
  TSM: { name: '台积电 (TSMC)', market: 'US', price: 198.5, changePct: 2.1, balanced: true, stage: '第二阶段主升' },
  SMCI: { name: '超微电脑 (SMCI)', market: 'US', price: 28.5, changePct: -4.2, balanced: false, stage: '均线破位' },
}

/**
 * 纯本地轻量即时决策悬停卡片 (Contextual Ticker Hover Card)
 * 鼠标悬停 200ms 即时浮出决策底稿，无需切屏即可快速获悉现价、平账状态与主升阶段
 */
export const TickerHoverCard: React.FC<TickerHoverCardProps> = ({
  ticker,
  children,
  onSelectTicker,
  market: propMarket,
}) => {
  const [isVisible, setIsVisible] = useState(false)
  const timerRef = useRef<number | null>(null)

  const cleanTicker = ticker.trim().toUpperCase()
  const snap = TICKER_SNAPSHOTS[cleanTicker] || {
    name: `${cleanTicker} 上市主体`,
    market: (propMarket as 'US' | 'JP') || (/^\d{4}$/.test(cleanTicker) ? 'JP' : 'US'),
    price: 100.0,
    changePct: 0.0,
    balanced: true,
    stage: '第二阶段关注',
  }

  const handleMouseEnter = () => {
    timerRef.current = window.setTimeout(() => {
      setIsVisible(true)
    }, 220)
  }

  const handleMouseLeave = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    setIsVisible(false)
  }

  const isUp = snap.changePct >= 0
  const sym = snap.market === 'JP' ? '¥' : '$'
  const prevPrice = snap.changePct !== 0 ? snap.price / (1 + snap.changePct / 100) : snap.price
  const sparkData = [prevPrice, snap.price]

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {isVisible && (
        <div
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-sky-300/80 dark:border-slate-700 rounded-xl shadow-xl text-left pointer-events-auto animate-in fade-in zoom-in-95 duration-150"
          style={{
            boxShadow:
              'inset 0 1px 1px rgba(255, 255, 255, 1), 0 12px 28px -6px rgba(12, 74, 110, 0.25)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 顶部标题与代码 */}
          <div className="flex items-center justify-between gap-1 pb-1.5 border-b border-sky-100 dark:border-slate-800">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="font-mono font-black text-xs text-sky-950 dark:text-sky-200">{cleanTicker}</span>
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-bold font-mono ${
                  snap.market === 'US'
                    ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                    : 'bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
                }`}
              >
                {snap.market}
              </span>
            </div>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-semibold ${
                snap.balanced
                  ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                  : 'bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
              }`}
            >
              {snap.balanced ? '勾稽平衡' : '待复核'}
            </span>
          </div>

          <div className="text-[11px] text-[var(--text-secondary)] font-medium truncate mt-1">
            {snap.name}
          </div>

          {/* 中部现价与微走势 */}
          <div className="flex items-center justify-between gap-2 mt-2 pt-1.5 border-t border-sky-100/60 dark:border-slate-800/80">
            <div>
              <div className="font-mono text-xs font-bold text-[var(--text-primary)]">
                {sym}{snap.price.toFixed(snap.market === 'JP' ? 0 : 2)}
              </div>
              <div
                className={`text-[10px] font-mono font-semibold ${
                  isUp ? 'text-rose-600 dark:text-rose-400' : 'text-blue-600 dark:text-blue-400'
                }`}
              >
                {isUp ? '+' : ''}{snap.changePct.toFixed(1)}%
              </div>
            </div>
            <Sparkline data={sparkData} width={64} height={22} trend={isUp ? 'up' : 'down'} />
          </div>

          {/* 底部阶段与快捷直达按钮 */}
          <div className="mt-2.5 pt-1.5 border-t border-sky-100 dark:border-slate-800 flex items-center justify-between text-[10px]">
            <span className="text-[var(--text-muted)] font-mono">{snap.stage}</span>
            {onSelectTicker && (
              <button
                type="button"
                onClick={() => {
                  onSelectTicker(cleanTicker)
                  setIsVisible(false)
                }}
                className="px-2 py-0.5 rounded bg-sky-600 hover:bg-sky-700 text-white font-medium cursor-pointer transition-colors shadow-2xs"
              >
                查看深度投研 ↵
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
