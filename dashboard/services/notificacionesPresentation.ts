import { Notificacion } from './notificacionesService';

export type NotificationSeverity = 'error' | 'warning' | 'info' | 'success';

export interface NotificationViewModel {
  title: string;
  message: string;
  detail?: string;
  severity: NotificationSeverity;
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen - 1)}…`;
}

function humanizeTipo(tipo: string): string {
  return (tipo || 'NOTIFICACION')
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function toNotificationViewModel(notificacion: Notificacion): NotificationViewModel {
  const tipo = String(notificacion.tipo || '').toUpperCase();
  const descripcion = (notificacion.descripcion || '').trim();

  switch (tipo) {
    case 'SYNC_FAILED':
      return {
        title: 'Sincronización fallida',
        message: 'Uno o más dispositivos no confirmaron la sincronización.',
        detail: descripcion || undefined,
        severity: 'error',
      };
    case 'PLAYBACK_FAILED':
      {
        const text = String(descripcion || '').trim();
        const deviceMatch = text.match(/^(.*?)\s+no pudo reproducir\s+/i);
        const mediaMatch = text.match(/no pudo reproducir\s+['\"]([^'\"]+)['\"]/i);
        const reasonMatch = text.match(/:\s*(.+)$/);
        const deviceName = deviceMatch?.[1]?.trim();
        const mediaName = mediaMatch?.[1]?.trim();
        const reason = reasonMatch?.[1]?.trim();

        const message = mediaName
          ? `No se pudo reproducir ${mediaName}${deviceName ? ` en ${deviceName}` : ''}`
          : 'Se detectó un fallo de reproducción en una tablet';

        const detailParts = [reason, descripcion].filter(Boolean) as string[];

        return {
          severity: 'error',
          title: 'Error de reproducción',
          message,
          detail: detailParts[0],
        };
      }
    case 'SINCRONIZACION_FORZADA':
      return {
        title: 'Sincronización ejecutada',
        message: 'Se ejecutó una sincronización forzada desde el panel.',
        detail: descripcion || undefined,
        severity: 'info',
      };
    case 'RENOMBRAR_DISPOSITIVO':
      return {
        title: 'Dispositivo actualizado',
        message: 'Se actualizó el nombre del dispositivo.',
        detail: descripcion || undefined,
        severity: 'success',
      };
    case 'CAMBIO_ESTADO_SERVIDOR':
      return {
        title: 'Cambio de estado del servidor',
        message: 'Un servidor cambió su estado.',
        detail: descripcion || undefined,
        severity: 'warning',
      };
    case 'ALERTA_SERVIDOR':
      return {
        title: 'Alerta de servidor',
        message: 'Se detectó una condición de alerta en un servidor.',
        detail: descripcion || undefined,
        severity: 'warning',
      };
    default:
      return {
        title: humanizeTipo(tipo),
        message: truncate(descripcion || 'Hay una notificación nueva.', 110),
        detail: descripcion || undefined,
        severity: 'info',
      };
  }
}
