import api from './axiosInstance';

export interface Notificacion {
  id: number;
  usuario_id: number;
  tipo: string;
  descripcion: string;
  fecha_creacion: string;
}

export interface NotificacionesResponse {
  success: boolean;
  notificaciones: Notificacion[];
  limit: number;
  offset: number;
  count: number;
}

export async function fetchNotificaciones(limit = 10, offset = 0): Promise<NotificacionesResponse> {
  const response = await api.get<NotificacionesResponse>(
    `/notificaciones?limit=${limit}&offset=${offset}`
  );
  return response.data;
}
