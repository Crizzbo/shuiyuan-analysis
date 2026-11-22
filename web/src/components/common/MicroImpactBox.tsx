import React from 'react';
import { formatEventCategory } from '../../utils/format';

interface MicroImpactBoxProps {
  impact?: string;
  category?: string;
  title?: string;
  style?: React.CSSProperties;
}

export const MicroImpactBox: React.FC<MicroImpactBoxProps> = ({
  impact,
  category,
  title = '核心研判与业务影响',
  style,
}) => {
  if (!impact) return null;
  const catLabel = formatEventCategory(category);

  return (
    <div
      style={style}
      className="mt-2 p-3 rounded-lg border-l-4 border-l-amber-500 bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-900/50 text-xs shadow-2xs"
    >
      <div className="flex items-center gap-1.5 text-amber-900 dark:text-amber-400 font-bold mb-1.5">
        <span>{title}</span>
        {catLabel && (
          <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-amber-100 dark:bg-amber-900/60 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            {catLabel}
          </span>
        )}
      </div>
      <div className="text-[var(--text-secondary)] dark:text-slate-200 text-xs leading-relaxed font-normal">
        {impact}
      </div>
    </div>
  );
};
