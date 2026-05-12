import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, X, Monitor, Edit2, Play, RotateCcw, Eye, AlertCircle, Clock, Trash, Search, ArrowUpDown } from 'lucide-react';
import ServerCard from './monitoreo/ServerCard';
import { useNotification } from './useNotification';
import {
  getServersStatusWithDevices,
  renameDevice,
  renameServer,
  getDeviceContent,
  restartDevice,
  deleteDevice,
  deleteServer,
  scheduleRestart,
  getQueueStatus,
  ServerStatusDetail,
  DeviceContent,
  QueueStatus,
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
  const [previewInterval, setPreviewInterval] = useState<NodeJS.Timeout | null>(null);

  // Modal de reinicio
  const [restartModal, setRestartModal] = useState<{ deviceId: string; deviceName: string } | null>(null);
  const [restarting, setRestarting] = useState(false);

  // Modal de eliminar dispositivo
  const [deleteDeviceModal, setDeleteDeviceModal] = useState<{ deviceId: string; deviceName: string } | null>(null);
  const [deletingDevice, setDeletingDevice] = useState(false);

  // Estado de cola por dispositivo (FASE 17.2.3)
  const [queueStatusMap, setQueueStatusMap] = useState<Record<string, QueueStatus>>({});
  const [loadingQueues, setLoadingQueues] = useState(false);

  // Modal de eliminar servidor
  const [deleteServerModal, setDeleteServerModal] = useState<{ serverId: string; serverName: string } | null>(null);
  const [deletingServer, setDeletingServer] = useState(false);

  // Modal de programar reinicio masivo
  const [scheduleRestartModal, setScheduleRestartModal] = useState<{
    isOpen: boolean;
    mode: 'all' | 'selected';
    selectedDevices: string[];
    hour: string;
    recurring: boolean;
    scheduling: boolean;
  }>({
    isOpen: false,
    mode: 'all',
    selectedDevices: [],
    hour: '06:35',
    recurring: true,
    scheduling: false,
  });

  // Búsqueda y orden
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'nombre' | 'estado' | 'dispositivos'>('nombre');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getServersStatusWithDevices();
      const servidoresData = Array.isArray(data) ? data : [];
      setServidores(servidoresData);
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

  // Cleanup del intervalo de preview al desmontar
  useEffect(() => {
    return () => {
      if (previewInterval) {
        clearInterval(previewInterval);
      }
    };
  }, [previewInterval]);

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

  const fetchQueueStatus = async (deviceId: string) => {
    try {
      const status = await getQueueStatus(deviceId);
      setQueueStatusMap(prev => ({ ...prev, [deviceId]: status }));
    } catch {
      // Silently fail — endpoint might not be available
    }
  };

  useEffect(() => {
    if (!expandedServerId) return;
    const server = servidores.find(s => s.id === expandedServerId);
    if (!server) return;
    setLoadingQueues(true);
    Promise.all(server.dispositivos.map(d => fetchQueueStatus(d.device_id)))
      .finally(() => setLoadingQueues(false));
  }, [expandedServerId, servidores]);

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
      
      // Actualizar contenido cada 5 segundos
      const interval = setInterval(async () => {
        try {
          const newContent = await getDeviceContent(deviceId);
          setPreviewModal(prev => prev && prev.deviceId === deviceId ? { ...prev, content: newContent } : prev);
        } catch (e) {
          console.error('Error actualizando contenido:', e);
        }
      }, 5000);
      setPreviewInterval(interval);
    } catch {
      showNotification('Error al obtener contenido del dispositivo', 'error');
      setPreviewModal(null);
    }
  };

  const closePreviewModal = () => {
    if (previewInterval) {
      clearInterval(previewInterval);
      setPreviewInterval(null);
    }
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

  const openDeleteDeviceModal = (deviceId: string, deviceName: string) => {
    setDeleteDeviceModal({ deviceId, deviceName });
  };

  const closeDeleteDeviceModal = () => {
    if (deletingDevice) return;
    setDeleteDeviceModal(null);
  };

  const handleDeleteDevice = async () => {
    if (!deleteDeviceModal) return;
    setDeletingDevice(true);
    try {
      const result = await deleteDevice(deleteDeviceModal.deviceId);
      if (result.success) {
        showNotification('Dispositivo eliminado correctamente', 'success');
        await fetchStatus();
      } else {
        showNotification(result.message || 'Error al eliminar dispositivo', 'error');
      }
      closeDeleteDeviceModal();
    } catch {
      showNotification('Error al eliminar dispositivo', 'error');
    } finally {
      setDeletingDevice(false);
    }
  };

  const openDeleteServerModal = (serverId: string, serverName: string) => {
    setDeleteServerModal({ serverId, serverName });
  };

  const closeDeleteServerModal = () => {
    if (deletingServer) return;
    setDeleteServerModal(null);
  };

  const handleDeleteServer = async () => {
    if (!deleteServerModal) return;
    setDeletingServer(true);
    try {
      const result = await deleteServer(deleteServerModal.serverId);
      if (result.success) {
        showNotification('Servidor eliminado correctamente', 'success');
        await fetchStatus();
      } else {
        showNotification(result.message || 'Error al eliminar servidor', 'error');
      }
      closeDeleteServerModal();
    } catch {
      showNotification('Error al eliminar servidor', 'error');
    } finally {
      setDeletingServer(false);
    }
  };

  const closeScheduleRestartModal = () => {
    if (scheduleRestartModal.scheduling) return;
    setScheduleRestartModal(prev => ({ ...prev, isOpen: false }));
  };

  const handleScheduleRestart = async () => {
    if (!scheduleRestartModal.hour) return;
    setScheduleRestartModal(prev => ({ ...prev, scheduling: true }));
    try {
      const deviceIds = scheduleRestartModal.mode === 'selected' ? scheduleRestartModal.selectedDevices : [];
      const result = await scheduleRestart({
        device_ids: deviceIds,
        hour: scheduleRestartModal.hour,
        recurring: scheduleRestartModal.recurring,
      });
      if (result.enviados > 0 || result.fallidos === 0) {
        showNotification(
          `Reinicio programado para ${result.enviados} dispositivo(s) a las ${scheduleRestartModal.hour}${scheduleRestartModal.recurring ? ' (diario)' : ''}`,
          'success'
        );
      } else {
        showNotification(`Error: ${result.fallidos} dispositivo(s) no recibieron el comando`, 'error');
      }
      closeScheduleRestartModal();
    } catch {
      showNotification('Error al programar reinicio', 'error');
    } finally {
      setScheduleRestartModal(prev => ({ ...prev, scheduling: false }));
    }
  };

  const filteredAndSortedServidores = servidores
    .filter(s => {
      if (!search) return true;
      const searchLower = search.toLowerCase();
      return (
        s.nombre.toLowerCase().includes(searchLower) ||
        s.ip.toLowerCase().includes(searchLower) ||
        s.dispositivos.some(d =>
          d.device_id.toLowerCase().includes(searchLower) ||
          (d.nombre_amigable || '').toLowerCase().includes(searchLower) ||
          (d.nombre_mostrado || '').toLowerCase().includes(searchLower)
        )
      );
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'nombre') {
        comparison = a.nombre.localeCompare(b.nombre);
      } else if (sortBy === 'estado') {
        comparison = (a.online ? 0 : 1) - (b.online ? 0 : 1);
      } else if (sortBy === 'dispositivos') {
        comparison = b.dispositivos_online - a.dispositivos_online;
      }
      return sortDir === 'asc' ? comparison : -comparison;
    });

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

  const formatDuration = (seconds: number | null) => {
    if (!seconds || seconds <= 0) return null;

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  const getDeviceUptime = (d: any) => {
    if (d.sesion_activa && d.tiempo_actual) {
      return formatDuration(d.tiempo_actual);
    } else if (!d.sesion_activa && d.ultima_duracion) {
      return formatDuration(d.ultima_duracion);
    }
    return null;
  };

  return (
    <div className="flex flex-col min-w-0 p-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Servidores y Dispositivos</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Monitoreo en tiempo real</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              className="pl-9 pr-8 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full sm:w-48 transition-all"
              placeholder="Buscar..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                ×
              </button>
            )}
          </div>
          <select
            value={`${sortBy}-${sortDir}`}
            onChange={e => {
              const [by, dir] = e.target.value.split('-');
              setSortBy(by as 'nombre' | 'estado' | 'dispositivos');
              setSortDir(dir as 'asc' | 'desc');
            }}
            className="py-2 px-3 bg-slate-100 dark:bg-[#1c2936] rounded-lg text-sm text-slate-900 dark:text-white border-none focus:ring-2 focus:ring-primary"
          >
            <option value="nombre-asc">Nombre A-Z</option>
            <option value="nombre-desc">Nombre Z-A</option>
            <option value="estado-asc">Online primero</option>
            <option value="estado-desc">Offline primero</option>
            <option value="dispositivos-desc">Más dispositivos</option>
            <option value="dispositivos-asc">Menos dispositivos</option>
          </select>
          <button
            onClick={fetchStatus}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <RefreshCw size={16} />
            Refrescar
          </button>
          <button
            onClick={() => setScheduleRestartModal(prev => ({ ...prev, isOpen: true }))}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <Clock size={16} />
            Programar Reinicio
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-slate-500">Cargando monitoreo...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-baseline">
          {filteredAndSortedServidores.length === 0 ? (
            <div className="col-span-full text-center text-slate-500 py-8">No se encontraron servidores.</div>
          ) : (
            filteredAndSortedServidores.map((s) => (
              <div key={s.id} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                <div className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <ServerCard
                      className="flex-1"
                      nombre={s.nombre}
                      ip={s.ip}
                      online={s.online}
                      porcentaje_uso={s.porcentaje_uso}
                      onRename={() => openRenameServerModal(s)}
                    />
                    <button
                      onClick={() => openDeleteServerModal(s.id, s.nombre)}
                      className="p-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition shrink-0"
                      title="Eliminar servidor"
                    >
                      <Trash size={16} />
                    </button>
                  </div>

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
                                  {getDeviceUptime(d) && (
                                    <span className={`ml-auto text-xs font-medium px-1.5 py-0.5 rounded ${
                                      d.sesion_activa 
                                        ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30' 
                                        : 'text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800'
                                    }`}>
                                      {getDeviceUptime(d)}
                                    </span>
                                  )}
                                  {queueStatusMap[d.device_id] && queueStatusMap[d.device_id]!.total > 0 && (
                                    <span className="ml-1 text-xs font-medium px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300" title={`${queueStatusMap[d.device_id]!.pending} pendientes, ${queueStatusMap[d.device_id]!.inflight} en vuelo`}>
                                      Cola: {queueStatusMap[d.device_id]!.total}
                                    </span>
                                  )}
                                  {queueStatusMap[d.device_id] && (
                                    <span className={`ml-1 text-xs font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 ${(queueStatusMap[d.device_id]!.pending_sync || queueStatusMap[d.device_id]!.pending_reboot) ? '' : 'opacity-50'}`} title="Comando pendiente de reconexión del dispositivo">
                                      En espera: {(queueStatusMap[d.device_id]!.pending_sync ? 1 : 0) + (queueStatusMap[d.device_id]!.pending_reboot ? 1 : 0)}
                                    </span>
                                  )}
                                  {loadingQueues && !queueStatusMap[d.device_id] && (
                                    <span className="ml-1 text-xs text-slate-400">...</span>
                                  )}
                                </div>
                                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                  ID: {d.device_id}
                                </div>
                                <div className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                                  <span className="text-slate-500 dark:text-slate-400">Última conexión: </span>
                                  {formatLastSeen(d.last_seen)}
                                </div>
                                <div className="text-xs mt-1">
                                  {d.hora_reinicio ? (
                                    <span className="text-blue-600 dark:text-blue-400">
                                      <Clock size={10} className="inline mr-1" />
                                      Reinicio: {d.hora_reinicio}
                                      {d.reinicio_recurrente ? ' (diario)' : ''}
                                    </span>
                                  ) : (
                                    <span className="text-slate-400 dark:text-slate-500">Sin reinicio</span>
                                  )}
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
                                  <button
                                    onClick={() => openDeleteDeviceModal(d.device_id, d.nombre_mostrado || d.device_id)}
                                    className="text-xs flex items-center gap-1 text-red-500 hover:underline"
                                  >
                                    <Trash size={12} />
                                    Eliminar
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
            ))
          )}
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

      {/* Modal de eliminar dispositivo */}
      {deleteDeviceModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closeDeleteDeviceModal}>
          <div className="bg-white dark:bg-slate-900 w-full max-w-sm rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="p-6 text-center">
              <div className="w-12 h-12 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
                <Trash size={24} className="text-red-500" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Eliminar Dispositivo</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                ¿Estás seguro de eliminar <span className="font-medium text-slate-900 dark:text-white">{deleteDeviceModal.deviceName}</span>? Esta acción no se puede deshacer.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={closeDeleteDeviceModal}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  disabled={deletingDevice}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeleteDevice}
                  className="flex-1 px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50"
                  disabled={deletingDevice}
                >
                  {deletingDevice ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de eliminar servidor */}
      {deleteServerModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closeDeleteServerModal}>
          <div className="bg-white dark:bg-slate-900 w-full max-w-sm rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="p-6 text-center">
              <div className="w-12 h-12 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
                <Trash size={24} className="text-red-500" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Eliminar Servidor</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">
                ¿Estás seguro de eliminar <span className="font-medium text-slate-900 dark:text-white">{deleteServerModal.serverName}</span>?
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400 mb-6">
                Los dispositivos asociados se desvincularán pero no se eliminarán.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={closeDeleteServerModal}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  disabled={deletingServer}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeleteServer}
                  className="flex-1 px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50"
                  disabled={deletingServer}
                >
                  {deletingServer ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de programar reinicio masivo */}
      {scheduleRestartModal.isOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closeScheduleRestartModal}>
          <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Programar Reinicio Masivo</h3>
                <button onClick={closeScheduleRestartModal} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                  <X size={20} />
                </button>
              </div>
              
              <div className="space-y-4">
                {/* Selección de dispositivos */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Dispositivos</label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="deviceMode"
                        checked={scheduleRestartModal.mode === 'all'}
                        onChange={() => setScheduleRestartModal(prev => ({ ...prev, mode: 'all', selectedDevices: [] }))}
                        className="text-primary"
                      />
                      <span className="text-sm text-slate-700 dark:text-slate-300">Todos los dispositivos</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="deviceMode"
                        checked={scheduleRestartModal.mode === 'selected'}
                        onChange={() => setScheduleRestartModal(prev => ({ ...prev, mode: 'selected' }))}
                        className="text-primary"
                      />
                      <span className="text-sm text-slate-700 dark:text-slate-300">Seleccionar dispositivos</span>
                    </label>
                  </div>
                  
                  {scheduleRestartModal.mode === 'selected' && (
                    <div className="mt-2 max-h-32 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg p-2">
                      {servidores.flatMap(s => s.dispositivos).map(d => (
                        <label key={d.device_id} className="flex items-center gap-2 cursor-pointer py-1">
                          <input
                            type="checkbox"
                            checked={scheduleRestartModal.selectedDevices.includes(d.device_id)}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              setScheduleRestartModal(prev => ({
                                ...prev,
                                selectedDevices: checked
                                  ? [...prev.selectedDevices, d.device_id]
                                  : prev.selectedDevices.filter(id => id !== d.device_id)
                              }));
                            }}
                            className="text-primary"
                          />
                          <span className="text-sm text-slate-600 dark:text-slate-400">
                            {d.nombre_amigable || d.device_id}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                {/* Hora */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    Hora de reinicio
                  </label>
                  <input
                    type="time"
                    value={scheduleRestartModal.hour}
                    onChange={(e) => setScheduleRestartModal(prev => ({ ...prev, hour: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Si la hora ya pasó hoy, se programará para mañana
                  </p>
                </div>

                {/* Recurrente */}
                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={scheduleRestartModal.recurring}
                      onChange={(e) => setScheduleRestartModal(prev => ({ ...prev, recurring: e.target.checked }))}
                      className="text-primary rounded"
                    />
                    <span className="text-sm text-slate-700 dark:text-slate-300">
                      Repetir diariamente a las {scheduleRestartModal.hour}
                    </span>
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={closeScheduleRestartModal}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  disabled={scheduleRestartModal.scheduling}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleScheduleRestart}
                  className="flex-1 px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50"
                  disabled={scheduleRestartModal.scheduling || (scheduleRestartModal.mode === 'selected' && scheduleRestartModal.selectedDevices.length === 0)}
                >
                  {scheduleRestartModal.scheduling ? 'Programando...' : 'Programar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
