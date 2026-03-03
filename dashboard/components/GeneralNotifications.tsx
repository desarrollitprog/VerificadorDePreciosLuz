import React, { useEffect, useState, useRef } from 'react';
import { Bell, AlertTriangle } from 'lucide-react';
import { useNotification } from './useNotification';
import { fetchNotificaciones, markNotificacionesRead, Notificacion } from '../services/notificacionesService';
import { toNotificationViewModel } from '../services/notificacionesPresentation';

interface GeneralNotificationsProps {}

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

export const GeneralNotifications: React.FC<GeneralNotificationsProps> = () => {
  const [open, setOpen] = useState(false);
  const showNotification = useNotification();
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const shownSyncFailedIdsRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (open) {
      setLoading(true);
      fetchNotificaciones(10, 0)
        .then((res) => {
          const seenSyncFailedKeys = new Set<string>();
          const normalized = (res.notificaciones || []).filter((n) => {
            if (n.tipo !== 'SYNC_FAILED') return true;
            const key = `${n.tipo}::${(n.descripcion || '').trim()}`;
            if (seenSyncFailedKeys.has(key)) return false;
            seenSyncFailedKeys.add(key);
            return true;
          });

          setNotificaciones(normalized);
          setUnreadCount(Number(res.unread_count || 0));
          // Mostrar toast para SYNC_FAILED
          normalized
            .filter((n) => n.tipo === 'SYNC_FAILED')
            .filter((n) => !shownSyncFailedIdsRef.current.has(n.id))
            .forEach((n) => {
              shownSyncFailedIdsRef.current.add(n.id);
              showNotification(
                `Fallo de sincronización: ${n.descripcion}`,
                'error',
                7000
              );
            });

          if ((res.unread_count || 0) > 0) {
            markNotificacionesRead()
              .then(() => {
                setNotificaciones((prev) => prev.map((n) => ({ ...n, leida: true })));
                setUnreadCount(0);
              })
              .catch(() => {
                // no-op: mantener estado local actual si falla marcado
              });
          }
        })
        .finally(() => setLoading(false));
    }
  }, [open, showNotification]);

  // Cerrar dropdown al hacer click fuera
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
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-900 dark:text-white">Notificaciones Generales</div>
          <div className="max-h-72 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-slate-500">Cargando...</div>
            ) : notificaciones.length === 0 ? (
              <div className="p-4 text-center text-slate-500">No hay notificaciones</div>
            ) : (
              notificaciones.map((n) => {
                const view = toNotificationViewModel(n);
                const isError = view.severity === 'error';
                const badge = getBadgeBySeverity(view.severity);
                const exactTime = new Date(n.fecha_creacion).toLocaleString();
                const relativeTime = getRelativeTimeLabel(n.fecha_creacion);
                return (
                  <div
                    key={n.id}
                    className={`px-4 py-3 border-b last:border-b-0 border-slate-100 dark:border-slate-800 ${isError ? 'bg-red-50 dark:bg-red-900/30' : ''}`}
                  >
                    <div className="flex items-center gap-2 mb-1 justify-between">
                      <div className="text-xs text-slate-500" title={exactTime}>{relativeTime} · {exactTime}</div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${badge.classes}`}>{badge.label}</span>
                      {isError && (
                        <span title={view.title} className="inline-flex">
                          <AlertTriangle size={16} className="text-red-500" />
                        </span>
                      )}
                    </div>
                    <div className={`text-sm font-medium ${isError ? 'text-red-700 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{view.title}</div>
                    <div className={`text-sm ${isError ? 'text-red-800 dark:text-red-200' : 'text-slate-700 dark:text-slate-300'}`}>{view.message}</div>
                    {view.detail && view.detail !== view.message && (
                      <div className="text-xs text-slate-500 mt-1">Detalle técnico: {view.detail}</div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
