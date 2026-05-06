import React from 'react';
import { Servidor } from '../types';
import { Server, Smartphone, ChevronDown, ChevronRight } from 'lucide-react';

interface ServerDeviceSelectorProps {
  servidores: Servidor[];
  selectedServidorIds: number[];
  selectedDispositivoIds: string[];
  onServidorChange: (id: number, checked: boolean) => void;
  onDispositivoChange: (id: string, checked: boolean) => void;
  expandedServidores: number[];
  onToggleExpand: (id: number) => void;
  label?: string;
  maxHeight?: string;
}

export const ServerDeviceSelector: React.FC<ServerDeviceSelectorProps> = ({
  servidores,
  selectedServidorIds,
  selectedDispositivoIds,
  onServidorChange,
  onDispositivoChange,
  expandedServidores,
  onToggleExpand,
  label = 'Seleccionar servidores:',
  maxHeight = 'max-h-32',
}) => {
  if (servidores.length === 0) {
    return <p className="text-xs text-slate-500">No hay servidores disponibles</p>;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1">
        <Server size={16} />
        {label}
      </p>
      <div className={`${maxHeight} overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg p-3 space-y-2`}>
        {servidores.map(srv => (
          <div key={srv.id}>
            <label className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-2 rounded">
              <input
                type="checkbox"
                checked={selectedServidorIds.includes(Number(srv.id))}
                onChange={(e) => {
                  e.stopPropagation();
                  onServidorChange(Number(srv.id), e.target.checked);
                }}
                className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
              />
              <span className="text-base text-slate-700 dark:text-slate-300 flex items-center gap-1">
                <Server size={16} />
                {srv.nombre}
                <span className={`text-xs px-1.5 py-0.5 rounded ${srv.online ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-500/10 text-slate-500'}`}>
                  {srv.online ? 'Online' : 'Offline'}
                </span>
              </span>
              <button
                type="button"
                onClick={() => onToggleExpand(srv.id)}
                className="ml-auto p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
              >
                {expandedServidores.includes(srv.id) ? (
                  <ChevronDown size={16} className="text-slate-500" />
                ) : (
                  <ChevronRight size={16} className="text-slate-500" />
                )}
              </button>
            </label>
            {expandedServidores.includes(srv.id) && srv.dispositivos && srv.dispositivos.length > 0 && (
              <div className="ml-8 mt-2 space-y-1">
                {srv.dispositivos.map(disp => (
                  <label key={`${srv.id}-${disp.id}`} className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1.5 rounded">
                    <input
                      type="checkbox"
                      checked={selectedDispositivoIds.includes(disp.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        onDispositivoChange(disp.id, e.target.checked);
                      }}
                      className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                    />
                    <span className="text-sm text-slate-600 dark:text-slate-400 flex items-center gap-1">
                      <Smartphone size={14} />
                      {disp.nombre_amigable || disp.codigo_kioko}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        Seleccionados: {selectedServidorIds.length} servidores, {selectedDispositivoIds.length} dispositivos
      </p>
    </div>
  );
};