import React, { useEffect, useState, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import { getVideosWithDateFilter } from '../services/videoService';
import { Video } from '../types';

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
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  const fetchEvents = useCallback(async (start: Date, end: Date) => {
    setLoading(true);
    try {
      const data = await getVideosWithDateFilter(
        start.toISOString(),
        end.toISOString(),
        true
      );
      
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
          } else if (estado === 'programado' || estado === 'borrador') {
            backgroundColor = '#3b82f6';
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
    const now = new Date();
    const threeMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 3, 1);
    const threeMonthsLater = new Date(now.getFullYear(), now.getMonth() + 4, 0);
    
    setDateRange({
      start: threeMonthsAgo.toISOString(),
      end: threeMonthsLater.toISOString()
    });
    
    fetchEvents(threeMonthsAgo, threeMonthsLater);
  }, [fetchEvents]);

  const handleDatesSet = (dateInfo: any) => {
    const start = dateInfo.view.currentStart;
    const end = dateInfo.view.currentEnd;
    
    const newStart = new Date(start);
    const newEnd = new Date(end);
    
    setDateRange({
      start: newStart.toISOString(),
      end: newEnd.toISOString()
    });
    
    fetchEvents(newStart, newEnd);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-2 border-primary/30 border-t-primary animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800 dark:text-white flex items-center gap-2">
            <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Programación de Anuncios
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Vista de anuncios programados por fecha de inicio
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-emerald-500"></span>
              Activo
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-blue-500"></span>
              Programado
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-rose-500"></span>
              Vencido
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-slate-400"></span>
              Inactivo
            </span>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-800 p-4">
        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          events={events}
          eventClick={handleEventClick}
          datesSet={handleDatesSet}
          locale="es"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,dayGridWeek'
          }}
          buttonText={{
            today: 'Hoy',
            month: 'Mes',
            week: 'Semana',
          }}
          eventDisplay="block"
          dayMaxEvents={3}
          moreLinkClick="popover"
          height="auto"
          contentHeight="auto"
          aspectRatio={1.5}
        />
      </div>

      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-[#1c2936] rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
              <h3 className="font-semibold text-slate-800 dark:text-white truncate pr-4">{selectedEvent.title}</h3>
              <button 
                onClick={() => setSelectedEvent(null)} 
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="p-4">
              <div className="flex items-center gap-3 mb-4">
                <div className={`px-2 py-1 rounded-full text-xs font-medium text-white ${selectedEvent.extendedProps.estado === 'activo' ? 'bg-emerald-500' : selectedEvent.extendedProps.estado === 'vencido' ? 'bg-rose-500' : selectedEvent.extendedProps.estado === 'inactivo' ? 'bg-slate-400' : 'bg-blue-500'}`}>
                  {selectedEvent.extendedProps.estado}
                </div>
                <span className="text-xs text-slate-500">
                  {selectedEvent.extendedProps.tipo}
                </span>
              </div>
              
              <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                <strong>Inicio:</strong> {new Date(selectedEvent.start).toLocaleDateString('es-VE', { day: '2-digit', month: 'long', year: 'numeric' })}
                {selectedEvent.end && (
                  <span> • <strong>Fin:</strong> {new Date(selectedEvent.end).toLocaleDateString('es-VE', { day: '2-digit', month: 'long', year: 'numeric' })}</span>
                )}
              </p>

              <div className="bg-slate-100 dark:bg-slate-800 rounded-lg p-2">
                {selectedEvent.extendedProps.tipo === 'image' ? (
                  <img 
                    src={selectedEvent.extendedProps.thumbnail || selectedEvent.extendedProps.url} 
                    alt={selectedEvent.title} 
                    className="max-h-48 mx-auto rounded"
                  />
                ) : (
                  <video 
                    src={selectedEvent.extendedProps.url} 
                    controls 
                    className="max-h-48 mx-auto rounded"
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};