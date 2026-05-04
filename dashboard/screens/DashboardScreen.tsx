import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNotification } from '../components/useNotification';
import { Search, UploadCloud, MoreVertical, Eye, Trash, Film, Plus, Server, Smartphone, ChevronDown, ChevronRight, Clock } from 'lucide-react';
import { getVideos, uploadMedia, deleteVideo, sincronizarServidores, updateBannerMetadata, updateBannerAsignations, FileMetadata } from '../services/videoService';
import { Video, Servidor } from '../types';
import { ServerDeviceSelector } from '../components/ServerDeviceSelector';
import {
  getForceSyncJobStatus,
  getSecondaryServersVideoCounts,
  startForceSyncJob,
  getServersStatusWithDevices,
} from '../services/monitoreoService';


// Formatea una fecha a la hora de Caracas (UTC-4) sin depender de la hora local del sistema
function formatCaracasTime(dateString: string | Date): string {
  const date = typeof dateString === 'string' ? new Date(dateString) : new Date(dateString.getTime());
  return date.toLocaleString('es-VE', { timeZone: 'America/Caracas' });
}

type SyncServerProgress = {
  nombre: string;
  ip: string;
  total: number;
  confirmed: number;
  failed: number;
  progress: number;
  ok?: boolean;
  reason?: string;
};

type SecondaryVideoCounter = {
  id: string;
  nombre: string;
  ip: string;
  videos_actuales: number;
};

const normalizeServerProgress = (details: any[] = []): SyncServerProgress[] => {
  return details.map((detail) => {
    const total = Number(detail.sync_total ?? 0);
    const confirmed = Number(detail.sync_confirmed ?? 0);
    const failed = Number(detail.sync_failed ?? 0);
    const progress = total > 0 ? Math.min(100, Math.round((confirmed / total) * 100)) : 0;

    return {
      nombre: String(detail.nombre ?? detail.ip ?? 'Servidor'),
      ip: String(detail.ip ?? ''),
      total,
      confirmed,
      failed,
      progress,
      ok: detail.ok,
      reason: detail.reason,
    };
  });
};

