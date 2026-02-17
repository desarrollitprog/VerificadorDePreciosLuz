export enum VideoStatus {
  Live = 'Live',
  Processing = 'Processing',
  Error = 'Error',
  Queued = 'Queued'
}

export interface Video {
  id: string;
  filename: string;
  thumbnail: string;
  duration: string;
  date: string;
  size: string;
  status: VideoStatus;
  views?: number;
}

export type Screen = 'login' | 'dashboard' | 'list';
