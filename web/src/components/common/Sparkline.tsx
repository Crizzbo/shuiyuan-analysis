import React, { useMemo } from 'react'

export interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
  trend?: 'up' | 'down' | 'neutral'
  showAnchor?: boolean
  strokeWidth?: number
}

/**
 * 0-Dependency 纯轻量 SVG 趋势微折线图 (Lightweight Sparkline)
 * 遵循 pstack 极简原则，纯数学几何拟合，支持上涨赤火与下跌冰蓝微光流光
 */
export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 120,
  height = 32,
  className = '',
  trend,
  showAnchor = true,
  strokeWidth = 2,
}) => {
  const points = useMemo(() => {
    if (!data || data.length < 2) return null

    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    const padding = 3

    const innerWidth = width - padding * 2
    const innerHeight = height - padding * 2

    const coords = data.map((val, idx) => {
      const x = padding + (idx / (data.length - 1)) * innerWidth
      const y = padding + (1 - (val - min) / range) * innerHeight
      return { x, y }
    })

    // 构造 SVG 折线路径
    const pathD = coords.reduce((acc, pt, i) => {
      return i === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`
    }, '')

    // 构造渐变闭合区域路径
    const lastX = coords[coords.length - 1].x
    const firstX = coords[0].x
    const bottomY = height
    const areaD = `${pathD} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`

    return {
      coords,
      pathD,
      areaD,
      lastPt: coords[coords.length - 1],
    }
  }, [data, width, height])

  if (!points) {
    return <div className={`h-[${height}px] w-[${width}px] bg-slate-100/50 rounded`} />
  }

  // 判断走势方向 (首尾对比)
  const isUp = trend ? trend === 'up' : data[data.length - 1] >= data[0]
  const strokeColor = isUp ? '#dc2626' : '#2563eb' // 红涨蓝跌
  const gradientId = `spark-grad-${isUp ? 'up' : 'down'}-${width}-${height}`

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={`overflow-visible shrink-0 ${className}`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.28" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
        </linearGradient>
      </defs>

      {/* 渐变微光面积填充 */}
      <path d={points.areaD} fill={`url(#${gradientId})`} />

      {/* 核心走势平滑折线 */}
      <path
        d={points.pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* 尾部最新价格锚点与脉冲光圈 */}
      {showAnchor && (
        <g transform={`translate(${points.lastPt.x}, ${points.lastPt.y})`}>
          <circle r="4" fill={strokeColor} opacity="0.25" className="animate-ping" />
          <circle r="2.5" fill={strokeColor} />
          <circle r="1.2" fill="#ffffff" />
        </g>
      )}
    </svg>
  )
}
