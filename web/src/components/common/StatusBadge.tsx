import React from 'react';
import { getSeverityBadge, getVerificationBadge } from '../../utils/format';

interface SeverityBadgeProps {
  level?: string;
  size?: 'sm' | 'md';
  style?: React.CSSProperties;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ level, size = 'md', style }) => {
  const sev = getSeverityBadge(level);
  const fontSize = size === 'sm' ? '0.7rem' : '0.75rem';
  return (
    <span className={`badge ${sev.cls}`} style={{ fontSize, ...style }}>
      {sev.text}
    </span>
  );
};

interface VerificationBadgeProps {
  status?: string;
  size?: 'sm' | 'md';
  style?: React.CSSProperties;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({ status, size = 'md', style }) => {
  const ver = getVerificationBadge(status);
  const fontSize = size === 'sm' ? '0.7rem' : '0.75rem';
  return (
    <span className={`badge ${ver.cls}`} style={{ fontSize, ...style }}>
      {ver.text}
    </span>
  );
};
