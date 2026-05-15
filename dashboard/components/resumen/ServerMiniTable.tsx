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
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5 animate-pulse">
        <div className="h-4 w-36 bg-zinc-800 rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-zinc-800 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
        <h3 className="text-white font-semibold text-sm mb-2">Servidores</h3>
        <p className="text-zinc-500 text-sm">Sin servidores registrados</p>
      </div>
    );
  }

  return (
    <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
      <h3 className="text-white font-semibold text-sm mb-4">Servidores</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-800">
              <th className="text-left py-2 pr-2">Servidor</th>
              <th className="text-left py-2 px-2 hidden sm:table-cell">IP</th>
              <th className="text-left py-2 px-2">Estado</th>
              <th className="text-left py-2 px-2">Almacenamiento</th>
              <th className="text-center py-2 px-2">Dispositivos</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/50">
            {data.map((s) => (
              <tr key={s.id} className="hover:bg-zinc-800/30 transition-colors">
                <td className="py-3 pr-2">
                  <span className="text-white font-medium">{s.nombre}</span>
                </td>
                <td className="py-3 px-2 hidden sm:table-cell text-zinc-400">{s.ip}</td>
                <td className="py-3 px-2">
                  <div className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${s.online ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className={s.online ? 'text-green-400' : 'text-red-400'}>
                      {s.online ? 'Online' : 'Offline'}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-2">
                  <div className="flex items-center gap-2 min-w-[100px]">
                    <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${getBarColor(s.porcentaje_uso)}`} style={{ width: `${Math.min(s.porcentaje_uso, 100)}%` }} />
                    </div>
                    <span className="text-zinc-400 text-xs w-12 text-right">{s.porcentaje_uso}%</span>
                  </div>
                </td>
                <td className="py-3 px-2 text-center">
                  <span className="text-zinc-300">
                    {s.dispositivos_online}/{s.dispositivos_total}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ServerMiniTable;
