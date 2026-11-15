import { useState, useEffect } from 'react'
import type { SettingsData } from '../types/api'
import { api } from '../services/api'
import { BrandLogo } from './common/BrandLogo'

export function SettingsTab() {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(true)

  const loadSettings = async () => {
    try {
      setLoading(true)
      const res = await api.getSettings()
      if (res.ok) {
        setSettings(res.data)
      }
    } catch (err) {
      console.error('Failed to load settings:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  if (loading && !settings) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-[#176249] border-t-transparent rounded-full animate-spin" />
          <div className="text-xs text-[var(--text-muted)]">加载系统配置与账本验签状态...</div>
        </div>
      </div>
    )
  }

  const arch = settings?.architecture_policy
  const ledger = settings?.prediction_ledger
  const env = settings?.environment_discovery
  const lifecycle = settings?.lifecycle_policy

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-6">
      {/* 顶部标题与功能说明 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-[var(--text-primary)]">
            投研合规与系统设置
          </h2>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
            全链路健康
          </span>
        </div>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
          监控数据准入合规准则、决策轨迹防伪溯源及数据存储生命周期。
        </p>
      </div>

      {/* 水·凤凰 品牌视觉与设计体系规范 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3.5">
            <BrandLogo size="lg" className="rounded-xl shadow-xs" />
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <span>「水 · 凤凰」视觉设计与品牌体系</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#176249]/10 text-[#176249] border border-[#176249]/20 font-medium">
                  Impeccable 设计系统
                </span>
              </h3>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                水蕴深潭（理智防守、资本厚度）与 凤鸣朝阳（价值重估、破局飞升）的设计哲学
              </p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 text-xs">
          <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)] space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#176249]" />
              <span className="font-bold text-[var(--text-primary)]">深潭墨翠 (#176249)</span>
            </div>
            <p className="text-[var(--text-muted)] text-[11px] leading-relaxed">
              象征理智基底、充足资本储备与深厚护城河，承载核心架构、品牌主色与基准线。
            </p>
          </div>
          <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)] space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gradient-to-r from-amber-500 to-rose-500" />
              <span className="font-bold text-[var(--text-primary)]">凤翎赤金 (Amber & Rose)</span>
            </div>
            <p className="text-[var(--text-muted)] text-[11px] leading-relaxed">
              徽标右捺化为振翅高翔的赤金飞羽，象征 VCP 临界突破、Alpha 跃迁与浴火新生。
            </p>
          </div>
          <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)] space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-slate-100 border border-slate-300" />
              <span className="font-bold text-[var(--text-primary)]">凝霜玉阶 (Clean White/Slate)</span>
            </div>
            <p className="text-[var(--text-muted)] text-[11px] leading-relaxed">
              现代机构级高清晰度排版底色，无杂色干扰，数据图表一目了然。
            </p>
          </div>
        </div>
      </div>

      {/* 架构合规与账本验签 (三层结构化：状态、信息、说明) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. 投研风控与数据合规准则 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          {/* 状态层 */}
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              投研风控与数据合规准则
            </h3>
            <span className="text-xs px-2 py-0.5 rounded bg-[#176249]/10 text-[#176249] border border-[#176249]/25 font-semibold">
              合规运行中
            </span>
          </div>

          {/* 信息层 */}
          <div className="bg-[var(--bg-card)] rounded-lg p-3.5 text-xs space-y-2.5 border border-[var(--border-color)]/60">
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">数据准入机制:</span>
              <span className="text-[var(--text-primary)] font-semibold">单向流动 (官方原始财报 → 量化核验 → 决策看板)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">模型计算机制:</span>
              <span className="text-[#176249] font-semibold">本地量化计算引擎</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">投研决策输出:</span>
              <span className="text-[var(--text-primary)] font-semibold">多阶段现金流折现与估值区间</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">行情时效控制:</span>
              <span className="text-[var(--text-primary)] font-semibold">盘前/盘中时段动态门禁 ({arch?.quote_max_staleness_hours || 24}h)</span>
            </div>
          </div>

          {/* 说明层 */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-[var(--text-secondary)] leading-relaxed">
            <span className="font-semibold text-slate-800">准则说明: </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              系统遵循严谨的金融量化分析准则，依托官方原始财报与多阶段现金流折现 (DCF) 模型进行估值推演。
            </span>
          </div>
        </div>

        {/* 2. 决策轨迹与复盘溯源账本 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          {/* 状态层 */}
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              决策轨迹与复盘溯源账本
            </h3>
            <span
              className={`text-xs px-2 py-0.5 rounded font-semibold ${
                ledger?.integrity_valid
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}
            >
              {ledger?.integrity_valid ? '防伪审计有效' : '验签异常'}
            </span>
          </div>

          {/* 信息层 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]">
              <div className="text-xs text-[var(--text-muted)]">累计投研决策点位</div>
              <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-1">
                {ledger?.total_predictions.toLocaleString()} 条
              </div>
            </div>
            <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]">
              <div className="text-xs text-[var(--text-muted)]">覆盖资产标的</div>
              <div className="text-2xl font-bold font-mono text-[#176249] mt-1">
                {ledger?.unique_tickers} 家
              </div>
            </div>
          </div>

          <div className="text-xs text-[var(--text-muted)] flex items-center justify-between px-1">
            <span>实盘跟踪记录: <strong className="text-[var(--text-primary)] font-mono">{ledger?.total_outcomes} 条</strong></span>
            <span>复盘分析归档: <strong className="text-[var(--text-primary)] font-mono">{ledger?.total_reviews} 次</strong></span>
          </div>

          {/* 说明层 */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)]/60 rounded-lg p-3 text-xs text-[var(--text-secondary)] leading-relaxed">
            <span className="font-semibold text-[var(--text-primary)]">溯源保障: </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              每一笔投研推演的悲观底价、中性公允价值与目标靶心均永久记录时间戳，确保历史决策轨迹真实不可逆，支持全生命周期复盘对账。
            </span>
          </div>
        </div>
      </div>

      {/* 环境发现与生命周期策略 (两栏卡片) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 宿主环境连接 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              外部连接与数据源状态
            </h3>
            <span className="text-xs text-[var(--text-muted)]">动态探测</span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">行情数据同步接口:</span>
              <span className={`font-mono font-semibold ${env?.gdrive_detected ? 'text-[#176249]' : 'text-gray-400'}`}>
                {env?.gdrive_detected ? '已连接 (行情专有表)' : '未连接'}
              </span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">官方监管披露核验:</span>
              <span className={`font-mono font-semibold ${env?.edge_detected ? 'text-[#176249]' : 'text-gray-400'}`}>
                {env?.edge_detected ? '已就绪 (SEC / 东证 / 美联储)' : '未就绪'}
              </span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">本地投研计算引擎:</span>
              <span className="font-mono text-[11px] text-[#176249] font-semibold">
                {env?.python_executable ? '已就绪 (本地隔离运行)' : '默认环境就绪'}
              </span>
            </div>
          </div>
        </div>

        {/* 数据分层生命周期规则 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              数据存储与归档周期
            </h3>
            <span className="text-xs text-[var(--text-muted)]">自动归档</span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">动态盘中数据:</span>
              <span className="font-mono font-semibold text-[#176249]">{lifecycle?.hot_quote_max_age_days || 30} 天 (高频动态计算)</span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">历史财务数据:</span>
              <span className="font-mono font-semibold text-amber-700">{lifecycle?.warm_quote_max_age_days || 1095} 天 (3年财报全息归档)</span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">长周期历史归档:</span>
              <span className="font-mono font-semibold text-slate-700">自动化离线压缩归档</span>
            </div>
          </div>
        </div>
      </div>

      {/* 业务服务模块健康状态矩阵 (三层结构化：状态、信息、说明) */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
          <div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              核心投研服务模块运行状态
            </h3>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              已接入的模块和当前数据条件。
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded bg-[#176249]/10 text-[#176249] border border-[#176249]/25 font-medium">
            {settings ? '配置已读取' : '配置读取失败'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { name: '行情时效与完备度核验', desc: '按报价时间和市场时段检查本地归档', status: '按报价核验' },
            { name: '全市场趋势形态初筛', desc: '正式初筛依赖可验证的历史日线价量', status: '等待 OHLCV' },
            { name: '权威事件雷达', desc: '检索本地事件档案和传闻隔离记录', status: '本地档案' },
            { name: '企业基本面与情景估值', desc: '查看个股档案或在计算器中输入假设', status: '按证据计算' },
            { name: '任务调度控制台', desc: '在采集中心查看任务计划、进度和归档回执', status: '见任务页' },
            { name: '预测账本', desc: '校验预测记录的哈希链条', status: ledger?.integrity_valid ? '验签通过' : '待核验' },
          ].map((svc) => (
            <div key={svc.name} className="bg-[var(--bg-card)] border border-[var(--border-color)]/60 rounded-lg p-3.5 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-[var(--text-primary)]">{svc.name}</span>
                <span className="text-[11px] px-2 py-0.5 rounded bg-[#176249]/10 text-[#176249] border border-[#176249]/25 shrink-0 font-medium">
                  {svc.status}
                </span>
              </div>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">{svc.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
export default SettingsTab
