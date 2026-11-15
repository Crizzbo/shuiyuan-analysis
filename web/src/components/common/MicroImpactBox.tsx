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
  title = '💡 核心研判与影响',
  style,
}) => {
  if (!impact) return null;
  const catLabel = formatEventCategory(category);

  return (
    <div
      style={{
        marginTop: 8,
        padding: '8px 12px',
        background: 'rgba(255, 255, 255, 0.03)',
        borderRadius: 6,
        borderLeft: '3px solid #ff9800',
        fontSize: '0.82rem',
        ...style,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          color: '#ffb74d',
          fontWeight: 600,
          marginBottom: 4,
        }}
      >
        <span>{title}</span>
        {catLabel && (
          <span
            style={{
              fontSize: '0.72rem',
              padding: '1px 6px',
              background: 'rgba(255, 152, 0, 0.15)',
              borderRadius: 4,
            }}
          >
            {catLabel}
          </span>
        )}
      </div>
      <div style={{ color: '#ccc', lineHeight: 1.4 }}>{impact}</div>
    </div>
  );
};
