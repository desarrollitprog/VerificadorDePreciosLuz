import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, AlertTriangle, ChevronRight, Check, Circle } from 'lucide-react';
import { useNotification } from './useNotification';
import { deleteReadNotificaciones, fetchNotificaciones, markNotificacionesRead, markNotificacionRead, Notificacion } from '../services/notificacionesService';
import { toNotificationViewModel } from '../services/notificacionesPresentation';
import type { NotificationType } from './NotificationContext';

function formatCaracasTime(dateString: string | Date): Date {
  const date = typeof dateString === 'string' ? new Date(dateString) : new Date(dateString.getTime());
  return date;
}

function getRelativeTimeLabel(dateIso: string): string {
  const now = Date.now();
  const then = new Date(dateIso).getTime();
  const diffSeconds = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSeconds < 60) return 'hace segundos';
  const minutes = Math.floor(diffSeconds / 60);
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} d`;
}

function getBadgeBySeverity(severity: 'error' | 'warning' | 'info' | 'success') {
  if (severity === 'error') {
    return { label: 'Error', classes: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' };
  }
  if (severity === 'warning') {
    return { label: 'Alerta', classes: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' };
  }
  if (severity === 'success') {
    return { label: 'OK', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' };
  }
  return { label: 'Info', classes: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' };
}

function getBadgeByAction(actionBadge?: 'carga' | 'eliminacion') {
  if (actionBadge === 'carga') {
    return { label: 'Carga', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' };
  }
  if (actionBadge === 'eliminacion') {
    return { label: 'Eliminación', classes: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' };
  }
  return undefined;
}

export const GeneralNotifications: React.FC = () => {
  const [open, setOpen] = useState(false);
  const showNotification = useNotification();
  const navigate = useNavigate();
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const shownErrorNotificationIdsRef = useRef<Set<number>>(new Set());
  const [search, setSearch] = useState("");

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  const loadNotifications = async (markAsRead: boolean) => {
    if (markAsRead) setLoading(true);
    try {
      const res = await fetchNotificaciones(10, 0, false);
      const seenErrorKeys = new Set<string>();
      const normalized = (res.notificaciones || []).filter((n) => {
        const tipo = String(n.tipo || '').toUpperCase();
        if (tipo !== 'SYNC_FAILED' && tipo !== 'PLAYBACK_FAILED' && tipo !== 'SINCRONIZACION_SELECTIVA') return true;
        const key = `${n.tipo}::${(n.descripcion || '').trim()}`;
        if (seenErrorKeys.has(key)) return false;
        seenErrorKeys.add(key);
        return true;
      });

      setNotificaciones(normalized);
      setUnreadCount(Number(res.unread_count || 0));

      normalized
        .filter((n) => {
          const tipo = String(n.tipo || '').toUpperCase();
          return tipo === 'SYNC_FAILED' || tipo === 'PLAYBACK_FAILED' || tipo === 'PUBLICIDAD_VENCIDA' || tipo === 'SINCRONIZACION_COMPLETADA';
        })
        .filter((n) => !shownErrorNotificationIdsRef.current.has(n.id))
        .forEach((n) => {
          shownErrorNotificationIdsRef.current.add(n.id);
          const tipo = String(n.tipo || '');
          let prefix = '';
          let tipo_notif: NotificationType = 'info';
          if (tipo === 'PLAYBACK_FAILED') {
            prefix = 'Error de reproducción';
            tipo_notif = 'error';
          } else if (tipo === 'PUBLICIDAD_VENCIDA') {
            prefix = 'Publicidad vencida';
            tipo_notif = 'warning';
          } else if (tipo === 'SINCRONIZACION_COMPLETADA') {
            prefix = 'Sincronización completada';
            tipo_notif = 'success';
          } else {
            prefix = 'Fallo de sincronización';
            tipo_notif = 'error';
          }
            showNotification(`${prefix}: ${n.descripcion}`, tipo_notif, 7000);
        });

      if (markAsRead && (res.unread_count || 0) > 0) {
        markNotificacionesRead()
          .then(() => {
            setNotificaciones((prev) => prev.map((n) => ({ ...n, leida: true })));
            setUnreadCount(0);
          })
          .catch(() => {});
      }

    } finally {
      if (markAsRead) setLoading(false);
    }
  };

  const handleClearNotifications = async () => {
    setLoading(true);
    try {
      const result = await deleteReadNotificaciones();
      await loadNotifications(false);
      showNotification(`Se eliminaron ${result.deleted} notificaciones leídas`, 'success', 3000);
    } catch {
      showNotification('No se pudieron limpiar las notificaciones', 'error', 4000);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications(false);
    const intervalId = window.setInterval(() => {
      loadNotifications(false);
    }, 10000);

    return () => window.clearInterval(intervalId);
  }, [showNotification]);

  useEffect(() => {
    if (open) {
      loadNotifications(true);
    }
  }, [open, showNotification]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [open]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        className="relative p-2 text-slate-400 hover:text-primary transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full"
        onClick={() => setOpen((v) => !v)}
        aria-label="Ver notificaciones generales"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 border-2 border-white dark:border-[#111a22]"></span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-[#111a22] border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg z-50">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center">
            <div className="font-semibold text-slate-900 dark:text-white">Notificaciones Generales</div>
          </div>
          <div className="px-4 py-2 border-b border-slate-200 dark:border-slate-800">
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar notificaciones..."
              className="w-full px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 text-sm bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="max-h-72 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-slate-500">Cargando...</div>
            ) : notificaciones.length === 0 ? (
              <div className="p-4 text-center text-slate-500">No hay notificaciones</div>
            ) : (
              notificaciones
                .filter(n => {
                  const view = toNotificationViewModel(n);
                  const nombreUsuario = n.nombre_usuario || 'Desconocido';
                  const searchLower = search.toLowerCase();
                  return (
                    view.title.toLowerCase().includes(searchLower) ||
                    view.message.toLowerCase().includes(searchLower) ||
                    (view.detail && view.detail.toLowerCase().includes(searchLower)) ||
                    nombreUsuario.toLowerCase().includes(searchLower)
                  );
                })
                .map((n) => {
                  const view = toNotificationViewModel(n);
                  const isError = view.severity === 'error';
                  const badge = getBadgeBySeverity(view.severity);
                  const actionBadge = getBadgeByAction(view.actionBadge);
                  const utcDate = new Date(n.fecha_creacion.endsWith('Z') ? n.fecha_creacion : n.fecha_creacion + 'Z');
                  const exactTime = utcDate.toLocaleString('es-VE', { timeZone: 'America/Caracas' });
                  const relativeTime = getRelativeTimeLabel(n.fecha_creacion);
                  const nombreUsuario = n.nombre_usuario || 'Desconocido';
                  const isLeida = n.leida === true;
                  
                  const handleMarkAsRead = async (e: React.MouseEvent) => {
                    e.stopPropagation();
                    if (!isLeida) {
                      try {
                        await markNotificacionRead(n.id);
                        setNotificaciones(prev => prev.map(notif => 
                          notif.id === n.id ? { ...notif, leida: true } : notif
                        ));
                        setUnreadCount(prev => Math.max(0, prev - 1));
                      } catch (err) {
                      }
                    }
                  };
                  
                  return (
                    <div
                      key={n.id}
                      className={`px-4 py-3 border-b last:border-b-0 border-slate-100 dark:border-slate-800 ${isLeida ? 'bg-slate-50 dark:bg-slate-900/50' : 'bg-white dark:bg-[#111a22]'} ${isError ? 'bg-red-50 dark:bg-red-900/30' : ''}`}
                    >
                      <div className="flex items-center gap-2 mb-1 justify-between">
                        <div className="text-xs text-slate-500" title={exactTime}>{relativeTime} · {exactTime}</div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={handleMarkAsRead}
                            title={isLeida ? 'Marcar como no leída' : 'Marcar como leída'}
                            className={`p-1 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors ${isLeida ? 'text-green-500' : 'text-blue-400'}`}
                          >
                            {isLeida ? <Check size={14} /> : <Circle size={14} />}
                          </button>
                          {actionBadge && (
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${actionBadge.classes}`}>{actionBadge.label}</span>
                          )}
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${badge.classes}`}>{badge.label}</span>
                          {isError && (
                            <span title={view.title} className="inline-flex">
                              <AlertTriangle size={16} className="text-red-500" />
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-xs text-primary font-semibold mb-1">Usuario: {nombreUsuario}</div>
                      <div className={`text-sm font-medium ${isError ? 'text-red-700 dark:text-red-400' : isLeida ? 'text-slate-600 dark:text-slate-400' : 'text-slate-900 dark:text-white'}`}>{view.title}</div>
                      <div className={`text-sm ${isError ? 'text-red-800 dark:text-red-200' : isLeida ? 'text-slate-500 dark:text-slate-500' : 'text-slate-700 dark:text-slate-300'}`}>{view.message}</div>
                      {view.detail && view.detail !== view.message && (
                        <div className="text-xs text-slate-500 mt-1">Detalle técnico: {view.detail}</div>
                      )}
                    </div>
                  );
                })
            )}
          </div>
          <div className="p-3 border-t border-slate-200 dark:border-slate-800">
            <button
              onClick={() => {
                setOpen(false);
                handleNavigate('/auditoria');
              }}
              className="w-full flex items-center justify-center gap-2 py-2 text-sm font-medium text-primary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              Ver historial completo
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
