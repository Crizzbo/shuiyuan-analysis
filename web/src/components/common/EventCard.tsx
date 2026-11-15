import React from 'react';
import { SeverityBadge, VerificationBadge } from './StatusBadge';
import { EntityPills } from './EntityPills';
import { MicroImpactBox } from './MicroImpactBox';
import { TargetIcon, ShieldCheckIcon } from './Icons';
import { formatDeviceTime, toList, formatEventCategory, formatSourceName } from '../../utils/format';

export interface EventCardProps {
  id?: string;
  title: string;
  severity?: string;
  verification_status?: string;
  is_quarantined_rumor?: boolean;
  published_at?: string;
  source_name?: string;
  category?: string;
  micro_physical_impact?: string;
  involved_entities?: string | string[];
  affected_business_segments?: string | string[];
  is_distilled?: boolean;
  onClick?: () => void;
  onSelectTicker?: (ticker: string) => void;
  onViewRadarDetail?: () => void;
  compact?: boolean;
  className?: string;
}

export const EventCard: React.FC<EventCardProps> = ({
  title,
  severity,
  verification_status,
  is_quarantined_rumor,
  published_at,
  source_name,
  category,
  micro_physical_impact,
  involved_entities,
  affected_business_segments,
  is_distilled,
  onClick,
  onSelectTicker,
  onViewRadarDetail,
  compact = false,
  className = '',
}) => {
  const segments = toList(affected_business_segments);

  return (
    <div
      onClick={onClick}
      className={`bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/50 rounded-xl p-3.5 space-y-2 transition-all shadow-sm ${
        onClick ? 'cursor-pointer' : ''
      } ${className}`}
    >
      {/* 头部标题与徽章行 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <SeverityBadge level={severity} size={compact ? 'sm' : 'md'} />
          <h4 className="text-xs font-bold text-[var(--text-primary)] hover:text-[#3987e5] leading-snug truncate">
            {title}
          </h4>
          {(() => {
            const catLabel = formatEventCategory(category);
            return catLabel ? (
              <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[var(--surface-color)] text-[var(--text-secondary)] border border-[var(--border-color)] shrink-0">
                {catLabel}
              </span>
            ) : null;
          })()}
          {is_distilled && onViewRadarDetail && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onViewRadarDetail();
              }}
              className="text-[10px] px-2 py-0.2 rounded font-semibold bg-[#199e70]/15 hover:bg-[#199e70]/25 text-[#199e70] border border-[#199e70]/30 cursor-pointer transition-all flex items-center gap-1 shrink-0"
              title="查看权威事件雷达研判档案"
            >
              <TargetIcon className="w-3 h-3 text-[#199e70]" />
              <span>已提炼 (查看研判 →)</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {is_quarantined_rumor ? (
            <span className="text-[11px] px-2 py-0.5 rounded bg-[#d03b3b]/20 text-[#d03b3b] border border-[#d03b3b]/40 font-semibold flex items-center gap-1">
              <ShieldCheckIcon className="w-3 h-3 text-[#d03b3b]" />
              <span>传闻隔离</span>
            </span>
          ) : (
            <VerificationBadge status={verification_status} size={compact ? 'sm' : 'md'} />
          )}
          {published_at && (
            <span className="text-[10px] text-[var(--text-muted)] font-mono">
              {formatDeviceTime(published_at)}
            </span>
          )}
        </div>
      </div>

      {/* 微观物理与业务冲击传导 */}
      {micro_physical_impact && (
        <MicroImpactBox impact={micro_physical_impact} category={category} />
      )}

      {/* 关联主体与业务分部 */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          {source_name && (
            <span className="text-[var(--text-muted)]">
              信源: <span className="text-[var(--text-secondary)]">{formatSourceName(source_name)}</span>
            </span>
          )}
          <EntityPills entities={involved_entities} onSelectTicker={onSelectTicker} />
          {segments.length > 0 && (
            <div className="inline-flex flex-wrap items-center gap-1">
              {segments.slice(0, 3).map((seg, i) => (
                <span
                  key={`seg-${i}`}
                  className="px-1.5 py-0.2 rounded bg-[#199e70]/10 text-[#199e70] border border-[#199e70]/20 font-medium"
                >
                  📊 {seg}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
