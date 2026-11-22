import React from 'react';
import type { Provenance } from '../types';

interface Props {
  provenance: Provenance;
  label?: string;
  className?: string;
}

export const ProvenanceBadge: React.FC<Props> = ({ provenance, label, className = '' }) => {
  const styles: Record<Provenance, { bg: string; text: string; border: string; desc: string }> = {
    OBSERVED: {
      bg: 'bg-emerald-950/70',
      text: 'text-emerald-400',
      border: 'border-emerald-700/60',
      desc: 'Verified case-study fact',
    },
    ASSUMED: {
      bg: 'bg-amber-950/70',
      text: 'text-amber-400',
      border: 'border-amber-700/60',
      desc: 'Explicit modelling assumption',
    },
    SYNTHETIC: {
      bg: 'bg-purple-950/70',
      text: 'text-purple-400',
      border: 'border-purple-700/60',
      desc: 'Generated disturbance profile',
    },
    SYNTHETIC_CALIBRATION: {
      bg: 'bg-indigo-950/70',
      text: 'text-indigo-300',
      border: 'border-indigo-700/60',
      desc: 'Bounded calibration against case benchmarks',
    },
  };

  const current = styles[provenance] || styles.ASSUMED;

  return (
    <span
      title={`${provenance}: ${current.desc}`}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold tracking-wide border ${current.bg} ${current.text} ${current.border} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      {label || provenance}
    </span>
  );
};
