import api from './axiosInstance';

export interface ServerStatus {
  id: string;
  nombre: string;
  online: boolean;
  almacenamiento_total: number;
  almacenamiento_usado: number;
  porcentaje_uso: number;
}

export interface AlertaCritica {
  nombre_servidor: string;
  mensaje: string;
}

export interface AuditoriaItem {
  id: number;
  tipo: string;
  usuario: string;
  descripcion: string;
  fecha_creacion: string;
}

export async function getServersStatus(): Promise<ServerStatus[]> {
  const response = await api.get('/status');
  return response.data as ServerStatus[];
}

export async function getAlertasCriticas(): Promise<AlertaCritica[]> {
  const response = await api.get('/alertas');
  return response.data as AlertaCritica[];
}

export async function getAuditoria(page = 1, limit = 20): Promise<{ items: AuditoriaItem[]; total: number }> {
  const offset = (page - 1) * limit;
  const response = await api.get('/notificaciones', { params: { limit, offset } });
  const { notificaciones, count } = response.data;
  return {
    items: (notificaciones || []).map((n: any) => ({
      id: n.id,
      tipo: n.tipo,
      usuario: n.usuario || n.user_id,
      descripcion: n.descripcion || n.mensaje,
      fecha_creacion: n.fecha_creacion,
    })),
    total: count || 0,
  };
}
