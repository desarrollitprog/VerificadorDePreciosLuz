import React, { useEffect, useState, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import { getVideos } from '../services/videoService';
import { Video } from '../types';


const calendarStyles = `
  /* Base */
  .fc {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
  }
  
  /* Header */
  .fc .fc-toolbar-title {
    color: #22d3ee;
    font-weight: 700;
    font-size: 1.25rem;
    letter-spacing: -0.02em;
  }
  
  /* Day headers */
  .fc .fc-col-header-cell-cushion {
    color: #64748b;
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.75rem 0;
    text-decoration: none;
  }
  
  /* Day numbers */
  .fc .fc-daygrid-day-number {
    color: #334155;
    font-weight: 500;
    font-size: 0.85rem;
    padding: 0.5rem;
    text-decoration: none;
  }
  
  .fc .fc-daygrid-day-top {
    padding: 0.25rem 0.5rem;
  }
  
  /* Days grid */
  .fc .fc-daygrid-day {
    border-color: #e2e8f0 !important;
    transition: background-color 0.2s ease;
  }
  
  .fc .fc-daygrid-day:hover {
    background-color: #f8fafc;
  }
  
  .fc .fc-day-other .fc-daygrid-day-number {
    color: #cbd5e1;
  }
  
  /* Today */
  .fc .fc-day-today {
    background-color: rgba(34, 211, 238, 0.1) !important;
  }
  
  .fc .fc-day-today .fc-daygrid-day-number {
    background: #22d3ee;
    color: white;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(34, 211, 238, 0.4);
  }
  
  /* Buttons */
  .fc .fc-button {
    background: white;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-weight: 600;
    font-size: 0.75rem;
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    text-transform: capitalize;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    transition: all 0.2s ease;
  }
  
  .fc .fc-button:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
    color: #0f172a;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
  }
  
  .fc .fc-button-active {
    background: #22d3ee !important;
    border-color: transparent !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(34, 211, 238, 0.4) !important;
  }
  
  .fc .fc-button-group {
    background: #f1f5f9;
    border-radius: 0.625rem;
    padding: 0.25rem;
    gap: 0.25rem;
  }
  
  .fc .fc-button-group .fc-button {
    border-radius: 0.375rem;
  }
  
  /* Events */
  .fc .fc-daygrid-day-events {
    padding: 0.125rem 0.25rem;
  }
  
  .fc-daygrid-event {
    border-radius: 0.375rem !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    padding: 0.2rem 0.4rem !important;
    border: none !important;
    margin-bottom: 0.25rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
  
  .fc-daygrid-event:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.12);
  }
  
  .fc-event-main {
    padding: 0 !important;
  }
  
  .fc-daygrid-event-dot {
    display: none !important;
  }
  
  .fc-more-link {
    color: #22d3ee !important;
    font-weight: 600 !important;
    font-size: 0.7rem !important;
  }
  
  /* Popover */
  .fc-popover {
    border-radius: 0.75rem !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12) !important;
  }
  
  .fc-popover-header {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    font-weight: 600 !important;
    padding: 0.75rem !important;
    border-radius: 0.75rem 0.75rem 0 0 !important;
  }

  /* Dark Mode */
  .dark .fc .fc-toolbar-title {
    color: #f1f5f9;
  }
  
  .dark .fc .fc-col-header-cell-cushion {
    color: #94a3b8;
  }
  
  .dark .fc .fc-daygrid-day-number {
    color: #cbd5e1;
  }
  
  .dark .fc .fc-daygrid-day {
    background-color: #1e293b !important;
    border-color: #334155 !important;
  }
  
  .dark .fc .fc-day-other {
    background-color: #0f172a !important;
    opacity: 0.7;
  }
  
  .dark .fc .fc-daygrid-day:hover {
    background-color: #334155 !important;
  }
  
  .dark .fc .fc-day-other .fc-daygrid-day-number {
    color: #94a3b8;
  }
  
  .dark .fc .fc-day-today {
    background-color: rgba(34, 211, 238, 0.15) !important;
  }
  
  .dark .fc .fc-button {
    background: #1e293b;
    border-color: #334155;
    color: #cbd5e1;
  }
  
  .dark .fc .fc-button:hover {
    background: #334155;
    border-color: #475569;
    color: #f1f5f9;
  }
  
  .dark .fc .fc-button-group {
    background: #0f172a;
  }
  
  .dark .fc-popover {
    background-color: #1e293b !important;
    border-color: #334155 !important;
  }
  
  .dark .fc-popover-header {
    background-color: #334155 !important;
    color: #f1f5f9 !important;
  }

  /* Mobile responsive */
  @media (max-width: 640px) {
    .fc .fc-daygrid-day-frame {
      min-height: 32px !important;
    }
    .fc .fc-daygrid-day-events {
      min-height: 16px !important;
    }
    .fc-daygrid-event {
      font-size: 0.6rem !important;
      padding: 0.1rem 0.2rem !important;
      margin-bottom: 0.1rem !important;
    }
    .fc .fc-daygrid-day-number {
      font-size: 0.6rem !important;
      padding: 0.1rem !important;
    }
    .fc .fc-toolbar-title {
      font-size: 0.85rem !important;
    }
    .fc .fc-button {
      font-size: 0.55rem !important;
      padding: 0.25rem 0.4rem !important;
    }
    .fc .fc-col-header-cell-cushion {
      font-size: 0.5rem !important;
    }
    .fc-more-link {
      font-size: 0.5rem !important;
    }
  }
`;

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end?: string;
  backgroundColor: string;
  borderColor: string;
  extendedProps: {
    tipo: string;
    url: string;
    thumbnail: string;
    estado: string;
    activo: boolean;
  };
}

