export enum VideoStatus {
  Live = 'Live',
  Processing = 'Processing',
  Error = 'Error',
  Queued = 'Queued'
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
}

export type Screen = 'login' | 'dashboard' | 'list' | 'servers' | 'users';
