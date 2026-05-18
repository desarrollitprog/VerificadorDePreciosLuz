import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, X, Monitor, Edit2, Play, RotateCcw, Eye, AlertCircle, Clock, Trash, Search, ArrowUpDown, Check } from 'lucide-react';
import ServerCard from './monitoreo/ServerCard';
import { useNotification } from './useNotification';
import {
  getServersStatusWithDevices,
  renameDevice,
  renameServer,
  getDeviceContent,
  restartDevice,
  purgeDevice,
  deleteDevice,
  deleteServer,
  scheduleRestart,
  getQueueStatus,
  ServerStatusDetail,
  DeviceContent,
  QueueStatus,
} from '../services/monitoreoService';
import { Servidor } from '../types';
import { ServerDeviceSelector } from './ServerDeviceSelector';

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
  const [initialLoading, setInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isFirstLoadRef = useRef(true);
  const [renameModal, setRenameModal] = useState<RenameModalState | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [renameSaving, setRenameSaving] = useState(false);

  // Modal de previsualización
  const [previewModal, setPreviewModal] = useState<{ deviceId: string; content: DeviceContent | null; loading: boolean } | null>(null);
  const [previewInterval, setPreviewInterval] = useState<NodeJS.Timeout | null>(null);

  // Modal de reinicio
  const [restartModal, setRestartModal] = useState<{ deviceId: string; deviceName: string } | null>(null);
  const [restarting, setRestarting] = useState(false);

  // Modal de limpiar cache
  const [purgeModal, setPurgeModal] = useState<{ deviceId: string; deviceName: string } | null>(null);
  const [purging, setPurging] = useState(false);

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
    selectAll: boolean;
    selectedServidorIds: number[];
    selectedDispositivoIds: string[];
    expandedServidores: number[];
    hour: string;
    recurring: boolean;
    scheduling: boolean;
  }>({
    isOpen: false,
    selectAll: true,
    selectedServidorIds: [],
    selectedDispositivoIds: [],
    expandedServidores: [],
    hour: '06:35',
    recurring: true,
    scheduling: false,
  });

  // Búsqueda y orden
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'nombre' | 'estado' | 'dispositivos'>('nombre');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const fetchStatus = async () => {
    if (isFirstLoadRef.current) setInitialLoading(true);
    else setIsRefreshing(true);
    setError(null);
    try {
      const data = await getServersStatusWithDevices();
      setServidores(Array.isArray(data) ? data : []);
    } catch {
      if (isFirstLoadRef.current) {
        setServidores([]);
        setError('Error al conectar con el servicio de monitoreo');
      }
    } finally {
      setInitialLoading(false);
      setIsRefreshing(false);
      isFirstLoadRef.current = false;
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

  const fetchQueueStatus = async (deviceId: string, serverIp: string) => {
    try {
      const serversStatus = await getQueueStatus(deviceId);
      const match = serversStatus.find(s => s.server.includes(serverIp));
      if (match) {
        setQueueStatusMap(prev => ({ ...prev, [deviceId]: match.status }));
      }
    } catch {
      // Silently fail — endpoint might not be available
    }
  };

  const pollQueues = useCallback(async () => {
    if (servidores.length === 0) return;
    setLoadingQueues(true);
    await Promise.all(
      servidores.flatMap(s =>
        s.dispositivos.map(d => fetchQueueStatus(d.device_id, s.ip))
      )
    );
    setLoadingQueues(false);
  }, [servidores]);

  useEffect(() => {
    if (servidores.length === 0) return;
    pollQueues();
    const interval = setInterval(pollQueues, 30000);
    return () => clearInterval(interval);
  }, [servidores, pollQueues]);

  useEffect(() => {
    const handleSyncCompleted = (e: CustomEvent<{ deviceId: string }>) => {
      const deviceId = e.detail.deviceId;
      const server = servidores.find(s =>
        s.dispositivos.some(d => d.device_id === deviceId)
      );
      if (server) {
        fetchQueueStatus(deviceId, server.ip);
      }
    };
    window.addEventListener('sync-completed', handleSyncCompleted as EventListener);
    return () => window.removeEventListener('sync-completed', handleSyncCompleted as EventListener);
  }, [servidores]);

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
      if (result.success && result.status === 'QUEUED') {
        showNotification('Comando de reinicio encolado — se ejecutará cuando el dispositivo reconecte', 'warning');
      } else if (result.success) {
        showNotification('Dispositivo reiniciado correctamente', 'success');
      } else {
        showNotification(result.message || 'Error al reiniciar dispositivo', 'error');
      }
      closeRestartModal();
    } catch (error: any) {
      if (error?.response?.data?.status === 'QUEUED') {
        showNotification('Comando de reinicio encolado — se ejecutará cuando el dispositivo reconecte', 'warning');
        closeRestartModal();
      } else {
        showNotification('Error al reiniciar dispositivo', 'error');
      }
    } finally {
      setRestarting(false);
    }
  };

  const openPurgeModal = (deviceId: string, deviceName: string) => {
    setPurgeModal({ deviceId, deviceName });
  };

  const closePurgeModal = () => {
    if (purging) return;
    setPurgeModal(null);
  };

  const handlePurge = async () => {
    if (!purgeModal) return;
    setPurging(true);
    try {
      const result = await purgeDevice(purgeModal.deviceId);
      if (result.success && result.status === 'QUEUED') {
        showNotification('Comando de limpieza encolado — se ejecutará cuando el dispositivo reconecte', 'warning');
      } else if (result.success) {
        showNotification('Cache del dispositivo limpiado y sincronizado correctamente', 'success');
      } else {
        showNotification(result.message || 'Error al limpiar cache del dispositivo', 'error');
      }
      closePurgeModal();
    } catch (error: any) {
      if (error?.response?.data?.status === 'QUEUED') {
        showNotification('Comando de limpieza encolado — se ejecutará cuando el dispositivo reconecte', 'warning');
        closePurgeModal();
      } else {
        showNotification('Error al limpiar cache del dispositivo', 'error');
      }
    } finally {
      setPurging(false);
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

  const servidoresForSelector = useMemo<Servidor[]>(() =>
    servidores.map(s => ({
      id: Number(s.id),
      nombre: s.nombre,
      ip: s.ip,
      api_url: '',
      online: s.online,
      dispositivos: (s.dispositivos || []).map(d => ({
        id: Number(d.device_id),
        codigo_kiosko: d.device_id,
        nombre_amigable: d.nombre_amigable || null,
        online: d.online,
      })),
    })),
  [servidores]);

  const handleRestartSelectAll = () => {
    setScheduleRestartModal(prev => ({
      ...prev,
      selectAll: !prev.selectAll,
      selectedServidorIds: [],
      selectedDispositivoIds: [],
      expandedServidores: [],
    }));
  };

  const handleRestartServidorChange = (id: number, checked: boolean) => {
    setScheduleRestartModal(prev => {
      const srv = servidoresForSelector.find(s => s.id === id);
      const deviceIds = srv?.dispositivos.map(d => String(d.id)) || [];
      return {
        ...prev,
        selectedServidorIds: checked
          ? [...prev.selectedServidorIds, id]
          : prev.selectedServidorIds.filter(sid => sid !== id),
        selectedDispositivoIds: checked
          ? [...prev.selectedDispositivoIds, ...deviceIds]
          : prev.selectedDispositivoIds.filter(did => !deviceIds.includes(did)),
      };
    });
  };

  const handleRestartDispositivoChange = (id: string, checked: boolean) => {
    setScheduleRestartModal(prev => ({
      ...prev,
      selectedDispositivoIds: checked
        ? [...prev.selectedDispositivoIds, id]
        : prev.selectedDispositivoIds.filter(did => did !== id),
    }));
  };

  const handleRestartToggleExpand = (id: number) => {
    setScheduleRestartModal(prev => ({
      ...prev,
      expandedServidores: prev.expandedServidores.includes(id)
        ? prev.expandedServidores.filter(eid => eid !== id)
        : [...prev.expandedServidores, id],
    }));
  };

  const handleScheduleRestart = async () => {
    if (!scheduleRestartModal.hour) return;
    setScheduleRestartModal(prev => ({ ...prev, scheduling: true }));
    try {
      const deviceIds = scheduleRestartModal.selectAll ? [] : scheduleRestartModal.selectedDispositivoIds;
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
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative w-full sm:w-auto">
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
            className="py-2 px-3 bg-slate-100 dark:bg-[#1c2936] rounded-lg text-sm text-slate-900 dark:text-white border-none focus:ring-2 focus:ring-primary w-full sm:w-auto"
          >
            <option value="nombre-asc">Nombre A-Z</option>
            <option value="nombre-desc">Nombre Z-A</option>
            <option value="estado-asc">En línea primero</option>
            <option value="estado-desc">Desconectado primero</option>
            <option value="dispositivos-desc">Más dispositivos</option>
            <option value="dispositivos-asc">Menos dispositivos</option>
          </select>
          <button
            onClick={fetchStatus}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition w-full sm:w-auto justify-center disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
            {isRefreshing ? 'Actualizando...' : 'Refrescar'}
          </button>
          <button
            onClick={() => setScheduleRestartModal(prev => ({ ...prev, isOpen: true }))}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition w-full sm:w-auto justify-center"
          >
            <Clock size={16} />
            Programar Reinicio
          </button>
        </div>
      </div>

      {initialLoading ? (
        <div className="text-slate-500">Cargando monitoreo...</div>
      ) : error && servidores.length === 0 ? (
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
                                <div className="flex items-center gap-2 flex-wrap">
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
                                <div className="flex items-center gap-2 mt-2 flex-wrap">
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
                                    onClick={() => openPurgeModal(d.device_id, d.nombre_mostrado || d.device_id)}
                                    className="text-xs flex items-center gap-1 text-blue-600 hover:underline"
                                  >
                                    <RefreshCw size={12} />
                                    Limpiar y Sincronizar
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

      {/* Modal de limpiar cache */}
      {purgeModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closePurgeModal}>
          <div className="bg-white dark:bg-slate-900 w-full max-w-sm rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="p-6 text-center">
              <div className="w-12 h-12 mx-auto bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-4">
                <RefreshCw size={24} className="text-blue-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Limpiar y Sincronizar</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                ¿Estás seguro de limpiar el cache de <span className="font-medium text-slate-900 dark:text-white">{purgeModal.deviceName}</span>? Se eliminarán todos los banners descargados y se volverán a descargar.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={closePurgeModal}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  disabled={purging}
                >
                  Cancelar
                </button>
                <button
                  onClick={handlePurge}
                  className="flex-1 px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50"
                  disabled={purging}
                >
                  {purging ? 'Limpiando...' : 'Limpiar'}
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
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fade-in" onClick={closeScheduleRestartModal}>
          <div
            className="bg-white dark:bg-[#0f172a] w-full max-w-2xl mx-auto rounded-2xl shadow-2xl border border-blue-500/20 overflow-hidden flex flex-col max-h-[90vh] sm:max-h-none"
            style={{ boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.1)' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-slate-200/70 dark:border-slate-800/70">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: 'rgba(59,130,246,0.1)' }}>
                    <Clock size={18} className="sm:size-5" style={{ color: '#3b82f6' }} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white truncate">Programar Reinicio Masivo</h3>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 truncate">Programa un reinicio en uno o varios dispositivos</p>
                  </div>
                </div>
                <button onClick={closeScheduleRestartModal} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors shrink-0">
                  <X size={20} className="text-slate-400" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-5 sm:space-y-6">
              {/* Toggle todos */}
              <div
                className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl cursor-pointer border-2 transition-all duration-200"
                style={{
                  borderColor: scheduleRestartModal.selectAll ? 'rgba(59,130,246,0.3)' : 'rgba(148,163,184,0.2)',
                  backgroundColor: scheduleRestartModal.selectAll ? 'rgba(59,130,246,0.03)' : 'transparent',
                }}
                onClick={handleRestartSelectAll}
              >
                <div
                  className="w-5 h-5 sm:w-6 sm:h-6 rounded-lg border-2 flex items-center justify-center transition-all duration-200 shrink-0"
                  style={{
                    backgroundColor: scheduleRestartModal.selectAll ? '#3b82f6' : 'transparent',
                    borderColor: scheduleRestartModal.selectAll ? '#3b82f6' : '#94a3b8',
                    transform: scheduleRestartModal.selectAll ? 'scale(1.1)' : 'scale(1)',
                  }}
                >
                  {scheduleRestartModal.selectAll && <Check size={13} className="sm:size-[15px] text-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-100 tracking-wide break-words">
                    PROGRAMAR A TODOS LOS DISPOSITIVOS
                  </span>
                </div>
                <span
                  className="text-[9px] sm:text-[10px] px-2 sm:px-3 py-1 rounded-full font-bold uppercase tracking-widest transition-all duration-200 shrink-0"
                  style={{
                    backgroundColor: scheduleRestartModal.selectAll ? 'rgba(59,130,246,0.12)' : 'rgba(100,116,139,0.1)',
                    color: scheduleRestartModal.selectAll ? '#3b82f6' : '#64748b',
                  }}
                >
                  {scheduleRestartModal.selectAll ? 'ACTIVO' : 'SELECC.'}
                </span>
              </div>

              {/* Selector jerárquico */}
              {!scheduleRestartModal.selectAll && (
                <ServerDeviceSelector
                  servidores={servidoresForSelector}
                  selectedServidorIds={scheduleRestartModal.selectedServidorIds}
                  selectedDispositivoIds={scheduleRestartModal.selectedDispositivoIds}
                  onServidorChange={handleRestartServidorChange}
                  onDispositivoChange={handleRestartDispositivoChange}
                  expandedServidores={scheduleRestartModal.expandedServidores}
                  onToggleExpand={handleRestartToggleExpand}
                  label="Seleccionar servidores para reinicio:"
                  maxHeight="max-h-64"
                  accentColor="#3b82f6"
                />
              )}

              {/* Hora */}
              <div className="space-y-2">
                <label className="block text-[10px] sm:text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock size={12} className="sm:size-[14px]" style={{ color: '#3b82f6' }} />
                  Hora de reinicio
                </label>
                <input
                  type="time"
                  value={scheduleRestartModal.hour}
                  onChange={(e) => setScheduleRestartModal(prev => ({ ...prev, hour: e.target.value }))}
                  className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl border-2 bg-white dark:bg-slate-800/50 text-slate-900 dark:text-white text-base sm:text-lg font-mono tracking-[0.15em] sm:tracking-[0.2em] outline-none transition-all"
                  style={{
                    borderColor: 'rgba(148,163,184,0.3)',
                  }}
                  onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                  onBlur={e => e.currentTarget.style.borderColor = 'rgba(148,163,184,0.3)'}
                />
                <p className="text-xs text-slate-500 dark:text-slate-500 flex items-center gap-1">
                  <AlertCircle size={12} />
                  Si la hora ya pasó hoy, se programará para mañana
                </p>
              </div>

              {/* Recurrente — switch estilo píldora */}
              <label className="flex items-center justify-between p-3 sm:p-4 rounded-xl cursor-pointer border-2 transition-all duration-200 gap-3" style={{ borderColor: 'rgba(148,163,184,0.2)' }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className="w-10 sm:w-11 h-6 rounded-full transition-all duration-300 relative shrink-0"
                    style={{ backgroundColor: scheduleRestartModal.recurring ? '#3b82f6' : 'rgba(100,116,139,0.3)' }}
                  >
                    <div
                      className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md transition-all duration-300"
                      style={{
                        left: scheduleRestartModal.recurring ? 'calc(100% - 22px)' : '2px',
                        boxShadow: scheduleRestartModal.recurring ? '0 0 8px rgba(59,130,246,0.4)' : '0 1px 3px rgba(0,0,0,0.2)',
                      }}
                    />
                  </div>
                  <span className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 break-words">
                    Repetir diariamente a las <span className="font-mono font-bold whitespace-nowrap" style={{ color: '#3b82f6' }}>{scheduleRestartModal.hour}</span>
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={scheduleRestartModal.recurring}
                  onChange={(e) => setScheduleRestartModal(prev => ({ ...prev, recurring: e.target.checked }))}
                  className="sr-only"
                />
              </label>
            </div>


            {/* Footer */}
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-slate-200/70 dark:border-slate-800/70 flex flex-col-reverse sm:flex-row gap-2 sm:gap-3">
              <button
                onClick={closeScheduleRestartModal}
                className="w-full sm:flex-1 px-4 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all"
                style={{ borderColor: 'rgba(148,163,184,0.3)', color: '#64748b' }}
                disabled={scheduleRestartModal.scheduling}
              >
                Cancelar
              </button>
              <button
                onClick={handleScheduleRestart}
                className="w-full sm:flex-1 px-4 py-2.5 rounded-xl text-sm font-bold text-white transition-all disabled:opacity-40"
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                  boxShadow: scheduleRestartModal.scheduling ? 'none' : '0 4px 14px rgba(59,130,246,0.35)',
                }}
                onMouseEnter={e => { if (!scheduleRestartModal.scheduling) e.currentTarget.style.boxShadow = '0 6px 20px rgba(59,130,246,0.5)'; }}
                onMouseLeave={e => { if (!scheduleRestartModal.scheduling) e.currentTarget.style.boxShadow = '0 4px 14px rgba(59,130,246,0.35)'; }}
                disabled={scheduleRestartModal.scheduling || (!scheduleRestartModal.selectAll && scheduleRestartModal.selectedDispositivoIds.length === 0)}
              >
                {scheduleRestartModal.scheduling ? (
                  <span className="flex items-center justify-center gap-2">
                    <RefreshCw size={16} className="animate-spin" />
                    Programando...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <Clock size={16} />
                    Programar
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
