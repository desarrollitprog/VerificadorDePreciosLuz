import React, { useEffect, useState, useRef } from 'react';
import { Bell } from 'lucide-react';
import { fetchNotificaciones, Notificacion } from '../services/notificacionesService';

interface GeneralNotificationsProps {}

export const GeneralNotifications: React.FC<GeneralNotificationsProps> = () => {
  const [open, setOpen] = useState(false);
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setLoading(true);
      fetchNotificaciones(10, 0)
        .then((res) => setNotificaciones(res.notificaciones))
        .finally(() => setLoading(false));
    }
  }, [open]);

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
        {notificaciones.length > 0 && (
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
              notificaciones.map((n) => (
                <div key={n.id} className="px-4 py-3 border-b last:border-b-0 border-slate-100 dark:border-slate-800">
                  <div className="text-xs text-slate-500 mb-1">{new Date(n.fecha_creacion).toLocaleString()}</div>
                  <div className="text-sm font-medium text-slate-900 dark:text-white">{n.tipo}</div>
                  <div className="text-sm text-slate-700 dark:text-slate-300">{n.descripcion}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
