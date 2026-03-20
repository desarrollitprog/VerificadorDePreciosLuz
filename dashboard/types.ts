export enum VideoStatus {
  Live = 'Live',
  Processing = 'Processing',
  Error = 'Error',
  Queued = 'Queued'
}

export interface Asignacion {
  servidor_id: number;
  servidor_nombre: string;
  dispositivo_id: number;
  dispositivo_nombre: string | null;
  dispositivo_codigo: string | null;
}

export interface Video {
  id: string;
  filename: string;
  url: string;
  thumbnail: string;
  tipo: string;
  titulo: string;
  duration: string;
  date: string;
  size: string;
  status: VideoStatus;
  activo?: boolean;
  fechaInicio?: string | null;
  fechaFin?: string | null;
  prioridad?: number;
  views?: number;
  asignacion_todos?: boolean;
  asignaciones?: Asignacion[];
  dispositivos_count?: number;
  estado?: 'activo' | 'inactivo' | 'borrador' | 'vencido';
}

export interface Servidor {
  id: number;
  nombre: string;
  ip: string;
  api_url: string;
  online: boolean;
  dispositivos: Dispositivo[];
}

export interface Dispositivo {
  id: number;
  codigo_kiosko: string;
  nombre_amigable: string | null;
  online: boolean;
}

export type Screen = 'login' | 'dashboard' | 'list' | 'servers' | 'users';
