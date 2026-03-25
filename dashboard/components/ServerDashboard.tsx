import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, X, Monitor, Edit2, Play, RotateCcw, Eye, AlertCircle, Clock } from 'lucide-react';
import ServerCard from './monitoreo/ServerCard';
import { useNotification } from './useNotification';
import {
  getServersStatusWithDevices,
  renameDevice,
  renameServer,
  getDeviceContent,
  restartDevice,
  ServerStatusDetail,
  DeviceContent,
} from '../services/monitoreoService';

type RenameModalState =
  | {
      type: 'server';
      server: ServerStatusDetail;
    }
  | {
      type: 'device';
      deviceId: string;
      currentName?: string | null;
    };

export function ServerDashboard() {
  const showNotification = useNotification();
  const [servidores, setServidores] = useState<ServerStatusDetail[]>([]);
  const [expandedServerId, setExpandedServerId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renameModal, setRenameModal] = useState<RenameModalState | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [renameSaving, setRenameSaving] = useState(false);

  // Modal de previsualización
  const [previewModal, setPreviewModal] = useState<{ deviceId: string; content: DeviceContent | null; loading: boolean } | null>(null);

  // Modal de reinicio
  const [restartModal, setRestartModal] = useState<{ deviceId: string; deviceName: string } | null>(null);
  const [restarting, setRestarting] = useState(false);

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

  const openRenameServerModal = (server: ServerStatusDetail) => {
    setRenameModal({ type: 'server', server });
    setRenameValue(server.nombre || server.ip || '');
  };

  const openRenameDeviceModal = (deviceId: string, currentName?: string | null) => {
    setRenameModal({ type: 'device', deviceId, currentName });
    setRenameValue(currentName ?? deviceId);
  };

  const closeRenameModal = () => {
    if (renameSaving) return;
    setRenameModal(null);
    setRenameValue('');
  };

  const submitRename = async () => {
    if (!renameModal) return;
    const normalized = renameValue.trim();

    if (renameModal.type === 'server' && !normalized) {
      showNotification('El nombre del servidor no puede estar vacío', 'warning');
      return;
    }

    setRenameSaving(true);
    try {
      if (renameModal.type === 'server') {
        await renameServer(renameModal.server.id, normalized);
        showNotification('Servidor renombrado correctamente', 'success');
      } else {
        await renameDevice(renameModal.deviceId, normalized.length > 0 ? normalized : null);
        showNotification('Dispositivo renombrado correctamente', 'success');
      }
      await fetchStatus();
      closeRenameModal();
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
      showNotification(
        renameModal.type === 'server' ? 'No se pudo renombrar el servidor' : 'No se pudo renombrar el dispositivo',
        'error'
      );
    } finally {
      setRenameSaving(false);
    }
  };

  const openPreviewModal = async (deviceId: string) => {
    setPreviewModal({ deviceId, content: null, loading: true });
    try {
      const content = await getDeviceContent(deviceId);
      setPreviewModal({ deviceId, content, loading: false });
    } catch {
      showNotification('Error al obtener contenido del dispositivo', 'error');
      setPreviewModal(null);
    }
  };

  const closePreviewModal = () => {
    setPreviewModal(null);
  };

  const openRestartModal = (deviceId: string, deviceName: string) => {
    setRestartModal({ deviceId, deviceName });
  };

  const closeRestartModal = () => {
    setRestartModal(null);
  };

  const handleRestart = async () => {
    if (!restartModal) return;
    setRestarting(true);
    try {
      const result = await restartDevice(restartModal.deviceId);
      if (result.success) {
        showNotification('Dispositivo reiniciado correctamente', 'success');
      } else {
        showNotification(result.message || 'Error al reiniciar dispositivo', 'error');
      }
      closeRestartModal();
    } catch {
      showNotification('Error al reiniciar dispositivo', 'error');
    } finally {
      setRestarting(false);
    }
  };

  const formatLastSeen = (lastSeen: string | null) => {
    if (!lastSeen) return 'Sin conexión';
    const date = new Date(lastSeen);
    return date.toLocaleString('es-VE', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatUptime = (primeraConexion: string | null, uptime: number | null) => {
    if (!primeraConexion && !uptime) return null;
    
    let totalSeconds = 0;
    
    if (uptime && uptime > 0) {
      totalSeconds = uptime;
    } else if (primeraConexion) {
      const start = new Date(primeraConexion).getTime();
      const now = Date.now();
      totalSeconds = Math.floor((now - start) / 1000);
    }
    
    if (totalSeconds <= 0) return null;

    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  return (
    <div className="flex flex-col min-w-0 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Servidores y Dispositivos</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Monitoreo en tiempo real</p>
        </div>
        <button
          onClick={fetchStatus}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition"
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
            <div key={s.id} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div className="p-4">
                <ServerCard
                  nombre={s.nombre}
                  ip={s.ip}
                  online={s.online}
                  porcentaje_uso={s.porcentaje_uso}
                  onRename={() => openRenameServerModal(s)}
                />

                <button
                  className="mt-3 w-full flex items-center justify-between px-4 py-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition text-sm font-medium"
                  onClick={() => setExpandedServerId(expandedServerId === s.id ? null : s.id)}
                >
                  <span className="flex items-center gap-2">
                    <Monitor size={16} className="text-slate-500" />
                    Dispositivos ({s.dispositivos_online}/{s.dispositivos_total})
                  </span>
                  {expandedServerId === s.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {expandedServerId === s.id && (
                  <div className="mt-2 max-h-64 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
                    {s.dispositivos.length === 0 ? (
                      <div className="p-4 text-sm text-slate-500 text-center">Sin dispositivos reportados</div>
                    ) : (
                      s.dispositivos.map((d) => (
                        <div key={d.device_id} className="p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${d.online ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                <span className="font-medium text-sm text-slate-900 dark:text-white truncate">
                                  {d.nombre_mostrado || d.device_id}
                                </span>
                                {formatUptime(d.primera_conexion, d.uptime) && (
                                  <span className="ml-auto text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-1.5 py-0.5 rounded">
                                    {formatUptime(d.primera_conexion, d.uptime)}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                ID: {d.device_id}
                              </div>
                              <div className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                                <span className="text-slate-500 dark:text-slate-400">Última conexión: </span>
                                {formatLastSeen(d.last_seen)}
                              </div>
                              <div className="flex items-center gap-2 mt-2">
                                <button
                                  onClick={() => openRenameDeviceModal(d.device_id, d.nombre_amigable)}
                                  className="text-xs flex items-center gap-1 text-primary hover:underline"
                                >
                                  <Edit2 size={12} />
                                  Renombrar
                                </button>
                                <button
                                  onClick={() => openPreviewModal(d.device_id)}
                                  className="text-xs flex items-center gap-1 text-primary hover:underline"
                                >
                                  <Eye size={12} />
                                  Ver contenido
                                </button>
                                <button
                                  onClick={() => openRestartModal(d.device_id, d.nombre_mostrado || d.device_id)}
                                  className="text-xs flex items-center gap-1 text-amber-600 hover:underline"
                                >
                                  <RotateCcw size={12} />
                                  Reiniciar
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal de renombrar */}
      {renameModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                {renameModal.type === 'server' ? 'Renombrar Servidor' : 'Renombrar Dispositivo'}
              </h3>
              <button
                onClick={closeRenameModal}
                className="text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                disabled={renameSaving}
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-bold text-slate-900 dark:text-slate-200">
                  {renameModal.type === 'server' ? 'Nombre del servidor' : 'Nombre del dispositivo'}
                </label>
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder={renameModal.type === 'server' ? 'Ej: Sede Centro' : 'Ej: Tablet Caja 1'}
                  disabled={renameSaving}
                />
                {renameModal.type === 'device' ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400">Deja vacío para quitar alias del dispositivo.</p>
                ) : null}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={closeRenameModal}
                  className="px-4 h-10 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  disabled={renameSaving}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={submitRename}
                  className="px-4 h-10 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                  disabled={renameSaving}
                >
                  {renameSaving ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de previsualización */}
      {previewModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closePreviewModal}>
          <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Contenido del Dispositivo</h3>
              <button onClick={closePreviewModal} className="text-slate-400 hover:text-slate-900 dark:hover:text-white">
                <X className="size-5" />
              </button>
            </div>

            <div className="p-6">
              {previewModal.loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                </div>
              ) : previewModal.content?.contenido ? (
                <div className="space-y-4">
                  <div className="bg-slate-100 dark:bg-slate-800 rounded-lg p-2">
                    {previewModal.content.contenido.tipo === 'image' ? (
                      <img
                        src={previewModal.content.contenido.thumbnail || previewModal.content.contenido.url}
                        alt={previewModal.content.contenido.titulo}
                        className="max-h-48 mx-auto rounded"
                      />
                    ) : (
                      <video
                        src={previewModal.content.contenido.url}
                        controls
                        className="max-h-48 mx-auto rounded"
                      />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{previewModal.content.contenido.titulo}</p>
                    <p className="text-xs text-slate-500 mt-1 capitalize">{previewModal.content.contenido.tipo}</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <AlertCircle size={40} className="text-slate-400 mb-3" />
                  <p className="text-slate-500 dark:text-slate-400">No hay contenido asignado</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal de reinicio */}
      {restartModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closeRestartModal}>
          <div className="bg-white dark:bg-slate-900 w-full max-w-sm rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="p-6 text-center">
              <div className="w-12 h-12 mx-auto bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mb-4">
                <RotateCcw size={24} className="text-amber-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Reiniciar Dispositivo</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                ¿Estás seguro de reiniciar <span className="font-medium text-slate-900 dark:text-white">{restartModal.deviceName}</span>?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={closeRestartModal}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  disabled={restarting}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleRestart}
                  className="flex-1 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600 disabled:opacity-50"
                  disabled={restarting}
                >
                  {restarting ? 'Reiniciando...' : 'Reiniciar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
