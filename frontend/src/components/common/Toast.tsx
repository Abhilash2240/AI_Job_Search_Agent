import React from 'react';
import { useCandidate } from '../../context/CandidateContext';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useCandidate();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        let borderClass = 'border-slate-200 bg-white text-slate-800';
        let Icon = Info;
        let iconColor = 'text-sky-500';

        if (toast.type === 'success') {
          borderClass = 'border-emerald-200 bg-emerald-50 text-emerald-900';
          Icon = CheckCircle2;
          iconColor = 'text-emerald-600';
        } else if (toast.type === 'error') {
          borderClass = 'border-rose-200 bg-rose-50 text-rose-900';
          Icon = AlertCircle;
          iconColor = 'text-rose-600';
        }

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center justify-between p-3.5 rounded-lg border shadow-lg transition-all animate-in slide-in-from-bottom-2 ${borderClass}`}
          >
            <div className="flex items-center gap-2.5">
              <Icon className={`w-5 h-5 flex-shrink-0 ${iconColor}`} />
              <p className="text-sm font-medium">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 focus:outline-none"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

