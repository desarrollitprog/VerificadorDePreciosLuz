import React from 'react';
import { Servidor } from '../types';
import { Server, Smartphone, ChevronDown, ChevronRight, Check } from 'lucide-react';

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
    return <p className="text-sm text-slate-500">No hay servidores disponibles</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/70 dark:border-slate-700/50">
        <p className="text-base font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
          <Server size={18} className="text-primary" />
          {label}
        </p>
        <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full font-medium text-slate-600 dark:text-slate-400">
          {selectedServidorIds.length} seleccionados
        </span>
      </div>

      <div className={`${maxHeight} overflow-y-auto space-y-3 pr-2 custom-scrollbar`}>
        {servidores.map(srv => (
          <div key={srv.id} className="border border-slate-200/70 dark:border-slate-700/50 rounded-xl overflow-hidden hover:border-primary/30 transition-all duration-300 server-card-glow">
            <label className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
              <div className={`w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all duration-200 ${
                selectedServidorIds.includes(Number(srv.id))
                  ? 'bg-primary border-primary scale-110'
                  : 'border-slate-300 dark:border-slate-600 hover:border-primary/50 scale-100'
              }`}>
                {selectedServidorIds.includes(Number(srv.id)) && <Check size={14} className="text-white" />}
              </div>

              <Server size={18} className="text-slate-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-base font-medium text-slate-700 dark:text-slate-200 block truncate">
                  {srv.nombre}
                </span>
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    srv.online ? 'bg-emerald-500' : 'bg-slate-400'
                  }`} />
                  {srv.dispositivos?.length ?? 0} dispositivos
                </span>
              </div>

              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                srv.online
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-slate-500/10 text-slate-500'
              }`}>
                {srv.online ? 'Online' : 'Offline'}
              </span>

              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  onToggleExpand(srv.id);
                }}
                className="ml-auto p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                {expandedServidores.includes(srv.id) ? (
                  <ChevronDown size={18} className="text-slate-500" />
                ) : (
                  <ChevronRight size={18} className="text-slate-500" />
                )}
              </button>
            </label>

            {expandedServidores.includes(srv.id) && srv.dispositivos && srv.dispositivos.length > 0 && (
              <div className="bg-slate-50/50 dark:bg-slate-800/30 px-3 pb-3">
                <div className="grid grid-cols-2 gap-2">
                  {srv.dispositivos.map(disp => (
                    <label
                      key={`${srv.id}-${disp.id}`}
                      className="flex items-center gap-2 p-2 rounded-lg hover:bg-white dark:hover:bg-slate-700/50 cursor-pointer transition-colors group"
                    >
                      <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all duration-200 ${
                        selectedDispositivoIds.includes(String(disp.id))
                          ? 'bg-primary border-primary scale-110'
                          : 'border-slate-300 dark:border-slate-600 group-hover:border-primary/50'
                      }`}>
                        {selectedDispositivoIds.includes(String(disp.id)) && <Check size={12} className="text-white" />}
                      </div>
                      <Smartphone size={12} className="text-slate-400 flex-shrink-0" />
                      <span className="text-sm text-slate-600 dark:text-slate-300 truncate">
                        {disp.nombre_amigable || String(disp.codigo_kiosko)}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="pt-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          <span className="font-semibold text-slate-700 dark:text-slate-300">{selectedServidorIds.length}</span> servidores,{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">{selectedDispositivoIds.length}</span> dispositivos
        </p>
        {(selectedServidorIds.length > 0 || selectedDispositivoIds.length > 0) && (
          <button
            type="button"
            onClick={() => {
              selectedServidorIds.forEach(id => onServidorChange(id, false));
              selectedDispositivoIds.forEach(id => onDispositivoChange(id, false));
            }}
            className="text-xs text-red-500 hover:text-red-700 font-medium"
          >
            Limpiar selección
          </button>
        )}
      </div>
    </div>
  );
};
