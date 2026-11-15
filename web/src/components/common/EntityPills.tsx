import React from 'react';
import { cleanEntityList } from '../../utils/format';

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
    <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: 4, alignItems: 'center', ...style }}>
      {list.map((ent, i) => (
        <span
          key={i}
          onClick={(e) => {
            if (onSelectTicker) {
              e.stopPropagation();
              onSelectTicker(ent);
            }
          }}
          style={{
            fontSize: '0.72rem',
            padding: '1px 6px',
            background: 'rgba(76, 175, 80, 0.15)',
            color: '#81c784',
            borderRadius: 4,
            cursor: onSelectTicker ? 'pointer' : 'default',
            transition: 'all 0.15s ease',
          }}
          title={onSelectTicker ? `在个股分析中查看 ${ent}` : undefined}
        >
          {ent}
        </span>
      ))}
    </div>
  );
};
