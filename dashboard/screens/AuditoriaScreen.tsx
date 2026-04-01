import React, { useEffect, useState, useCallback } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Calendar, Server, Monitor, Clock, X, ChevronDown, ChevronUp, User, RotateCcw, Check, Circle } from 'lucide-react';
import { getAuditoria, markNotificacionRead, AuditoriaItem, AuditoriaFiltros } from '../services/auditoriaService';
import { useNotification } from '../components/useNotification';

const PAGE_SIZE = 20;

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

function getTypeBadge(tipo: string) {
  const tipoUpper = tipo.toUpperCase();
  
  if (tipoUpper.includes('DESCONEXION') || tipoUpper.includes('SESION_CERRADA')) {
    return { label: 'Desconexión', classes: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' };
  }
  if (tipoUpper.includes('CONEXION') || tipoUpper.includes('SESION_ACTIVA')) {
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

export const AuditoriaScreen: React.FC = () => {
  const showNotification = useNotification();
  const [items, setItems] = useState<AuditoriaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  
  const [busqueda, setBusqueda] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const fetchAuditoria = async (pageNum: number = 1) => {
    setLoading(true);
    try {
      const filtros: AuditoriaFiltros = {
        busqueda: busqueda || undefined,
        tipo: tipoFiltro || undefined,
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
    } catch (error) {
      showNotification('Error al cargar el historial de auditoría', 'error', 4000);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditoria();
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
    setFechaDesde('');
    setFechaHasta('');
    setPage(1);
    fetchAuditoria(1);
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
        <div className="flex gap-3">
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
        </div>

        {/* Panel de Filtros */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Tipo de Evento</label>
                <select
                  value={tipoFiltro}
                  onChange={(e) => setTipoFiltro(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Todos</option>
                  <option value="CONEXION_DISPOSITIVO">Conexión</option>
                  <option value="DESCONEXION_DISPOSITIVO">Desconexión</option>
                  <option value="SESION_ACTIVA">Sesión Activa</option>
                  <option value="SESION_CERRADA">Sesión Cerrada</option>
                  <option value="SINCRONIZACION_FORZADA">Sincronización Forzada</option>
                  <option value="RENOMBRAR_DISPOSITIVO">Renombrar Dispositivo</option>
                  <option value="RENOMBRAR_SERVIDOR">Renombrar Servidor</option>
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
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <Server size={14} className="inline mr-1" />
                  Servidor
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Descripción
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <User size={14} className="inline mr-1" />
                  Usuario
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Duración
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                      Cargando...
                    </div>
                  </td>
                </tr>
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
                      <td className="px-4 py-3">
                        <div className="text-sm text-slate-600 dark:text-slate-300">
                          {item.servidor_nombre || '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 max-w-xs">
                        {item.descripcion.length > 80 ? (
                          <ExpandableDescription text={item.descripcion} maxLength={80} />
                        ) : (
                          item.descripcion
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                        {item.usuario || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 whitespace-nowrap">
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
