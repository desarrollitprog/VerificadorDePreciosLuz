import api from './axiosInstance';

export interface AuditoriaItem {
  id: number;
  fecha: string;
  tipo: string;
  descripcion: string;
  dispositivo_id: string | null;
  dispositivo_nombre: string | null;
  servidor_id: number | null;
  servidor_nombre: string | null;
  sesion_inicio: string | null;
  sesion_fin: string | null;
  duracion_segundos: number | null;
  usuario: string | null;
  origen: 'sesion' | 'notificacion';
}

export interface AuditoriaResponse {
  success: boolean;
  items: AuditoriaItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface AuditoriaFiltros {
  busqueda?: string;
  tipo?: string;
  dispositivo_id?: string;
  servidor_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  page?: number;
  limit?: number;
}

export async function getAuditoria(filtros: AuditoriaFiltros = {}): Promise<AuditoriaResponse> {
  const params = new URLSearchParams();
  
  if (filtros.busqueda) params.append('busqueda', filtros.busqueda);
  if (filtros.tipo) params.append('tipo', filtros.tipo);
  if (filtros.dispositivo_id) params.append('dispositivo_id', filtros.dispositivo_id);
  if (filtros.servidor_id) params.append('servidor_id', String(filtros.servidor_id));
  if (filtros.fecha_desde) params.append('fecha_desde', filtros.fecha_desde);
  if (filtros.fecha_hasta) params.append('fecha_hasta', filtros.fecha_hasta);
  if (filtros.page) params.append('page', String(filtros.page));
  if (filtros.limit) params.append('limit', String(filtros.limit));

  const response = await api.get(`/auditoria?${params.toString()}`);
  return response.data as AuditoriaResponse;
}
