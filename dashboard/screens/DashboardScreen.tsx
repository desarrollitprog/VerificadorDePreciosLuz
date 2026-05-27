import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNotification } from '../components/useNotification';
import { Spinner } from '../components/Spinner';
import { CardSkeleton } from '../components/CardSkeleton';
import { Search, UploadCloud, MoreVertical, Eye, Trash, Film, Plus, Server, Smartphone, ChevronDown, ChevronRight, Clock, Check, Pencil, RefreshCw, List, Grid, Download } from 'lucide-react';
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
  queued: number;
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
    const queued = Number(detail.sync_queued ?? 0);
    const failed = Number(detail.sync_failed ?? 0);
    const progress = total > 0 ? Math.min(100, Math.round(((confirmed + queued) / total) * 100)) : 0;

    return {
      nombre: String(detail.nombre ?? detail.ip ?? 'Servidor'),
      ip: String(detail.ip ?? ''),
      total,
      confirmed,
      queued,
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
  const [preview, setPreview] = useState<{url: string, tipo: string, titulo: string, thumbnail?: string} | null>(null);
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
  const [filterType, setFilterType] = useState<'all' | 'image' | 'video'>('all');
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const videosPerPage = 12;
  const tableVideosPerPage = 20;
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([]);
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);
  
  // Computed values for views - filters apply to BOTH views
  const filteredVideos = videos.filter(v => {
    const searchLower = search.toLowerCase();
    const matchesSearch = (
      v.titulo?.toLowerCase().includes(searchLower) ||
      v.filename?.toLowerCase().includes(searchLower) ||
      v.id?.toString().includes(searchLower)
    );
    
    const matchesType = filterType === 'all' || v.tipo === filterType;
    
    const matchesDateFrom = !filterDateFrom || (v.date && new Date(v.date) >= new Date(filterDateFrom + 'T00:00:00'));
    const matchesDateTo = !filterDateTo || (v.date && new Date(v.date) <= new Date(filterDateTo + 'T23:59:59'));
    
    return matchesSearch && matchesType && matchesDateFrom && matchesDateTo;
  });
  
  const paginatedCardVideos = filteredVideos.slice(
    (currentPage - 1) * videosPerPage, 
    (currentPage - 1) * videosPerPage + videosPerPage
  );
  const paginatedTableVideos = filteredVideos.slice(
    (currentPage - 1) * tableVideosPerPage, 
    (currentPage - 1) * tableVideosPerPage + tableVideosPerPage
  );
  
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
   // View mode and selection states (Fase 16)
   const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
   const [selected, setSelected] = useState<string[]>([]);

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
  const [confirmBulkDelete, setConfirmBulkDelete] = useState<{ open: boolean; videoIds: string[] }>({ open: false, videoIds: [] });
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
            tipo: d.tipo ?? 'verificador',
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

  const getTodayAt22 = (): string => {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}T22:00`;
  };

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
      setUploadStatuses([]);
    if (!event.target.files?.length) return;
    const files = Array.from(event.target.files);
    const maxSize = 500 * 1024 * 1024;
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
        fechaInicio: getTodayAt22(),
        fechaFin: getTodayAt22(),
        activo: true,
        asignacionTodos: true,
        servidorIds: [],
        dispositivoIds: [],
      });
    });
    if (rejected > 0) {
      setError(`Se rechazaron ${rejected} archivos por tamaño (max 500MB).`);
      showNotification(`Se rechazaron ${rejected} archivos por tamaño (max 500MB)`, 'warning');
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
      if (fechaFinIso && !fechaInicioIso) {
        showNotification(`Debes establecer fecha de inicio si pones fecha de fin para el archivo #${i + 1}`, 'warning');
        return;
      }
      if (fechaInicioIso && !fechaFinIso) {
        showNotification(`Debes establecer fecha de fin si pones fecha de inicio para el archivo #${i + 1}`, 'warning');
        return;
      }
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
      resetUploadModal();
      showNotification('Todos los archivos subidos correctamente', 'success');
      const anyTodos = fileMetadatas.some(m => m.asignacionTodos && m.servidorIds.length === 0);
      if (anyTodos) {
        handleForceSync();
      } else {
        const srvIds = [...new Set(fileMetadatas.flatMap(m => m.servidorIds))];
        const dispIds = [...new Set(fileMetadatas.flatMap(m => m.dispositivoIds))];
        handleForceSync(srvIds.length > 0 ? srvIds : undefined, dispIds.length > 0 ? dispIds : undefined);
      }
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
     const deletedVideo = videos.find(v => v.id === confirmDelete.videoId);
     setConfirmDelete({ open: false, videoId: null, titulo: '' });
     try {
        await deleteVideo(confirmDelete.videoId);
        showNotification('Archivo borrado correctamente', 'success');
        if (deletedVideo?.asignacion_todos) {
          handleForceSync();
        } else if (deletedVideo?.asignaciones?.length) {
          const srvIds = [...new Set(deletedVideo.asignaciones.map(a => a.servidor_id).filter(Boolean))];
          const dispIds = [...new Set(deletedVideo.asignaciones.map(a => String(a.dispositivo_id)).filter(Boolean))];
          handleForceSync(srvIds.length > 0 ? srvIds : undefined, dispIds.length > 0 ? dispIds : undefined);
        } else {
          handleForceSync();
        }
       } catch (err: any) {
        setError('Error al borrar el video');
        showNotification('Error al borrar archivo', 'error');
      } finally {
        setDeletingVideoId(null);
        try {
          const data = await getVideos();
          setVideos(data);
        } catch {}
      }
    };

   // Función para confirmar borrado masivo
   const handleBulkDeleteConfirm = async () => {
     if (confirmBulkDelete.videoIds.length === 0) return;
     
     setError(null);
     const idsToDelete = [...confirmBulkDelete.videoIds];
     const deletedVideos = videos.filter(v => idsToDelete.includes(v.id));
     
     try {
       for (const id of idsToDelete) {
         await deleteVideo(id);
       }
       
        showNotification(`${idsToDelete.length} archivo${idsToDelete.length > 1 ? 's' : ''} borrado${idsToDelete.length > 1 ? 's' : ''} correctamente`, 'success');
        setSelectedVideoIds([]);

        const anyTodos = deletedVideos.some(v => v.asignacion_todos);
        if (anyTodos) {
          handleForceSync();
        } else {
          const srvIds = [...new Set(deletedVideos.flatMap(v => v.asignaciones?.map(a => a.servidor_id).filter(Boolean) ?? []))];
          const dispIds = [...new Set(deletedVideos.flatMap(v => v.asignaciones?.map(a => String(a.dispositivo_id)).filter(Boolean) ?? []))];
          handleForceSync(srvIds.length > 0 ? srvIds : undefined, dispIds.length > 0 ? dispIds : undefined);
        }
        
       const data = await getVideos();
       setVideos(data);
     } catch (err: any) {
       setError('Error al borrar archivos');
       showNotification('Error al borrar archivos', 'error');
     } finally {
       setConfirmBulkDelete({ open: false, videoIds: [] });
     }
   };

  // Fase 16.5: Descargar archivo
  const downloadVideoFile = (video: Video) => {
    if (!video.url) {
      showNotification('No hay URL disponible para descargar', 'warning');
      return;
    }
    const link = document.createElement('a');
    link.href = video.url;
    link.download = video.filename || video.url.split('/').pop() || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeleteCancel = () => {
    setConfirmDelete({ open: false, videoId: null, titulo: '' });
  };

  const handleForceSync = async (servidor_ids?: number[], dispositivo_ids?: string[]) => {
    setSyncLoading(true);
    setSyncServerProgress([]);
    try {
      const start = await startForceSyncJob(servidor_ids, dispositivo_ids);
      if (!start.success || !start.job_id) {
        showNotification('No se pudo iniciar la sincronización', 'error');
        return;
      }

      const maxPolls = 90;
      const pollDelayMs = 2000;
      let finalStatus: any = null;
      let queuedToastShown = false;

      for (let i = 0; i < maxPolls; i++) {
        await new Promise((resolve) => setTimeout(resolve, pollDelayMs));
        const status = await getForceSyncJobStatus(start.job_id);
        setSyncServerProgress(normalizeServerProgress(status.details || []));

        if (!queuedToastShown) {
          const anyQueued = (status.details || []).some((d: any) => Number(d.sync_queued ?? 0) > 0);
          if (anyQueued) {
            queuedToastShown = true;
            showNotification('Uno o más dispositivos están en cola — se ejecutarán al reconectar.', 'warning');
          }
        }

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
        const failedCount = finalStatus.failed_count ?? 0;
        const totalQueued = (finalStatus.details || []).reduce(
          (acc: number, d: any) => acc + Number(d.sync_queued ?? 0), 0
        );
        if (failedCount > 0) {
          showNotification(
            `Sincronización completada con fallos (${failedCount} servidores, ${totalQueued} en cola).`,
            'error'
          );
        } else if (totalQueued > 0) {
          showNotification(
            `Sincronización completada. ${totalQueued} dispositivos en cola.`,
            'info'
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
      let queuedToastShown = false;

      for (let i = 0; i < maxPolls; i++) {
        await new Promise((resolve) => setTimeout(resolve, pollDelayMs));
        const status = await getForceSyncJobStatus(start.job_id);
        setSyncServerProgress(normalizeServerProgress(status.details || []));

        if (!queuedToastShown) {
          const anyQueued = (status.details || []).some((d: any) => Number(d.sync_queued ?? 0) > 0);
          if (anyQueued) {
            queuedToastShown = true;
            showNotification('Uno o más dispositivos están en cola — se ejecutarán al reconectar.', 'warning');
          }
        }

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
        const failedCount = finalStatus.failed_count ?? 0;
        const totalQueued = (finalStatus.details || []).reduce(
          (acc: number, d: any) => acc + Number(d.sync_queued ?? 0), 0
        );
        if (failedCount > 0) {
          showNotification(
            `Sincronización completada con fallos (${failedCount} servidores, ${totalQueued} en cola).`,
            'error'
          );
        } else if (totalQueued > 0) {
          showNotification(
            `Sincronización completada. ${totalQueued} dispositivos en cola.`,
            'info'
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
    <div className="max-w-screen-xl mx-auto flex flex-col gap-8">
       {/* Title & Sync Button */}
       <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
         <div>
           <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">Mis Videos</h2>
           <p className="text-slate-500 mt-1">ADMINISTRA TUS VIDEOS YA SEA SUBIR, ELIMINAR Y SINCRONIZAR.</p>
         </div>
         <div className="flex items-center gap-3">
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
          <p className="text-slate-500 text-sm max-w-sm mb-6">Click o arrastra aquí para subir Videos o Imagenes (Tamaño maximo = 100MB, Formatos soportados: MP4, MKV, PNG, JPEG, JPG.)</p>
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
                <p className="text-[11px] text-slate-500 mt-1">Última sincronización: {lastSyncAt}</p>
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
                      {serverProgress.confirmed} confirmados
                      {serverProgress.queued > 0 ? `, ${serverProgress.queued} en cola` : ''}
                      / {serverProgress.total} ({serverProgress.progress}%)
                    </span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-2.5 ${
                        serverProgress.failed > 0 && serverProgress.queued === 0
                          ? 'bg-amber-500'
                          : serverProgress.queued > 0
                          ? 'bg-orange-400'
                          : 'bg-primary'
                      }`}
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
          <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Contenido Subido Recientemente</h3>
           <div className="flex items-center gap-2 flex-wrap">
              {/* Search bar (moved from top) */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  type="text"
                  className="pl-10 pr-8 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full sm:w-48 transition-all"
                  placeholder="Buscar..."
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
              
              {/* Type filter */}
              <select
                value={filterType}
                onChange={e => { setFilterType(e.target.value as any); setCurrentPage(1); }}
                className="px-3 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-primary"
              >
                <option value="all">Todos</option>
                <option value="image">Imágenes</option>
                <option value="video">Videos</option>
              </select>
              
              {/* Date range filters */}
              <div className="flex items-center gap-1">
                <span className="text-xs text-slate-500 font-medium">Desde</span>
                <input
                  type="date"
                  value={filterDateFrom}
                  onChange={e => { setFilterDateFrom(e.target.value); setCurrentPage(1); }}
                  className="px-3 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex items-center gap-1">
                <span className="text-xs text-slate-500 font-medium">Hasta</span>
                <input
                  type="date"
                  value={filterDateTo}
                  onChange={e => { setFilterDateTo(e.target.value); setCurrentPage(1); }}
                  className="px-3 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-primary"
                />
              </div>
              
              {/* View Toggle Buttons */}
               <button 
                 onClick={() => { setViewMode('cards'); setCurrentPage(1); }} 
                 className={`p-2 rounded-lg transition-colors ${viewMode === 'cards' ? 'bg-slate-200 dark:bg-slate-700 text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-white'}`}
                 title="Vista de tarjetas"
               >
                 <Grid size={18} />
               </button>
               <button 
                 onClick={() => { setViewMode('table'); setCurrentPage(1); }} 
                 className={`p-2 rounded-lg transition-colors ${viewMode === 'table' ? 'bg-slate-200 dark:bg-slate-700 text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-white'}`}
                 title="Vista de tabla"
               >
                 <List size={18} />
               </button>
             </div>
          </div>
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {Array.from({ length: 8 }).map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          ) : viewMode === 'cards' ? (
            /* VISTA DE TARJETAS - Diseño original restaurado + nuevos botones */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 items-baseline">
              {paginatedCardVideos.length > 0 ? paginatedCardVideos.map((video) => (
                  <div key={video.id} className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-white dark:bg-slate-800 hover:shadow-md transition-shadow flex flex-col">
                    {/* Thumbnail */}
                    <div className="relative aspect-video bg-slate-100 dark:bg-slate-700">
                      {video.tipo === 'image' ? (
                        <img src={video.thumbnail || video.url} alt={video.titulo || video.filename} className="w-full h-full object-cover" />
                      ) : (
                        <video src={video.url} className="w-full h-full object-cover" poster={video.thumbnail} />
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
                          className="text-slate-400 hover:text-primary dark:hover:text-primary transition-colors shrink-0"
                          title="Editar"
                        >
                          <MoreVertical size={16} />
                        </button>
                      </div>
                      {/* Badges de asignación */}
                       <div className="flex items-center gap-2 mb-2 flex-wrap">
                         <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold border ${
                           video.estado === 'activo' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' :
                           video.estado === 'inactivo' ? 'bg-slate-500/10 text-slate-500 border-slate-500/20' :
                           video.estado === 'vencido' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                           'bg-amber-500/10 text-amber-500 border-amber-500/20'
                         }`}>
                           {(video.estado || 'activo').toUpperCase()}
                         </span>
                         {/* Badge de tipo de archivo */}
                         <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold border ${
                           video.tipo === 'image' ? 'bg-blue-500/10 text-blue-500 border-blue-500/20' :
                           'bg-purple-500/10 text-purple-500 border-purple-500/20'
                         }`}>
                           {video.tipo === 'image' ? 'IMAGEN' : 'VIDEO'}
                         </span>
                        {/* Badge de programado */}
                        {(video.fechaInicio || video.fechaFin) && (
                          <span className="relative group/badges">
                            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-purple-500/10 text-purple-500 border border-purple-500/20">
                              <Clock size={10} />
                              PROGRAMADO
                            </span>
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
                            {video.dispositivos_count || 0} disp.
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
                        {video.asignaciones && video.asignaciones.slice(0, 3).map((asig: any, idx: number) => (
                               <div key={idx} className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1">
                                 <Smartphone size={10} />
                                 <span className="truncate">
                                   {asig.dispositivo_nombre || asig.dispositivo_codigo || 'Dispositivo'} - {asig.servidor_nombre || 'Servidor'}
                                 </span>
                               </div>
                             ))}
                              {video.asignaciones && video.asignaciones.length > 3 && (
                                <button 
                                  onClick={(e) => {
                                    const isExpanding = expandedCardId !== video.id;
                                    setExpandedCardId(isExpanding ? video.id : null);
                                    if (isExpanding) {
                                      const btn = e.currentTarget;
                                      setTimeout(() => {
                                        btn.scrollIntoView({ behavior: 'smooth', block: 'end' });
                                      }, 100);
                                    }
                                  }}
                                  className="text-xs text-primary hover:underline font-medium"
                                >
                                  {expandedCardId === video.id ? 'Ver menos' : `Ver más (${video.asignaciones.length - 3})`}
                                </button>
                              )}
                             {expandedCardId === video.id && video.asignaciones && video.asignaciones.slice(3).map((asig: any, idx: number) => (
                               <div key={idx} className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1">
                                 <Smartphone size={10} />
                                 <span className="truncate">
                                   {asig.dispositivo_nombre || asig.dispositivo_codigo || 'Dispositivo'} - {asig.servidor_nombre || 'Servidor'}
                                 </span>
                               </div>
                             ))}
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
                      {/* Action Buttons - Original + Nuevos */}
                      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                        <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs font-medium" onClick={() => handlePreview(video)}>
                          <Eye size={14} />
                          Reproducir
                        </button>
                        <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-blue-500 hover:bg-blue-500/10 transition-colors text-xs font-medium" onClick={() => downloadVideoFile(video)}>
                          <Download size={14} />
                          Descargar
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
                )}
            </div>
           ) : (
             /* VISTA DE TABLA */
             <div className="overflow-x-auto">
                {/* Botones de acción masiva */}
               {selectedVideoIds.length > 0 && (
                 <div className="flex items-center gap-4 mb-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                   <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                     {selectedVideoIds.length} seleccionado{selectedVideoIds.length > 1 ? 's' : ''}
                   </span>
                   <button 
                     onClick={() => {
                       const videosToDownload = videos.filter(v => selectedVideoIds.includes(v.id));
                       videosToDownload.forEach(v => downloadVideoFile(v));
                     }}
                     className="text-sm text-blue-500 hover:text-blue-600 font-medium"
                   >
                     Descargar seleccionados
                   </button>
                    <button 
                      onClick={() => {
                        setConfirmBulkDelete({ 
                          open: true, 
                          videoIds: [...selectedVideoIds] 
                        });
                      }}
                      className="text-sm text-red-500 hover:text-red-600 font-medium"
                    >
                      Eliminar seleccionados
                    </button>
                   <button 
                     onClick={() => setSelectedVideoIds([])}
                     className="text-sm text-slate-500 hover:text-slate-600 font-medium ml-auto"
                   >
                     Limpiar selección
                   </button>
                 </div>
               )}
                  <div className="grid grid-cols-12 gap-4 max-lg:min-w-[1100px] border-b border-slate-200 dark:border-slate-700 px-3 py-2 bg-slate-50 dark:bg-slate-800/50 text-sm font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    <div className="col-span-1 flex items-center">
                     <input 
                       type="checkbox" 
                       checked={selectedVideoIds.length === paginatedTableVideos.length && paginatedTableVideos.length > 0}
                       onChange={() => {
                         if (selectedVideoIds.length === paginatedTableVideos.length) {
                           setSelectedVideoIds([]);
                         } else {
                           setSelectedVideoIds(paginatedTableVideos.map(v => v.id));
                         }
                       }}
                       className="rounded border-slate-300 dark:border-slate-600"
                     />
                   </div>
                  <div className="col-span-4">Archivo</div>
                  <div className="col-span-1">Subida</div>
                  <div className="col-span-1">Tamaño</div>
                  <div className="col-span-2 relative group/estado-header">Estado</div>
                  <div className="col-span-1">ASIGNACION</div>
                  <div className="col-span-2 text-right">Acciones</div>
                </div>
                {(() => {
                  return paginatedTableVideos.length > 0 ? paginatedTableVideos.map((video, index) => (
                    <div key={video.id} className="grid grid-cols-12 gap-4 max-lg:min-w-[1100px] border-b border-slate-100 dark:border-slate-700/30 px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors items-center">
                      <div className="col-span-1 flex items-center">
                        <input 
                          type="checkbox" 
                          checked={selectedVideoIds.includes(video.id)}
                          onChange={() => {
                            if (selectedVideoIds.includes(video.id)) {
                              setSelectedVideoIds(selectedVideoIds.filter(id => id !== video.id));
                            } else {
                              setSelectedVideoIds([...selectedVideoIds, video.id]);
                            }
                          }}
                          className="rounded border-slate-300 dark:border-slate-600"
                        />
                      </div>
                      <div className="col-span-4 flex items-center gap-2 overflow-hidden">
                        <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded bg-slate-100 dark:bg-slate-800">
                          <img src={video.thumbnail || video.url} alt={video.titulo || video.filename} className="w-6 h-6 object-cover rounded" />
                        </div>
                        <span className="text-sm font-medium text-slate-900 dark:text-white truncate min-w-0" title={video.titulo || video.filename}>
                          {video.titulo || video.filename}
                        </span>
                      </div>
                      <div className="col-span-1 text-sm text-slate-600 dark:text-slate-400 truncate">
                        {video.date ? formatCaracasTime(video.date) : '-'}
                      </div>
                      <div className="col-span-1 text-sm text-slate-600 dark:text-slate-400 font-mono">
                        {video.size}
                      </div>
                      <div className="col-span-2 relative group/estado">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold border ${
                          video.estado === 'activo' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' :
                          video.estado === 'inactivo' ? 'bg-slate-500/10 text-slate-500 border-slate-500/20' :
                          video.estado === 'vencido' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                          'bg-amber-500/10 text-amber-500 border-amber-500/20'
                        }`}>
                          {(video.estado || 'activo').toUpperCase()}
                        </span>
                        {/* Tooltip: Programación + Tipo de archivo */}
                        <div className={`absolute left-1/2 -translate-x-1/2 ${index === 0 ? 'top-full mt-2' : 'bottom-full mb-2'} px-3 py-2 bg-slate-900 dark:bg-slate-800 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/estado:opacity-100 group-hover/estado:visible transition-all duration-200 z-50 whitespace-nowrap`}>
                            <div className="font-semibold mb-1">Programación</div>
                            <div className="text-slate-300">Tipo: <span className="text-white">{video.tipo === 'image' ? 'Imagen' : 'Video'}</span></div>
                            {video.fechaInicio && (
                              <div className="text-slate-300">Inicio: <span className="text-white">{video.fechaInicio}</span></div>
                            )}
                            {video.fechaFin && (
                              <div className="text-slate-300">Fin: <span className="text-white">{video.fechaFin}</span></div>
                            )}
                            <div className={`absolute left-1/2 -translate-x-1/2 border-4 border-transparent ${index === 0 ? 'bottom-full border-b-slate-900 dark:border-b-slate-800' : 'top-full border-t-slate-900 dark:border-t-slate-800'}`}></div>
                          </div>
                      </div>
                      <div className="col-span-1 text-sm text-slate-600 dark:text-slate-400">
                        {video.asignacion_todos ? (
                          <span className="inline-flex items-center gap-1">
                            <Server size={12} />
                            Todos
                          </span>
                        ) : (
                          <div className="relative group/assign">
                            <span className="cursor-help border-b border-dotted border-slate-400">
                              {video.dispositivos_count || 0} disp.
                            </span>
                            {video.asignaciones && video.asignaciones.length > 0 && (() => {
                              const grouped: Record<string, any[]> = {};
                              video.asignaciones!.forEach(a => {
                                const key = a.servidor_nombre || `Servidor #${a.servidor_id}`;
                                if (!grouped[key]) grouped[key] = [];
                                grouped[key].push(a);
                              });
                              return (
                                <div className={`absolute left-1/2 -translate-x-1/2 ${index === 0 ? 'top-full mt-2' : 'bottom-full mb-2'} px-3 py-2 bg-slate-900 dark:bg-slate-800 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/assign:opacity-100 group-hover/assign:visible transition-all duration-200 z-50 min-w-[220px] max-h-[300px] overflow-y-auto`}>
                                  <div className="font-semibold mb-1.5 sticky top-0 bg-slate-900 dark:bg-slate-800 pb-1 border-b border-slate-700">
                                    Dispositivos asignados
                                  </div>
                                  {Object.entries(grouped).map(([server, devices]) => (
                                    <div key={server} className="mt-2 first:mt-0">
                                      <div className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold mb-1">
                                        {server}
                                      </div>
                                      {devices.map((a: any, i: number) => (
                                        <div key={i} className="text-slate-300 py-0.5 pl-2 flex items-center gap-1.5">
                                          <span className="w-1 h-1 rounded-full bg-primary/60" />
                                          {a.dispositivo_nombre || a.dispositivo_codigo || `ID: ${a.dispositivo_id}`}
                                        </div>
                                      ))}
                                    </div>
                                  ))}
                                  <div className={`absolute left-1/2 -translate-x-1/2 border-4 border-transparent ${index === 0 ? 'bottom-full border-b-slate-900 dark:border-b-slate-800' : 'top-full border-t-slate-900 dark:border-t-slate-800'}`}></div>
                                </div>
                              );
                            })()}
                          </div>
                        )}
                      </div>
                       <div className="col-span-2 flex items-center justify-end gap-1.5 md:gap-3">
                        <button onClick={() => handlePreview(video)} className="p-1.5 md:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-transform hover:scale-110" title="Reproducir">
                          <Eye size={16} />
                        </button>
                        <button onClick={() => downloadVideoFile(video)} className="p-1.5 md:p-2 rounded hover:bg-blue-500/10 transition-transform hover:scale-110" title="Descargar">
                          <Download size={16} />
                        </button>
                        <button
                          onClick={() => {
                            setEditingVideo(video);
                            setEditFormData({
                              titulo: video.titulo || video.filename || '',
                              activo: video.activo ?? true,
                              fechaInicio: video.fechaInicio || '',
                              fechaFin: video.fechaFin || '',
                            });
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
                          className="p-1.5 md:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-transform hover:scale-110"
                          title="Editar"
                        >
                          <MoreVertical size={16} />
                        </button>
                        <button onClick={() => handleDeleteClick(video.id, video.titulo || video.filename)} className="p-1.5 md:p-2 rounded hover:bg-red-500/10 transition-transform hover:scale-110" title="Borrar" disabled={deletingVideoId === video.id}>
                          {deletingVideoId === video.id ? '...' : <Trash size={16} />}
                        </button>
                      </div>
                    </div>
                 )) : (
                  <div className="px-3 py-8 text-center text-slate-500">No se encontraron videos.</div>
                );
              })()}
            </div>
          )}
         
          {/* Pagination */}
          {(() => {
            const activePerPage = viewMode === 'cards' ? videosPerPage : tableVideosPerPage;
            const totalPages = Math.ceil(filteredVideos.length / activePerPage);
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
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-gradient-to-br from-black/70 via-black/60 to-black/80 px-4 pt-4 md:pt-20 animate-fade-in">
           <div className="w-full max-w-6xl bg-white dark:bg-[#1c2936] rounded-2xl border border-slate-300/50 dark:border-slate-600/50 shadow-[0_20px_60px_rgba(0,0,0,0.3)] p-6">
             <div className="flex items-start justify-between mb-6 pb-4 border-b border-gradient-to-r from-transparent via-slate-300 to-transparent">
               <div>
                 <h3 className="text-xl font-bold text-slate-900 dark:text-white tracking-wide">DATOS DE ARCHIVOS</h3>
                 <p className="text-sm text-slate-500 mt-1">Configura antes de subir</p>
               </div>
                <button
                  type="button"
                  className="text-slate-400 hover:text-red-500 text-2xl leading-none transition-all duration-200 hover:rotate-90 active:scale-90"
                  onClick={resetUploadModal}
                  disabled={uploading}
                >
                  ×
                </button>
              </div>
             <div className="space-y-3 max-h-[65vh] overflow-y-auto custom-scrollbar">
               {selectedFiles.map((file, idx) => (
                 <div key={file.name} className="border rounded-lg p-4 mb-2 bg-slate-50 dark:bg-[#17202b]">
                    <div className="flex items-start gap-4 mb-3">
                     <div className="shrink-0">
                        {file.type.startsWith('image') && (
                          <img
                            src={URL.createObjectURL(file)}
                            alt={file.name}
                            className="h-28 w-28 object-cover rounded-lg"
                          />
                        )}
                        {file.type.startsWith('video') && (
                          <video
                            src={URL.createObjectURL(file)}
                            className="h-28 w-28 rounded-lg"
                            controls={false}
                          />
                        )}
                      </div>
                     <div className="flex-1 min-w-0">
                       <span className="font-bold text-slate-900 dark:text-white block text-lg truncate">{file.name}</span>
                       <span className="text-sm text-slate-500">({Math.round(file.size / 1024)} KB)</span>
                     </div>
                    <button
                      type="button"
                      className="px-3 py-1.5 rounded bg-slate-200 dark:bg-slate-700 text-sm shrink-0"
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
                           <label className="block text-base font-medium text-slate-700 dark:text-slate-200 mb-2">TÍTULO</label>
                           <input
                             type="text"
                             className="w-full rounded-lg border border-slate-300/70 dark:border-slate-600/70 bg-slate-50/50 dark:bg-[#17202b]/80 px-4 py-3 text-base text-slate-800 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200 "
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
                           <label className="block text-base font-medium text-slate-700 dark:text-slate-200 mb-2">ESTADO</label>
                         <select
                         className="w-full rounded-lg border border-slate-300/70 dark:border-slate-600/70 bg-slate-50/50 dark:bg-[#17202b]/80 px-4 py-3 text-base text-slate-800 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                         value={fileMetadatas[idx]?.activo ? 'activo' : 'inactivo'}
                         onChange={e => {
                           const newMetas = [...fileMetadatas];
                           newMetas[idx].activo = e.target.value === 'activo';
                           setFileMetadatas(newMetas);
                         }}
                       >
                         <option value="activo">ACTIVO</option>
                         <option value="inactivo">INACTIVO</option>
                       </select>
                        </div>
                      </div>
                       <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                         {/* Fecha Inicio */}
                         <div>
                           <label className="block text-base font-medium text-slate-700 dark:text-slate-200 mb-2 ">FECHA INICIO</label>
                            <input
                              type="datetime-local"
                              className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl border-2 bg-white dark:bg-slate-800/50 text-slate-900 dark:text-white text-base sm:text-lg font-mono tracking-[0.15em] sm:tracking-[0.2em] outline-none transition-all"
                              style={{ borderColor: 'rgba(148,163,184,0.3)' }}
                              onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                              onBlur={e => e.currentTarget.style.borderColor = 'rgba(148,163,184,0.3)'}
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
                           <label className="block text-base font-medium text-slate-700 dark:text-slate-200 mb-2">FECHA FIN</label>
                            <input
                              type="datetime-local"
                              className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl border-2 bg-white dark:bg-slate-800/50 text-slate-900 dark:text-white text-base sm:text-lg font-mono tracking-[0.15em] sm:tracking-[0.2em] outline-none transition-all"
                              style={{ borderColor: 'rgba(148,163,184,0.3)' }}
                              onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                              onBlur={e => e.currentTarget.style.borderColor = 'rgba(148,163,184,0.3)'}
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
                        <div 
                          className="flex items-center gap-3 mb-4 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/30 cursor-pointer transition-colors"
                          onClick={() => {
                            const newMetas = [...fileMetadatas];
                            const nuevoEstado = !(newMetas[idx]?.asignacionTodos ?? true);
                            newMetas[idx].asignacionTodos = nuevoEstado;
                            if (nuevoEstado) {
                              newMetas[idx].servidorIds = [];
                              newMetas[idx].dispositivoIds = [];
                            }
                            setFileMetadatas(newMetas);
                          }}
                        >
                          <div className={`w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all duration-200 ${
                            (fileMetadatas[idx]?.asignacionTodos ?? true)
                              ? 'bg-blue-500 border-blue-500 scale-110'
                              : 'border-slate-300 dark:border-slate-600 hover:border-blue-500/50 scale-100'
                          }`}>
                            {(fileMetadatas[idx]?.asignacionTodos ?? true) && <Check size={14} className="text-white" />}
                          </div>
                          <span className="text-base font-medium text-slate-700 dark:text-slate-200 tracking-wide">
                            ASIGNAR A TODAS LAS SEDES Y DISPOSITIVOS 
                          </span>
                          <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            (fileMetadatas[idx]?.asignacionTodos ?? true)
                              ? 'bg-emerald-500/10 text-emerald-500' 
                              : 'bg-slate-500/10 text-slate-500'
                          }`}>
                            {(fileMetadatas[idx]?.asignacionTodos ?? true) ? 'ACTIVO' : 'INACTIVO'}
                          </span>
                        </div>
                        {!fileMetadatas[idx]?.asignacionTodos && (
                          <ServerDeviceSelector
                            servidores={servidores}
                            selectedServidorIds={fileMetadatas[idx]?.servidorIds || []}
                            selectedDispositivoIds={fileMetadatas[idx]?.dispositivoIds || []}
                             onServidorChange={(servidorId, checked) => {
                                setFileMetadatas(prevMetas => {
                                  const newMetas = [...prevMetas];
                                  const currentServidorIds = [...(newMetas[idx]?.servidorIds || [])];
                                  if (checked) {
                                    newMetas[idx] = {
                                      ...newMetas[idx],
                                      asignacionTodos: false,
                                      servidorIds: [...currentServidorIds, servidorId],
                                    };
                                  } else {
                                    newMetas[idx] = {
                                      ...newMetas[idx],
                                      asignacionTodos: false,
                                      servidorIds: currentServidorIds.filter(id => id !== servidorId),
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
                            maxHeight="max-h-[40vh] sm:max-h-[30vh]"
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
            <div className="mt-6 flex flex-col-reverse sm:flex-row justify-end gap-2">
              <button
                type="button"
                onClick={resetUploadModal}
                disabled={uploading}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-base text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-95 transition-transform duration-150"
              >
                CANCELAR
              </button>
              <button
                type="button"
                onClick={handleSubmitUpload}
                disabled={uploading}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary text-white text-base font-semibold disabled:opacity-60 active:scale-95 transition-all duration-150"
              >
                {uploading ? 'SUBIENDO...' : 'GUARDAR Y SUBIR'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sync Modal */}
      {isSyncModalOpen && (
        <div className="fixed inset-0 bg-gradient-to-br from-black/70 via-black/60 to-black/80 flex items-start justify-center z-50 p-4 pt-4 md:pt-20 animate-fade-in">
          <div className="bg-white dark:bg-[#1c2936] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.3)] w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-gradient-to-r from-transparent via-slate-300 to-transparent shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <RefreshCw size={20} className="text-blue-500" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-wide">SINCRONIZACIÓN SELECTIVA</h2>
                  <p className="text-sm text-slate-500 mt-1">Selecciona los dispositivos a sincronizar</p>
                </div>
              </div>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1">
              <div 
                className="flex items-center gap-3 mb-4 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/30 cursor-pointer transition-colors flex-wrap"
                onClick={() => {
                  const nuevoEstado = !syncAllDevices;
                  setSyncAllDevices(nuevoEstado);
                  if (nuevoEstado) {
                    setSyncServidorIds([]);
                    setSyncDispositivoIds([]);
                  }
                }}
              >
                <div className={`w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all duration-200 ${
                  syncAllDevices
                    ? 'bg-blue-500 border-blue-500 scale-110'
                    : 'border-slate-300 dark:border-slate-600 hover:border-blue-500/50 scale-100'
                }`}>
                  {syncAllDevices && <Check size={14} className="text-white" />}
                </div>
                  <span className="text-base font-medium text-slate-700 dark:text-slate-200 tracking-wide">
                    SINCRONIZAR A TODOS LOS DISPOSITIVOS
                  </span>
                <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  syncAllDevices
                    ? 'bg-emerald-500/10 text-emerald-500' 
                    : 'bg-slate-500/10 text-slate-500'
                }`}>
                  {syncAllDevices ? 'ACTIVO' : 'INACTIVO'}
                </span>
              </div>
              
              {!syncAllDevices && (
                <ServerDeviceSelector
                  servidores={servidores}
                  selectedServidorIds={syncServidorIds}
                  selectedDispositivoIds={syncDispositivoIds}
                   onServidorChange={(id, checked) => {
                     setSyncServidorIds(prev =>
                       checked ? [...prev, id] : prev.filter(srvId => srvId !== id)
                     );
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
                  maxHeight="max-h-[50vh] sm:max-h-[65vh]"
                />
              )}
            </div>

            <div className="mt-4 flex flex-col-reverse sm:flex-row justify-end gap-2 p-6 border-t border-gradient-to-r from-transparent via-slate-300 to-transparent">
              <button
                type="button"
                onClick={() => {
                  setIsSyncModalOpen(false);
                  setSyncAllDevices(true);
                  setSyncServidorIds([]);
                  setSyncDispositivoIds([]);
                  setSyncExpandedServers([]);
                }}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-base text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-95 transition-transform duration-150"
              >
                CANCELAR
              </button>
              <button
                type="button"
                onClick={async () => {
                  setIsSyncModalOpen(false);
                  await executeSync();
                }}
                disabled={!syncAllDevices && syncServidorIds.length === 0 && syncDispositivoIds.length === 0}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-base font-semibold disabled:opacity-60 active:scale-95 transition-all duration-150"
              >
                SINCRONIZAR
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Edit Modal */}
      {isEditModalOpen && editingVideo && (
        <div className="fixed inset-0 bg-gradient-to-br from-black/70 via-black/60 to-black/80 flex items-start justify-center z-50 p-4 pt-4 md:pt-20 animate-fade-in">
          <div className="bg-white dark:bg-[#1c2936] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.3)] w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="p-6 border-b border-gradient-to-r from-transparent via-slate-300 to-transparent shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Pencil size={20} className="text-blue-500" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-wide">EDITAR PUBLICIDAD</h2>
                  <p className="text-sm text-slate-500 mt-1 ">Modifica los datos de la publicidad</p>
                </div>
              </div>
            </div>
            
            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              <div>
                  <label className="block text-base font-medium text-slate-700 dark:text-slate-300 mb-2">
                  TÍTULO
                </label>
                <input
                  type="text"
                  value={editFormData.titulo}
                  onChange={e => setEditFormData({ ...editFormData, titulo: e.target.value })}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-300/70 dark:border-slate-600/70 rounded-lg text-base text-slate-900 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                />
              </div>
              
              <div>
                  <label className="block text-base font-medium text-slate-700 dark:text-slate-300 mb-2">
                  FECHA DE INICIO
                </label>
                <input
                  type="datetime-local"
                  value={editFormData.fechaInicio}
                  onChange={e => setEditFormData({ ...editFormData, fechaInicio: e.target.value })}
                  className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl border-2 bg-white dark:bg-slate-800/50 text-slate-900 dark:text-white text-base sm:text-lg font-mono tracking-[0.15em] sm:tracking-[0.2em] outline-none transition-all"
                  style={{ borderColor: 'rgba(148,163,184,0.3)' }}
                  onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                  onBlur={e => e.currentTarget.style.borderColor = 'rgba(148,163,184,0.3)'}
                />
              </div>
              
              <div>
                  <label className="block text-base font-medium text-slate-700 dark:text-slate-300 mb-2">
                  FECHA DE FIN
                </label>
                <input
                  type="datetime-local"
                  value={editFormData.fechaFin}
                  onChange={e => setEditFormData({ ...editFormData, fechaFin: e.target.value })}
                  className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl border-2 bg-white dark:bg-slate-800/50 text-slate-900 dark:text-white text-base sm:text-lg font-mono tracking-[0.15em] sm:tracking-[0.2em] outline-none transition-all"
                  style={{ borderColor: 'rgba(148,163,184,0.3)' }}
                  onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                  onBlur={e => e.currentTarget.style.borderColor = 'rgba(148,163,184,0.3)'}
                />
              </div>
              
              <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/30 cursor-pointer transition-colors">
                <div 
                  className={`w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all duration-200 ${
                    editFormData.activo
                      ? 'bg-emerald-500 border-emerald-500 scale-110'
                      : 'border-slate-300 dark:border-slate-600 hover:border-emerald-500/50 scale-100'
                  }`}
                  onClick={() => setEditFormData({ ...editFormData, activo: !editFormData.activo })}
                >
                  {editFormData.activo && <Check size={14} className="text-white" />}
                </div>
                <label 
                  className="text-base text-slate-700 dark:text-slate-300 tracking-wide cursor-pointer"
                  onClick={() => setEditFormData({ ...editFormData, activo: !editFormData.activo })}
                >
                  ACTIVO
                </label>
                <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  editFormData.activo
                    ? 'bg-emerald-500/10 text-emerald-500' 
                    : 'bg-slate-500/10 text-slate-500'
                }`}>
                  {editFormData.activo ? 'ACTIVO' : 'INACTIVO'}
                </span>
              </div>
               
               {/* Sección de asignación */}
               <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-2">
                 <div 
                   className="flex items-center gap-3 mb-4 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/30 cursor-pointer transition-colors"
                   onClick={() => {
                     const nuevoEstado = !editAsignacionTodos;
                     setEditAsignacionTodos(nuevoEstado);
                     if (nuevoEstado) {
                       setEditServidorIds([]);
                       setEditDispositivoIds([]);
                     }
                   }}
                 >
                   <div className={`w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all duration-200 ${
                     editAsignacionTodos
                       ? 'bg-blue-500 border-blue-500 scale-110'
                       : 'border-slate-300 dark:border-slate-600 hover:border-blue-500/50 scale-100'
                   }`}>
                     {editAsignacionTodos && <Check size={14} className="text-white" />}
                   </div>
                   <span className="text-base font-medium text-slate-700 dark:text-slate-200 tracking-wide">
                     ASIGNAR A TODAS LAS SEDES Y DISPOSITIVOS
                   </span>
                   <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium ${
                     editAsignacionTodos
                       ? 'bg-emerald-500/10 text-emerald-500' 
                       : 'bg-slate-500/10 text-slate-500'
                   }`}>
                     {editAsignacionTodos ? 'ACTIVO' : 'INACTIVO'}
                   </span>
                 </div>
                
                {!editAsignacionTodos && (
                  <ServerDeviceSelector
                    servidores={servidores}
                    selectedServidorIds={editServidorIds}
                    selectedDispositivoIds={editDispositivoIds}
                     onServidorChange={(id, checked) => {
                        setEditServidorIds(prev =>
                          checked ? [...prev, id] : prev.filter(srvId => srvId !== id)
                        );
                      }}
                     onDispositivoChange={(id, checked) => {
                       setEditDispositivoIds(prev =>
                         checked ? [...prev, id] : prev.filter(dispId => dispId !== id)
                       );
                     }}
                    expandedServidores={editExpandedServers}
                    onToggleExpand={(id) => {
                      setEditExpandedServers(prev =>
                        prev.includes(id)
                          ? prev.filter(srvId => srvId !== id)
                          : [...prev, id]
                      );
                    }}
                    maxHeight="max-h-[40vh] sm:max-h-[30vh]"
                  />
                )}
              </div>
            </div>

            <div className="mt-4 flex flex-col-reverse sm:flex-row justify-end gap-2 p-4 border-t border-slate-200 dark:border-slate-700">
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
                 className="w-full sm:w-auto px-5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-base text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-95 transition-transform duration-150"
                >
                  CANCELAR
                </button>
                <button
                  type="button"
                   onClick={async () => {
                    const fechaInicio = editFormData.fechaInicio;
                    const fechaFin = editFormData.fechaFin;

                    if (fechaFin && !fechaInicio) {
                      showNotification('Debes establecer fecha de inicio si pones fecha de fin', 'warning');
                      return;
                    }
                    if (fechaInicio && !fechaFin) {
                      showNotification('Debes establecer fecha de fin si pones fecha de inicio', 'warning');
                      return;
                    }
                    if (fechaInicio && fechaFin && new Date(fechaInicio) > new Date(fechaFin)) {
                      showNotification('La fecha de inicio no puede ser mayor a la fecha fin', 'warning');
                      return;
                    }

                    const hadSchedule = editingVideo?.fechaInicio || editingVideo?.fechaFin;
                    const nowHasSchedule = !!(fechaInicio && fechaFin);
                    const willUnschedule = hadSchedule && !nowHasSchedule;
                    if (willUnschedule) {
                      const ok = window.confirm('¿Estás seguro de desprogramar esta publicidad?\n\nSe eliminarán las fechas de inicio y fin.');
                      if (!ok) return;
                    }

                    setIsSavingEdit(true);
                   try {
                     // Actualizar metadata
                      await updateBannerMetadata(editingVideo.id, {
                        activo: editFormData.activo,
                        titulo: editFormData.titulo || '',
                        fecha_inicio: editFormData.fechaInicio || null,
                        fecha_fin: editFormData.fechaFin || null,
                      });
                    
                    // Actualizar asignaciones
                    await updateBannerAsignations(
                      editingVideo.id,
                      editAsignacionTodos,
                      editServidorIds,
                      editDispositivoIds
                    );
                    
                    const msg = hadSchedule && nowHasSchedule
                      ? 'Publicidad reprogramada correctamente'
                      : hadSchedule && !nowHasSchedule
                      ? 'Publicidad desprogramada correctamente'
                      : !hadSchedule && nowHasSchedule
                      ? 'Publicidad programada correctamente'
                      : 'Publicidad actualizada correctamente';
                    showNotification(msg, 'success');
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
                 className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary text-white text-base font-semibold disabled:opacity-60 active:scale-95 transition-all duration-150"
                >
                  {isSavingEdit ? 'GUARDANDO...' : 'GUARDADO'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Delete Modal */}
      {confirmDelete.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
              Confirmar eliminación
            </h3>
            <p className="text-slate-600 dark:text-slate-300 mb-6">
              ¿Eliminar <strong className="text-slate-700 dark:text-slate-300">{confirmDelete.titulo}</strong>? Esta acción no se puede deshacer.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={handleDeleteCancel}
                className="px-5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-base text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                CANCELAR
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                className="px-5 py-2.5 rounded-lg bg-red-500 text-white text-base font-medium hover:bg-red-600 active:scale-95 transition-transform duration-150"
              >
                ELIMINAR
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Bulk Delete Modal */}
      {confirmBulkDelete.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
              Confirmar eliminación masiva
            </h3>
            <p className="text-slate-600 dark:text-slate-300 mb-6">
              ¿Eliminar {confirmBulkDelete.videoIds.length} archivo{confirmBulkDelete.videoIds.length > 1 ? 's' : ''} seleccionado{confirmBulkDelete.videoIds.length > 1 ? 's' : ''}?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmBulkDelete({ open: false, videoIds: [] })}
                className="px-5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-base text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                CANCELAR
              </button>
              <button
                onClick={handleBulkDeleteConfirm}
                className="px-5 py-2.5 rounded-lg bg-red-500 text-white text-base font-medium hover:bg-red-600 active:scale-95 transition-transform duration-150"
              >
                ELIMINAR
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