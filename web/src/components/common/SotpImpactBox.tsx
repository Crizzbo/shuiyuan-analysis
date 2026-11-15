import React from 'react';
import type { SotpImpactData } from '../../types/api';

interface SotpImpactBoxProps {
  sotp?: SotpImpactData | null;
  style?: React.CSSProperties;
}

export const SotpImpactBox: React.FC<SotpImpactBoxProps> = ({ sotp, style }) => {
  if (!sotp) return null;

  return (
    <div
      style={{
        marginTop: 8,
        padding: '8px 12px',
        background: 'rgba(0, 188, 212, 0.05)',
        borderRadius: 6,
        borderLeft: '3px solid #00bcd4',
        fontSize: '0.82rem',
        ...style,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          color: '#4dd0e1',
          fontWeight: 600,
          marginBottom: 4,
        }}
      >
        <span>SOTP 业务分部因果敏感性穿透:</span>
        <span style={{ color: '#fff' }}>{sotp.penetration_level || '直接核心业务冲击'}</span>
      </div>
      {sotp.affected_segments && sotp.affected_segments.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 4 }}>
          {sotp.affected_segments.map((seg: any, si: number) => (
            <span
              key={si}
              style={{
                fontSize: '0.72rem',
                padding: '2px 8px',
                background: 'rgba(0, 188, 212, 0.15)',
                color: '#80deea',
                borderRadius: 4,
              }}
            >
              {typeof seg === 'string' ? seg : (seg.segment_name || seg.segment || JSON.stringify(seg))}
            </span>
          ))}
        </div>
      )}
      {sotp.impact_summary && (
        <div style={{ color: '#b2ebf2', fontSize: '0.78rem' }}>{sotp.impact_summary}</div>
      )}
    </div>
  );
};
