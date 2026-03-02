import api from './axiosInstance';

export interface DeviceStatus {
  device_id: string;
  online: boolean;
  last_seen: string | null;
}

export interface ServerStatus {
  id: string;
  nombre: string;
  ip: string;
  online: boolean;
  almacenamiento_total: number;
  almacenamiento_usado: number;
  porcentaje_uso: number;
}

export interface ServerStatusDetail extends ServerStatus {
  dispositivos_total: number;
  dispositivos_online: number;
  dispositivos: DeviceStatus[];
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

export interface ForceSyncJobStart {
  success: boolean;
  message?: string;
  job_id: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
}

export interface ForceSyncJobStatus {
  success: boolean;
  job_id: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  total_online?: number;
  success_count?: number;
  failed_count?: number;
  details?: any[];
  error?: string;
}

function extractServers(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.servidores)) return data.servidores;
  return [];
}

export async function getServersStatus(): Promise<ServerStatus[]> {
  const response = await api.get('/status');
  return extractServers(response.data) as ServerStatus[];
}

export async function getServersStatusWithDevices(): Promise<ServerStatusDetail[]> {
  const response = await api.get('/status-detalle');
  return extractServers(response.data).map((s: any) => ({
    id: String(s.id),
    nombre: s.nombre,
    ip: s.ip,
    online: !!s.online,
    almacenamiento_total: Number(s.almacenamiento_total || 0),
    almacenamiento_usado: Number(s.almacenamiento_usado || 0),
    porcentaje_uso: Number(s.porcentaje_uso || 0),
    dispositivos_total: Number(s.dispositivos_total || 0),
    dispositivos_online: Number(s.dispositivos_online || 0),
    dispositivos: Array.isArray(s.dispositivos) ? s.dispositivos : [],
  }));
}

export async function startForceSyncJob(): Promise<ForceSyncJobStart> {
  const response = await api.post('/monitoreo/sincronizar-fuerza');
  return response.data as ForceSyncJobStart;
}

export async function getForceSyncJobStatus(jobId: string): Promise<ForceSyncJobStatus> {
  const response = await api.get(`/monitoreo/sincronizar-fuerza/${jobId}`);
  return response.data as ForceSyncJobStatus;
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
