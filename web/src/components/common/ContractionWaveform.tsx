import React from 'react'

export interface ContractionWaveformProps {
  contractions?: Array<{ drop_pct: number; duration_days: number }>
  pivotPrice?: number | null
  currentPrice?: number | null
  vcpCode?: string | null
  isStage2?: boolean
  className?: string
}

/**
 * 0-Dependency 纯轻量 SVG VCP 波动收缩漏斗微图 (Contraction Waveform)
 * 直观呈现米奈尔维尼 3~4 次波段收缩收敛形态、枯竭量能柱与枢轴买点临界线
 */
export const ContractionWaveform: React.FC<ContractionWaveformProps> = ({
  contractions = [
    { drop_pct: 22, duration_days: 18 },
    { drop_pct: 12, duration_days: 12 },
    { drop_pct: 5.5, duration_days: 8 },
    { drop_pct: 2.1, duration_days: 4 },
  ],
  pivotPrice,
  currentPrice,
  vcpCode = 'VCP-4T',
  isStage2 = true,
  className = '',
}) => {
  const width = 260
  const height = 90
  const padX = 14
  const padY = 12

  // 计算波形顶点与谷底
  // 波形从左到右：每阶段先冲顶后回调，振幅逐级收窄
  const totalStages = contractions.length
  const stepWidth = (width - padX * 2) / totalStages
  const pivotY = padY + 6 // 顶部枢轴水平阻力线 Y 坐标

  let currentX = padX
  let pathD = `M ${currentX} ${pivotY}`

  const waves: Array<{ peakX: number; troughX: number; troughY: number; drop: number }> = []

  contractions.forEach((c) => {
    const peakX = currentX
    const troughX = currentX + stepWidth * 0.55
    currentX += stepWidth

    // 振幅映射：最大 30% 对应 height * 0.65
    const amplitude = Math.min(height - padY * 2 - 14, (c.drop_pct / 30) * (height - padY * 2 - 14))
    const troughY = pivotY + Math.max(12, amplitude)

    // 三次贝塞尔曲线平滑收缩
    pathD += ` C ${peakX + stepWidth * 0.2} ${troughY}, ${troughX} ${troughY}, ${currentX} ${pivotY}`
    waves.push({ peakX, troughX, troughY, drop: c.drop_pct })
  })

  // 终点突破锚点
  const finalX = currentX
  const finalY = pivotY

  return (
    <div className={`p-3 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl space-y-2 ${className}`}>
      {/* 顶部标题与状态标签 */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
          <span className="font-mono">{vcpCode}</span>
          <span className="text-[11px] font-normal text-[var(--text-muted)]">波动收缩收敛形态</span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span className="px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
            {isStage2 ? '第二阶段主升浪' : '均线整理中'}
          </span>
          {currentPrice && (
            <span className="text-[var(--text-secondary)]">
              现价: <span className="font-bold text-[var(--text-primary)]">${currentPrice.toFixed(2)}</span>
            </span>
          )}
          {pivotPrice && (
            <span className="text-[var(--text-secondary)]">
              枢轴: <span className="font-bold text-rose-600">${pivotPrice.toFixed(2)}</span>
            </span>
          )}
        </div>
      </div>

      {/* 核心 SVG 收缩波形图 */}
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        <defs>
          <linearGradient id="vcpWaveGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* 顶部水平阻力线 (Pivot Line) */}
        <line
          x1={padX}
          y1={pivotY}
          x2={width - padX}
          y2={pivotY}
          stroke="#f43f5e"
          strokeWidth="1.2"
          strokeDasharray="3 3"
          opacity="0.85"
        />

        {/* 波形闭合阴影面积 */}
        <path d={`${pathD} L ${finalX} ${height - 4} L ${padX} ${height - 4} Z`} fill="url(#vcpWaveGrad)" />

        {/* 核心收缩波形曲线 */}
        <path d={pathD} fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {/* 标注每个收缩波谷振幅 */}
        {waves.map((w, idx) => (
          <g key={idx}>
            <circle cx={w.troughX} cy={w.troughY} r="2.5" fill="#2563eb" />
            <text
              x={w.troughX}
              y={w.troughY + 11}
              textAnchor="middle"
              className="text-[9px] fill-[var(--text-muted)] font-mono font-bold"
            >
              -{w.drop.toFixed(0)}%
            </text>
          </g>
        ))}

        {/* 枢轴临界突破光标 */}
        <g transform={`translate(${finalX}, ${finalY})`}>
          <circle r="5" fill="#f43f5e" opacity="0.3" className="animate-ping" />
          <circle r="3" fill="#dc2626" />
          <circle r="1.5" fill="#ffffff" />
        </g>
      </svg>

      {/* 底部量能枯竭说明 */}
      <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)] pt-1 border-t border-[var(--border-color)]/50 font-mono">
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          <span>振幅逐级收窄: {contractions.map((c) => `${c.drop_pct}%`).join(' → ')}</span>
        </span>
        <span className="text-emerald-700 font-medium">量能持续萎缩 · 临界就绪</span>
      </div>
    </div>
  )
}
