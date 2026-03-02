import api from './axiosInstance';

export interface Notificacion {
  id: number;
  usuario_id: number;
  tipo: string;
  descripcion: string;
  fecha_creacion: string;
  leida?: boolean;
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

export async function fetchNotificaciones(limit = 10, offset = 0): Promise<NotificacionesResponse> {
  const response = await api.get<NotificacionesResponse>(
    `/notificaciones?limit=${limit}&offset=${offset}`
  );
  return response.data;
}

export async function markNotificacionesRead(): Promise<MarkReadResponse> {
  const response = await api.patch<MarkReadResponse>('/notificaciones/marcar-leidas');
  return response.data;
}
