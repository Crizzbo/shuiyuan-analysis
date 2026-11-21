import React from 'react'

export interface SkeletonProps {
  className?: string
  variant?: 'text' | 'rect' | 'circle'
  width?: string | number
  height?: string | number
}

/**
 * 具有玄冰流动微光质感的骨架屏占位组件 (Ice-Flow Shimmer Skeleton)
 * 遵循 pstack principle-experience-first 准则，杜绝因异步加载引起的布局抖动 (CLS)
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rect',
  width,
  height,
}) => {
  const variantClass =
    variant === 'circle'
      ? 'rounded-full'
      : variant === 'text'
      ? 'rounded-md h-4 my-1'
      : 'rounded-xl'

  const style: React.CSSProperties = {
    width: width !== undefined ? width : undefined,
    height: height !== undefined ? height : undefined,
  }

  return (
    <div
      style={style}
      className={`relative overflow-hidden bg-sky-200/40 border border-sky-300/30 ${variantClass} ${className}`}
      aria-hidden="true"
    >
      <div
        className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_infinite] bg-gradient-to-r from-transparent via-white/50 to-transparent"
        style={{
          background: 'linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.6) 50%, transparent 100%)',
        }}
      />
    </div>
  )
}

/** 预置列表加载骨架 */
export const CardListSkeleton: React.FC<{ count?: number; itemHeight?: string }> = ({
  count = 3,
  itemHeight = 'h-24',
}) => {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`p-4 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3 ${itemHeight}`}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 w-2/3">
              <Skeleton width="60px" height="20px" />
              <Skeleton width="65%" height="18px" />
            </div>
            <Skeleton width="70px" height="20px" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton width="120px" height="14px" />
            <Skeleton width="90px" height="14px" />
            <Skeleton width="80px" height="14px" />
          </div>
        </div>
      ))}
    </div>
  )
}
