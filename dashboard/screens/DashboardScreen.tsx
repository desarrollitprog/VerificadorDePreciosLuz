import React, { useEffect, useState } from 'react';
import { useNotification } from '../components/useNotification';
import { Search, UploadCloud, MoreVertical, Eye, Trash, Film, Plus } from 'lucide-react';
import { getVideos, uploadMedia, deleteVideo } from '../services/videoService';
import { Video } from '../types';
import { getForceSyncJobStatus, startForceSyncJob } from '../services/monitoreoService';

export const DashboardScreen: React.FC = () => {
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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadTitulo, setUploadTitulo] = useState('');
  const [uploadFechaInicio, setUploadFechaInicio] = useState('');
  const [uploadFechaFin, setUploadFechaFin] = useState('');
  const [uploadActivo, setUploadActivo] = useState(true);

  const [syncLoading, setSyncLoading] = useState(false);

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

  const resetUploadModal = () => {
    setSelectedFile(null);
    setUploadTitulo('');
    setUploadFechaInicio('');
    setUploadFechaFin('');
    setUploadActivo(true);
    setIsUploadModalOpen(false);
  };

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files?.length) return;
    const file = event.target.files[0];
    const maxSize = 20 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('El archivo excede el tamaño máximo permitido (20 MB).');
      showNotification('El archivo excede el tamaño máximo permitido (20 MB)', 'warning');
      event.target.value = '';
      return;
    }
    const decoratedDefault = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
    setSelectedFile(file);
    setUploadTitulo(decoratedDefault || file.name);
    setUploadFechaInicio('');
    setUploadFechaFin('');
    setUploadActivo(true);
    setIsUploadModalOpen(true);
    event.target.value = '';
  };

  const handleSubmitUpload = async () => {
    if (!selectedFile) {
      showNotification('Selecciona un archivo primero', 'warning');
      return;
    }
    if (!uploadTitulo.trim()) {
      showNotification('El título es obligatorio', 'warning');
      return;
    }

    const fechaInicioIso = uploadFechaInicio ? new Date(uploadFechaInicio).toISOString() : null;
    const fechaFinIso = uploadFechaFin ? new Date(uploadFechaFin).toISOString() : null;

    if (fechaInicioIso && fechaFinIso && new Date(fechaInicioIso) > new Date(fechaFinIso)) {
      showNotification('La fecha de inicio no puede ser mayor a la fecha fin', 'warning');
      return;
    }

    setUploading(true);
    setError(null);
    try {
      await uploadMedia(selectedFile, {
        titulo: uploadTitulo.trim(),
        fechaInicio: fechaInicioIso,
        fechaFin: fechaFinIso,
        activo: uploadActivo,
      });
      const data = await getVideos();
      setVideos(data);
      showNotification('Archivo subido correctamente', 'success');
      resetUploadModal();
    } catch (err: any) {
      setError('Error uploading archivo');
      showNotification('Error al subir archivo', 'error');
    } finally {
      setUploading(false);
    }
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

        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          finalStatus = status;
          break;
        }
      }

      if (!finalStatus) {
        showNotification('Sincronización en progreso', 'warning');
        return;
      }

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
      <div className="relative group cursor-pointer">
        <div className="absolute inset-0 bg-primary/5 rounded-xl border-2 border-dashed border-primary/30 group-hover:border-primary/60 transition-colors pointer-events-none"></div>
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center rounded-xl bg-slate-50/50 dark:bg-[#151f2b] transition-all group-hover:bg-slate-100 dark:group-hover:bg-[#1a2532]">
          <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
            <UploadCloud className="text-primary" size={28} />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Sube Nuevo Contenido</h3>
          <p className="text-slate-500 text-sm max-w-sm mb-6">Click Aqui para subir Videos o Imagenes (Tamaño maximo = 20MB)</p>
          <label className="px-6 py-2.5 bg-primary hover:bg-primary/90 text-white text-sm font-semibold rounded-lg shadow-lg shadow-primary/20 transition-all flex items-center gap-2 cursor-pointer">
            <Plus size={18} />
            Seleccionar Archivo
            <input type="file" accept="video/mp4,video/mkv,image/png,image/jpeg,image/jpg" className="hidden" onChange={handleUpload} />
          </label>
          {uploading && <div className="mt-2 text-primary">Subiendo...</div>}
          {error && <div className="mt-2 text-red-500">{error}</div>}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-[#1c2936] p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">Videos Totales</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              Local: {Array.isArray(videos) ? videos.length : 0}
              {/* Remoto: aquí puedes mostrar la cantidad de videos remotos si tienes ese dato */}
            </p>
          </div>
          <Film className="text-slate-400" size={32} />
        </div>
        {/*<div className="bg-white dark:bg-[#1c2936] p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">Almacenamiento usado</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {/* Aquí debes mostrar el almacenamiento real del servidor secundario, por ejemplo: */}
              {/* {servidores[0]?.almacenamiento || 'N/A'} 
              N/A
            </p>
          </div>
          <HardDrive className="text-slate-400" size={32} />
        </div>*/}
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
            return filteredVideos.length > 0 ? filteredVideos.map((video, idx) => (
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
                      Fecha subida: {video.date ? new Date(video.date).toLocaleString() : 'Fecha desconocida'}
                    </span>
                  </div>
                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                    <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs font-medium" onClick={() => handlePreview(video)}>
                      <Eye size={14} />
                      Reproducir
                    </button>
                          {/* Modal de vista previa */}
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
          <div className="w-full max-w-lg bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-xl p-5">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Datos del Archivo</h3>
              <button
                type="button"
                className="text-slate-500 hover:text-red-500 text-xl leading-none"
                onClick={resetUploadModal}
                disabled={uploading}
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Título</label>
                <input
                  type="text"
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
                  value={uploadTitulo}
                  onChange={(e) => setUploadTitulo(e.target.value)}
                  placeholder="Ej: Promo principal - Sucursal Centro"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fecha Inicio</label>
                  <input
                    type="datetime-local"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
                    value={uploadFechaInicio}
                    onChange={(e) => setUploadFechaInicio(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fecha Fin</label>
                  <input
                    type="datetime-local"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
                    value={uploadFechaFin}
                    onChange={(e) => setUploadFechaFin(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Estado</label>
                <select
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#17202b] px-3 py-2 text-sm text-slate-900 dark:text-white"
                  value={uploadActivo ? 'activo' : 'inactivo'}
                  onChange={(e) => setUploadActivo(e.target.value === 'activo')}
                >
                  <option value="activo">Activo</option>
                  <option value="inactivo">Inactivo</option>
                </select>
              </div>
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