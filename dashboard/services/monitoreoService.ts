import api from './axiosInstance';

export interface DeviceStatus {
  device_id: string;
  nombre_amigable?: string | null;
  nombre_mostrado?: string;
  online: boolean;
  last_seen: string | null;
  sesion_activa?: boolean;
  tiempo_actual?: number | null;
  ultima_duracion?: number | null;
  tiempo_acumulado?: number | null;
  server_id?: string | null;
  hora_reinicio?: string | null;
  reinicio_recurrente?: boolean;
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

export interface RenameDeviceResponse {
  success: boolean;
  device_id: string;
  nombre_amigable: string | null;
}

export interface RenameServerResponse {
  success: boolean;
  server_id: number;
  nombre: string;
  ip: string;
}

export interface SecondaryServerVideoCount {
  id: string;
  nombre: string;
  ip: string;
  videos_actuales: number;
}

export interface DeviceContent {
  device_id: string;
  contenido: {
    titulo: string;
    url: string;
    tipo: 'video' | 'image';
    thumbnail?: string;
  } | null;
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
    dispositivos: Array.isArray(s.dispositivos)
      ? s.dispositivos.map((d: any) => ({
          device_id: String(d.device_id),
          nombre_amigable: d.nombre_amigable ?? null,
          nombre_mostrado: d.nombre_mostrado ?? String(d.device_id),
          online: !!d.online,
          last_seen: d.last_seen ?? null,
          sesion_activa: d.sesion_activa ?? false,
          tiempo_actual: d.tiempo_actual ?? null,
          ultima_duracion: d.ultima_duracion ?? null,
          tiempo_acumulado: d.tiempo_acumulado ?? null,
          server_id: d.server_id ?? null,
          hora_reinicio: d.hora_reinicio ?? null,
          reinicio_recurrente: d.reinicio_recurrente ?? false,
        }))
      : [],
  }));
}

export async function renameDevice(deviceId: string, nombreAmigable: string | null): Promise<RenameDeviceResponse> {
  const response = await api.patch(`/dispositivos/${encodeURIComponent(deviceId)}/nombre`, {
    nombre_amigable: nombreAmigable,
  });
  return response.data as RenameDeviceResponse;
}

export async function renameServer(serverId: string, nombre: string): Promise<RenameServerResponse> {
  const response = await api.patch(`/servidores/${encodeURIComponent(serverId)}/nombre`, {
    nombre,
  });
  return response.data as RenameServerResponse;
}

export async function getSecondaryServersVideoCounts(): Promise<SecondaryServerVideoCount[]> {
  const response = await api.get('/monitoreo/servidores/videos-actuales');
  const servers = Array.isArray(response.data?.servidores) ? response.data.servidores : [];
  return servers.map((s: any) => ({
    id: String(s.id),
    nombre: String(s.nombre ?? s.ip ?? 'Servidor'),
    ip: String(s.ip ?? ''),
    videos_actuales: Number(s.videos_actuales ?? 0),
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

export async function getDeviceContent(deviceId: string): Promise<DeviceContent> {
  const response = await api.get(`/dispositivos/${encodeURIComponent(deviceId)}/contenido`);
  return response.data as DeviceContent;
}

export async function restartDevice(deviceId: string): Promise<{ success: boolean; message: string }> {
  const response = await api.post(`/dispositivos/${encodeURIComponent(deviceId)}/reiniciar`);
  return response.data as { success: boolean; message: string };
}

export async function purgeDevice(deviceId: string): Promise<{ success: boolean; status: string; message: string }> {
  const response = await api.post(`/dispositivos/${encodeURIComponent(deviceId)}/purge`);
  return response.data as { success: boolean; status: string; message: string };
}

export async function deleteDevice(deviceId: string): Promise<{ success: boolean; message: string }> {
  const response = await api.delete(`/dispositivos/${encodeURIComponent(deviceId)}`);
  return response.data as { success: boolean; message: string };
}

export async function deleteServer(serverId: string): Promise<{ success: boolean; message: string }> {
  const response = await api.delete(`/servidores/${encodeURIComponent(serverId)}`);
  return response.data as { success: boolean; message: string };
}

export interface ScheduleRestartParams {
  device_ids: string[];  // vacío = todos
  hour: string;          // formato "06:35"
  recurring: boolean;
}

export interface ScheduleRestartResult {
  total: number;
  enviados: number;
  fallidos: number;
  details: Array<{
    device_id: string;
    status: string;
    scheduled_at?: string;
    message?: string;
  }>;
}

export async function scheduleRestart(params: ScheduleRestartParams): Promise<ScheduleRestartResult> {
  const response = await api.post('/dispositivos/programar-reinicio', params);
  return response.data as ScheduleRestartResult;
}

export interface QueueStatus {
  device_id: string;
  pending: number;
  inflight: number;
  total: number;
  dlq: number;
  pending_sync: boolean;
  pending_reboot: boolean;
}

export interface QueueStatusPerServer {
  server: string;
  status: QueueStatus;
}

export async function getQueueStatus(deviceId: string): Promise<QueueStatusPerServer[]> {
  const response = await api.get(`/monitoreo/cola/${encodeURIComponent(deviceId)}`);
  return response.data as QueueStatusPerServer[];
}
