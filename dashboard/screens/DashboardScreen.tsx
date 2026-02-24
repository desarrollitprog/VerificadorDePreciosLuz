import React, { useEffect, useState } from 'react';
import { Search, Filter, UploadCloud, MoreVertical, Play, Eye, Trash, Film, HardDrive, TrendingUp, Plus } from 'lucide-react';
import axios from 'axios';

import { getVideos, uploadMedia, deleteVideo } from '../services/videoService';
import { Video } from '../types';
import { getServersStatus } from '../services/monitoreoService';
import ServerCard from '../components/monitoreo/ServerCard';

export const DashboardScreen: React.FC = () => {
  const [preview, setPreview] = useState<{url: string, tipo: string, titulo: string} | null>(null);
  const handlePreview = (video: Video) => {
    setPreview({ url: video.url, tipo: video.tipo, titulo: video.titulo || video.filename });
  };
  const closePreview = () => setPreview(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Monitoreo de servidores
  const [servidores, setServidores] = useState<any[]>([]);
  const [loadingMonitoreo, setLoadingMonitoreo] = useState(true);
  const [errorMonitoreo, setErrorMonitoreo] = useState<string | null>(null);

  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    const fetchStatus = async () => {
      setLoadingMonitoreo(true);
      setErrorMonitoreo(null);
      try {
        const data = await getServersStatus();
        setServidores(Array.isArray(data) ? data : []);
      } catch {
        setServidores([]);
        setErrorMonitoreo('Error al conectar con el servicio de monitoreo');
      } finally {
        setLoadingMonitoreo(false);
      }
    };
    fetchStatus();
    interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    async function fetchVideos() {
      setLoading(true);
      try {
        const data = await getVideos();
        setVideos(Array.isArray(data) ? data : []);
      } catch (err: any) {
        setVideos([]);
        setError('Error loading videos');
      } finally {
        setLoading(false);
      }
    }
    fetchVideos();
  }, []);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files?.length) return;
    setUploading(true);
    setError(null);
    try {
      await uploadMedia(event.target.files[0]);
      const data = await getVideos();
      setVideos(data);
    } catch (err: any) {
      setError('Error uploading archivo');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (videoId: string) => {
    setError(null);
    try {
      await deleteVideo(videoId);
      setVideos(videos.filter(v => v.id !== videoId));
    } catch (err: any) {
      setError('Error deleting video');
    }
  };

  const handleForceSync = async () => {
    setSyncLoading(true);
    setSyncResult(null);
    const endpoint = '/monitoreo/sincronizar-fuerza';
    console.log('[SYNC] Intentando sincronización forzada. Endpoint:', endpoint);
    try {
      const response = await api.post(endpoint);
      console.log('[SYNC] Respuesta recibida:', response);
      if (response.data.success) {
        setSyncResult('Sincronización forzada ejecutada correctamente.');
        console.log('[SYNC] Sincronización exitosa.');
      } else {
        setSyncResult('Sincronización fallida.');
        console.warn('[SYNC] Sincronización fallida. Respuesta:', response.data);
      }
    } catch (error: any) {
      setSyncResult('Error al ejecutar la sincronización.');
      if (error.response) {
        console.error('[SYNC] Error de respuesta del backend:', error.response);
      } else if (error.request) {
        console.error('[SYNC] No se recibió respuesta del backend. Request:', error.request);
      } else {
        console.error('[SYNC] Error al configurar la petición:', error.message);
      }
    } finally {
      setSyncLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8">
      {/* Botón de sincronización forzada arriba de Video Library */}
      <div className="flex items-center justify-end mb-4">
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow hover:bg-blue-700 transition disabled:opacity-50"
          onClick={handleForceSync}
          disabled={syncLoading}
        >
          {syncLoading ? 'Sincronizando...' : 'Sincronización Forzada'}
        </button>
      </div>
      {syncResult && (
        <div className="mb-4 text-green-600 font-semibold">{syncResult}</div>
      )}

      {/* Monitoreo de Servidores */}
      {/* Bloque de monitoreo eliminado, debe ir en otra sección/menu */}

      {/* Title & Search */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">Video Library</h2>
          <p className="text-slate-500 mt-1">Manage, upload, and organize your video content.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              className="pl-10 pr-4 py-2 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full sm:w-64 transition-all"
              placeholder="Search videos..."
            />
          </div>
          <button className="p-2 bg-slate-100 dark:bg-[#1c2936] rounded-lg text-slate-500 hover:text-primary transition-colors">
            <Filter size={20} />
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
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Upload New Video</h3>
          <p className="text-slate-500 text-sm max-w-sm mb-6">Drag & drop files here or click to browse. Supports MP4, MKV (Max 500MB)</p>
          <label className="px-6 py-2.5 bg-primary hover:bg-primary/90 text-white text-sm font-semibold rounded-lg shadow-lg shadow-primary/20 transition-all flex items-center gap-2 cursor-pointer">
            <Plus size={18} />
            Select Files
            <input type="file" accept="video/mp4,video/mkv,image/png,image/jpeg,image/jpg" className="hidden" onChange={handleUpload} />
          </label>
          {uploading && <div className="mt-2 text-primary">Uploading...</div>}
          {error && <div className="mt-2 text-red-500">{error}</div>}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-[#1c2936] p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">Total Videos</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              Local: {Array.isArray(videos) ? videos.length : 0}
              {/* Remoto: aquí puedes mostrar la cantidad de videos remotos si tienes ese dato */}
            </p>
          </div>
          <Film className="text-slate-400" size={32} />
        </div>
        <div className="bg-white dark:bg-[#1c2936] p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">Storage Used</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {/* Aquí debes mostrar el almacenamiento real del servidor secundario, por ejemplo: */}
              {/* {servidores[0]?.almacenamiento || 'N/A'} */}
              N/A
            </p>
          </div>
          <HardDrive className="text-slate-400" size={32} />
        </div>
      </div>

      {/* Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">Recent Uploads</h3>
          <button className="text-sm text-primary font-medium hover:underline">View All</button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.isArray(videos) && videos.length > 0 && videos[0] && (
            <div className="col-span-1">
              <div className="border-2 border-primary rounded-xl p-4 bg-white dark:bg-[#1c2936] shadow-lg">
                <div className="text-xs text-primary font-bold mb-2">Last Uploaded</div>
                {/* Miniatura y datos del último video */}
                <div className="aspect-video bg-slate-800 relative overflow-hidden mb-2 flex items-center justify-center">
                  {videos[0].tipo === 'image' ? (
                    <img src={videos[0].thumbnail} alt={videos[0].titulo || videos[0].filename} className="w-full h-full object-cover" />
                  ) : (
                    <div className="flex items-center justify-center w-full h-full">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect width="24" height="24" rx="6" fill="#1c2936" />
                        <polygon points="9,7 17,12 9,17" fill="#fff" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                  {videos[0].titulo || videos[0].filename}
                </div>
                <div className="text-xs text-slate-500">
                  Fecha subida: {videos[0].date ? new Date(videos[0].date).toLocaleString() : 'Fecha desconocida'}
                </div>
              </div>
            </div>
          )}
          {/* El resto de videos, excluyendo el último */}
          {Array.isArray(videos) && videos.length > 1 && videos.slice(1).map((video) => (
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
                    View
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
          ))}
        </div>
      </div>
    </div>
  );
};