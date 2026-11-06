import React from 'react';

interface ProgressBarProps {
  value: number; // 0 to 100
  color?: 'emerald' | 'brand' | 'amber' | 'indigo';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  color = 'brand',
  size = 'md',
  showLabel = false,
}) => {
  const clamped = Math.min(100, Math.max(0, value));

  const heightClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-3.5',
  }[size];

  const colorClasses = {
    brand: 'bg-brand-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    indigo: 'bg-indigo-500',
  }[color];

  return (
    <div className="w-full">
      <div className={`w-full bg-slate-200 rounded-full overflow-hidden ${heightClasses}`}>
        <div
          className={`${colorClasses} h-full transition-all duration-500 rounded-full`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 flex justify-between text-xs text-slate-500">
          <span>Progress</span>
          <span className="font-semibold text-slate-700">{clamped}%</span>
        </div>
      )}
    </div>
  );
};