export const DashboardScreen: React.FC = () => {
    // Drag & drop states
    const [dragActive, setDragActive] = useState(false);
    // Feedback por archivo
    const [uploadStatuses, setUploadStatuses] = useState<Array<'pending' | 'uploading' | 'success' | 'error'>>([]);
  const showNotification = useNotification();
  const [preview, setPreview] = useState<{url: string, tipo: string, titulo: string} | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const handlePreview = useCallback((video: Video) => {
    setPreview({ url: video.url, tipo: video.tipo, titulo: video.titulo || video.filename });
    setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 50);
  }, []);
  
  const closePreview = useCallback(() => setPreview(null), []);
  
  // Efecto para precargar video 15 segundos antes de reproducir
  useEffect(() => {
    if (preview && preview.tipo === 'video' && videoRef.current) {
      const videoEl = videoRef.current;
      videoEl.load();
      videoEl.play().catch(() => {});
      
      const preloadInterval = setInterval(() => {
        if (videoEl.readyState >= 2) {
          clearInterval(preloadInterval);
        }
      }, 500);
      
      return () => clearInterval(preloadInterval);
    }
  }, [preview]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const videosPerPage = 12;
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Batch upload states
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileMetadatas, setFileMetadatas] = useState<FileMetadata[]>([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [currentEditIndex, setCurrentEditIndex] = useState<number | null>(null);
  const [servidores, setServidores] = useState<Servidor[]>([]);
  const [uploadExpandedServers, setUploadExpandedServers] = useState<number[]>([]);

  const [syncLoading, setSyncLoading] = useState(false);
  const [syncServerProgress, setSyncServerProgress] = useState<SyncServerProgress[]>([]);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [secondaryVideoCounts, setSecondaryVideoCounts] = useState<SecondaryVideoCounter[]>([]);
  
  // Sync modal states
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);
  const [syncAllDevices, setSyncAllDevices] = useState(true);
  const [syncServidorIds, setSyncServidorIds] = useState<number[]>([]);
  const [syncDispositivoIds, setSyncDispositivoIds] = useState<string[]>([]);
  const [syncExpandedServers, setSyncExpandedServers] = useState<number[]>([]);
  const [selectedSecondaryServerId, setSelectedSecondaryServerId] = useState<string>('');
  
  // Edit modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingVideo, setEditingVideo] = useState<Video | null>(null);
  const [editFormData, setEditFormData] = useState({
    titulo: '',
    activo: true,
    fechaInicio: '',
    fechaFin: '',
  });
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [deletingVideoId, setDeletingVideoId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; videoId: string | null; titulo: string }>({ open: false, videoId: null, titulo: '' });
  const [editAsignacionTodos, setEditAsignacionTodos] = useState(true);
  const [editServidorIds, setEditServidorIds] = useState<number[]>([]);
  const [editDispositivoIds, setEditDispositivoIds] = useState<string[]>([]);
  const [editExpandedServers, setEditExpandedServers] = useState<number[]>([]);

  // Estado para vista compacta
  const [expandedFiles, setExpandedFiles] = useState<boolean[]>([]);

  useEffect(() => {
    async function fetchVideos() {
      setLoading(true);
      try {
        const data = await getVideos();
        setVideos(Array.isArray(data) ? data : []);
      } catch (err: any) {
        setVideos([]);
        setError('Error Cargando Videos');
      } finally {
        setLoading(false);
      }
    }
    fetchVideos();
  }, []);

  useEffect(() => {
    async function fetchServidores() {
      try {
        const data = await getServersStatusWithDevices();
        const mapped: Servidor[] = data.map((s: any) => ({
          id: Number(s.id),
          nombre: s.nombre,
          ip: s.ip,
          api_url: `http://${s.ip}:8000`,
          online: s.online,
          dispositivos: s.dispositivos.map((d: any) => ({
            id: d.device_id,
            codigo_kiosko: d.device_id,
            nombre_amigable: d.nombre_amigable,
            online: d.online,
          })),
        }));
        setServidores(mapped);
      } catch {
        setServidores([]);
      }
    }
    fetchServidores();
  }, []);

  useEffect(() => {
    let mounted = true;

    const loadSecondaryVideoCounts = async () => {
      try {
        const data = await getSecondaryServersVideoCounts();
        if (!mounted) return;

        setSecondaryVideoCounts(data);
        setSelectedSecondaryServerId((prev) => {
          if (!data.length) return '';
          const exists = data.some((server) => server.id === prev);
          return exists ? prev : data[0].id;
        });
      } catch {
        if (!mounted) return;
        setSecondaryVideoCounts([]);
        setSelectedSecondaryServerId('');
      }
    };

    loadSecondaryVideoCounts();
    const intervalId = setInterval(loadSecondaryVideoCounts, 30000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const selectedSecondaryServer = secondaryVideoCounts.find((server) => server.id === selectedSecondaryServerId) || null;

  const resetUploadModal = () => {
    setSelectedFiles([]);
    setFileMetadatas([]);
    setIsUploadModalOpen(false);
    setCurrentEditIndex(null);
    setUploadExpandedServers([]);
    setUploadStatuses([]);
    setExpandedFiles([]);
  };

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
      setUploadStatuses([]);
    if (!event.target.files?.length) return;
    const files = Array.from(event.target.files);
    const maxSize = 20 * 1024 * 1024;
    const validFiles: File[] = [];
    const metadatas: FileMetadata[] = [];
    let rejected = 0;
    files.forEach(file => {
      if (file.size > maxSize) {
        rejected++;
        return;
      }
      const decoratedDefault = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
      validFiles.push(file);
      metadatas.push({
        titulo: decoratedDefault || file.name,
        fechaInicio: '',
        fechaFin: '',
        activo: true,
        asignacionTodos: true,
        servidorIds: [],
        dispositivoIds: [],
      });
    });
    if (rejected > 0) {
      setError(`Se rechazaron ${rejected} archivos por tamaño (max 20MB).`);
      showNotification(`Se rechazaron ${rejected} archivos por tamaño (max 20MB)`, 'warning');
    }
    if (validFiles.length === 0) return;
    setSelectedFiles(validFiles);
    setFileMetadatas(metadatas);
    setIsUploadModalOpen(true);
    setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 50);
    event.target.value = '';
  };

  // Convierte fechas locales tipo 'dd/MM/yyyy hh:mm a. m.' a ISO
  function parseLocalDateString(str: string): string | null {
    // Si es formato ISO, retorna igual
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(str)) return str;
    // Si es formato 'dd/MM/yyyy hh:mm a. m.'
    const match = str.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{1,2}):(\d{2}) (\d{1,2})\.(\w+)\.$/);
    if (match) {
      let [_, day, month, year, hour, minute, ampmHour, ampm] = match;
      hour = String(Number(hour));
      if (ampm.toLowerCase().startsWith('p')) hour = String(Number(hour) + 12);
      return `${year}-${month}-${day}T${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
    }
    // Si es formato 'dd/MM/yyyy hh:mm', sin am/pm
    const match2 = str.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{1,2}):(\d{2})/);
    if (match2) {
      let [_, day, month, year, hour, minute] = match2;
      return `${year}-${month}-${day}T${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
    }
    return null;
  }

  const handleSubmitUpload = async () => {
    if (selectedFiles.length === 0) {
      showNotification('Selecciona archivos primero', 'warning');
      return;
    }
    for (let i = 0; i < fileMetadatas.length; i++) {
      const meta = fileMetadatas[i];
      if (!meta.titulo.trim()) {
        showNotification(`El título es obligatorio para el archivo #${i + 1}`, 'warning');
        return;
      }
      let fechaInicioIso = meta.fechaInicio || null;
      let fechaFinIso = meta.fechaFin || null;
      if (fechaInicioIso && fechaFinIso && new Date(fechaInicioIso) > new Date(fechaFinIso)) {
        showNotification(`La fecha de inicio no puede ser mayor a la fecha fin para el archivo #${i + 1}`, 'warning');
        return;
      }
      if (!meta.asignacionTodos && meta.servidorIds.length === 0) {
        showNotification(`Selecciona al menos un servidor para el archivo #${i + 1}`, 'warning');
        return;
      }
    }
    setUploading(true);
    setError(null);
    setUploadStatuses(Array(selectedFiles.length).fill('pending'));
    let allSuccess = true;
    for (let i = 0; i < selectedFiles.length; i++) {
      setUploadStatuses(prev => {
        const next = [...prev];
        next[i] = 'uploading';
        return next;
      });
      try {
        let fechaInicioIso = fileMetadatas[i].fechaInicio || null;
        let fechaFinIso = fileMetadatas[i].fechaFin || null;
        await uploadMedia(selectedFiles[i], {
          titulo: fileMetadatas[i].titulo,
          fechaInicio: fechaInicioIso,
          fechaFin: fechaFinIso,
          activo: fileMetadatas[i].activo,
          asignacionTodos: fileMetadatas[i].asignacionTodos,
          servidorIds: fileMetadatas[i].servidorIds,
          dispositivoIds: fileMetadatas[i].dispositivoIds,
        });
        setUploadStatuses(prev => {
          const next = [...prev];
          next[i] = 'success';
          return next;
        });
      } catch (err) {
        setUploadStatuses(prev => {
          const next = [...prev];
          next[i] = 'error';
          return next;
        });
        allSuccess = false;
      }
    }
    try {
      const data = await getVideos();
      setVideos(data);
    } catch {}
    if (allSuccess) {
      showNotification('Todos los archivos subidos correctamente', 'success');
      resetUploadModal();
    } else {
      showNotification('Algunos archivos fallaron al subir', 'error');
    }
    setUploading(false);
  };

  const handleDeleteClick = (videoId: string, titulo: string) => {
    setConfirmDelete({ open: true, videoId, titulo });
  };

  const handleDeleteConfirm = async () => {
    if (!confirmDelete.videoId) return;
    setError(null);
    setDeletingVideoId(confirmDelete.videoId);
    setConfirmDelete({ open: false, videoId: null, titulo: '' });
    try {
      await deleteVideo(confirmDelete.videoId);
      showNotification('Archivo borrado correctamente', 'success');
    } catch (err: any) {
      setError('Error deleting video');
      showNotification('Error al borrar archivo', 'error');
    } finally {
      setDeletingVideoId(null);
      try {
        const data = await getVideos();
        setVideos(data);
      } catch {}
    }
  };

  const handleDeleteCancel = () => {
    setConfirmDelete({ open: false, videoId: null, titulo: '' });
  };

  const handleForceSync = async () => {
    setSyncLoading(true);
    setSyncServerProgress([]);
    try {
      const start = await startForceSyncJob();
      if (!start.success || !start.job_id) {
        showNotification('No se pudo iniciar la sincronización', 'error');
        return;
      }

      const maxPolls = 90;
      const pollDelayMs = 2000;
      let finalStatus: any = null;

      for (let i = 0; i < maxPolls; i++) {
        await new Promise((resolve) => setTimeout(resolve, pollDelayMs));
        const status = await getForceSyncJobStatus(start.job_id);
        setSyncServerProgress(normalizeServerProgress(status.details || []));

        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          finalStatus = status;
          break;
        }
      }

      if (!finalStatus) {
        showNotification('Sincronización en progreso', 'warning');
        return;
      }

      setLastSyncAt(formatCaracasTime(new Date()));

      if (finalStatus.status === 'COMPLETED') {
        const successCount = finalStatus.success_count ?? 0;
        const failedCount = finalStatus.failed_count ?? 0;
        const totalOnline = finalStatus.total_online ?? 0;
        if (failedCount > 0) {
          showNotification(
            `Sincronización completada con fallos (${failedCount}/${totalOnline || successCount + failedCount}).`,
            'error'
          );
        } else {
          showNotification('Sincronización completada', 'success');
        }
      } else {
        showNotification('Sincronización fallida', 'error');
      }
    } catch (error: any) {
      showNotification('Error al ejecutar la sincronización', 'error');
    } finally {
      setSyncLoading(false);
    }
  };

  const executeSync = async () => {
    setSyncLoading(true);
    setSyncServerProgress([]);
    try {
      if (syncAllDevices) {
        await handleForceSync();
        return;
      }

      if (syncServidorIds.length === 0 && syncDispositivoIds.length === 0) {
        showNotification('Selecciona al menos un servidor o dispositivo', 'warning');
        return;
      }

      const start = await sincronizarServidores(syncServidorIds, syncDispositivoIds);
      if (!start.success || !start.job_id) {
        showNotification('No se pudo iniciar la sincronización', 'error');
        return;
      }

      showNotification('Sincronización iniciada correctamente', 'success');

      const maxPolls = 90;
      const pollDelayMs = 2000;
      let finalStatus: any = null;

      for (let i = 0; i < maxPolls; i++) {
        await new Promise((resolve) => setTimeout(resolve, pollDelayMs));
        const status = await getForceSyncJobStatus(start.job_id);
        setSyncServerProgress(normalizeServerProgress(status.details || []));

        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          finalStatus = status;
          break;
        }
      }

      if (!finalStatus) {
        showNotification('Sincronización en progreso', 'warning');
        return;
      }

      setLastSyncAt(formatCaracasTime(new Date()));

      if (finalStatus.status === 'COMPLETED') {
        const successCount = finalStatus.success_count ?? 0;
        const failedCount = finalStatus.failed_count ?? 0;
        const totalOnline = finalStatus.total_online ?? 0;
        if (failedCount > 0) {
          showNotification(
            `Sincronización completada con fallos (${failedCount}/${totalOnline || successCount + failedCount}).`,
            'error'
          );
        } else {
          showNotification('Sincronización completada', 'success');
        }
      } else {
        showNotification('Sincronización fallida', 'error');
      }
    } catch (error: any) {
      showNotification('Error al ejecutar la sincronización', 'error');
    } finally {
      setSyncLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8">
      {/* Title & Search */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">Mis Videos</h2>
          <p className="text-slate-500 mt-1">ADMINISTRA TUS VIDEOS YA SEA SUBIR, ELIMINAR y SINCRONIZAR.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              className="pl-10 pr-8 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full sm:w-64 transition-all"
              placeholder="Buscar Videos..."
              value={search}
              onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
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
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow hover:bg-blue-700 transition disabled:opacity-50"
            onClick={() => {
              setIsSyncModalOpen(true);
              setTimeout(() => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }, 50);
            }}
            disabled={syncLoading}
          >
            {syncLoading ? 'Sincronizando...' : 'Sincronizar'}
          </button>
        </div>
      </div>

      {/* Upload Area */}
      <div
        className={`relative group cursor-pointer ${dragActive ? 'ring-2 ring-primary' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={e => { e.preventDefault(); setDragActive(false); }}
        onDrop={e => {
          e.preventDefault();
          setDragActive(false);
          const files = Array.from(e.dataTransfer.files);
          const fakeEvent = { target: { files } } as any;
          handleUpload(fakeEvent);
        }}
      >
        <div className="absolute inset-0 bg-primary/5 rounded-xl border-2 border-dashed border-primary/30 group-hover:border-primary/60 transition-colors pointer-events-none"></div>
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center rounded-xl bg-slate-50/50 dark:bg-[#151f2b] transition-all group-hover:bg-slate-100 dark:group-hover:bg-[#1a2532]">
          <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
            <UploadCloud className="text-primary" size={28} />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Sube Nuevo Contenido</h3>
          <p className="text-slate-500 text-sm max-w-sm mb-6">Click o arrastra aquí para subir Videos o Imagenes (Tamaño maximo = 20MB)</p>
          <label className="px-6 py-2.5 bg-primary hover:bg-primary/90 text-white text-sm font-semibold rounded-lg shadow-lg shadow-primary/20 transition-all flex items-center gap-2 cursor-pointer">
            <Plus size={18} />
            Seleccionar Archivos
            <input type="file" accept="video/mp4,video/mkv,image/png,image/jpeg,image/jpg" className="hidden" multiple onChange={handleUpload} />
          </label>
          {uploading && <div className="mt-2 text-primary">Subiendo...</div>}
          {error && <div className="mt-2 text-red-500">{error}</div>}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-[#1c2936] p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Film className="text-slate-400 shrink-0" size={20} />
                  <p className="text-slate-500 text-sm font-semibold uppercase tracking-wider">Videos Totales</p>
                </div>
                <div className="flex items-center gap-2 min-w-0 sm:max-w-[65%] w-full sm:w-auto">
                  <span className="text-xs text-slate-500 whitespace-nowrap">Servidor secundario:</span>
                  <select
                    className="text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-2 py-1 h-8 min-w-0 w-full sm:w-[240px]"
                    value={selectedSecondaryServerId}
                    onChange={(e) => setSelectedSecondaryServerId(e.target.value)}
                    disabled={secondaryVideoCounts.length === 0}
                  >
                    {secondaryVideoCounts.length === 0 ? (
                      <option value="">Sin servidores conectados</option>
                    ) : (
                      secondaryVideoCounts.map((server) => (
                        <option key={server.id} value={server.id} title={`${server.nombre} (${server.ip})`}>
                          {server.nombre} ({server.ip})
                        </option>
                      ))
                    )}
                  </select>
                </div>
              </div>

              <div className="mt-3 rounded-lg border border-slate-200 dark:border-slate-700 divide-x divide-slate-200 dark:divide-slate-700 grid grid-cols-2">
                <div className="px-3 py-2 text-center">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Local</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white leading-tight">
                    {Array.isArray(videos) ? videos.length : 0}
                  </p>
                </div>
                <div className="px-3 py-2 text-center">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Secundario</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white leading-tight">
                    {selectedSecondaryServer ? selectedSecondaryServer.videos_actuales : 0}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#1c2936] p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-slate-500 text-sm font-semibold uppercase tracking-wider">
                Progreso de sincronización por servidor
              </p>
              {lastSyncAt && (
                <p className="text-[11px] text-slate-500 mt-1">Última sync: {lastSyncAt}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                setSyncServerProgress([]);
                setLastSyncAt(null);
              }}
              className="text-xs px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
              disabled={syncLoading || (syncServerProgress.length === 0 && !lastSyncAt)}
            >
              Limpiar resultado
            </button>
          </div>

          {syncServerProgress.length === 0 ? (
            <p className="text-sm text-slate-500 mt-2">Sin sincronización activa.</p>
          ) : (
            <div className="mt-3 space-y-3">
              {syncServerProgress.map((serverProgress) => (
                <div key={`${serverProgress.ip}-${serverProgress.nombre}`}>
                  <div className="flex justify-between text-xs mb-1 gap-2">
                    <span className="truncate">{serverProgress.nombre} ({serverProgress.ip})</span>
                    <span>
                      {serverProgress.confirmed}/{serverProgress.total} ({serverProgress.progress}%)
                    </span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-2.5 ${serverProgress.failed > 0 ? 'bg-amber-500' : 'bg-primary'}`}
                      style={{ width: `${serverProgress.progress}%` }}
                    />
                  </div>
                  {serverProgress.reason ? <p className="text-[11px] text-red-500 mt-1">{serverProgress.reason}</p> : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">Contenido Subido Recientemente</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {(() => {
            // Filtrar videos por búsqueda
            const filteredVideos = videos.filter(v => {
              const searchLower = search.toLowerCase();
              return (
                v.titulo?.toLowerCase().includes(searchLower) ||
                v.filename?.toLowerCase().includes(searchLower) ||
                v.id?.toString().includes(searchLower)
              );
            });
            // Calcular paginación
            const totalPages = Math.ceil(filteredVideos.length / videosPerPage);
            const startIndex = (currentPage - 1) * videosPerPage;
            const paginatedVideos = filteredVideos.slice(startIndex, startIndex + videosPerPage);
            // Renderizar tarjetas
            return paginatedVideos.length > 0 ? paginatedVideos.map((video) => (
              <div key={video.id} className="group relative bg-white dark:bg-[#1c2936] rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 hover:border-primary/40 transition-all hover:-translate-y-1 hover:shadow-lg hover:shadow-slate-900/10 dark:hover:shadow-black/30 flex flex-col">
                {/* Thumbnail */}
                <div className="aspect-video bg-slate-800 relative overflow-hidden">
                  {video.tipo === 'image' ? (
                    <img src={video.thumbnail} alt={video.titulo || video.filename} className="w-full h-full object-cover" />
                  ) : (
                    <img src={video.thumbnail || video.url} alt={video.titulo || video.filename} className="w-full h-full object-cover" />
                  )}
                  <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-colors"></div>
                  {video.duration && video.tipo === 'video' && (
                    <div className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] font-bold px-1.5 py-0.5 rounded backdrop-blur-sm">
                      {video.duration} seg
                    </div>
                  )}
                </div>
                {/* Info */}
                <div className="p-4 flex-1 flex flex-col">
                  <div className="flex justify-between items-start gap-2 mb-2">
                    <h4 className="text-slate-900 dark:text-white font-semibold text-sm leading-tight line-clamp-2" title={video.titulo || video.filename}>
                      {video.titulo || video.filename}
                    </h4>
                    <button 
                      onClick={() => {
                        setEditingVideo(video);
                        setEditFormData({
                          titulo: video.titulo || video.filename || '',
                          activo: video.activo ?? true,
                          fechaInicio: video.fechaInicio || '',
                          fechaFin: video.fechaFin || '',
                        });
                        // Inicializar estados de asignación
                        const asignacionTodos = video.asignacion_todos ?? true;
                        setEditAsignacionTodos(asignacionTodos);
                        if (!asignacionTodos && video.asignaciones) {
                          const srvIds = [...new Set(video.asignaciones.map((a: any) => a.servidor_id).filter(Boolean))];
                          const dispIds = video.asignaciones.map((a: any) => a.dispositivo_id).filter(Boolean);
                          setEditServidorIds(srvIds);
                          setEditDispositivoIds(dispIds);
                        } else {
                          setEditServidorIds([]);
                          setEditDispositivoIds([]);
                        }
                        setIsEditModalOpen(true);
                        setTimeout(() => {
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }, 50);
                      }}
                      className="text-slate-400 hover:text-primary dark:hover:text-primary transition-colors"
                      title="Editar"
                    >
                      <MoreVertical size={16} />
                    </button>
                  </div>
                  {/* Badges de asignación */}
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold border ${video.estado === 'activo' ? 'bg-green-500/10 text-green-500 border-green-500/20' : video.estado === 'inactivo' ? 'bg-slate-500/10 text-slate-500 border-slate-500/20' : video.estado === 'vencido' ? 'bg-red-500/10 text-red-500 border-red-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                      {(video.estado || 'activo').toUpperCase()}
                    </span>
                    {/* Badge de programado */}
                    {(video.fechaInicio || video.fechaFin) && (
                      <span className="relative group/badges">
                        <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-purple-500/10 text-purple-500 border border-purple-500/20">
                          <Clock size={10} />
                          PROGRAMADO
                        </span>
                        {/* Tooltip con fechas */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-900 dark:bg-slate-800 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/badges:opacity-100 group-hover/badges:visible transition-all duration-200 z-50 whitespace-nowrap">
                          <div className="font-semibold mb-1">Programación</div>
                          {video.fechaInicio && (
                            <div className="text-slate-300">Inicio: <span className="text-white">{video.fechaInicio}</span></div>
                          )}
                          {video.fechaFin && (
                            <div className="text-slate-300">Fin: <span className="text-white">{video.fechaFin}</span></div>
                          )}
                          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900 dark:border-t-slate-800"></div>
                        </div>
                      </span>
                    )}
                    {video.asignacion_todos ? (
                      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                        <Server size={10} />
                        Todos
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">
                        <Smartphone size={10} />
                        {video.dispositivos_count || 0} devs
                      </span>
                    )}
                  </div>
                  {/* Texto de asignación */}
                  <div className="mb-2">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                      Asignado a: {video.asignacion_todos ? 'Todos los dispositivos' : `${video.dispositivos_count || 0} dispositivos`}
                    </p>
                    {video.asignacion_todos ? (
                      <p className="text-xs text-slate-600 dark:text-slate-400 flex items-center gap-1">
                        <Server size={10} />
                        Todos los servidores y dispositivos del sistema
                      </p>
                    ) : (
                      <div className="space-y-0.5">
                        {video.asignaciones && video.asignaciones.slice(0, 3).map((asig, idx) => (
                          <div key={idx} className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1">
                            <Smartphone size={10} />
                            <span className="truncate">
                              {asig.dispositivo_nombre || asig.dispositivo_codigo || 'Dispositivo'} - {asig.servidor_nombre || 'Servidor'}
                            </span>
                          </div>
                        ))}
                        {video.asignaciones && video.asignaciones.length > 3 && (
                          <p className="text-xs text-slate-400">+{video.asignaciones.length - 3} más</p>
                        )}
                        {(!video.asignaciones || video.asignaciones.length === 0) && (
                          <p className="text-xs text-slate-400 italic">Sin asignaciones específicas</p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-auto pt-2">
                    <span className="text-slate-500 text-xs">
                      Fecha subida: {video.date ? formatCaracasTime(video.date) : 'Fecha desconocida'}
                    </span>
                  </div>
                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                    <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs font-medium" onClick={() => handlePreview(video)}>
                      <Eye size={14} />
                      Reproducir
                    </button>
                    <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors text-xs font-medium disabled:opacity-50" onClick={() => handleDeleteClick(video.id, video.titulo || video.filename)} disabled={deletingVideoId === video.id}>
                      {deletingVideoId === video.id ? (
                        <>Borrando...</>
                      ) : (
                        <>
                          <Trash size={14} />
                          Borrar
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )) : (
              <div className="col-span-full text-center text-slate-500 py-8">No se encontraron videos.</div>
            );
          })()}
        </div>
        
        {/* Pagination */}
        {(() => {
          const filteredVideos = videos.filter(v => {
            const searchLower = search.toLowerCase();
            return (
              v.titulo?.toLowerCase().includes(searchLower) ||
              v.filename?.toLowerCase().includes(searchLower) ||
              v.id?.toString().includes(searchLower)
            );
          });
          const totalPages = Math.ceil(filteredVideos.length / videosPerPage);
          if (totalPages <= 1) return null;
          return (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                type="button"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                Anterior
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                <button
                  key={page}
                  type="button"
                  onClick={() => setCurrentPage(page)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    currentPage === page
                      ? 'bg-primary text-white'
                      : 'border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {page}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          );
        })()}
      </div>

      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 px-4 pt-20">
          <div className="w-full max-w-2xl bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-xl p-5">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Datos de Archivos</h3>
              <button
                type="button"
                className="text-slate-500 hover:text-red-500 text-xl leading-none"
                onClick={resetUploadModal}
                disabled={uploading}
              >
                ×
              </button>
            </div>
            <div className="space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar">
              {selectedFiles.map((file, idx) => (
                <div key={file.name} className="border rounded-lg p-4 mb-2 bg-slate-50 dark:bg-[#17202b]">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold text-slate-900 dark:text-white">{file.name}</span>
                    <span className="text-xs text-slate-500">({Math.round(file.size / 1024)} KB)</span>
                    {file.type.startsWith('image') && (
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="h-12 w-12 object-cover rounded ml-2"
                      />
                    )}
                    {file.type.startsWith('video') && (
                      <video
                        src={URL.createObjectURL(file)}
                        className="h-12 w-12 rounded ml-2"
                        controls
                      />
                    )}
                    <button
                      type="button"
                      className="ml-auto px-2 py-1 rounded bg-slate-200 dark:bg-slate-700 text-xs"
                      onClick={() => {
                        const next = [...expandedFiles];
                        next[idx] = !next[idx];
                        setExpandedFiles(next);
                      }}
                    >
                      {expandedFiles[idx] ? 'Ocultar detalles' : 'Ver detalles'}
                    </button>
                  </div>
                  {expandedFiles[idx] && (
                    <div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {/* Título */}
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Título</label>
                          <input
                            type="text"
                            className="w-full rounded-lg border border-slate-200/50 dark:border-slate-700/50 bg-white/50 dark:bg-[#17202b]/50 px-3 py-2 text-sm text-slate-800 dark:text-white focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all duration-200"
                            value={fileMetadatas[idx]?.titulo || ''}
                            onChange={e => {
                              const newMetas = [...fileMetadatas];
                              newMetas[idx].titulo = e.target.value;
                              setFileMetadatas(newMetas);
                            }}
                            placeholder="Ej: Promo principal - Sucursal Centro"
                          />
                        </div>
                        {/* Estado */}
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Estado</label>
                          <select
                            className="w-full rounded-lg border border-slate-200/50 dark:border-slate-700/50 bg-white/50 dark:bg-[#17202b]/50 px-3 py-2 text-sm text-slate-800 dark:text-white focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all duration-200"
                            value={fileMetadatas[idx]?.activo ? 'activo' : 'inactivo'}
                            onChange={e => {
                              const newMetas = [...fileMetadatas];
                              newMetas[idx].activo = e.target.value === 'activo';
                              setFileMetadatas(newMetas);
                            }}
                          >
                            <option value="activo">Activo</option>
                            <option value="inactivo">Inactivo</option>
                          </select>
                        </div>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                        {/* Fecha Inicio */}
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fecha Inicio</label>
                          <input
                            type="datetime-local"
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
                            value={fileMetadatas[idx]?.fechaInicio || ''}
                            onChange={e => {
                              const newMetas = [...fileMetadatas];
                              newMetas[idx].fechaInicio = e.target.value;
                              setFileMetadatas(newMetas);
                            }}
                          />
                        </div>
                        {/* Fecha Fin */}
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fecha Fin</label>
                          <input
                            type="datetime-local"
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
                            value={fileMetadatas[idx]?.fechaFin || ''}
                            onChange={e => {
                              const newMetas = [...fileMetadatas];
                              newMetas[idx].fechaFin = e.target.value;
                              setFileMetadatas(newMetas);
                            }}
                          />
                        </div>
                      </div>
                      {/* Asignación */}
                      <div className="mt-3 border-t border-slate-200 dark:border-slate-700 pt-3">
                        <label className="flex items-center gap-2 mb-3">
                          <input
                            type="checkbox"
                            checked={fileMetadatas[idx]?.asignacionTodos ?? true}
                            onChange={e => {
                              const newMetas = [...fileMetadatas];
                              newMetas[idx].asignacionTodos = e.target.checked;
                              if (e.target.checked) {
                                newMetas[idx].servidorIds = [];
                                newMetas[idx].dispositivoIds = [];
                              }
                              setFileMetadatas(newMetas);
                            }}
                            className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                          />
                          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                            Asignar a TODOS los servidores y dispositivos
                          </span>
                        </label>
                        {!fileMetadatas[idx]?.asignacionTodos && (
                          <ServerDeviceSelector
                            servidores={servidores}
                            selectedServidorIds={fileMetadatas[idx]?.servidorIds || []}
                            selectedDispositivoIds={fileMetadatas[idx]?.dispositivoIds || []}
                            onServidorChange={(servidorId, checked) => {
                              setFileMetadatas(prevMetas => {
                                const newMetas = [...prevMetas];
                                const currentIds = [...(newMetas[idx]?.servidorIds || [])];
                                if (checked) {
                                  newMetas[idx] = {
                                    ...newMetas[idx],
                                    asignacionTodos: false,
                                    servidorIds: [...currentIds, servidorId]
                                  };
                                } else {
                                  newMetas[idx] = {
                                    ...newMetas[idx],
                                    asignacionTodos: false,
                                    servidorIds: currentIds.filter(id => id !== servidorId)
                                  };
                                }
                                return newMetas;
                              });
                            }}
                            onDispositivoChange={(dispositivoId, checked) => {
                              setFileMetadatas(prevMetas => {
                                const newMetas = [...prevMetas];
                                const currentIds = [...(newMetas[idx]?.dispositivoIds || [])];
                                if (checked) {
                                  newMetas[idx] = {
                                    ...newMetas[idx],
                                    asignacionTodos: false,
                                    dispositivoIds: [...currentIds, dispositivoId]
                                  };
                                } else {
                                  newMetas[idx] = {
                                    ...newMetas[idx],
                                    asignacionTodos: false,
                                    dispositivoIds: currentIds.filter(id => id !== dispositivoId)
                                  };
                                }
                                return newMetas;
                              });
                            }}
                            expandedServidores={uploadExpandedServers}
                            onToggleExpand={(id) => {
                              setUploadExpandedServers(prev =>
                                prev.includes(id)
                                  ? prev.filter(srvId => srvId !== id)
                                  : [...prev, id]
                              );
                            }}
                          />
                        )}
                      </div>
                      {/* Feedback por archivo */}
                      {uploadStatuses[idx] === 'uploading' && <div className="mt-2 text-primary">Subiendo...</div>}
                      {uploadStatuses[idx] === 'success' && <div className="mt-2 text-green-600">Subido correctamente</div>}
                      {uploadStatuses[idx] === 'error' && <div className="mt-2 text-red-500">Error al subir</div>}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={resetUploadModal}
                disabled={uploading}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSubmitUpload}
                disabled={uploading}
                className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white text-sm font-semibold disabled:opacity-60"
              >
                {uploading ? 'Subiendo...' : 'Guardar y Subir'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sync Modal */}
      {isSyncModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 pt-20">
          <div className="bg-white dark:bg-[#1c2936] rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Sincronización Selectiva</h2>
              <p className="text-sm text-slate-500">Selecciona los dispositivos a sincronizar</p>
            </div>
            
            <div className="p-4 overflow-y-auto max-h-[50vh]">
              <label className="flex items-center gap-2 mb-4">
                <input
                  type="checkbox"
                  checked={syncAllDevices}
                  onChange={e => {
                    setSyncAllDevices(e.target.checked);
                    if (e.target.checked) {
                      setSyncServidorIds([]);
                      setSyncDispositivoIds([]);
                    }
                  }}
                  className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  Sincronizar a TODOS los dispositivos
                </span>
              </label>
              
              {!syncAllDevices && (
                <ServerDeviceSelector
                  servidores={servidores}
                  selectedServidorIds={syncServidorIds}
                  selectedDispositivoIds={syncDispositivoIds}
                  onServidorChange={(id, checked) => {
                    setSyncServidorIds(prev => {
                      if (checked) {
                        return [...prev, id];
                      }
                      return prev.filter(srvId => srvId !== id);
                    });
                  }}
                  onDispositivoChange={(id, checked) => {
                    setSyncDispositivoIds(prev => {
                      if (checked) {
                        return [...prev, id];
                      }
                      return prev.filter(dispId => dispId !== id);
                    });
                  }}
                  expandedServidores={syncExpandedServers}
                  onToggleExpand={(id) => {
                    setSyncExpandedServers(prev =>
                      prev.includes(id)
                        ? prev.filter(srvId => srvId !== id)
                        : [...prev, id]
                    );
                  }}
                />
              )}
            </div>

            <div className="mt-4 flex justify-end gap-2 p-4 border-t border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => {
                  setIsSyncModalOpen(false);
                  setSyncAllDevices(true);
                  setSyncServidorIds([]);
                  setSyncDispositivoIds([]);
                  setSyncExpandedServers([]);
                }}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={async () => {
                  setIsSyncModalOpen(false);
                  await executeSync();
                }}
                disabled={!syncAllDevices && syncServidorIds.length === 0 && syncDispositivoIds.length === 0}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold disabled:opacity-60"
              >
                Sincronizar
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Edit Modal */}
      {isEditModalOpen && editingVideo && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 pt-20">
          <div className="bg-white dark:bg-[#1c2936] rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Editar Publicidad</h2>
              <p className="text-sm text-slate-500">Modifica los datos de la publicidad</p>
            </div>
            
            <div className="p-4 space-y-4 overflow-y-auto flex-1">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Título
                </label>
                <input
                  type="text"
                  value={editFormData.titulo}
                  onChange={e => setEditFormData({ ...editFormData, titulo: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Fecha Inicio
                </label>
                <input
                  type="datetime-local"
                  value={editFormData.fechaInicio}
                  onChange={e => setEditFormData({ ...editFormData, fechaInicio: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Fecha Fin
                </label>
                <input
                  type="datetime-local"
                  value={editFormData.fechaFin}
                  onChange={e => setEditFormData({ ...editFormData, fechaFin: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="editActivo"
                  checked={editFormData.activo}
                  onChange={e => setEditFormData({ ...editFormData, activo: e.target.checked })}
                  className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                />
                <label htmlFor="editActivo" className="text-sm text-slate-700 dark:text-slate-300">
                  Activo
                </label>
              </div>
              
              {/* Sección de asignación */}
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-2">
                <label className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    id="editAsignacionTodos"
                    checked={editAsignacionTodos}
                    onChange={e => {
                      setEditAsignacionTodos(e.target.checked);
                      if (e.target.checked) {
                        setEditServidorIds([]);
                        setEditDispositivoIds([]);
                      }
                    }}
                    className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                  />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    Asignar a TODOS los dispositivos
                  </span>
                </label>
                
                {!editAsignacionTodos && (
                  <ServerDeviceSelector
                    servidores={servidores}
                    selectedServidorIds={editServidorIds}
                    selectedDispositivoIds={editDispositivoIds}
                    onServidorChange={(id, checked) => {
                      if (checked) {
                        setEditServidorIds([...editServidorIds, id]);
                      } else {
                        setEditServidorIds(editServidorIds.filter(srvId => srvId !== id));
                      }
                    }}
                    onDispositivoChange={(id, checked) => {
                      if (checked) {
                        setEditDispositivoIds([...editDispositivoIds, id]);
                      } else {
                        setEditDispositivoIds(editDispositivoIds.filter(dispId => dispId !== id));
                      }
                    }}
                    expandedServidores={editExpandedServers}
                    onToggleExpand={(id) => {
                      setEditExpandedServers(prev =>
                        prev.includes(id)
                          ? prev.filter(srvId => srvId !== id)
                          : [...prev, id]
                      );
                    }}
                    maxHeight="max-h-40"
                  />
                )}
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-2 p-4 border-t border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingVideo(null);
                  setEditAsignacionTodos(true);
                  setEditServidorIds([]);
                  setEditDispositivoIds([]);
                  setEditExpandedServers([]);
                }}
                disabled={isSavingEdit}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={async () => {
                  const fechaInicio = editFormData.fechaInicio;
                  const fechaFin = editFormData.fechaFin;
                  if (fechaInicio && fechaFin && new Date(fechaInicio) > new Date(fechaFin)) {
                    showNotification('La fecha de inicio no puede ser mayor a la fecha fin', 'warning');
                    return;
                  }
                  setIsSavingEdit(true);
                  try {
                    // Actualizar metadata
                    await updateBannerMetadata(editingVideo.id, {
                      activo: editFormData.activo,
                      titulo: editFormData.titulo || '',
                      fechaInicio: editFormData.fechaInicio || null,
                      fechaFin: editFormData.fechaFin || null,
                    });
                    
                    // Actualizar asignaciones
                    await updateBannerAsignations(
                      editingVideo.id,
                      editAsignacionTodos,
                      editServidorIds,
                      editDispositivoIds
                    );
                    
                    showNotification('Publicidad actualizada correctamente', 'success');
                    setIsEditModalOpen(false);
                    setEditingVideo(null);
                    setEditAsignacionTodos(true);
                    setEditServidorIds([]);
                    setEditDispositivoIds([]);
                    setEditExpandedServers([]);
                    // Refresh videos
                    const data = await getVideos();
                    setVideos(data);
                  } catch (error: any) {
                    // Mostrar mensaje de error específico del backend si está disponible
                    // FastAPI devuelve el error en 'detail' o 'error'
                    const backendError = error?.response?.data?.detail || error?.response?.data?.error;
                    const errorMessage = backendError || (error.message === 'Request failed with status code 400' 
                        ? 'Error de validación' 
                        : 'Error al actualizar la publicidad');
                    showNotification(errorMessage, 'error');
                  } finally {
                    setIsSavingEdit(false);
                  }
                }}
                disabled={isSavingEdit}
                className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white text-sm font-semibold disabled:opacity-60"
              >
                {isSavingEdit ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Delete Modal */}
      {confirmDelete.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-[#1c2936] rounded-xl shadow-2xl w-full max-w-sm p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Confirmar eliminación</h3>
            <p className="text-sm text-slate-500 mb-4">
              ¿Estás seguro de que deseas eliminar <strong className="text-slate-700 dark:text-slate-300">{confirmDelete.titulo}</strong>? Esta acción no se puede deshacer.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleDeleteCancel}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal - Fuera del map para evitar re-renders innecesarios */}
      {preview && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-20" onClick={closePreview}>
          <div className="bg-white dark:bg-[#1c2936] rounded-lg shadow-lg p-6 max-w-lg w-full relative" onClick={e => e.stopPropagation()}>
            <button onClick={closePreview} className="absolute top-2 right-2 text-slate-500 hover:text-red-500 text-xl font-bold">&times;</button>
            <div className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">{preview.titulo}</div>
            {preview.tipo === 'image' ? (
              <img src={preview.url} alt={preview.titulo} className="max-h-[60vh] w-auto mx-auto rounded" />
            ) : (
              <video 
                ref={videoRef}
                src={preview.url} 
                poster={preview.thumbnail || preview.url}
                controls 
                autoPlay 
                preload="none"
                className="max-h-[60vh] w-auto mx-auto rounded" 
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};