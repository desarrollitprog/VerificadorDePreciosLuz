import { Notificacion } from './notificacionesService';

export type NotificationSeverity = 'error' | 'warning' | 'info' | 'success';
export type NotificationActionBadge = 'carga' | 'eliminacion';

export interface NotificationViewModel {
  title: string;
  message: string;
  detail?: string;
  severity: NotificationSeverity;
  actionBadge?: NotificationActionBadge;
}

function firstNonEmpty(...values: Array<string | undefined>): string | undefined {
  return values.map((value) => value?.trim()).find(Boolean);
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
    case 'SINCRONIZACION_FORZADA': {
      // Elimina la línea de "Fallos" si ya está resumida en éxito/fallo
      let resumen = descripcion;
      if (descripcion.includes('Fallos:')) {
        resumen = descripcion.replace(/\.\s*Fallos:.*$/, '');
      }
      return {
        title: 'Sincronización ejecutada',
        message: 'Se ejecutó una sincronización forzada desde el panel.',
        detail: resumen !== '' ? resumen : undefined,
        severity: 'info',
      };
    }
    case 'RENOMBRAR_DISPOSITIVO':
      return {
        title: 'Dispositivo actualizado',
        message: 'Se actualizó el nombre del dispositivo.',
        detail: descripcion || undefined,
        severity: 'success',
      };
    case 'SUBIDA_MULTIMEDIA':
    case 'SUBIDA MULTIMEDIA':
      {
        const fileMatch = descripcion.match(/Archivo\s+subido\s*[:=]\s*([^,;]+)/i);
        const fallbackFileMatch = descripcion.match(/archivo\s+([^,;]+)\s+subid[oa]/i);
        const idMatch = descripcion.match(/IdPublicidad\s*[:=]\s*(\d+)/i);
        const fileName = firstNonEmpty(fileMatch?.[1], fallbackFileMatch?.[1]);
        const pubId = idMatch?.[1];

        return {
          title: 'Multimedia subida',
          message: fileName ? `Se subió ${fileName}` : (descripcion || 'Se subió un archivo multimedia.'),
          detail: pubId ? `IdPublicidad: ${pubId}` : (descripcion || undefined),
          severity: 'success',
          actionBadge: 'carga',
        };
      }
    case 'BORRADO_MULTIMEDIA':
    case 'BORRADO MULTIMEDIA':
      {
        const idMatch = descripcion.match(/IdPublicidad\s*[:=]\s*(\d+)/i);
        const titleMatch = descripcion.match(/T[ií]tulo\s*[:=]\s*([^,;]+)/i);
        const fallbackTitleMatch = descripcion.match(/se\s+elimin[oó]\s+([^,;]+)/i);
        const pubId = idMatch?.[1];
        const title = firstNonEmpty(titleMatch?.[1], fallbackTitleMatch?.[1]);

        return {
          title: 'Multimedia eliminada',
          message: title ? `Se eliminó ${title}` : (descripcion || 'Se eliminó un archivo multimedia.'),
          detail: pubId ? `IdPublicidad: ${pubId}` : (descripcion || undefined),
          severity: 'warning',
          actionBadge: 'eliminacion',
        };
      }
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
      // Para otras notificaciones, solo mostrar detalle si la descripción es distinta al mensaje y no está vacía
      const msg = truncate(descripcion || 'Hay una notificación nueva.', 110);
      let detail: string | undefined = undefined;
      if (descripcion && descripcion !== msg) {
        detail = descripcion;
      }
      return {
        title: humanizeTipo(tipo),
        message: msg,
        detail,
        severity: 'info',
      };
  }
}
