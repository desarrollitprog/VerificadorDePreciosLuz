import React, { useState } from 'react';
import { Servidor } from '../types';
import { Server, Smartphone, ChevronDown, ChevronRight, Check, Monitor, Search, Minus } from 'lucide-react';

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
  accentColor?: string;
}

type TipoFilter = 'todos' | 'verificador' | 'televisor';

export const ServerDeviceSelector: React.FC<ServerDeviceSelectorProps> = ({
  servidores,
  selectedServidorIds,
  selectedDispositivoIds,
  onServidorChange,
  onDispositivoChange,
  expandedServidores,
  onToggleExpand,
  label = 'Seleccionar sedes:',
  maxHeight = 'max-h-32',
  accentColor = '#3b82f6',
}) => {
  const [tipoFilter, setTipoFilter] = useState<TipoFilter>('todos');

  if (servidores.length === 0) {
    return <p className="text-sm text-slate-500">No hay sedes disponibles</p>;
  }

  const filteredServidores = servidores
    .map(srv => ({
      ...srv,
      dispositivos: tipoFilter === 'todos'
        ? srv.dispositivos
        : (srv.dispositivos || []).filter(d => d.tipo === tipoFilter),
    }))
    .filter(srv => srv.dispositivos.length > 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/70 dark:border-slate-700/50">
        <p className="text-base font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
          <Server size={18} style={{ color: accentColor }} />
          {label}
        </p>
        <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full font-medium text-slate-600 dark:text-slate-400">
          {selectedServidorIds.length} seleccionados
        </span>
      </div>

      <div className="flex gap-1 pb-2 border-b border-slate-200/50 dark:border-slate-700/30">
        {(['todos', 'verificador', 'televisor'] as TipoFilter[]).map(t => {
          const isActive = tipoFilter === t;
          const label = t === 'todos' ? 'Todos' : t === 'verificador' ? '🔍 Verificadores' : '📺 Televisores';
          return (
            <button
              key={t}
              type="button"
              onClick={() => setTipoFilter(t)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all ${
                isActive
                  ? 'bg-slate-800 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className={`${maxHeight} overflow-y-auto space-y-3 pr-2 custom-scrollbar`}>
        {filteredServidores.map(srv => {
          const onlineCount = srv.dispositivos?.filter(d => d.online).length ?? 0;
          const offlineCount = srv.dispositivos?.filter(d => !d.online).length ?? 0;
          const totalDispositivos = onlineCount + offlineCount;
          const serverDispIds = (srv.dispositivos || []).map(d => String(d.id));
          const serverSelectedCount = serverDispIds.filter(id => selectedDispositivoIds.includes(id)).length;
          const allServerDevicesSelected = serverSelectedCount === serverDispIds.length && serverDispIds.length > 0;
          return (
          <div key={srv.id} className="border border-slate-200/70 dark:border-slate-700/50 rounded-xl overflow-hidden hover:border-primary/30 transition-all duration-300 server-card-glow">
            <div className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                 onClick={() => onServidorChange(Number(srv.id), !selectedServidorIds.includes(Number(srv.id)))}>
              <div className={`w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all duration-200 shrink-0 ${
                selectedServidorIds.includes(Number(srv.id))
                  ? 'scale-110'
                  : 'border-slate-300 dark:border-slate-600 hover:border-primary/50 scale-100'
              }`}
              style={selectedServidorIds.includes(Number(srv.id)) ? { backgroundColor: accentColor, borderColor: accentColor } : undefined}>
                {selectedServidorIds.includes(Number(srv.id)) && <Check size={14} className="text-white" />}
              </div>

              <Server size={18} className="text-slate-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-lg font-medium text-slate-700 dark:text-slate-200 block truncate">
                  {srv.nombre}
                </span>
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  {onlineCount > 0 && (
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      {onlineCount}
                    </span>
                  )}
                  {offlineCount > 0 && (
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                      {offlineCount}
                    </span>
                  )}
                  <span className="text-slate-400 mx-0.5">|</span>
                  {totalDispositivos} dispositivos
                </span>
              </div>

              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                srv.online
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-slate-500/10 text-slate-500'
              }`}>
                {srv.online ? 'En línea' : 'Desconectado'}
              </span>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
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
            </div>

            {expandedServidores.includes(srv.id) && srv.dispositivos && srv.dispositivos.length > 0 && (
              <div className="bg-slate-50/50 dark:bg-slate-800/30 px-3 pb-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {srv.dispositivos.map(disp => (
                    <div
                      key={`${srv.id}-${disp.id}`}
                      className="flex items-center gap-2 p-2 rounded-lg hover:bg-white dark:hover:bg-slate-700/50 cursor-pointer transition-colors group"
                      onClick={() => onDispositivoChange(String(disp.id), !selectedDispositivoIds.includes(String(disp.id)))}
                    >
                      <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all duration-200 shrink-0 ${
                        selectedDispositivoIds.includes(String(disp.id))
                          ? 'scale-110'
                          : 'border-slate-300 dark:border-slate-600 group-hover:border-primary/50'
                      }`}
                      style={selectedDispositivoIds.includes(String(disp.id)) ? { backgroundColor: accentColor, borderColor: accentColor } : undefined}>
                        {selectedDispositivoIds.includes(String(disp.id)) && <Check size={12} className="text-white" />}
                      </div>
                      <div className="flex-shrink-0">
                        {disp.tipo === 'televisor' ? (
                          <Monitor size={12} className="text-green-500" />
                        ) : (
                          <Search size={12} className="text-blue-500" />
                        )}
                      </div>
                      <span className="text-base text-slate-600 dark:text-slate-300 truncate">
                        {disp.nombre_amigable || String(disp.codigo_kiosko)}
                      </span>
                      <span className={`inline-flex items-center px-1 py-0.5 rounded text-[10px] font-bold ${
                        disp.tipo === 'televisor'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                      }`}>
                        {disp.tipo === 'televisor' ? 'TV' : 'VER'}
                      </span>
                      <span className={`text-[10px] flex items-center gap-1 ml-1 ${
                        disp.online ? 'text-emerald-500' : 'text-slate-400'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${disp.online ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                        {disp.online ? 'En línea' : 'Desconectado'}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end mt-1.5">
                  <div
                    className="flex items-center gap-2 px-2 py-1 rounded-md cursor-pointer hover:bg-white/60 dark:hover:bg-slate-700/20 transition-colors group"
                    onClick={(e) => {
                      e.stopPropagation();
                      const newState = !allServerDevicesSelected;
                      serverDispIds.forEach(id => {
                        if (selectedDispositivoIds.includes(id) === newState) return;
                        onDispositivoChange(id, newState);
                      });
                    }}
                  >
                    <div
                      className="w-3.5 h-3.5 rounded border-2 flex items-center justify-center transition-all shrink-0"
                      style={{
                        borderColor: serverSelectedCount === 0 ? '#cbd5e1' : serverSelectedCount === serverDispIds.length ? accentColor : '#94a3b8',
                        backgroundColor: serverSelectedCount === 0 ? 'transparent' : serverSelectedCount === serverDispIds.length ? accentColor : '#94a3b8',
                      }}
                    >
                      {serverSelectedCount === 0 ? null : serverSelectedCount === serverDispIds.length ? (
                        <Check size={10} className="text-white" />
                      ) : (
                        <Minus size={10} className="text-white" />
                      )}
                    </div>
                    <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 transition-colors whitespace-nowrap">
                      {allServerDevicesSelected ? 'Deseleccionar todos' : 'Seleccionar todos'}
                    </span>
                    <span className="text-[10px] font-mono tabular-nums text-slate-400 dark:text-slate-500">
                      {serverSelectedCount}/{serverDispIds.length}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
          );
        })}
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
