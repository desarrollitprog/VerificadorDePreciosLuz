import api from './axiosInstance';

export interface Notificacion {
  id: number;
  usuario_id: number;
  nombre_usuario?: string;
  tipo: string;
  descripcion: string;
  fecha_creacion: string;
  leida?: boolean;
  dispositivo_id?: string;
  servidor_id?: number;
}

export interface NotificacionesResponse {
  success: boolean;
  notificaciones: Notificacion[];
  limit: number;
  offset: number;
  count: number;
  unread_count: number;
}

export interface MarkReadResponse {
  success: boolean;
  updated: number;
}

export interface DeleteReadResponse {
  success: boolean;
  deleted: number;
}

export async function fetchNotificaciones(limit = 10, offset = 0, soloNoLeidas = false): Promise<NotificacionesResponse> {
  const response = await api.get<NotificacionesResponse>(
    `/notificaciones?limit=${limit}&offset=${offset}&solo_no_leidas=${soloNoLeidas}`
  );
  return response.data;
}

export async function markNotificacionesRead(): Promise<MarkReadResponse> {
  const response = await api.patch<MarkReadResponse>('/notificaciones/marcar-leidas');
  return response.data;
}

export async function markNotificacionRead(notificacionId: number): Promise<{ success: boolean; message: string }> {
  const response = await api.patch<{ success: boolean; message: string }>(`/notificaciones/${notificacionId}/marcar-leida`);
  return response.data;
}

export async function deleteReadNotificaciones(): Promise<DeleteReadResponse> {
  const response = await api.delete<DeleteReadResponse>('/notificaciones/leidas');
  return response.data;
}
