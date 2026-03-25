import React from 'react';
import { Server, Edit2 } from 'lucide-react';

interface ServerCardProps {
  nombre: string;
  ip: string;
  online: boolean;
  porcentaje_uso: number;
  onRename?: () => void;
}

const getBarColor = (porcentaje: number) => {
  if (porcentaje > 90) return 'bg-red-500';
  if (porcentaje > 70) return 'bg-yellow-500';
  return 'bg-emerald-500';
};

const ServerCard: React.FC<ServerCardProps> = ({ nombre, ip, online, porcentaje_uso, onRename }) => {

  return (
    <div 
      className={`
        relative overflow-hidden rounded-xl border-l-4 bg-white dark:bg-slate-900 
        shadow-sm hover:shadow-md transition-all duration-200
        ${online 
          ? 'border-l-emerald-500 dark:border-l-emerald-600' 
          : 'border-l-red-500 dark:border-l-red-600'
        }
      `}
    >
      <div className="p-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div 
              className={`
                p-2 rounded-lg 
                ${online 
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' 
                  : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                }
              `}
            >
              <Server size={18} />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-sm">
                {nombre}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{ip}</p>
            </div>
          </div>
          
          {onRename && (
            <button
              onClick={onRename}
              className="p-1 rounded text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Renombrar servidor"
            >
              <Edit2 size={12} />
            </button>
          )}
        </div>

        <div className="mt-3">
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Almacenamiento</span>
            <span className={`text-[10px] font-bold ${porcentaje_uso > 90 ? 'text-red-500' : porcentaje_uso > 70 ? 'text-yellow-500' : 'text-emerald-500'}`}>
              {porcentaje_uso}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${getBarColor(porcentaje_uso)} transition-all duration-500 rounded-full`}
              style={{ width: `${Math.min(porcentaje_uso, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServerCard;
