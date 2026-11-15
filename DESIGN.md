# 水源分析终端设计系统规范 (DESIGN.md)
> **设计哲学：水蕴深潭，凤鸣朝阳 (The Water & Phoenix Design System)**  
> 遵循 **Impeccable** 工业级前端设计标准，根除 AI 模板感（AI Slop），建立兼具东方深邃哲思与现代买方量化终端严谨美学的专业设计语言。

---

## 1. 核心意象与设计哲学 (The Core Metaphor)

在专业金融量化投资中，决策需要极度的理性沉潜与敏锐的破局生机：

- **水 (Water / 泉深润物)**：
  - **金融内涵**：流动性 (Liquidity)、深层底蕴、客观严谨、安全边际、深水吸筹与价值深潜。
  - **色彩表征**：
    - **沧澜墨翠 (Abyssal Jade)**：主基调与交互主轴 (`#176249` / `#0e3a2f`)，象征沉稳厚重的价值底座。
    - **微澜水面 (Mist Surface)**：页面基底色 (`#f4f7f5`) 与卡片表面 (`#ffffff`)，透亮温润，避免刺眼惨白。
    - **寒潭清冽 (Glacial Blue / 蓝表示下跌)**：安全边际、折价、底部蓄势、防守区间 (`#2563eb` / `#1d4ed8`，背景浅蓝 `#eff6ff`)。

- **凤凰 (Phoenix / 浴火振翅)**：
  - **金融内涵**：困境反转 (Turnaround)、主升浪突破、成长蜕变、Alpha 爆发。
  - **色彩表征**：
    - **凤羽朱砂 (Phoenix Crimson / 红表示上涨)**：行情上涨、估值溢价、买点爆发、多头能量 (`#dc2626` / `#b91c1c`，背景浅红 `#fef2f2`)。
    - **凤翎赤金 (Auric Gold)**：顶层决断、关键里程碑、星标高光 (`#b45309` / `#d97706`，背景暖金 `#fffbeb`)。
    - **羽墨沉青 (Feather Obsidian)**：排版文字主色 (`#111d18`)，高对比、易辨识、阅读舒适。

---

## 2. 调色板与语义 Token (Semantic Tokens)

### 2.1 基础色彩表 (Palette)

```css
:root {
  /* ========================================================================= */
  /* 水 (Water) 主题基调与界面系统 */
  /* ========================================================================= */
  --water-deep: #0e3a2f;           /* 沉水墨绿，顶层深色底 */
  --water-primary: #176249;        /* 沧澜碧翠，品牌主要操作与聚焦态 */
  --water-primary-hover: #124e3a;  /* 墨翠悬浮态 */
  --water-surface: #ffffff;        /* 容器纯白表面 */
  --water-surface-subtle: #f8faf9; /* 轻微次层背景 */
  --water-bg: #f4f7f5;             /* 全局水汽雾白底色 */
  --water-line: #d5e2da;           /* 柔和水纹分割线 */
  --water-line-focus: #176249;     /* 激活边框 */

  /* ========================================================================= */
  /* 文字与油墨系统 (Feather & Ink) */
  /* ========================================================================= */
  --ink-title: #0f1a15;            /* 主标题与极深强调 */
  --ink-body: #23352c;             /* 正文内容 */
  --ink-secondary: #475b51;        /* 次级说明 */
  --ink-muted: #647a6f;            /* 辅助与时间戳 */

  /* ========================================================================= */
  /* 市场行情与动态语义 (股票统一红涨蓝跌) */
  /* ========================================================================= */
  /* 凤羽红：上涨 / 估值溢价 / 多头强势 */
  --phoenix-rise: #dc2626;
  --phoenix-rise-hover: #b91c1c;
  --phoenix-rise-bg: #fef2f2;
  --phoenix-rise-border: #fecaca;

  /* 寒潭蓝：下跌 / 估值折价 / 安全边际 */
  --water-depth: #2563eb;
  --water-depth-hover: #1d4ed8;
  --water-depth-bg: #eff6ff;
  --water-depth-border: #bfdbfe;

  /* 凤翎金：核心研判 / 关键触发 / 关注 */
  --phoenix-gold: #b45309;
  --phoenix-gold-bg: #fffbeb;
  --phoenix-gold-border: #fde68a;

  /* 稳态灰：平盘 / 中性跟踪 / 基准 */
  --neutral-steady: #475569;
  --neutral-steady-bg: #f1f5f9;
  --neutral-steady-border: #e2e8f0;
}
```

---

## 3. Impeccable 防劣化硬约束 (Anti-AI-Slop Rules)

1. **绝对禁止彩虹色散落 (No Rainbow Clutter)**：
   - 严禁无序使用紫色、青色、品红、荧光绿等无关色；
   - 全站严格收敛为：**水墨青绿（品牌基调）+ 凤羽赤红（上涨/溢价）+ 寒潭深蓝（下跌/安全边际）+ 沉静灰白（底色与线框）**。
2. **绝对禁止 AI 提示词与说教口号 (No AI Prompt Slop)**：
   - 杜绝“0-Token 纯本地物理计算”、“严禁机械打分”、“零大模型幻觉”、“单一事实来源 (SSOT)”等口号；
   - 转换为客观金融用语：“本地量化引擎实时计算”、“多情景估值区间”、“财务报表勾稽平衡核验”。
3. **数字排版严格等宽 (Tabular Numerals)**：
   - 所有股价、涨跌幅、估值倍数、DCF折现价、财务比率均使用等宽字体并开启表格数字模式：
     `font-mono font-variant-numeric: tabular-nums`，确保小数点与千分位对齐。
4. **导航纯文本高阶感 (Clean Text-Only Navigation)**：
   - 顶部主导航与模块锚点采用纯文本极简下划线与胶囊设计，去除多余 Emoji 或彩标，专注内容投研。
5. **层次分明的卡片与微交互 (Elevated Hierarchy)**：
   - 卡片背景以 `--water-surface` (#fff) 为主，边框使用 `--water-line` (#d5e2da)；
   - 悬浮态使用细腻过渡 `transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1)`，避免突兀位移。
