import { Notificacion } from './notificacionesService';

export type NotificationSeverity = 'error' | 'warning' | 'info' | 'success';

export interface NotificationViewModel {
  title: string;
  message: string;
  severity: NotificationSeverity;
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
        message: descripcion || 'Uno o más dispositivos no confirmaron la sincronización.',
        severity: 'error',
      };
    case 'SINCRONIZACION_FORZADA':
      return {
        title: 'Sincronización ejecutada',
        message: descripcion || 'Se ejecutó una sincronización forzada desde el panel.',
        severity: 'info',
      };
    case 'RENOMBRAR_DISPOSITIVO':
      return {
        title: 'Dispositivo actualizado',
        message: descripcion || 'Se actualizó el nombre del dispositivo.',
        severity: 'success',
      };
    case 'CAMBIO_ESTADO_SERVIDOR':
      return {
        title: 'Cambio de estado del servidor',
        message: descripcion || 'Un servidor cambió su estado.',
        severity: 'warning',
      };
    case 'ALERTA_SERVIDOR':
      return {
        title: 'Alerta de servidor',
        message: descripcion || 'Se detectó una condición de alerta en un servidor.',
        severity: 'warning',
      };
    default:
      return {
        title: humanizeTipo(tipo),
        message: descripcion || 'Hay una notificación nueva.',
        severity: 'info',
      };
  }
}
