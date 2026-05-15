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

export interface ResumenData {
  servidores: { total: number; online: number; offline: number };
  dispositivos: { total: number; online: number; offline: number };
  banners: { total: number; activos: number; inactivos: number; vencidos: number };
  usuarios: { total: number; activos: number };
  servidores_detalle: ServidorResumen[];
  banners_por_servidor: BannersPorServidor[];
  historial_subidas: HistorialSubida[];
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
