import api from './axiosInstance';

export interface ServidorResumen {
  id: number;
  nombre: string;
  ip: string;
  online: boolean;
  porcentaje_uso: number;
  almacenamiento_total: number;
  almacenamiento_usado: number;
  dispositivos_total: number;
  dispositivos_online: number;
}

export interface BannersPorServidor {
  servidor_id: number;
  nombre: string;
  cantidad: number;
}

export interface HistorialSubida {
  fecha: string;
  cantidad: number;
}

export interface DispositivosResumen {
  total: number;
  online: number;
  offline: number;
  verificadores?: number;
  televisores?: number;
}

export interface ResumenData {
  servidores: { total: number; online: number; offline: number };
  dispositivos: DispositivosResumen;
  banners: { total: number; programados: number; inactivos: number; vencidos: number; reproduciendose: number };
  usuarios: { total: number; activos: number };
  servidores_detalle: ServidorResumen[];
  banners_por_servidor: BannersPorServidor[];
  historial_subidas: HistorialSubida[];
}

export interface BannerMetrica {
  titulo: string;
  inicios: number;
  validas_50: number;
  vcr: number;
}

export interface TendenciaDiaria {
  fecha: string;
  tv_estimadas: number;
  ver_validas: number;
}

export interface ResumenReproducciones {
  total_eventos: number;
  inicios: number;
  validas_50: number;
  ver_total: number;
  tv_total: number;
  banners: BannerMetrica[];
}

export interface ReproduccionesResponse {
  success: boolean;
  fecha: string;
  resumen: ResumenReproducciones;
  tendencia_14d: TendenciaDiaria[];
}

export interface BannerPorSede {
  banner_id: number;
  titulo: string;
  reproducciones: number;
  validas_50: number;
  vcr: number;
}

export interface SedeMetrica {
  servidor_id: number;
  nombre: string;
  total_reproducciones: number;
  total_validas_50: number;
  vcr_general: number;
  banners: BannerPorSede[];
}

export interface ReproduccionesPorSedeResponse {
  success: boolean;
  fecha: string;
  sedes: SedeMetrica[];
}

export async function fetchReproduccionesPorSede(fecha?: string): Promise<ReproduccionesPorSedeResponse> {
  const params: any = {};
  if (fecha) params.fecha = fecha;
  const response = await api.get('/reproducciones/por-sede', { params });
  return response.data as ReproduccionesPorSedeResponse;
}

export async function fetchReproduccionesResumenDiario(fecha?: string): Promise<ReproduccionesResponse> {
  const params: any = {};
  if (fecha) params.fecha = fecha;
  const response = await api.get('/reproducciones/resumen-diario', { params });
  return response.data as ReproduccionesResponse;
}

export async function fetchResumen(): Promise<ResumenData> {
  const response = await api.get('/resumen');
  const d = response.data;
  return {
    servidores: d.servidores,
    dispositivos: d.dispositivos,
    banners: d.banners,
    usuarios: d.usuarios,
    servidores_detalle: (d.servidores_detalle || []).map((s: any) => ({
      id: Number(s.id),
      nombre: String(s.nombre),
      ip: String(s.ip),
      online: !!s.online,
      porcentaje_uso: Number(s.porcentaje_uso || 0),
      almacenamiento_total: Number(s.almacenamiento_total || 0),
      almacenamiento_usado: Number(s.almacenamiento_usado || 0),
      dispositivos_total: Number(s.dispositivos_total || 0),
      dispositivos_online: Number(s.dispositivos_online || 0),
    })),
    banners_por_servidor: (d.banners_por_servidor || []).map((b: any) => ({
      servidor_id: Number(b.servidor_id),
      nombre: String(b.nombre),
      cantidad: Number(b.cantidad),
    })),
    historial_subidas: (d.historial_subidas || []).map((h: any) => ({
      fecha: String(h.fecha),
      cantidad: Number(h.cantidad),
    })),
  };
}
