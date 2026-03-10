import React, { useEffect, useState } from 'react';
import { useNotification } from '../components/useNotification';
import { Search, UploadCloud, MoreVertical, Eye, Trash, Film, Plus } from 'lucide-react';
import { getVideos, uploadMedia, deleteVideo } from '../services/videoService';
import { Video } from '../types';
import {
  getForceSyncJobStatus,
  getSecondaryServersVideoCounts,
  startForceSyncJob,
} from '../services/monitoreoService';


// Formatea una fecha a la hora de Caracas (UTC-4) sin depender de la hora local del sistema
function formatCaracasTime(dateString: string | Date): string {
  const date = typeof dateString === 'string' ? new Date(dateString) : new Date(dateString.getTime());
  // Ajustar a UTC-4
  date.setHours(date.getHours() - 4);
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
  const handlePreview = (video: Video) => {
    setPreview({ url: video.url, tipo: video.tipo, titulo: video.titulo || video.filename });
  };
  const closePreview = () => setPreview(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Batch upload states
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileMetadatas, setFileMetadatas] = useState<Array<{
    titulo: string;
    fechaInicio: string;
    fechaFin: string;
    activo: boolean;
  }>>([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [currentEditIndex, setCurrentEditIndex] = useState<number | null>(null);

  const [syncLoading, setSyncLoading] = useState(false);
  const [syncServerProgress, setSyncServerProgress] = useState<SyncServerProgress[]>([]);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [secondaryVideoCounts, setSecondaryVideoCounts] = useState<SecondaryVideoCounter[]>([]);
  const [selectedSecondaryServerId, setSelectedSecondaryServerId] = useState<string>('');

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
  };

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
      setUploadStatuses([]);
    if (!event.target.files?.length) return;
    const files = Array.from(event.target.files);
    const maxSize = 20 * 1024 * 1024;
    const validFiles: File[] = [];
    const metadatas: typeof fileMetadatas = [];
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
    event.target.value = '';
  };

  const handleSubmitUpload = async () => {
    if (selectedFiles.length === 0) {
      showNotification('Selecciona archivos primero', 'warning');
      return;
    }
    // Validar metadatos
    for (let i = 0; i < fileMetadatas.length; i++) {
      const meta = fileMetadatas[i];
      if (!meta.titulo.trim()) {
        showNotification(`El título es obligatorio para el archivo #${i + 1}`, 'warning');
        return;
      }
      const fechaInicioIso = meta.fechaInicio ? new Date(formatCaracasTime(meta.fechaInicio)).toISOString() : null;
      const fechaFinIso = meta.fechaFin ? new Date(formatCaracasTime(meta.fechaFin)).toISOString() : null;
      if (fechaInicioIso && fechaFinIso && new Date(fechaInicioIso) > new Date(fechaFinIso)) {
        showNotification(`La fecha de inicio no puede ser mayor a la fecha fin para el archivo #${i + 1}`, 'warning');
        return;
      }
    }
    setUploading(true);
    setError(null);
    // Feedback por archivo
    setUploadStatuses(Array(selectedFiles.length).fill('pending'));
    let allSuccess = true;
    for (let i = 0; i < selectedFiles.length; i++) {
      setUploadStatuses(prev => {
        const next = [...prev];
        next[i] = 'uploading';
        return next;
      });
      try {
        await uploadMedia(selectedFiles[i], {
          titulo: fileMetadatas[i].titulo,
          fechaInicio: fileMetadatas[i].fechaInicio ? new Date(formatCaracasTime(fileMetadatas[i].fechaInicio)).toISOString() : null,
          fechaFin: fileMetadatas[i].fechaFin ? new Date(formatCaracasTime(fileMetadatas[i].fechaFin)).toISOString() : null,
          activo: fileMetadatas[i].activo
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

  const handleDelete = async (videoId: string) => {
    setError(null);
    try {
      await deleteVideo(videoId);
      setVideos(videos.filter(v => v.id !== videoId));
      showNotification('Archivo borrado correctamente', 'success');
    } catch (err: any) {
      setError('Error deleting video');
      showNotification('Error al borrar archivo', 'error');
    }
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
              className="pl-10 pr-4 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full sm:w-64 transition-all"
              placeholder="Buscar Videos..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow hover:bg-blue-700 transition disabled:opacity-50"
            onClick={handleForceSync}
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
            // Renderizar tarjetas
            return filteredVideos.length > 0 ? filteredVideos.map((video) => (
              <div key={video.id} className="group relative bg-white dark:bg-[#1c2936] rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 hover:border-primary/50 transition-all hover:shadow-xl hover:shadow-slate-900/10 dark:hover:shadow-black/40 flex flex-col">
                {/* Thumbnail */}
                <div className="aspect-video bg-slate-800 relative overflow-hidden">
                  {video.tipo === 'image' ? (
                    <img src={video.thumbnail} alt={video.titulo || video.filename} className="w-full h-full object-cover" />
                  ) : (
                    <div className="flex items-center justify-center w-full h-full">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect width="24" height="24" rx="6" fill="#1c2936" />
                        <polygon points="9,7 17,12 9,17" fill="#fff" />
                      </svg>
                    </div>
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
                    <button className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                      <MoreVertical size={16} />
                    </button>
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
                    {preview && (
                      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
                        <div className="bg-white dark:bg-[#1c2936] rounded-lg shadow-lg p-6 max-w-lg w-full relative">
                          <button onClick={closePreview} className="absolute top-2 right-2 text-slate-500 hover:text-red-500 text-xl font-bold">&times;</button>
                          <div className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">{preview.titulo}</div>
                          {preview.tipo === 'image' ? (
                            <img src={preview.url} alt={preview.titulo} className="max-h-[60vh] w-auto mx-auto rounded" />
                          ) : (
                            <video src={preview.url} controls autoPlay className="max-h-[60vh] w-auto mx-auto rounded" />
                          )}
                        </div>
                      </div>
                    )}
                    <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors text-xs font-medium" onClick={() => handleDelete(video.id)}>
                      <Trash size={14} />
                      Borrar
                    </button>
                  </div>
                </div>
              </div>
            )) : (
              <div className="col-span-full text-center text-slate-500 py-8">No se encontraron videos.</div>
            );
          })()}
        </div>
      </div>

      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
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
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
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
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
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
    </div>
  );
};