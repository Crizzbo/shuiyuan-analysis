import React from 'react'

export interface BrandLogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  variant?: 'sigil' | 'crest' // sigil = 金石字图合一 (Scheme C), crest = 纯水凤双生徽章 (Scheme A)
  showRing?: boolean
}

const sizeMap = {
  xs: 'w-5 h-5',
  sm: 'w-7 h-7',
  md: 'w-9 h-9',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
}

/**
 * 「水 · 凤凰」专属品牌矢量徽标 (Water & Phoenix Brand Emblem)
 * 设计哲学：
 * 1. 水（深潭墨翠）：苍劲底骨，代表资本厚度、深度理性与防守护城河；
 * 2. 凤（赤金火翎）：右捺凌霄，代表向右上腾跃的 Alpha、VCP 临界突破与浴火新生；
 * 3. 珠（凤眼朝阳）：极星火种，凝练价值与真知。
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = 'md',
  className = '',
  variant = 'sigil',
  showRing = true,
}) => {
  const sizeClass = sizeMap[size] || sizeMap.md

  if (variant === 'crest') {
    return (
      <svg
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`${sizeClass} ${className} shrink-0`}
        aria-label="水源分析终端 水凤徽标"
      >
        <defs>
          <linearGradient id="wpBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#123d2f" />
            <stop offset="100%" stop-color="#0a231b" />
          </linearGradient>
          <linearGradient id="wpWaterGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#0d9488" />
            <stop offset="60%" stop-color="#10b981" />
            <stop offset="100%" stop-color="#6ee7b7" />
          </linearGradient>
          <linearGradient id="wpPhoenixGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#e11d48" />
            <stop offset="40%" stop-color="#f43f5e" />
            <stop offset="75%" stop-color="#f59e0b" />
            <stop offset="100%" stop-color="#fef08a" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#wpBgGrad)" stroke="#1d664e" strokeWidth="1.5" />
        {/* 水纹：深潭涌动 */}
        <path
          d="M14 36 C14 47 23 52 33 52 C44 52 50 45 49 39 C48 33 41 31 35 33 C27 36 22 31 22 25 C22 18 29 13 36 12 C25 13 14 23 14 36 Z"
          fill="url(#wpWaterGrad)"
        />
        {/* 凤翎：金赤腾飞 */}
        <path
          d="M31 12 C36 18 43 20 47 25 C51 30 50 36 45 39 C41 41 37 39 38 35 C39 30 44 26 42 21 C40 17 35 14 31 12 Z"
          fill="url(#wpPhoenixGrad)"
        />
        <circle cx="33" cy="12" r="2.5" fill="#fef08a" />
        <circle cx="45" cy="27" r="1.5" fill="#ffffff" opacity="0.9" />
      </svg>
    )
  }

  // 默认方案：金石字图一体印鉴 (Sigil)
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${sizeClass} ${className} shrink-0`}
      aria-label="水源分析终端 水凤徽标"
    >
      <defs>
        <radialGradient id="sigilBg" cx="30%" cy="30%" r="70%">
          <stop offset="0%" stop-color="#1a684f" />
          <stop offset="60%" stop-color="#124937" />
          <stop offset="100%" stop-color="#09261c" />
        </radialGradient>
        <linearGradient id="phoenixEmber" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#e11d48" />
          <stop offset="45%" stop-color="#f43f5e" />
          <stop offset="80%" stop-color="#f59e0b" />
          <stop offset="100%" stop-color="#fef08a" />
        </linearGradient>
      </defs>

      {/* 墨翠玉璧外框 */}
      <rect width="64" height="64" rx="15" fill="url(#sigilBg)" stroke="#237d5f" strokeWidth="1.2" />
      {showRing && (
        <circle cx="32" cy="32" r="26" stroke="#2dd4bf" strokeWidth="0.8" strokeDasharray="2 3" opacity="0.35" />
      )}

      {/* 水字主脊骨：垂瀑挺拔 */}
      <path d="M32 15 V49" stroke="#ffffff" strokeWidth="4.2" strokeLinecap="round" />

      {/* 水字左折撇点：碧玉清泉波纹 */}
      <path d="M21 27 C24 29 27 34 26 39" stroke="#5eead4" strokeWidth="3.2" strokeLinecap="round" />
      <path d="M16 41 C20 41 24 38 27 35" stroke="#2dd4bf" strokeWidth="2.8" strokeLinecap="round" opacity="0.9" />

      {/* 水字右挑捺：振翅凌霄的赤金凤翎飞羽（向右上强劲上扬） */}
      <path
        d="M34 26 C41 24 49 20 52 14 C51 22 47 31 38 38 C43 39 49 42 51 46"
        stroke="url(#phoenixEmber)"
        strokeWidth="3.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* 凤眼真火余烬（右上极星） */}
      <circle cx="52" cy="14" r="2.8" fill="#fef08a" />
      <circle cx="52" cy="14" r="1.2" fill="#ffffff" />
    </svg>
  )
}
