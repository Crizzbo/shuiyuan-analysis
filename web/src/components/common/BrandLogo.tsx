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
 * 水源分析终端「冰魄烈焰战牛」品牌矢量徽标 (Frost-Fire Bull Sigil)
 * 1. 动物形态：昂首向右上蓄势强攻的战牛 (Bull)，象征突破、成长与主升浪 Alpha；
 * 2. 玄冰战甲：面部与身躯由晶莹剔透的多面体玄冰切面雕琢而成，坚实沉稳，构筑理性护城河；
 * 3. 破天烈焰：双角与鬃脊破冰化火，呈现炽烈流动的液态火翎与赤金真火；
 * 4. 冰下地火：胸腔深处暗藏沉睡流动的琥珀地火暖核，冰中蕴热，刚柔并济。
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = 'md',
  className = '',
}) => {
  const sizeClass = sizeMap[size] || sizeMap.md

  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${sizeClass} ${className} shrink-0`}
      aria-label="水源分析终端 冰魄烈焰战牛徽标"
    >
      <defs>
        {/* 背景渐变 (深邃极地冰海) */}
        <radialGradient id="bullBgGrad" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#0a4b70" />
          <stop offset="50%" stopColor="#082f49" />
          <stop offset="100%" stopColor="#031826" />
        </radialGradient>

        {/* 烈焰主犄角渐变 (自玄冰拔节，升华至炽烈赤金真火) */}
        <linearGradient id="hornFlamePrimary" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#0284c7" />
          <stop offset="25%" stopColor="#ea580c" />
          <stop offset="60%" stopColor="#dc2626" />
          <stop offset="85%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#fef08a" />
        </linearGradient>

        {/* 远侧犄角渐变 (深邃暗火景深) */}
        <linearGradient id="hornFlameSecondary" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#0369a1" />
          <stop offset="40%" stopColor="#b91c1c" />
          <stop offset="80%" stopColor="#ea580c" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>

        {/* 烈焰鬃毛渐变 (流火飞翎) */}
        <linearGradient id="maneFlameGrad" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#fef08a" />
          <stop offset="30%" stopColor="#f59e0b" />
          <stop offset="70%" stopColor="#ea580c" />
          <stop offset="100%" stopColor="#dc2626" />
        </linearGradient>

        {/* 冰下地火暗核 (沉睡流动的能量内核) */}
        <radialGradient id="heartCoreGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fef08a" stopOpacity="0.95" />
          <stop offset="35%" stopColor="#f59e0b" stopOpacity="0.8" />
          <stop offset="70%" stopColor="#dc2626" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#0284c7" stopOpacity="0" />
        </radialGradient>

        {/* 玄冰高光切面 */}
        <linearGradient id="iceHighlightGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#bae6fd" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.1" />
        </linearGradient>
      </defs>

      {/* 1. 玄冰外框徽章底座 */}
      <rect width="64" height="64" rx="16" fill="url(#bullBgGrad)" stroke="#38bdf8" strokeWidth="1.4" />
      <rect x="2" y="2" width="60" height="60" rx="14" stroke="url(#iceHighlightGrad)" strokeWidth="1" opacity="0.6" />

      {/* 背景冰棱辅助几何暗纹 */}
      <path d="M10 54 L20 40 L12 28 Z" fill="#0284c7" opacity="0.15" />
      <path d="M50 56 L58 42 L48 36 Z" fill="#38bdf8" opacity="0.1" />

      {/* 2. 远侧犄角 (破冰冲天，向右上延展) */}
      <path d="M 26 23 C 28 14 34 9 46 7 C 40 12 34 18 31 25 Z" fill="url(#hornFlameSecondary)" opacity="0.9" />

      {/* 3. 烈焰鬃毛 (沿颈部向左后方猎猎飞扬，传递冲锋动能) */}
      <path d="M 24 28 C 18 20 12 22 7 27 C 12 26 18 28 22 32 Z" fill="url(#maneFlameGrad)" />
      <path d="M 19 33 C 13 27 7 30 3 36 C 8 34 14 35 17 38 Z" fill="url(#maneFlameGrad)" opacity="0.9" />
      <path d="M 14 39 C 9 35 5 38 2 44 C 6 41 10 42 13 44 Z" fill="url(#maneFlameGrad)" opacity="0.75" />

      {/* 4. 冰下沉睡地火之心 (透过胸甲散发温润暗火) */}
      <circle cx="24" cy="42" r="9" fill="url(#heartCoreGrad)" />

      {/* 5. 战牛身躯与肩颈 (玄冰切面甲胄，刚劲雄浑) */}
      {/* 颈背主冰甲 */}
      <polygon points="14,44 23,28 30,36 20,49" fill="#0369a1" stroke="#38bdf8" strokeWidth="0.8" strokeLinejoin="round" />
      {/* 前胸坚冰 */}
      <polygon points="20,49 30,36 36,46 25,56" fill="#0284c7" opacity="0.85" stroke="#7dd3fc" strokeWidth="0.8" strokeLinejoin="round" />
      {/* 胸肋下缘沉底 */}
      <polygon points="14,44 20,49 25,56 16,56" fill="#075985" stroke="#0284c7" strokeWidth="0.6" strokeLinejoin="round" />

      {/* 6. 近侧主犄角 (破冰化火！自额头拔地而起，直挑九天) */}
      <path d="M 33 27 C 36 17 44 10 56 6 C 49 14 42 22 38 31 C 35 30 33 28 33 27 Z" fill="url(#hornFlamePrimary)" />
      {/* 犄角流光棱线 */}
      <path d="M 34 27 C 38 18 45 12 56 6" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
      {/* 角尖真火炽焰明珠 */}
      <circle cx="56" cy="6" r="2.2" fill="#fef08a" />
      <circle cx="56" cy="6" r="1" fill="#ffffff" />

      {/* 7. 牛首面部 (玄冰立体切割，冷峻果决) */}
      {/* 额头冰棱 (与犄角连接处) */}
      <polygon points="28,26 37,29 36,36 26,32" fill="#38bdf8" stroke="#bae6fd" strokeWidth="0.8" strokeLinejoin="round" />
      {/* 鼻梁主棱面 (强劲俯冲角度) */}
      <polygon points="36,36 46,42 43,49 34,44" fill="#7dd3fc" stroke="#ffffff" strokeWidth="0.9" strokeLinejoin="round" />
      {/* 口鼻吻端 (沉实坚毅) */}
      <polygon points="46,42 51,45 48,51 43,49" fill="#0284c7" stroke="#38bdf8" strokeWidth="0.8" strokeLinejoin="round" />
      {/* 下颌与咽喉 */}
      <polygon points="34,44 43,49 39,55 31,48" fill="#0369a1" stroke="#0284c7" strokeWidth="0.8" strokeLinejoin="round" />

      {/* 8. 神牛极星之目 (锐利如炬，坚定洞悉) */}
      <polygon points="32,34 35,31 38,34 35,36" fill="#fef08a" />
      <polygon points="33.5,33.5 35,32 36.5,33.5 35,34.5" fill="#ffffff" />
      <circle cx="35" cy="33.5" r="0.8" fill="#dc2626" />

      {/* 9. 鼻息微火暗流 (生命力与力量感) */}
      <path d="M 49 49 C 52 50 54 53 53 55 C 51 54 50 52 48 50 Z" fill="#f59e0b" opacity="0.85" />
    </svg>
  )
}

export default BrandLogo