export const CalendarScreen: React.FC = () => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [dayMaxEvents, setDayMaxEvents] = useState(
    typeof window !== 'undefined' && window.innerWidth < 640 ? 2 : 3
  );
  const [initialView, setInitialView] = useState<'dayGridMonth' | 'dayGridWeek'>(
    typeof window !== 'undefined' && window.innerWidth < 640 ? 'dayGridWeek' : 'dayGridMonth'
  );

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getVideos();
      
      const calendarEvents: CalendarEvent[] = [];
      
      data.forEach((video: Video) => {
        if (video.fechaInicio) {
          const estado = video.estado || 'activo';
          let backgroundColor = '#64748b';
          
          if (estado === 'activo') {
            backgroundColor = '#10b981';
          } else if (estado === 'inactivo') {
            backgroundColor = '#94a3b8';
          } else if (estado === 'vencido') {
            backgroundColor = '#f43f5e';
          } else {
            const estadoLower = String(estado).toLowerCase();
            if (estadoLower === 'programado' || estadoLower === 'borrador') {
              backgroundColor = '#8b5cf6';
            }
          }

          const event: CalendarEvent = {
            id: video.id,
            title: video.titulo || video.filename,
            start: video.fechaInicio,
            end: video.fechaFin || undefined,
            backgroundColor,
            borderColor: backgroundColor,
            extendedProps: {
              tipo: video.tipo,
              url: video.url,
              thumbnail: video.thumbnail,
              estado,
              activo: video.activo ?? true,
            },
          };
          calendarEvents.push(event);
        }
      });
      
      setEvents(calendarEvents);
    } catch (error) {
      console.error('Error fetching videos:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    const handleResize = () => {
      setDayMaxEvents(window.innerWidth < 640 ? 2 : 3);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleDatesSet = (dateInfo: any) => {
    // Recargar todos los eventos al cambiar de mes/semana
    fetchEvents();
  };

  const handleEventClick = (info: any) => {
    const event = info.event;
    setSelectedEvent({
      id: event.id,
      title: event.title,
      start: event.startStr,
      end: event.endStr,
      backgroundColor: event.backgroundColor,
      borderColor: event.borderColor,
      extendedProps: event.extendedProps,
    });
  };

  const calendarOptions = {
    plugins: [dayGridPlugin, interactionPlugin],
    initialView: initialView,
    events: events,
    eventClick: handleEventClick,
    datesSet: handleDatesSet,
    locale: 'es',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,dayGridWeek'
    },
    buttonText: {
      today: 'Hoy',
      month: 'Mes',
      week: 'Semana',
    },
    eventDisplay: 'block' as const,
    dayMaxEvents: dayMaxEvents,
    moreLinkClick: 'popover' as const,
    eventDidMount: (info: any) => {
      info.el.title = info.event.title;
    },
    height: 'auto' as const,
    contentHeight: 'auto' as const,
    aspectRatio: 1.5,
  };

  return (
    <>
      <style>{calendarStyles}</style>
      <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="w-full">
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">
            Programación
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 ml-13">
            Vista de anuncios programados por fecha de inicio
          </p>
        </div>
        
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-4 text-xs font-medium bg-white dark:bg-slate-800 px-4 py-2 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50"></span>
              <span className="text-slate-600 dark:text-slate-300">Activo</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-violet-500 shadow-sm shadow-violet-500/50"></span>
              <span className="text-slate-600 dark:text-slate-300">Programado</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm shadow-rose-500/50"></span>
              <span className="text-slate-600 dark:text-slate-300">Vencido</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400 shadow-sm"></span>
              <span className="text-slate-600 dark:text-slate-300">Inactivo</span>
            </span>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg shadow-slate-200/50 dark:shadow-none border border-slate-200 dark:border-slate-800 p-4 relative">
        <div className="absolute top-0 left-0 right-0 h-1 bg-primary dark:bg-slate-700"></div>
        {loading && (
          <div className="absolute inset-0 z-10 flex flex-col gap-3 p-6 bg-white/60 dark:bg-slate-900/60 rounded-2xl animate-pulse">
            <div className="h-4 bg-slate-200 dark:bg-[#253247] rounded w-1/3"></div>
            <div className="flex gap-2">
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-20 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
            </div>
            <div className="flex gap-2">
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
              <div className="flex-1 h-24 bg-slate-200 dark:bg-[#253247] rounded-xl"></div>
            </div>
          </div>
        )}
        <FullCalendar {...calendarOptions} />
      </div>

      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-lg text-slate-800 dark:text-white truncate pr-4">{selectedEvent.title}</h3>
              <button 
                onClick={() => setSelectedEvent(null)} 
                className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className={`px-3 py-1.5 rounded-full text-xs font-bold ${selectedEvent.extendedProps.estado === 'activo' ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : selectedEvent.extendedProps.estado === 'vencido' ? 'bg-rose-100 text-rose-700 border border-rose-200' : selectedEvent.extendedProps.estado === 'inactivo' ? 'bg-slate-100 text-slate-600 border border-slate-200' : 'bg-violet-100 text-violet-700 border border-violet-200'}`}>
                  {selectedEvent.extendedProps.estado}
                </div>
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                  {selectedEvent.extendedProps.tipo}
                </span>
              </div>
              
              <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                <span className="font-semibold">Inicio:</span> {new Date(selectedEvent.start).toLocaleString('es-VE', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                {selectedEvent.end && (
                  <span> • <span className="font-semibold">Fin:</span> {new Date(selectedEvent.end).toLocaleString('es-VE', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                )}
              </p>

              <div className="bg-slate-100 dark:bg-slate-800/50 rounded-xl p-3">
                {selectedEvent.extendedProps.tipo === 'image' ? (
                  <img 
                    src={selectedEvent.extendedProps.thumbnail || selectedEvent.extendedProps.url} 
                    alt={selectedEvent.title} 
                    className="max-h-52 mx-auto rounded-lg shadow-md"
                  />
                ) : (
                  <video 
                    src={selectedEvent.extendedProps.url} 
                    controls 
                    className="max-h-52 mx-auto rounded-lg shadow-md"
                  />
                )}
              </div>
            </div>
          </div>
        </div>
        )}
    </div>
    </>
  );
};