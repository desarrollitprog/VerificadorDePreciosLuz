import React, { useState } from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';
import { useNotificationContext } from './NotificationContext';

const iconMap = {
  success: <CheckCircle className="text-emerald-500" size={24} />,
  error: <XCircle className="text-red-500" size={24} />,
  info: <Info className="text-blue-500" size={24} />,
  warning: <AlertTriangle className="text-amber-500" size={24} />,
};

const colorMap = {
  success: 'bg-emerald-100 border-emerald-500',
  error: 'bg-red-100 border-red-500',
  info: 'bg-blue-100 border-blue-500',
  warning: 'bg-amber-100 border-amber-500',
};

export const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotificationContext();
  const [exiting, setExiting] = useState<Set<string>>(new Set());

  const handleClose = (id: string) => {
    setExiting((prev) => new Set(prev).add(id));
    setTimeout(() => {
      setExiting((prev) => { const next = new Set(prev); next.delete(id); return next; });
      removeNotification(id);
    }, 300);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 items-end w-full max-w-sm">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`relative flex items-center gap-3 px-4 py-3 pr-10 rounded-lg shadow-lg border overflow-hidden ${colorMap[n.type]} ${exiting.has(n.id) ? 'animate-slide-fade-out' : 'animate-slide-fade-in'}`}
        >
          {iconMap[n.type]}
          <span className="text-sm font-medium text-slate-900 flex-1">{n.message}</span>
          <button
            onClick={() => handleClose(n.id)}
            className="absolute top-2 right-2 p-0.5 rounded-full text-slate-500 hover:text-slate-800 hover:bg-white/40 transition-colors"
          >
            <X size={14} />
          </button>
          {!n.persistent && (
            <div
              className="absolute bottom-0 left-0 h-0.5 bg-black/20 rounded-full animate-shrink"
              style={{ animationDuration: (n.duration ?? 5000) + 'ms' }}
            />
          )}
        </div>
      ))}
      <style>{`
        @keyframes slide-fade-in {
          0% { opacity: 0; transform: translateY(20px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes slide-fade-out {
          0% { opacity: 1; transform: translateY(0); }
          100% { opacity: 0; transform: translateY(20px); }
        }
        @keyframes shrink {
          from { width: 100%; }
          to { width: 0%; }
        }
        .animate-slide-fade-in {
          animation: slide-fade-in 0.4s ease;
        }
        .animate-slide-fade-out {
          animation: slide-fade-out 0.3s ease forwards;
        }
        .animate-shrink {
          animation: shrink linear;
        }
      `}</style>
    </div>
  );
};
