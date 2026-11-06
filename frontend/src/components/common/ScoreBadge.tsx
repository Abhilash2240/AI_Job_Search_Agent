import React from 'react';

interface ScoreBadgeProps {
  score: number; // 0.0 to 1.0 or percentage 0 to 100
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ScoreBadge: React.FC<ScoreBadgeProps> = ({ score, label, size = 'md' }) => {
  // Normalize to percentage 0-100
  const pct = score <= 1.0 ? Math.round(score * 100) : Math.round(score);

  let colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (pct < 50) {
    colorClasses = 'bg-slate-100 text-slate-700 border-slate-300';
  } else if (pct < 65) {
    colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (pct < 75) {
    colorClasses = 'bg-sky-50 text-sky-700 border-sky-200';
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5 font-bold',
  }[size];

  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full border font-semibold ${colorClasses} ${sizeClasses}`}>
      <span>{pct}%</span>
      {label && <span className="text-[11px] font-medium opacity-80 uppercase tracking-wider">{label}</span>}
    </div>
  );
};

