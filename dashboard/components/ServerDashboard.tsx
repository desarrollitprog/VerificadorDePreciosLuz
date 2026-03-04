import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import ServerCard from './monitoreo/ServerCard';
import { useNotification } from './useNotification';
import {
  getServersStatusWithDevices,
  renameDevice,
  renameServer,
  ServerStatusDetail,
} from '../services/monitoreoService';

export function ServerDashboard() {
  const showNotification = useNotification();
  const [servidores, setServidores] = useState<ServerStatusDetail[]>([]);
  const [expandedServerId, setExpandedServerId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getServersStatusWithDevices();
      setServidores(Array.isArray(data) ? data : []);
    } catch {
      setServidores([]);
      setError('Error al conectar con el servicio de monitoreo');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    fetchStatus();
    interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRenameDevice = async (deviceId: string, currentName?: string | null) => {
    const proposed = window.prompt(
      'Nombre para el dispositivo (deja vacío para quitar alias):',
      currentName ?? deviceId
    );
    if (proposed === null) return;

    const normalized = proposed.trim();
    await renameDevice(deviceId, normalized.length > 0 ? normalized : null);
    await fetchStatus();
  };

  const handleRenameServer = async (server: ServerStatusDetail) => {
    const proposed = window.prompt('Nombre para el servidor:', server.nombre || server.ip);
    if (proposed === null) return;

    const normalized = proposed.trim();
    if (!normalized) return;

    try {
      await renameServer(server.id, normalized);
      showNotification('Servidor renombrado correctamente', 'success');
      await fetchStatus();
    } catch (error: any) {
      const detail = String(error?.response?.data?.detail || '');
      if (error?.response?.status === 409) {
        showNotification('Ya existe un servidor con ese nombre', 'warning');
        return;
      }
      if (detail) {
        showNotification(detail, 'error');
        return;
      }
      showNotification('No se pudo renombrar el servidor', 'error');
    }
  };

  return (
    <div className="flex flex-col min-w-0 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Servidores y Dispositivos</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Monitoreo en tiempo real</p>
        </div>
        <button
          onClick={fetchStatus}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <RefreshCw size={16} />
          Refrescar
        </button>
      </div>

      {loading ? (
        <div className="text-slate-500">Cargando monitoreo...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {servidores.map((s) => (
            <div key={s.id} className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-800 p-4">
              <div className="flex items-center justify-end mb-2">
                <button
                  className="text-[11px] text-blue-500 hover:underline"
                  onClick={() => handleRenameServer(s)}
                >
                  Renombrar servidor
                </button>
              </div>
              <ServerCard
                nombre={s.nombre}
                ip={s.ip}
                online={s.online}
                porcentaje_uso={s.porcentaje_uso}
              />

              <button
                className="mt-3 w-full text-sm flex items-center justify-between px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
                onClick={() => setExpandedServerId(expandedServerId === s.id ? null : s.id)}
              >
                <span>Dispositivos ({s.dispositivos_online}/{s.dispositivos_total} online)</span>
                {expandedServerId === s.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>

              {expandedServerId === s.id && (
                <div className="mt-2 max-h-56 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg">
                  {s.dispositivos.length === 0 ? (
                    <div className="p-3 text-sm text-slate-500">Sin dispositivos reportados.</div>
                  ) : (
                    s.dispositivos.map((d) => (
                      <div
                        key={d.device_id}
                        className="px-3 py-2 border-b last:border-b-0 border-slate-100 dark:border-slate-800 flex items-center justify-between"
                      >
                        <div>
                          <div className="text-sm font-medium">{d.nombre_mostrado || d.device_id}</div>
                          <div className="text-[11px] text-slate-500">ID: {d.device_id}</div>
                          <button
                            className="text-[11px] text-blue-500 hover:underline mt-1"
                            onClick={() => handleRenameDevice(d.device_id, d.nombre_amigable)}
                          >
                            Renombrar
                          </button>
                        </div>
                        <div className="text-xs text-right">
                          <div className={d.online ? 'text-green-600' : 'text-red-500'}>
                            {d.online ? 'ONLINE' : 'OFFLINE'}
                          </div>
                          <div className="text-slate-500">
                            {d.last_seen ? new Date(d.last_seen).toLocaleString() : 'Sin last_seen'}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
