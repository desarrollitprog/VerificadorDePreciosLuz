import api from '../services/axiosInstance';
import { Video } from '../types';

export async function getVideos(): Promise<Video[]> {
  try {
    const response = await api.get('/banners');
    const banners = response.data?.banners;
    if (Array.isArray(banners)) {
      return banners.map((item) => ({
        id: item.IdPublicidad ?? item.id ?? '',
        filename: (item.Url ?? item.url ?? '').split('/').pop() || '',
        url: item.Url ?? item.url ?? '',
        thumbnail: (item.Tipo ?? item.tipo) === 'image' ? (item.Url ?? item.url ?? '') : '',
        tipo: item.Tipo ?? item.tipo ?? '',
        titulo: item.Titulo ?? item.titulo ?? '',
        size: '', // No lo provee el backend
        date: item.UpdatedAt ?? item.updated_at ?? '',
        duration: item.DuracionSeg ?? item.duracion_seg ?? '',
        prioridad: item.Prioridad ?? item.prioridad ?? 0,
        status: item.status ?? undefined,
        views: item.views ?? undefined,
      }));
    }
    return [];
  } catch {
    return [];
  }
}

export async function uploadMedia(file) {
  const formData = new FormData();
  formData.append('file', file);
  // Puedes agregar otros campos si tu backend los requiere
  const response = await api.post('/banners/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}


export async function deleteVideo(videoId) {
  const response = await api.delete(`/banners/${videoId}`);
  return response.data;
}
