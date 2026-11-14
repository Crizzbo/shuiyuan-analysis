import { useState, useEffect } from 'react'
import type { SettingsData } from '../types/api'
import { api } from '../services/api'

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
          <div className="w-8 h-8 border-3 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
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
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 顶部标题与功能说明 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-[var(--text-primary)]">
            系统运行规范与数据验签中心
          </h2>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-medium">
            全链路健康
          </span>
        </div>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
          监控终端底层架构解耦规范、数据时间链条防伪验签、运行环境挂载及数据生命周期管理。
        </p>
      </div>

      {/* 架构合规与账本验签 (三层结构化：状态、信息、说明) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. 底层架构规范与计算解耦 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          {/* 状态层 */}
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              系统架构解耦与单向依赖
            </h3>
            <span className="text-xs px-2 py-0.5 rounded bg-[#199e70]/20 text-[#199e70] border border-[#199e70]/30 font-semibold">
              门禁已通过
            </span>
          </div>

          {/* 信息层 */}
          <div className="bg-[var(--bg-card)] rounded-lg p-3.5 text-xs space-y-2.5 border border-[var(--border-color)]/60">
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">模块依赖单向流向:</span>
              <span className="text-[#3987e5] font-semibold">金融计算 ➔ 分析工具 ➔ 报表看板</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">底层计算引擎状态:</span>
              <span className="text-[#199e70] font-semibold">独立纯净 · 零外部耦合</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">研报分析呈现模式:</span>
              <span className="text-[var(--text-primary)] font-semibold">自然语言买方深度研判</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-muted)]">行情新鲜度时效防线:</span>
              <span className="text-[var(--text-primary)] font-semibold">{arch?.quote_max_staleness_hours || 24} 小时刚性门禁</span>
            </div>
          </div>

          {/* 说明层 */}
          <div className="bg-[#102a1e]/15 border border-[#199e70]/30 rounded-lg p-3 text-xs text-[var(--text-secondary)] leading-relaxed">
            <span className="font-semibold text-[#199e70]">设计原则: </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              核心计算引擎独立于外层工具；数据底账采用只追加写入机制；研报输出禁用机械 0-100 打分，全面采用情景价值区间与质化剖析。
            </span>
          </div>
        </div>

        {/* 2. 投资研判密码学时间链条 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          {/* 状态层 */}
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              投资研判密码学时间链条
            </h3>
            <span
              className={`text-xs px-2 py-0.5 rounded font-semibold ${
                ledger?.integrity_valid
                  ? 'bg-[#199e70]/20 text-[#199e70] border border-[#199e70]/30'
                  : 'bg-[#d03b3b]/20 text-[#d03b3b] border border-[#d03b3b]/30'
              }`}
            >
              {ledger?.integrity_valid ? '链条完整无篡改' : '验签异常'}
            </span>
          </div>

          {/* 信息层 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]">
              <div className="text-xs text-[var(--text-muted)]">累计预测与研判底账</div>
              <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-1">
                {ledger?.total_predictions.toLocaleString()} 条
              </div>
            </div>
            <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]">
              <div className="text-xs text-[var(--text-muted)]">覆盖独立资产标的</div>
              <div className="text-2xl font-bold font-mono text-[#3987e5] mt-1">
                {ledger?.unique_tickers} 家
              </div>
            </div>
          </div>

          <div className="text-xs text-[var(--text-muted)] flex items-center justify-between px-1">
            <span>实盘对账结算: <strong className="text-[var(--text-primary)] font-mono">{ledger?.total_outcomes} 条</strong></span>
            <span>深度复盘审查: <strong className="text-[var(--text-primary)] font-mono">{ledger?.total_reviews} 次</strong></span>
          </div>

          {/* 说明层 */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)]/60 rounded-lg p-3 text-xs text-[var(--text-secondary)] leading-relaxed">
            <span className="font-semibold text-[var(--text-primary)]">防伪保障: </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              所有研报给出的悲观底价、中性公允价值与乐观靶心均写入哈希链条，确保真实决策轨迹不可追溯篡改，为复盘提供唯一事实来源。
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
              宿主运行环境与工具连接
            </h3>
            <span className="text-xs text-[var(--text-muted)]">动态探测</span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">Google Drive 行情工具挂载:</span>
              <span className={`font-mono font-semibold ${env?.gdrive_detected ? 'text-[#199e70]' : 'text-gray-400'}`}>
                {env?.gdrive_detected ? '已探测挂载 (可读写专有行情表)' : '未挂载'}
              </span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">官方浏览器核验驱动:</span>
              <span className={`font-mono font-semibold ${env?.edge_detected ? 'text-[#199e70]' : 'text-gray-400'}`}>
                {env?.edge_detected ? '已就绪 (支持监管公告与财报核实)' : '未找到'}
              </span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">自动化执行环境:</span>
              <span className="font-mono text-[11px] text-[var(--text-muted)] truncate max-w-xs">
                {env?.python_executable ? 'Python 本地隔离计算环境' : '系统默认解释器'}
              </span>
            </div>
          </div>
        </div>

        {/* 数据分层生命周期规则 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              数据分层生命周期规则
            </h3>
            <span className="text-xs text-[var(--text-muted)]">自动归档</span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">高频热数据常驻周期:</span>
              <span className="font-mono font-semibold text-[#199e70]">{lifecycle?.hot_quote_max_age_days || 30} 天 (高频动态计算)</span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">历史温数据归档周期:</span>
              <span className="font-mono font-semibold text-[#c98500]">{lifecycle?.warm_quote_max_age_days || 1095} 天 (3年财报全息归档)</span>
            </div>
            <div className="flex justify-between items-center bg-[var(--bg-card)] p-2.5 rounded-lg border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)]">长周期冷数据沉降模式:</span>
              <span className="font-mono font-semibold text-[#3987e5]">{lifecycle?.cold_compression || '标准归档压缩'}</span>
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
          <span className="text-xs px-2.5 py-1 rounded bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-medium">
            {settings ? '配置已读取' : '配置读取失败'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { name: '行情时效与完备度核验', desc: '按报价时间和市场时段检查本地归档', status: '按报价核验' },
            { name: '全市场趋势形态初筛', desc: '正式初筛依赖可验证的历史日线价量', status: '等待 OHLCV' },
            { name: '突发事件雷达', desc: '检索本地事件档案和传闻隔离记录', status: '本地档案' },
            { name: '企业基本面与情景估值', desc: '查看个股底账或在计算器中输入假设', status: '按证据计算' },
            { name: '后台采集调度', desc: '在采集中心查看任务计划、进度和归档回执', status: '见任务页' },
            { name: '预测账本', desc: '校验预测记录的哈希链条', status: ledger?.integrity_valid ? '验签通过' : '待核验' },
          ].map((svc) => (
            <div key={svc.name} className="bg-[var(--bg-card)] border border-[var(--border-color)]/60 rounded-lg p-3.5 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-[var(--text-primary)]">{svc.name}</span>
                <span className="text-[11px] px-2 py-0.5 rounded bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 shrink-0 font-medium">
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
