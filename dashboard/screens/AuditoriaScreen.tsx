import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Calendar, Server, Monitor, Clock, X, ChevronDown, ChevronUp, User, RotateCcw, Check, Circle, Download, XCircle } from 'lucide-react';
import { getAuditoria, getAuditoriaTipos, markNotificacionRead, exportAuditoriaPDF, AuditoriaItem, AuditoriaFiltros } from '../services/auditoriaService';
import { getServersStatus } from '../services/monitoreoService';
import { useNotification } from '../components/useNotification';
import { TableSkeleton } from '../components/TableSkeleton';
import { Spinner } from '../components/Spinner';

const PAGE_SIZE = 25;

function ExpandableDescription({ text, maxLength = 80 }: { text: string; maxLength?: number }) {
  const [expanded, setExpanded] = useState(false);
  
  if (text.length <= maxLength) {
    return <span>{text}</span>;
  }
  
  return (
    <div>
      <span>{expanded ? text : text.substring(0, maxLength) + '...'}</span>
      <button
        onClick={() => setExpanded(!expanded)}
        className="ml-1 text-primary hover:underline text-xs"
      >
        {expanded ? 'Ver menos' : 'Ver más'}
      </button>
    </div>
  );
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '-';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
  
  return parts.join(' ');
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString('es-VE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const TIPO_LABELS: Record<string, string> = {
  'CONEXION_DISPOSITIVO': 'Conexión',
  'DESCONEXION_DISPOSITIVO': 'Desconexión',
  'SUBIDA_MULTIMEDIA': 'Subida Multimedia',
  'SUBIDA_MULTIMEDIA_BATCH': 'Subida Multimedia (Lote)',
  'BORRADO_MULTIMEDIA': 'Borrado Multimedia',
  'CAMBIO_ESTADO_MULTIMEDIA': 'Cambio Estado Multimedia',
  'EDICION_VIGENCIA_MULTIMEDIA': 'Edición Vigencia',
  'ASIGNAR_PUBLICIDAD': 'Asignar Publicidad',
  'ERROR_REPLICACION_ASIGNACION': 'Error Replicación',
  'SINCRONIZAR_PUBLICIDADES': 'Sincronizar Publicidades',
  'SINCRONIZACION_FORZADA': 'Sincronización Forzada',
  'SINCRONIZACION_SELECTIVA': 'Sincronización Selectiva',
  'SYNC_FAILED': 'Sincronización Fallida',
  'PLAYBACK_FAILED': 'Reproducción Fallida',
  'COMANDO_ENCOLADO': 'Comando Encolado',
  'SINCRONIZACION_COMPLETADA': 'Sincronización Completada',
  'BANNER_INICIADO': 'Banner Iniciado',
  'BANNER_FINALIZADO': 'Banner Finalizado',
  'CAMBIO_ESTADO_SERVIDOR': 'Cambio Estado Servidor',
  'ALERTA_SERVIDOR': 'Alerta Servidor',
  'RENOMBRAR_SERVIDOR': 'Renombrar Servidor',
  'ELIMINAR_SERVIDOR': 'Eliminar Servidor',
  'RENOMBRAR_DISPOSITIVO': 'Renombrar Dispositivo',
  'ELIMINAR_DISPOSITIVO': 'Eliminar Dispositivo',
  'REINICIAR_DISPOSITIVO': 'Reiniciar Dispositivo',
  'REINICIAR_DISPOSITIVO_FALLO': 'Reinicio Fallido',
  'PURGA_DISPOSITIVO': 'Purga Dispositivo',
  'PURGA_DISPOSITIVO_FALLO': 'Purga Fallida',
  'PROGRAMAR_REINICIO_MASIVO': 'Reinicio Masivo',
  'CREAR_USUARIO': 'Crear Usuario',
  'ACTUALIZAR_USUARIO': 'Actualizar Usuario',
  'BORRAR_USUARIO': 'Borrar Usuario',
  'PUBLICIDAD_VENCIDA': 'Publicidad Vencida',
};

function getTipoLabel(tipo: string): string {
  return TIPO_LABELS[tipo] || tipo.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getTypeBadge(tipo: string) {
  const tipoUpper = tipo.toUpperCase();
  
  if (tipoUpper.includes('DESCONEXION')) {
    return { label: 'Desconexión', classes: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' };
  }
  if (tipoUpper.includes('CONEXION')) {
    return { label: 'Conexión', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' };
  }
  if (tipoUpper.includes('SYNC') || tipoUpper.includes('SINCRONIZACION')) {
    return { label: 'Sincronización', classes: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' };
  }
  if (tipoUpper.includes('FAILED') || tipoUpper.includes('ERROR')) {
    return { label: 'Error', classes: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' };
  }
  if (tipoUpper.includes('RENOMBRAR') || tipoUpper.includes('NOMBRE')) {
    return { label: 'Renombrado', classes: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300' };
  }
  
  return { label: tipo, classes: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300' };
}

interface ServidorOption {
  id: string;
  nombre: string;
  ip: string;
}

export const AuditoriaScreen: React.FC = () => {
  const showNotification = useNotification();
  const [items, setItems] = useState<AuditoriaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  
  const [busqueda, setBusqueda] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [servidorFiltro, setServidorFiltro] = useState('');
  const [servidores, setServidores] = useState<ServidorOption[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [tipos, setTipos] = useState<string[]>([]);
  const [tipoOpen, setTipoOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchAuditoria = async (pageNum: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const filtros: AuditoriaFiltros = {
        busqueda: busqueda || undefined,
        tipo: tipoFiltro || undefined,
        servidor_id: servidorFiltro ? Number(servidorFiltro) : undefined,
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        page: pageNum,
        limit: PAGE_SIZE,
      };

      const response = await getAuditoria(filtros);
      setItems(response.items);
      setTotal(response.total);
      setPage(response.page);
      setPages(response.pages);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Error al cargar el historial de auditoría';
      setError(msg);
      showNotification(msg, 'error', 4000);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditoria();
  }, []);

  useEffect(() => {
    getServersStatus()
      .then((data) => setServidores(data.map((s) => ({ id: s.id, nombre: s.nombre, ip: s.ip }))))
      .catch(() => {});
    getAuditoriaTipos().then(setTipos).catch(() => setTipos([]));
  }, []);

  useEffect(() => {
    const f = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node))
        setTipoOpen(false);
    };
    document.addEventListener('mousedown', f);
    return () => document.removeEventListener('mousedown', f);
  }, []);

  const handleRefresh = () => {
    fetchAuditoria(page);
  };

  const handleMarkAsRead = async (item: AuditoriaItem) => {
    if (item.origen !== 'notificacion' || item.leida === true) return;
    
    try {
      await markNotificacionRead(item.id);
      setItems(prev => prev.map(i => 
        i.id === item.id && i.origen === 'notificacion' ? { ...i, leida: true } : i
      ));
      showNotification('Notificación marcada como leída', 'success', 2000);
    } catch (error) {
      showNotification('Error al marcar notificación', 'error', 4000);
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchAuditoria(1);
  };

  const handleClearFilters = () => {
    setBusqueda('');
    setTipoFiltro('');
    setServidorFiltro('');
    setFechaDesde('');
    setFechaHasta('');
    setPage(1);
    fetchAuditoria(1);
  };

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const filtros: AuditoriaFiltros = {
        busqueda: busqueda || undefined,
        tipo: tipoFiltro || undefined,
        servidor_id: servidorFiltro ? Number(servidorFiltro) : undefined,
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
      };
      const blob = await exportAuditoriaPDF(filtros);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `auditoria_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showNotification('PDF exportado correctamente', 'success');
    } catch {
      showNotification('Error al exportar PDF', 'error');
    } finally {
      setExporting(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pages) {
      fetchAuditoria(newPage);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="flex flex-col min-w-0">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Historial de Auditoría</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Registro completo de conexiones, desconexiones y eventos del sistema
        </p>
      </div>

      {/* Buscador Principal */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Buscar por dispositivo, servidor, descripción..."
              className="w-full h-10 pl-10 pr-4 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 h-10 rounded-lg border flex items-center gap-2 text-sm font-medium transition-colors ${
              showFilters 
                ? 'bg-primary text-white border-primary' 
                : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <Filter size={16} />
            Filtros
          </button>
          <button
            onClick={handleSearch}
            className="px-4 h-10 rounded-lg bg-primary text-white text-sm font-semibold hover:opacity-90"
          >
            Buscar
          </button>
          <button
            onClick={handleRefresh}
            className="px-4 h-10 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 text-sm font-medium"
            title="Actualizar datos"
          >
            <RotateCcw size={16} />
            Actualizar
          </button>
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="px-4 h-10 rounded-lg border border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 flex items-center gap-2 text-sm font-medium disabled:opacity-50"
            title="Exportar a PDF"
          >
            {exporting ? <Spinner size="sm" /> : <Download size={16} />}
            {exporting ? 'Exportando...' : 'Exportar PDF'}
          </button>
        </div>

        {/* Panel de Filtros */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Tipo de Evento</label>
                <div className="relative" ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setTipoOpen(!tipoOpen)}
                    className="w-full h-9 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-left flex items-center justify-between gap-2 focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <span className="truncate">{tipoFiltro ? getTipoLabel(tipoFiltro) : 'Todos'}</span>
                    <ChevronDown size={14} className={`shrink-0 transition-transform ${tipoOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {tipoOpen && (
                    <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-lg overflow-hidden">
                      <div className="max-h-60 overflow-y-auto">
                        <button
                          type="button"
                          onClick={() => { setTipoFiltro(''); setTipoOpen(false); }}
                          className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700 ${!tipoFiltro ? 'bg-primary/10 text-primary font-medium' : ''}`}
                        >
                          Todos
                        </button>
                        {tipos.map(t => (
                          <button
                            key={t}
                            type="button"
                            onClick={() => { setTipoFiltro(t); setTipoOpen(false); }}
                            className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700 ${tipoFiltro === t ? 'bg-primary/10 text-primary font-medium' : ''}`}
                          >
                            {getTipoLabel(t)}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                  <Server size={12} className="inline mr-1" />
                  Servidor
                </label>
                <select
                  value={servidorFiltro}
                  onChange={(e) => setServidorFiltro(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Todos</option>
                  {servidores.map((s) => (
                    <option key={s.id} value={s.id}>{s.nombre} ({s.ip})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Fecha Desde</label>
                <input
                  type="datetime-local"
                  value={fechaDesde}
                  onChange={(e) => setFechaDesde(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Fecha Hasta</label>
                <input
                  type="datetime-local"
                  value={fechaHasta}
                  onChange={(e) => setFechaHasta(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleClearFilters}
                  className="h-9 px-4 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Limpiar Filtros
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-4 flex items-center gap-3">
          <XCircle size={20} className="text-red-500 shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300 flex-1">{error}</p>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Tabla de Auditoría */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <Clock size={14} className="inline mr-1" />
                  Fecha/Hora
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Tipo
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <Monitor size={14} className="inline mr-1" />
                  Dispositivo
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider hidden md:table-cell">
                  <Server size={14} className="inline mr-1" />
                  Servidor
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Descripción
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider hidden md:table-cell">
                  <User size={14} className="inline mr-1" />
                  Usuario
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider hidden md:table-cell">
                  Duración
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <TableSkeleton rows={8} cols={8} />
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    No hay registros de auditoría
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const badge = getTypeBadge(item.tipo);
                  const isLeida = item.leida === true;
                  const isNotificacion = item.origen === 'notificacion';
                  
                  return (
                    <tr key={`${item.origen}-${item.id}`} className={`hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${isLeida ? 'bg-slate-50 dark:bg-slate-900/30' : ''}`}>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 whitespace-nowrap">
                        {formatDate(item.fecha)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.classes}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-slate-900 dark:text-white">
                          {item.dispositivo_nombre || item.dispositivo_id || '-'}
                        </div>
                        {item.dispositivo_nombre && item.dispositivo_id && (
                          <div className="text-xs text-slate-400">{item.dispositivo_id}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <div className="text-sm font-medium text-slate-900 dark:text-white">
                          {item.servidor_nombre || (item.servidor_id != null ? `ID: ${item.servidor_id}` : '-')}
                        </div>
                        {item.servidor_nombre && item.servidor_id != null && (
                          <div className="text-xs text-slate-400">ID: {item.servidor_id}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 max-w-xs">
                        {item.descripcion.length > 80 ? (
                          <ExpandableDescription text={item.descripcion} maxLength={80} />
                        ) : (
                          item.descripcion
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 hidden md:table-cell">
                        {item.usuario || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 whitespace-nowrap hidden md:table-cell">
                        {formatDuration(item.duracion_segundos)}
                      </td>
                      <td className="px-4 py-3">
                        {isNotificacion && (
                          <button
                            onClick={() => handleMarkAsRead(item)}
                            title={isLeida ? 'Leída' : 'Marcar como leída'}
                            className={`p-1.5 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors ${isLeida ? 'text-green-500' : 'text-blue-400'}`}
                          >
                            {isLeida ? <Check size={16} /> : <Circle size={16} />}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {pages > 1 && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <div className="text-sm text-slate-500">
              Mostrando {((page - 1) * PAGE_SIZE) + 1} - {Math.min(page * PAGE_SIZE, total)} de {total} registros
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 1}
                className="p-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm text-slate-600 dark:text-slate-300">
                Página {page} de {pages}
              </span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page === pages}
                className="p-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditoriaScreen;
