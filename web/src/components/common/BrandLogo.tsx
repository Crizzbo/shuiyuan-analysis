import React from 'react'

export interface BrandLogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  variant?: 'sigil' | 'crest'
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
 * 「冰 · 火」专属品牌矢量徽标 (Frost & Flame Sigil)
 * 1. 冰（玄冰冷蓝）：基底沉着，晶莹坚韧，代表资本厚度、深度理性与防守护城河；
 * 2. 火（流光赤翎）：破冰凌霄，炽烈流火，代表向右上腾跃的 Alpha、VCP 临界突破与主升浪；
 * 3. 珠（极星火种）：耀世明珠，冰中蕴火，真知凝练。
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
        aria-label="水源分析终端 冰火徽标"
      >
        <defs>
          <linearGradient id="iceBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#082f49" />
            <stop offset="100%" stopColor="#031e33" />
          </linearGradient>
          <linearGradient id="iceWaterGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0284c7" />
            <stop offset="60%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#bae6fd" />
          </linearGradient>
          <linearGradient id="flamePhoenixGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#e11d48" />
            <stop offset="40%" stopColor="#f43f5e" />
            <stop offset="75%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#fef08a" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#iceBgGrad)" stroke="#0ea5e9" strokeWidth="1.5" />
        {/* 玄冰水纹 */}
        <path
          d="M14 36 C14 47 23 52 33 52 C44 52 50 45 49 39 C48 33 41 31 35 33 C27 36 22 31 22 25 C22 18 29 13 36 12 C25 13 14 23 14 36 Z"
          fill="url(#iceWaterGrad)"
        />
        {/* 炽炎火翎 */}
        <path
          d="M31 12 C36 18 43 20 47 25 C51 30 50 36 45 39 C41 41 37 39 38 35 C39 30 44 26 42 21 C40 17 35 14 31 12 Z"
          fill="url(#flamePhoenixGrad)"
        />
        <circle cx="33" cy="12" r="2.5" fill="#fef08a" />
        <circle cx="45" cy="27" r="1.5" fill="#ffffff" opacity="0.9" />
      </svg>
    )
  }

  // 默认方案：金石字图一体冰火印鉴 (Sigil)
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${sizeClass} ${className} shrink-0`}
      aria-label="水源分析终端 冰火徽标"
    >
      <defs>
        <radialGradient id="sigilIceBg" cx="30%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#075985" />
          <stop offset="50%" stopColor="#0c4a6e" />
          <stop offset="100%" stopColor="#082f49" />
        </radialGradient>
        <linearGradient id="phoenixEmberGrad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#dc2626" />
          <stop offset="40%" stopColor="#ea580c" />
          <stop offset="80%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#fef08a" />
        </linearGradient>
      </defs>

      {/* 玄冰晶壁外框 */}
      <rect width="64" height="64" rx="16" fill="url(#sigilIceBg)" stroke="#38bdf8" strokeWidth="1.2" />
      {showRing && (
        <circle cx="32" cy="32" r="26" stroke="#7dd3fc" strokeWidth="0.8" strokeDasharray="2 3" opacity="0.4" />
      )}

      {/* 水字主脊骨：玄冰晶柱 */}
      <path d="M32 15 V49" stroke="#ffffff" strokeWidth="4.2" strokeLinecap="round" />

      {/* 水字左折撇点：清泉玄冰浪纹 */}
      <path d="M21 27 C24 29 27 34 26 39" stroke="#38bdf8" strokeWidth="3.2" strokeLinecap="round" />
      <path d="M16 41 C20 41 24 38 27 35" stroke="#7dd3fc" strokeWidth="2.8" strokeLinecap="round" opacity="0.9" />

      {/* 水字右挑捺：破冰凌霄的赤金流火飞羽（向右上强劲腾飞） */}
      <path
        d="M34 26 C41 24 49 20 52 14 C51 22 47 31 38 38 C43 39 49 42 51 46"
        stroke="url(#phoenixEmberGrad)"
        strokeWidth="3.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* 凤眼真火明珠（右上极星） */}
      <circle cx="52" cy="14" r="2.8" fill="#fef08a" />
      <circle cx="52" cy="14" r="1.2" fill="#ffffff" />
    </svg>
  )
}
export default BrandLogo
