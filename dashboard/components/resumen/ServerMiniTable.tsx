import React from 'react';
import { ServidorResumen } from '../../services/resumenService';

interface Props {
  data: ServidorResumen[];
  loading?: boolean;
}

function formatBytes(bytes: number): string {
  const gb = bytes / 1073741824;
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1048576).toFixed(0)} MB`;
}

function getBarColor(pct: number): string {
  if (pct >= 90) return 'bg-red-500';
  if (pct >= 70) return 'bg-yellow-500';
  return 'bg-cyan-500';
}

const ServerMiniTable: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 bg-slate-200 dark:bg-[#253247]" />
        <div className="p-5 animate-pulse">
          <div className="h-4 w-28 bg-slate-200 dark:bg-[#253247] rounded mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-slate-200 dark:bg-[#253247] rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 w-full bg-slate-400 dark:bg-slate-600" />
        <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-slate-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-slate-700/5 pointer-events-none" />
        <div className="relative z-10 p-5">
          <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-2">Sedes</h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin sedes registradas</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 overflow-hidden relative group">
      <div className="h-1 w-full bg-slate-400 dark:bg-slate-600" />
      <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-slate-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-slate-700/5 pointer-events-none" />
      <div className="relative z-10 p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-4">Sedes</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                <th className="text-left py-2 pr-2">Sede</th>
                <th className="text-left py-2 px-2 hidden sm:table-cell">IP</th>
                <th className="text-left py-2 px-2">Estado</th>
                <th className="text-left py-2 px-2">Almacenamiento</th>
                <th className="text-center py-2 px-2">Dispositivos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {data.map((s) => (
                <tr key={s.id} className="hover:bg-slate-100 dark:hover:bg-[#253247] transition-colors">
                  <td className="py-3 pr-2">
                    <span className="text-slate-900 dark:text-white font-medium">{s.nombre}</span>
                  </td>
                  <td className="py-3 px-2 hidden sm:table-cell text-slate-500 dark:text-slate-400">{s.ip}</td>
                  <td className="py-3 px-2">
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${s.online ? 'bg-green-500' : 'bg-red-500'}`} />
                      <span className={s.online ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                        {s.online ? 'Online' : 'Offline'}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-2">
                    <div className="flex items-center gap-2 min-w-[100px]">
                      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${getBarColor(s.porcentaje_uso)}`} style={{ width: `${Math.min(s.porcentaje_uso, 100)}%` }} />
                      </div>
                      <span className="text-slate-500 dark:text-slate-400 text-xs w-12 text-right">{s.porcentaje_uso}%</span>
                    </div>
                  </td>
                  <td className="py-3 px-2 text-center">
                    <span className="inline-flex items-center gap-1">
                      <span className="text-green-600 dark:text-green-400">{s.dispositivos_online}</span>
                      <span className="text-slate-400">/</span>
                      <span className="text-red-600 dark:text-red-400">{s.dispositivos_total - s.dispositivos_online}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ServerMiniTable;
