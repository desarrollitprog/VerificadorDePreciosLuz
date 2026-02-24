import React from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';
import { useNotificationContext } from './NotificationContext';

const iconMap = {
  success: <CheckCircle className="text-green-500" size={24} />,
  error: <XCircle className="text-red-500" size={24} />,
  info: <Info className="text-blue-500" size={24} />,
  warning: <AlertTriangle className="text-yellow-500" size={24} />,
};

const colorMap = {
  success: 'bg-green-100 border-green-500',
  error: 'bg-red-100 border-red-500',
  info: 'bg-blue-100 border-blue-500',
  warning: 'bg-yellow-100 border-yellow-500',
};

export const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotificationContext();

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 items-end">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border ${colorMap[n.type]} animate-slide-fade-in`}
        >
          {iconMap[n.type]}
          <span className="text-sm font-medium text-slate-900 flex-1">{n.message}</span>
          <button
            className="ml-2 text-slate-500 hover:text-slate-900"
            onClick={() => removeNotification(n.id)}
            aria-label="Cerrar notificación"
          >
            <X size={18} />
          </button>
        </div>
      ))}
      <style>{`
        @keyframes slide-fade-in {
          0% { opacity: 0; transform: translateY(20px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        .animate-slide-fade-in {
          animation: slide-fade-in 0.4s ease;
        }
      `}</style>
    </div>
  );
};
