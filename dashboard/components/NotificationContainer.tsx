import React, { useState } from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';
import { useNotificationContext } from './NotificationContext';

const iconMap = {
  success: <CheckCircle className="text-emerald-500 w-5 h-5 md:w-6 md:h-6" />,
  error: <XCircle className="text-red-500 w-5 h-5 md:w-6 md:h-6" />,
  info: <Info className="text-blue-500 w-5 h-5 md:w-6 md:h-6" />,
  warning: <AlertTriangle className="text-amber-500 w-5 h-5 md:w-6 md:h-6" />,
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
    <div className="fixed bottom-4 right-4 md:bottom-6 md:right-6 z-50 flex flex-col gap-2 md:gap-3 items-end w-[calc(100vw-2rem)] md:w-full max-w-xs md:max-w-sm">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`relative flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2 md:py-3 pr-8 md:pr-10 rounded-lg shadow-lg border overflow-hidden ${colorMap[n.type]} ${exiting.has(n.id) ? 'animate-slide-fade-out' : 'animate-slide-fade-in'}`}
        >
          {iconMap[n.type]}
          <span className="text-xs md:text-sm font-medium text-slate-900 flex-1">{n.message}</span>
          <button
            onClick={() => handleClose(n.id)}
            className="absolute top-1 right-1 md:top-2 md:right-2 p-1.5 md:p-1 rounded-full text-slate-500 hover:text-slate-800 hover:bg-white/40 transition-colors"
          >
            <X size={16} />
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
