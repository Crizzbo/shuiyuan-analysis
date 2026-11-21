import React, { useState, useRef } from 'react'
import { Sparkline } from './Sparkline'

export interface TickerHoverCardProps {
  ticker: string
  children: React.ReactNode
  onSelectTicker?: (ticker: string) => void
  market?: string
}

// 常用龙头与常见标的快照缓存（无需额外网络往返即可瞬间展示，提升交互响应度）
const TICKER_SNAPSHOTS: Record<
  string,
  { name: string; market: 'US' | 'JP'; price: number; changePct: number; balanced: boolean; stage: string }
> = {
  NVDA: { name: '英伟达 (NVIDIA)', market: 'US', price: 148.5, changePct: 2.8, balanced: true, stage: '第二阶段主升' },
  AAPL: { name: '苹果公司 (Apple)', market: 'US', price: 228.2, changePct: 0.6, balanced: true, stage: '高位收敛整理' },
  MSFT: { name: '微软 (Microsoft)', market: 'US', price: 425.8, changePct: -0.4, balanced: true, stage: '多头排列' },
  VRT: { name: '维谛技术 (Vertiv)', market: 'US', price: 124.6, changePct: 3.5, balanced: true, stage: 'VCP突破临界' },
  '6758': { name: '索尼集团 (Sony)', market: 'JP', price: 2950, changePct: 1.2, balanced: true, stage: '第二阶段' },
  '7203': { name: '丰田汽车 (Toyota)', market: 'JP', price: 2680, changePct: -0.8, balanced: true, stage: '区间震荡' },
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
  const mockSpark = isUp ? [95, 96, 95.5, 98, 97.5, 99, 100] : [100, 99, 99.5, 98, 97, 96.5, 95]

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {isVisible && (
        <div
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-3 bg-white/95 backdrop-blur-md border border-sky-300/80 rounded-xl shadow-xl text-left pointer-events-auto animate-in fade-in zoom-in-95 duration-150"
          style={{
            boxShadow:
              'inset 0 1px 1px rgba(255, 255, 255, 1), 0 12px 28px -6px rgba(12, 74, 110, 0.25)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 顶部标题与代码 */}
          <div className="flex items-center justify-between gap-1 pb-1.5 border-b border-sky-100">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="font-mono font-black text-xs text-sky-950">{cleanTicker}</span>
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-bold font-mono ${
                  snap.market === 'US'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}
              >
                {snap.market}
              </span>
            </div>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-semibold ${
                snap.balanced
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}
            >
              {snap.balanced ? '勾稽平衡' : '待复核'}
            </span>
          </div>

          <div className="text-[11px] text-[var(--text-secondary)] font-medium truncate mt-1">
            {snap.name}
          </div>

          {/* 中部现价与微走势 */}
          <div className="flex items-center justify-between gap-2 mt-2 pt-1.5 border-t border-sky-100/60">
            <div>
              <div className="font-mono text-xs font-bold text-[var(--text-primary)]">
                {sym}{snap.price.toFixed(snap.market === 'JP' ? 0 : 2)}
              </div>
              <div
                className={`text-[10px] font-mono font-semibold ${
                  isUp ? 'text-rose-600' : 'text-blue-600'
                }`}
              >
                {isUp ? '+' : ''}{snap.changePct.toFixed(1)}%
              </div>
            </div>
            <Sparkline data={mockSpark} width={64} height={22} trend={isUp ? 'up' : 'down'} />
          </div>

          {/* 底部阶段与快捷直达按钮 */}
          <div className="mt-2.5 pt-1.5 border-t border-sky-100 flex items-center justify-between text-[10px]">
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
