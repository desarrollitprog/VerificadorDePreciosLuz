import React from 'react';
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

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 items-end">
      {notifications.map((n) => {
        let title = '';
        let description = '';
        let icon = iconMap[n.type] || <Info className="text-blue-500" size={24} />;
        let borderColor = colorMap[n.type] || 'border-blue-500';

        // Personaliza el título y descripción según el tipo
        switch (n.type) {
          case 'success':
            title = 'Operación exitosa';
            description = 'La acción se realizó correctamente.';
            break;
          case 'error':
            title = 'Error';
            description = 'Ocurrió un error durante la operación.';
            break;
          case 'warning':
            title = 'Advertencia';
            description = 'Atención: se detectó una situación especial.';
            break;
          case 'info':
          default:
            title = 'Sincronización ejecutada';
            description = 'Se ejecutó una sincronización forzada desde el panel.';
            break;
        }

        return (
          <div
            key={n.id}
            className={`flex flex-col px-4 py-3 rounded-lg shadow-lg border bg-slate-100 dark:bg-[#1c2936] ${borderColor} animate-slide-fade-in w-96`}
          >
            <div className="flex items-center gap-3 mb-2">
              {icon}
              <span className="text-base font-bold text-slate-900 dark:text-white">{title}</span>
            </div>
            <div className="text-sm text-slate-700 dark:text-slate-200 mb-1">{description}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">{n.message}</div>
          </div>
        );
      })}
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
