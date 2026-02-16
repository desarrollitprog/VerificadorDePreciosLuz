export interface Device {
  id: string;
  name: string;
  location: string;
  ip: string;
  status: 'online' | 'offline' | 'warning';
  battery: number;
  wifiSignal: number; // dBm
  currentContent: string;
  lastSync: string;
  thumbnail: string;
}

export interface MediaItem {
  id: string;
  title: string;
  duration: string;
  status: 'live' | 'scheduled' | 'expired';
  resolution: string;
  dateRange: string;
  thumbnail: string;
  type: 'video' | 'image';
  fileSize?: string;
}

export interface PlaylistItem {
  id: string;
  mediaId: string;
  order: number;
}

export enum AnalyticsPeriod {
  Last24h = '24h',
  Last7d = '7d',
  Last30d = '30d'
}