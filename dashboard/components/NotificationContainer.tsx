import React from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle, X, Search } from 'lucide-react';
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
  const { notifications } = useNotificationContext();
  const [search, setSearch] = React.useState('');

  // Filtrar notificaciones por mensaje
  const filteredNotifications = notifications.filter(n =>
    n.message.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 items-end w-96">
      <div className="mb-2 w-full">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            className="pl-10 pr-4 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full transition-all"
            placeholder="Buscar notificaciones..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>
      {filteredNotifications.map((n) => (
        <div
          key={n.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border ${colorMap[n.type]} animate-slide-fade-in`}
        >
          {iconMap[n.type]}
          <span className="text-sm font-medium text-slate-900 flex-1">{n.message}</span>
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
