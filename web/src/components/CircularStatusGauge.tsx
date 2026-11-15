export interface CircularGaugeItem {
  id: string
  label: string
  valueText: string // e.g. "100%", "24/24", "0违规", "1,413条", "14.8k"
  percentage: number // 0 - 100
  statusText: string // e.g. "已达标", "100%平账", "有效验签", "全部覆盖"
  tone: 'good' | 'accent' | 'warning' | 'critical'
  subtext?: string
}

interface CircularStatusGaugeProps {
  item: CircularGaugeItem
  size?: number
}

export function CircularStatusGauge({ item, size = 56 }: CircularStatusGaugeProps) {
  const strokeWidth = 4.5
  const radius = (size - strokeWidth * 2) / 2
  const circumference = 2 * Math.PI * radius
  const clampedPct = Math.min(100, Math.max(0, item.percentage))
  const dashOffset = circumference * (1 - clampedPct / 100)

  // Tone colors following dataviz and project specifications
  const toneMap = {
    good: {
      stroke: '#176249',
      text: 'text-[#176249]',
      badgeBg: 'bg-[#176249]/15',
      badgeBorder: 'border-[#176249]/30',
      badgeText: 'text-[#176249]',
    },
    accent: {
      stroke: '#176249',
      text: 'text-[#176249]',
      badgeBg: 'bg-[#176249]/10',
      badgeBorder: 'border-[#176249]/25',
      badgeText: 'text-[#176249]',
    },
    warning: {
      stroke: '#d97706',
      text: 'text-amber-600',
      badgeBg: 'bg-amber-50',
      badgeBorder: 'border-amber-200',
      badgeText: 'text-amber-700',
    },
    critical: {
      stroke: '#e11d48',
      text: 'text-rose-600',
      badgeBg: 'bg-rose-50',
      badgeBorder: 'border-rose-200',
      badgeText: 'text-rose-700',
    },
  }

  const currentTone = toneMap[item.tone] || toneMap.accent

  return (
    <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-3 flex flex-col items-center justify-between hover:border-slate-300 transition-all shadow-sm">
      {/* 顶部标签 */}
      <div className="text-[11px] font-semibold text-[var(--text-secondary)] text-center truncate w-full mb-1">
        {item.label}
      </div>

      {/* 圆形进度图 (SVG Donut Ring) */}
      <div className="relative my-1 flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* 背景底环 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            className="text-[var(--border-color)] opacity-40"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* 进度前景色环 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={currentTone.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* 中心紧凑数值与状态 */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className={`text-[11px] font-extrabold font-mono leading-none ${currentTone.text}`}>
            {item.valueText}
          </span>
        </div>
      </div>

      {/* 底部紧凑状态胶囊 */}
      <div className="mt-1 flex flex-col items-center gap-0.5 w-full">
        <span
          className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${currentTone.badgeBg} ${currentTone.badgeBorder} ${currentTone.badgeText} leading-none`}
        >
          {item.statusText}
        </span>
        {item.subtext && (
          <span className="text-[9px] text-[var(--text-muted)] font-mono truncate max-w-full">
            {item.subtext}
          </span>
        )}
      </div>
    </div>
  )
}
