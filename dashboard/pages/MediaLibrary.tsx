import React, { useState, useEffect, useRef } from 'react';
import Notification from '../components/Notification';
import api from '../services/axiosInstance';
import { 
  Filter, 
  Trash2, 
  CalendarDays, 
  UploadCloud, 
  MoreVertical,
  PlayCircle,
  GripVertical,
  Info,
  Save
} from 'lucide-react';
import { MediaItem } from '../types';

const mapBackendBannerToMediaItem = (banner) => ({
  id: banner.IdPublicidad?.toString() || '',
  title: banner.Titulo || '',
  duration: banner.DuracionSeg ? `${banner.DuracionSeg}s` : '',
  status: banner.FechaFin && new Date(banner.FechaFin) < new Date() ? 'expired' : 'live',
  resolution: 'N/A',
  dateRange: banner.FechaInicio && banner.FechaFin ? `${banner.FechaInicio?.slice(0,10)} - ${banner.FechaFin?.slice(0,10)}` : '',
  thumbnail: banner.Tipo === 'image' ? banner.Url : 'https://picsum.photos/seed/media1/400/225',
  type: banner.Tipo || 'video',
  fileSize: ''
});

const StatusBadge = ({ status }: { status: MediaItem['status'] }) => {
  const styles = {
    live: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    scheduled: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    expired: 'bg-red-500/10 text-red-400 border-red-500/20',
  };
  
  const labels = {
    live: 'Live',
    scheduled: 'Scheduled',
    expired: 'Expired'
  };

  return (
    <span class={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[status]}`}>
      {status === 'live' && <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>}
      {labels[status]}
    </span>
  );
};

const MediaLibrary: React.FC = () => {
    // Eliminar banner
    const handleDelete = async (id: string) => {
      if (!window.confirm('¿Seguro que deseas eliminar este banner?')) return;
      try {
        const res = await api.delete(`/banners/${id}`);
        if (res.data && res.data.success) {
          setNotification({ message: res.data.message || 'Banner eliminado correctamente.', type: 'success' });
          // Refrescar lista
          const bannersRes = await api.get('/banners');
          setMedia(bannersRes.data.banners.map(mapBackendBannerToMediaItem));
        } else {
          setNotification({ message: res.data.message || 'Error al eliminar el banner.', type: 'error' });
        }
      } catch (err: any) {
        setNotification({ message: err?.response?.data?.message || 'Error al eliminar el banner.', type: 'error' });
      }
      setTimeout(() => setNotification(null), 4000);
    };
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [media, setMedia] = useState<MediaItem[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Obtener banners reales del backend
  useEffect(() => {
    const fetchBanners = async () => {
      try {
        const res = await api.get('/banners');
        if (res.data && res.data.banners) {
          setMedia(res.data.banners.map(mapBackendBannerToMediaItem));
        }
      } catch (err) {
        setNotification({ message: 'Error al obtener banners.', type: 'error' });
      }
    };
    fetchBanners();
  }, []);

  // Subida real de archivo
  const handleUpload = async () => {
    if (!fileInputRef.current?.files?.[0]) {
      setNotification({ message: 'Selecciona un archivo para subir.', type: 'error' });
      return;
    }
    const file = fileInputRef.current.files[0];
    // Validar si ya existe un archivo con el mismo nombre
    if (media.some(item => item.title === file.name)) {
      setNotification({ message: 'Ya existe un archivo con ese nombre.', type: 'error' });
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('Titulo', file.name);
    formData.append('Prioridad', '1');
    formData.append('DuracionSeg', '30');
    // Puedes agregar más campos según tu backend
    try {
      const res = await api.post('/banners/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (res.data && res.data.success) {
        setNotification({ message: res.data.message || 'Archivo subido correctamente.', type: 'success' });
        // Refrescar lista
        const bannersRes = await api.get('/banners');
        setMedia(bannersRes.data.banners.map(mapBackendBannerToMediaItem));
      } else {
        setNotification({ message: res.data.message || 'Error al subir el archivo.', type: 'error' });
      }
    } catch (err: any) {
      setNotification({ message: err?.response?.data?.message || 'Error al subir el archivo.', type: 'error' });
    }
    setTimeout(() => setNotification(null), 4000);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div class="flex h-[calc(100vh-4rem)] overflow-hidden">
      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}
      {/* Main Grid Area */}
      <div class="flex-1 overflow-y-auto p-6 bg-background">
        <div class="flex justify-between items-center mb-6">
          <div class="flex items-center gap-4">
            <div class="relative group">
              <button class="flex items-center gap-2 px-3 py-2 bg-surface hover:bg-surfaceHighlight border border-gray-700 rounded-lg text-sm font-medium text-gray-300 transition-colors shadow-sm">
                <Filter className="w-4 h-4" />
                <span>Filter Status</span>
              </button>
            </div>
          </div>
          <div class="flex items-center gap-4">
             <div class="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-blue-900/20 rounded-lg border border-blue-800">
                <span class="text-xs font-semibold text-blue-300 uppercase tracking-wide">2 Selected</span>
                <div class="h-4 w-px bg-blue-800 mx-1"></div>
                <button class="p-1 text-gray-400 hover:text-red-400 transition-colors"><Trash2 className="w-4 h-4" /></button>
                <button class="p-1 text-gray-400 hover:text-blue-400 transition-colors"><CalendarDays className="w-4 h-4" /></button>
             </div>
             <input
               type="file"
               ref={fileInputRef}
               accept="image/*,video/*"
               className="hidden"
               onClick={e => { (e.target as HTMLInputElement).value = ''; }}
             />
             <button
               class="flex items-center gap-2 bg-primary hover:bg-primary-hover text-white px-5 py-2.5 rounded-lg font-medium shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5 active:translate-y-0"
               onClick={() => fileInputRef.current?.click()}
             >
                <UploadCloud className="w-5 h-5" />
                <span>Upload Video</span>
             </button>
             <button
               class="ml-2 px-3 py-2 bg-emerald-700 text-white rounded hover:bg-emerald-800 transition-all"
               onClick={handleUpload}
             >Subir</button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
           {media.map((item) => (
            <div key={item.id} class={`group relative bg-surface rounded-xl border border-gray-700 hover:border-primary transition-all shadow-sm hover:shadow-xl hover:shadow-black/20 overflow-hidden flex flex-col ${item.status === 'expired' ? 'opacity-70 hover:opacity-100' : ''}`}>
              <div class="absolute top-3 left-3 z-10 flex gap-2 items-center">
                <input type="checkbox" class="w-5 h-5 rounded border-gray-600 text-primary focus:ring-primary bg-black/50 backdrop-blur cursor-pointer" />
                <button
                 class="p-1 rounded bg-red-700/80 hover:bg-red-800 text-white text-xs font-bold shadow transition-all"
                 title="Eliminar banner"
                 onClick={() => handleDelete(item.id)}
                >🗑</button>
              </div>
              <div class="relative aspect-video bg-gray-900 cursor-pointer overflow-hidden group/image">
                <img src={item.thumbnail} alt={item.title} class="w-full h-full object-cover transition-transform duration-700 group-hover/image:scale-105 opacity-80 group-hover:opacity-100" />
                <div class="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/80 to-transparent"></div>
                <span class="absolute bottom-3 right-3 bg-black/60 backdrop-blur-md text-white text-xs font-bold font-mono px-2 py-0.5 rounded border border-white/10">{item.duration}</span>
                <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover/image:opacity-100 transition-opacity duration-300 bg-black/20 backdrop-blur-[2px]">
                  <PlayCircle className="w-12 h-12 text-white drop-shadow-xl" />
                </div>
              </div>
              <div class="p-5 flex-1 flex flex-col">
                <div class="flex items-start justify-between gap-3 mb-2">
                  <h3 class="font-semibold text-gray-200 truncate text-sm leading-tight" title={item.title}>{item.title}</h3>
                  <button class="text-gray-400 hover:text-white"><MoreVertical className="w-4 h-4" /></button>
                </div>
                <div class="flex items-center gap-3 mb-4">
                  <StatusBadge status={item.status} />
                  <span class="text-xs font-medium text-gray-400 bg-gray-800 px-2 py-0.5 rounded tracking-wide">{item.resolution}</span>
                </div>
                <div class="mt-auto pt-3 border-t border-gray-700 flex items-center gap-2 text-xs text-gray-500">
                  <CalendarDays className="w-4 h-4" />
                  <span class={`font-medium ${item.status === 'expired' ? 'line-through decoration-red-500/50' : ''}`}>{item.dateRange}</span>
                </div>
              </div>
            </div>
           ))}
          
           <div class="flex flex-col items-center justify-center p-8 bg-surface/50 rounded-xl border-2 border-dashed border-gray-700 hover:border-primary hover:bg-gray-800/50 transition-all group h-full min-h-[300px]">
             <input
               type="file"
               ref={fileInputRef}
               accept="image/*,video/*"
               className="hidden"
               onClick={e => { (e.target as HTMLInputElement).value = ''; }}
             />
             <button
               class="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-inner"
               onClick={() => fileInputRef.current?.click()}
             >
                <UploadCloud className="w-8 h-8 text-gray-500 group-hover:text-primary transition-colors" />
             </button>
             <span class="font-semibold text-gray-400 group-hover:text-gray-200 text-lg">Upload New Video</span>
             <span class="text-sm text-gray-500 mt-2">MP4, MOV up to 200MB</span>
             <button
               class="mt-4 px-3 py-2 bg-emerald-700 text-white rounded hover:bg-emerald-800 transition-all"
               onClick={handleUpload}
             >Subir</button>
           </div>
        </div>
      </div>

      {/* Playlist Sidebar */}
      <aside class="w-80 bg-surface border-l border-gray-800 flex flex-col z-10 shadow-2xl">
        <div class="p-5 border-b border-gray-800 flex justify-between items-center bg-surface sticky top-0 z-20">
           <div>
              <h2 class="font-bold text-white text-lg">Playlist Order</h2>
              <p class="text-xs text-gray-500 mt-0.5 font-medium">Drag to reorder global playback</p>
           </div>
           <Info className="w-5 h-5 text-gray-500 cursor-help hover:text-primary transition-colors" />
        </div>
        <div class="flex-1 overflow-y-auto p-4 space-y-3 bg-black/20">
            {media.slice(0, 4).map((item, idx) => {
              return (
                 <div key={idx} class="flex items-center gap-3 p-3 bg-surface border border-gray-700 rounded-lg hover:border-blue-500/50 group select-none transition-all shadow-sm">
                    <div class="flex flex-col items-center gap-1 text-gray-600 hover:text-gray-400 cursor-move p-1">
                       <GripVertical className="w-5 h-5" />
                    </div>
                    <div class="w-6 h-6 rounded bg-gray-800 text-gray-400 text-xs font-bold flex items-center justify-center flex-shrink-0 border border-gray-700">
                       {idx}
                    </div>
                    <img src={item.thumbnail} alt="" class="w-12 h-8 rounded object-cover flex-shrink-0 bg-gray-800" />
                    <div class="min-w-0 flex-1">
                       <p class="text-sm font-semibold text-gray-300 truncate">{item.title}</p>
                       <div class="flex items-center gap-1.5 mt-0.5">
                          <span class={`w-1.5 h-1.5 rounded-full ${item.status === 'live' ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
                          <p class="text-[10px] uppercase font-bold text-gray-500">{item.duration} • {item.status}</p>
                       </div>
                    </div>
                 </div>
              );
           })}
        </div>
        <div class="p-4 border-t border-gray-800 bg-surface shadow-lg">
           <div class="flex justify-between items-center text-xs text-gray-500 mb-4 bg-gray-900/50 p-2 rounded border border-gray-800">
              <span class="font-medium">Total Loop Duration:</span>
              <span class="font-mono font-bold text-white text-sm">01:50</span>
           </div>
           <button class="w-full bg-primary hover:bg-primary-hover text-white py-3 rounded-lg font-bold shadow-lg shadow-blue-600/20 transition-all flex justify-center items-center gap-2 text-sm">
              <Save className="w-4 h-4" />
              Save Priority Order
           </button>
        </div>
      </aside>
    </div>
  );
};

export default MediaLibrary;