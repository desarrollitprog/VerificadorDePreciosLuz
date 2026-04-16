import api from '../services/axiosInstance';
import { Video, Servidor } from '../types';

export interface UpdateBannerMetadataPayload {
  activo?: boolean;
  fechaInicio?: string | null;
  fechaFin?: string | null;
  titulo?: string;
}

export interface UploadMediaPayload {
  titulo: string;
  fechaInicio?: string | null;
  fechaFin?: string | null;
  activo: boolean;
  asignacionTodos?: boolean;
  servidorIds?: number[];
  dispositivoIds?: string[];
}

export interface FileMetadata {
  titulo: string;
  fechaInicio: string;
  fechaFin: string;
  activo: boolean;
  asignacionTodos: boolean;
  servidorIds: number[];
  dispositivoIds: string[];
}

export interface AsignacionPayload {
  servidor_id: number;
  dispositivo_id: number;
}

export async function getVideos(): Promise<Video[]> {
  try {
    const response = await api.get('/banners');
    const banners = response.data?.banners;
    if (Array.isArray(banners)) {
      return banners.map((item: any) => ({
        id: String(item.IdPublicidad ?? item.id ?? ''),
        filename: (item.Url ?? item.url ?? '').split('/').pop() || '',
        url: item.Url ?? item.url ?? '',
        thumbnail: (item.Tipo ?? item.tipo) === 'image' ? (item.Url ?? item.url ?? '') : (item.ThumbnailUrl ?? ''),
        tipo: item.Tipo ?? item.tipo ?? '',
        titulo: item.Titulo ?? item.titulo ?? '',
        size: item.size_human ?? item.SizeHuman ?? item.size ?? '',
        date: item.UpdatedAt ?? item.updated_at ?? '',
        duration: '',
        status: item.status ?? undefined,
        activo: (item.Activo ?? item.activo) ?? true,
        fechaInicio: item.FechaInicio ?? item.fecha_inicio ?? null,
        fechaFin: item.FechaFin ?? item.fecha_fin ?? null,
        prioridad: item.Prioridad ?? item.prioridad ?? 0,
        views: item.views ?? undefined,
        asignacion_todos: item.asignacion_todos ?? true,
        asignaciones: item.asignaciones ?? [],
        dispositivos_count: item.dispositivos_count ?? 0,
        estado: item.estado ?? 'activo',
      }));
    }
    return [];
  } catch {
    return [];
  }
}

export async function getVideosWithDateFilter(
  fechaDesde?: string,
  fechaHasta?: string,
  incluirTodos: boolean = false
): Promise<Video[]> {
  try {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    if (incluirTodos) params.append('incluir_todos', 'true');
    
    const response = await api.get(`/banners?${params.toString()}`);
    const banners = response.data?.banners;
    if (Array.isArray(banners)) {
      return banners.map((item: any) => ({
        id: String(item.IdPublicidad ?? item.id ?? ''),
        filename: (item.Url ?? item.url ?? '').split('/').pop() || '',
        url: item.Url ?? item.url ?? '',
        thumbnail: (item.Tipo ?? item.tipo) === 'image' ? (item.Url ?? item.url ?? '') : (item.ThumbnailUrl ?? ''),
        tipo: item.Tipo ?? item.tipo ?? '',
        titulo: item.Titulo ?? item.titulo ?? '',
        size: item.size_human ?? item.SizeHuman ?? item.size ?? '',
        date: item.UpdatedAt ?? item.updated_at ?? '',
        duration: '',
        status: item.status ?? undefined,
        activo: (item.Activo ?? item.activo) ?? true,
        fechaInicio: item.FechaInicio ?? item.fecha_inicio ?? null,
        fechaFin: item.FechaFin ?? item.fecha_fin ?? null,
        prioridad: item.Prioridad ?? item.prioridad ?? 0,
        views: item.views ?? undefined,
        asignacion_todos: item.asignacion_todos ?? true,
        asignaciones: item.asignaciones ?? [],
        dispositivos_count: item.dispositivos_count ?? 0,
        estado: item.estado ?? 'activo',
      }));
    }
    return [];
  } catch {
    return [];
  }
}

export async function getServidores(): Promise<Servidor[]> {
  try {
    const response = await api.get('/servidores');
    return response.data?.servidores ?? [];
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

export async function updateBannerAsignations(
  videoId: string, 
  asignacionTodos: boolean, 
  servidorIds?: number[], 
  dispositivoIds?: string[]
) {
  const params = new URLSearchParams();
  params.append('asignacion_todos', String(asignacionTodos));
  if (servidorIds && servidorIds.length > 0) {
    params.append('servidor_ids', JSON.stringify(servidorIds));
  }
  // Siempre enviar dispositivo_ids (array vacío si es "todos")
  params.append('dispositivo_ids', JSON.stringify(dispositivoIds || []));
  const response = await api.put(`/banners/${videoId}/asignaciones?${params.toString()}`);
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
    formData.append('AsignacionTodos', String(payload.asignacionTodos ?? true));
    if (payload.servidorIds && payload.servidorIds.length > 0) {
      formData.append('ServidorIds', JSON.stringify(payload.servidorIds));
    }
    if (payload.dispositivoIds && payload.dispositivoIds.length > 0) {
      formData.append('DispositivoIds', JSON.stringify(payload.dispositivoIds));
    }
  }
  const response = await api.post('/banners/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

export async function asignarBanner(videoId: string, asignaciones: AsignacionPayload[]) {
  const response = await api.post(`/banners/${videoId}/asignaciones`, asignaciones);
  return response.data;
}

export async function sincronizarBanners(
  publicidadIds: string[],
  servidorIds: number[]
) {
  const response = await api.post('/banners/sincronizar', {
    publicidad_ids: publicidadIds,
    servidor_ids: servidorIds
  });
  return response.data;
}

export async function sincronizarServidores(
  servidorIds: number[],
  dispositivoIds?: string[]
) {
  const response = await api.post('/monitoreo/sincronizar-fuerza', {
    servidor_ids: servidorIds,
    dispositivo_ids: dispositivoIds
  });
  return response.data;
}

export async function deleteVideo(videoId: string) {
  const response = await api.delete(`/banners/${videoId}`);
  return response.data;
}
