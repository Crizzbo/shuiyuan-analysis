import React from 'react';
import { cleanEntityList } from '../../utils/format';
import { TickerHoverCard } from './TickerHoverCard';

interface EntityPillsProps {
  entities?: string | string[];
  max?: number;
  onSelectTicker?: (ticker: string) => void;
  style?: React.CSSProperties;
}

export const EntityPills: React.FC<EntityPillsProps> = ({ entities, max = 3, onSelectTicker, style }) => {
  const list = cleanEntityList(entities, max);
  if (!list || list.length === 0) return null;

  return (
    <div style={style} className="inline-flex flex-wrap gap-1.5 items-center">
      {list.map((ent, i) => (
        <TickerHoverCard key={i} ticker={ent} onSelectTicker={onSelectTicker}>
          <span
            onClick={(e) => {
              if (onSelectTicker) {
                e.stopPropagation();
                onSelectTicker(ent);
              }
            }}
            className={`text-[11px] font-semibold px-2 py-0.5 rounded border transition-all ${
              onSelectTicker
                ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 cursor-pointer shadow-2xs'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
            }`}
            title={onSelectTicker ? `在个股深度研报中穿透分析 ${ent}` : undefined}
          >
            {ent}
          </span>
        </TickerHoverCard>
      ))}
    </div>
  );
};
