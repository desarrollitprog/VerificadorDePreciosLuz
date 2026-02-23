import React from 'react';

interface ServerCardProps {
  nombre: string;
  ip: string;
  online: boolean;
  porcentaje_uso: number;
}

const getBarColor = (porcentaje: number) => {
  if (porcentaje > 90) return 'bg-red-500';
  if (porcentaje > 70) return 'bg-yellow-500';
  return 'bg-green-500';
};

const ServerCard: React.FC<ServerCardProps> = ({ nombre, ip, online, porcentaje_uso }) => (
  <div className="bg-white dark:bg-[#1c2936] rounded-xl shadow-md border border-slate-200 dark:border-slate-800 p-5 flex flex-col gap-3">
    <div className="flex items-center gap-3">
      <span
        className={`h-3 w-3 rounded-full ${online ? 'bg-green-500 animate-pulse' : 'bg-red-500'} border border-white shadow`}
        title={online ? 'Online' : 'Offline'}
      />
      <span className="font-bold text-slate-900 dark:text-white text-base truncate">{nombre}</span>
    </div>
    <div className="text-xs text-slate-500 dark:text-slate-400 truncate">IP: {ip}</div>
    <div className="mt-2">
      <div className="flex justify-between text-xs mb-1">
        <span>Almacenamiento</span>
        <span>{porcentaje_uso}%</span>
      </div>
      <div className="w-full h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-3 ${getBarColor(porcentaje_uso)}`}
          style={{ width: `${Math.min(porcentaje_uso, 100)}%` }}
        />
      </div>
    </div>
  </div>
);

export default ServerCard;
