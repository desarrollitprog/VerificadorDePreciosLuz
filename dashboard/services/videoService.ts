import api from '../services/axiosInstance';
import { Video } from '../types';

export interface UpdateBannerMetadataPayload {
  activo?: boolean;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
}

export interface UploadMediaPayload {
  titulo: string;
  fechaInicio?: string | null;
  fechaFin?: string | null;
  activo: boolean;
  DispositivoIds: number[];
  servidor?: string;
}

export async function getVideos(): Promise<Video[]> {
  try {
    const response = await api.get('/banners');
    const banners = response.data?.banners;
    if (Array.isArray(banners)) {
      return banners.map((item) => ({
        id: String(item.IdPublicidad ?? item.id ?? ''),
        filename: (item.Url ?? item.url ?? '').split('/').pop() || '',
        url: item.Url ?? item.url ?? '',
        thumbnail: (item.Tipo ?? item.tipo) === 'image' ? (item.Url ?? item.url ?? '') : '',
        tipo: item.Tipo ?? item.tipo ?? '',
        titulo: item.Titulo ?? item.titulo ?? '',
        size: item.size_human ?? item.SizeHuman ?? item.size ?? '',
        date: item.UpdatedAt ?? item.updated_at ?? '',
        duration: item.DuracionSeg ?? item.duracion_seg ?? '',
        status: item.status ?? undefined,
        activo: (item.Activo ?? item.activo) ?? true,
        fechaInicio: item.FechaInicio ?? item.fecha_inicio ?? null,
        fechaFin: item.FechaFin ?? item.fecha_fin ?? null,
        prioridad: item.Prioridad ?? item.prioridad ?? 0,
        views: item.views ?? undefined,
      }));
    }
    return [];
  } catch {
    return [];
  }
}

export async function updateBannerEstado(videoId: string, activo: boolean) {
  const response = await api.patch(`/banners/${videoId}/estado`, { activo });
  return response.data;
}

export async function updateBannerMetadata(videoId: string, payload: UpdateBannerMetadataPayload) {
  const response = await api.patch(`/banners/${videoId}`, payload);
  return response.data;
}

export async function uploadMedia(file: File, payload?: UploadMediaPayload) {
  const formData = new FormData();
  formData.append('file', file);
  if (payload) {
    formData.append('Titulo', payload.titulo);
    if (payload.fechaInicio) {
      formData.append('FechaInicio', payload.fechaInicio);
    }
    if (payload.fechaFin) {
      formData.append('FechaFin', payload.fechaFin);
    }
    formData.append('Activo', String(payload.activo));
    if (payload.DispositivoIds && Array.isArray(payload.DispositivoIds)) {
      payload.DispositivoIds.forEach(id => formData.append('DispositivoIds', String(id)));
    }
    if (payload.servidor) {
      formData.append('servidor', payload.servidor);
    }
  }
  const response = await api.post('/banners/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

export async function deleteVideo(videoId: string) {
  const response = await api.delete(`/banners/${videoId}`);
  return response.data;
}

export async function getBannerDevices(bannerId: string | number) {
  try {
    const response = await api.get(`/banners/${bannerId}/dispositivos`);
    return response.data?.dispositivos || [];
  } catch {
    return [];
  }
}

export async function reassignBannerDevices(bannerId: string | number, dispositivoIds: number[]) {
  try {
    const response = await api.patch(`/banners/${bannerId}/dispositivos`, { dispositivo_ids: dispositivoIds });
    return response.data;
  } catch (err) {
    throw err;
  }
}
