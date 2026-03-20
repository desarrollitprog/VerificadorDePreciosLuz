import React, { useEffect, useState } from 'react';
import { getVideos, deleteVideo, updateBannerEstado, sincronizarServidores, getServidores, updateBannerMetadata, asignarBanner } from '../services/videoService';
import { Video, Servidor } from '../types';
import { Search, FileVideo, AlertCircle, Clock, Edit2, Trash2, Eye, Monitor, Smartphone, Server, RefreshCw, ChevronDown, ChevronRight, Save, X } from 'lucide-react';

const toInputDateTime = (iso?: string | null): string => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const toIsoOrNull = (val: string): string | null => {
  if (!val) return null;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(val)) {
    return val.includes('-04:00') ? val : `${val}:00-04:00`;
  }
  return new Date(val).toISOString();
};

const formatCaracasTime = (value?: string): string => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('es-VE', { timeZone: 'America/Caracas' });
};

const getEstadoColor = (estado: string) => {
  switch (estado) {
    case 'activo':
      return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    case 'inactivo':
      return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
    case 'borrador':
      return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
    case 'vencido':
      return 'bg-rose-500/10 text-rose-500 border-rose-500/20';
    default:
      return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
  }
};

export const VideoListScreen: React.FC = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [servidores, setServidores] = useState<Servidor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [viewModal, setViewModal] = useState<Video | null>(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [syncServidores, setSyncServidores] = useState<number[]>([]);
  const [editModal, setEditModal] = useState<Video | null>(null);
  const [editTitulo, setEditTitulo] = useState('');
  const [editFechaInicio, setEditFechaInicio] = useState('');
  const [editFechaFin, setEditFechaFin] = useState('');
  const [editAsignacionTodos, setEditAsignacionTodos] = useState(true);
  const [editServidorIds, setEditServidorIds] = useState<number[]>([]);
  const [editDispositivoIds, setEditDispositivoIds] = useState<number[]>([]);
  const [expandedServers, setExpandedServers] = useState<number[]>([]);
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [videosData, servidoresData] = await Promise.all([
          getVideos(),
          getServidores()
        ]);
        setVideos(Array.isArray(videosData) ? videosData : []);
        setServidores(Array.isArray(servidoresData) ? servidoresData : []);
      } catch {
        setError('Error Cargando Datos');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleDelete = async (videoId: string) => {
    setError(null);
    try {
      await deleteVideo(videoId);
      setVideos((prev) => prev.filter((v) => v.id !== videoId));
    } catch {
      setError('Error Borrando Video');
    }
  };

  const handleToggleActivo = async (videoId: string, nextActivo: boolean) => {
    setError(null);
    try {
      await updateBannerEstado(videoId, nextActivo);
      setVideos((prev) => prev.map((v) => (v.id === videoId ? { ...v, activo: nextActivo, estado: nextActivo ? 'activo' : 'inactivo' } : v)));
    } catch {
      setError('Error actualizando estado');
    }
  };

  const handleSync = async () => {
    if (syncServidores.length === 0) {
      setError('Selecciona al menos un servidor');
      return;
    }
    setSincronizando(true);
    setError(null);
    try {
      await sincronizarServidores(syncServidores);
      setSyncServidores([]);
    } catch {
      setError('Error en sincronización');
    } finally {
      setSincronizando(false);
    }
  };

  const toggleServidorSync = (servidorId: number) => {
    setSyncServidores(prev =>
      prev.includes(servidorId)
        ? prev.filter(id => id !== servidorId)
        : [...prev, servidorId]
    );
  };

  const openEditModal = (video: Video) => {
    setEditModal(video);
    setEditTitulo(video.titulo || '');
    setEditFechaInicio(video.fechaInicio ? video.fechaInicio.split('T')[0] + 'T' + video.fechaInicio.split('T')[1]?.substring(0, 5) : '');
    setEditFechaFin(video.fechaFin ? video.fechaFin.split('T')[0] + 'T' + video.fechaFin.split('T')[1]?.substring(0, 5) : '');
    setEditAsignacionTodos(video.asignacion_todos ?? true);
    setEditServidorIds([]);
    setEditDispositivoIds([]);
    if (video.asignaciones) {
      const srvIds = [...new Set(video.asignaciones.map(a => a.servidor_id))];
      const dispIds = video.asignaciones.map(a => a.dispositivo_id);
      setEditServidorIds(srvIds);
      setEditDispositivoIds(dispIds);
    }
  };

  const closeEditModal = () => {
    setEditModal(null);
    setEditServidorIds([]);
    setEditDispositivoIds([]);
    setExpandedServers([]);
  };

  const handleSaveEdit = async () => {
    if (!editModal) return;
    setSavingEdit(true);
    try {
      await updateBannerMetadata(editModal.id, {
        fechaInicio: editFechaInicio || null,
        fechaFin: editFechaFin || null,
      });
      if (!editAsignacionTodos) {
        const asignaciones: { servidor_id: number; dispositivo_id: number }[] = [];
        for (const srvId of editServidorIds) {
          if (editDispositivoIds.length > 0) {
            for (const dispId of editDispositivoIds) {
              asignaciones.push({ servidor_id: srvId, dispositivo_id: dispId });
            }
          } else {
            const srv = servidores.find(s => s.id === srvId);
            if (srv?.dispositivos) {
              for (const disp of srv.dispositivos) {
                asignaciones.push({ servidor_id: srvId, dispositivo_id: disp.id });
              }
            }
          }
        }
        if (asignaciones.length > 0) {
          await asignarBanner(editModal.id, asignaciones);
        }
      }
      const updatedVideos = await getVideos();
      setVideos(updatedVideos);
      closeEditModal();
    } catch {
      setError('Error al guardar cambios');
    } finally {
      setSavingEdit(false);
    }
  };

  let filteredVideos = videos.filter((v: Video) => {
    const searchMatch =
      search === '' ||
      v.filename?.toLowerCase().includes(search.toLowerCase()) ||
      v.titulo?.toLowerCase().includes(search.toLowerCase()) ||
      v.id?.toString().includes(search);
    return searchMatch;
  });

  filteredVideos = filteredVideos.sort((a: Video, b: Video) => (b.date || '').localeCompare(a.date || ''));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">BIBLIOTECA DE PUBLICIDADES</h2>
          <p className="text-slate-500 mt-1 text-sm">Gestiona y asigna publicidades a dispositivos</p>
        </div>
        <div className="flex gap-2">
          {syncServidores.length > 0 && (
            <button
              onClick={handleSync}
              disabled={sincronizando}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw size={16} className={sincronizando ? 'animate-spin' : ''} />
              {sincronizando ? 'Sincronizando...' : `Sincronizar (${syncServidores.length})`}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="relative flex-1 w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="text-slate-400" size={18} />
          </div>
          <input
            type="text"
            className="block w-full rounded-lg bg-white dark:bg-[#16212b] border border-slate-200 dark:border-[#324d67]/30 py-2.5 pl-10 pr-3 text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:ring-1 focus:ring-primary"
            placeholder="Buscar por nombre o ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-500 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="flex gap-4">
        <div className="w-64 shrink-0 bg-white dark:bg-[#16212b] rounded-xl border border-slate-200 dark:border-[#324d67]/30 p-4">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-white mb-3 flex items-center gap-2">
            <Server size={16} />
            Servidores
          </h3>
          <div className="space-y-2">
            {servidores.map(srv => (
              <label
                key={srv.id}
                className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-2 rounded-lg"
              >
                <input
                  type="checkbox"
                  checked={syncServidores.includes(srv.id)}
                  onChange={() => toggleServidorSync(srv.id)}
                  className="rounded border-slate-300 dark:border-[#324d67] text-primary focus:ring-primary"
                />
                <span className="text-sm text-slate-700 dark:text-slate-300 truncate">{srv.nombre}</span>
                <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${srv.online ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-500/10 text-slate-500'}`}>
                  {srv.online ? 'Online' : 'Offline'}
                </span>
              </label>
            ))}
            {servidores.length === 0 && (
              <p className="text-xs text-slate-500">Sin servidores</p>
            )}
          </div>
        </div>

        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredVideos.map((item) => (
            <div
              key={item.id}
              className="bg-white dark:bg-[#16212b] rounded-xl border border-slate-200 dark:border-[#324d67]/30 overflow-hidden"
            >
              <div className="aspect-video bg-slate-100 dark:bg-[#0b1219] flex items-center justify-center">
                {item.tipo === 'image' ? (
                  <img
                    src={item.url}
                    alt={item.titulo || item.filename}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-slate-400">
                    <FileVideo size={48} />
                  </div>
                )}
              </div>

              <div className="p-4">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white truncate mb-1">
                  {item.titulo || item.filename}
                </h3>
                <div className="h-px bg-slate-200 dark:bg-slate-700 mb-3" />

                <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-2">
                  {item.tipo === 'image' ? (
                    <span className="flex items-center gap-1"><FileVideo size={14} /> Imagen</span>
                  ) : (
                    <span className="flex items-center gap-1"><FileVideo size={14} /> Video</span>
                  )}
                </div>

                {item.fechaInicio || item.fechaFin ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-3">
                    <Clock size={12} />
                    <span>
                      {formatCaracasTime(item.fechaInicio)} - {formatCaracasTime(item.fechaFin)}
                    </span>
                  </div>
                ) : (
                  <div className="mb-3" />
                )}

                <div className="flex items-center gap-2 mb-3">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold border ${getEstadoColor(item.estado || 'activo')}`}>
                    {(item.estado || 'activo').toUpperCase()}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">
                    <Smartphone size={10} />
                    {item.dispositivos_count || 0} devs
                  </span>
                </div>

                {item.asignaciones && item.asignaciones.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Asignado a:</p>
                    <div className="space-y-0.5">
                      {item.asignaciones.slice(0, 3).map((asig, idx) => (
                        <div key={idx} className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1">
                          <Smartphone size={10} />
                          <span className="truncate">
                            {asig.dispositivo_nombre || asig.dispositivo_codigo || 'Dispositivo'} - {asig.servidor_nombre}
                          </span>
                        </div>
                      ))}
                      {item.asignaciones.length > 3 && (
                        <p className="text-xs text-slate-400">+{item.asignaciones.length - 3} más</p>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                  <button
                    onClick={() => setViewModal(item)}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium hover:bg-slate-200 dark:hover:bg-slate-700"
                  >
                    <Eye size={14} />
                    Visualizar
                  </button>
                  <button
                    onClick={() => openEditModal(item)}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-blue-500/10 text-blue-500 text-xs font-medium hover:bg-blue-500/20"
                  >
                    <Edit2 size={14} />
                    Editar
                  </button>
                  <button
                    onClick={() => handleToggleActivo(item.id, !item.activo)}
                    className={`px-3 py-2 rounded-lg text-xs font-medium ${
                      item.activo
                        ? 'bg-amber-500/10 text-amber-500 hover:bg-amber-500/20'
                        : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20'
                    }`}
                  >
                    {item.activo ? 'Pausar' : 'Activar'}
                  </button>
                  <button
                    onClick={() => setDeleteId(item.id)}
                    className="px-3 py-2 rounded-lg bg-red-500/10 text-red-500 text-xs font-medium hover:bg-red-500/20"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}

          {filteredVideos.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-12 text-slate-500">
              <FileVideo size={48} className="mb-4 opacity-50" />
              <p>No hay publicidades {search ? 'que coincidan con la búsqueda' : 'disponibles'}</p>
            </div>
          )}
        </div>
      </div>

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-[#16212b] rounded-lg p-6 shadow-xl w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4 text-slate-900 dark:text-white">¿Eliminar publicidad?</h3>
            <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
              Esta acción eliminará la publicidad y sus asignaciones.
            </p>
            <div className="flex gap-3">
              <button
                className="flex-1 px-4 py-2 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white hover:bg-slate-300 dark:hover:bg-slate-600"
                onClick={() => setDeleteId(null)}
              >
                Cancelar
              </button>
              <button
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700"
                onClick={async () => {
                  await handleDelete(deleteId);
                  setDeleteId(null);
                }}
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      {viewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white dark:bg-[#16212b] rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {viewModal.titulo || viewModal.filename}
              </h3>
              <button
                onClick={() => setViewModal(null)}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <Trash2 size={20} className="text-slate-400" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)]">
              <div className="aspect-video bg-slate-100 dark:bg-slate-800 rounded-lg mb-4 flex items-center justify-center">
                {viewModal.tipo === 'image' ? (
                  <img src={viewModal.url} alt={viewModal.titulo} className="max-w-full max-h-full object-contain" />
                ) : (
                  <video src={viewModal.url} controls className="max-w-full max-h-full" />
                )}
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500 text-xs">Tipo</p>
                  <p className="text-slate-900 dark:text-white">{viewModal.tipo === 'image' ? 'Imagen' : 'Video'}</p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs">Estado</p>
                  <p className={`font-medium ${viewModal.estado === 'activo' ? 'text-emerald-500' : 'text-slate-500'}`}>
                    {(viewModal.estado || 'activo').toUpperCase()}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs">Fecha Inicio</p>
                  <p className="text-slate-900 dark:text-white">{formatCaracasTime(viewModal.fechaInicio)}</p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs">Fecha Fin</p>
                  <p className="text-slate-900 dark:text-white">{formatCaracasTime(viewModal.fechaFin)}</p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs">Asignado a</p>
                  <p className="text-slate-900 dark:text-white">
                    {viewModal.asignacion_todos ? 'Todos los dispositivos' : `${viewModal.dispositivos_count || 0} dispositivos`}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs">ID</p>
                  <p className="text-slate-900 dark:text-white font-mono text-xs">{viewModal.id}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {editModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white dark:bg-[#16212b] rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Editar Publicidad
              </h3>
              <button
                onClick={closeEditModal}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X size={20} className="text-slate-400" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-140px)] space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Título</label>
                <input
                  type="text"
                  value={editTitulo}
                  onChange={(e) => setEditTitulo(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#0b1219] px-3 py-2 text-sm text-slate-900 dark:text-white"
                  placeholder="Título de la publicidad"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fecha Inicio</label>
                  <input
                    type="datetime-local"
                    value={editFechaInicio}
                    onChange={(e) => setEditFechaInicio(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#0b1219] px-3 py-2 text-sm text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fecha Fin</label>
                  <input
                    type="datetime-local"
                    value={editFechaFin}
                    onChange={(e) => setEditFechaFin(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#0b1219] px-3 py-2 text-sm text-slate-900 dark:text-white"
                  />
                </div>
              </div>
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                <label className="flex items-center gap-2 mb-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editAsignacionTodos}
                    onChange={(e) => {
                      setEditAsignacionTodos(e.target.checked);
                      if (e.target.checked) {
                        setEditServidorIds([]);
                        setEditDispositivoIds([]);
                      }
                    }}
                    className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                  />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    Asignar a TODOS los servidores
                  </span>
                </label>
                {!editAsignacionTodos && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1">
                      <Server size={12} />
                      Seleccionar servidores:
                    </p>
                    <div className="max-h-40 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg p-2 space-y-1">
                      {servidores.length === 0 ? (
                        <p className="text-xs text-slate-500">No hay servidores disponibles</p>
                      ) : (
                        servidores.map(srv => (
                          <div key={srv.id}>
                            <label className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1.5 rounded">
                              <input
                                type="checkbox"
                                checked={editServidorIds.includes(srv.id)}
                                onChange={() => {
                                  setEditServidorIds(prev =>
                                    prev.includes(srv.id)
                                      ? prev.filter(id => id !== srv.id)
                                      : [...prev, srv.id]
                                  );
                                }}
                                className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                              />
                              <span className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-1">
                                <Server size={12} />
                                {srv.nombre}
                                <span className={`text-[10px] px-1 py-0.5 rounded ${srv.online ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-500/10 text-slate-500'}`}>
                                  {srv.online ? 'Online' : 'Offline'}
                                </span>
                              </span>
                              {srv.dispositivos && srv.dispositivos.length > 0 && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedServers(prev =>
                                      prev.includes(srv.id)
                                        ? prev.filter(id => id !== srv.id)
                                        : [...prev, srv.id]
                                    );
                                  }}
                                  className="ml-auto p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                                >
                                  {expandedServers.includes(srv.id) ? (
                                    <ChevronDown size={14} className="text-slate-500" />
                                  ) : (
                                    <ChevronRight size={14} className="text-slate-500" />
                                  )}
                                </button>
                              )}
                            </label>
                            {expandedServers.includes(srv.id) && srv.dispositivos && srv.dispositivos.length > 0 && (
                              <div className="ml-6 mt-1 space-y-0.5">
                                {srv.dispositivos.map(disp => (
                                  <label key={disp.id} className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1 rounded">
                                    <input
                                      type="checkbox"
                                      checked={editDispositivoIds.includes(disp.id)}
                                      onChange={() => {
                                        setEditDispositivoIds(prev =>
                                          prev.includes(disp.id)
                                            ? prev.filter(id => id !== disp.id)
                                            : [...prev, disp.id]
                                        );
                                      }}
                                      className="rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
                                    />
                                    <span className="text-xs text-slate-600 dark:text-slate-400 flex items-center gap-1">
                                      <Smartphone size={10} />
                                      {disp.nombre_amigable || disp.codigo_kiosko}
                                    </span>
                                  </label>
                                ))}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Seleccionados: {editServidorIds.length} servidores, {editDispositivoIds.length} dispositivos
                    </p>
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-3 p-4 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={closeEditModal}
                disabled={savingEdit}
                className="flex-1 px-4 py-2 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white hover:bg-slate-300 dark:hover:bg-slate-600 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={savingEdit || (!editAsignacionTodos && editServidorIds.length === 0)}
                className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Save size={16} />
                {savingEdit ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="pb-4 text-xs text-slate-400 dark:text-[#58728a] text-center">
        © 2026 Verificador de Precios Luz. Todos los derechos reservados.
      </div>
    </div>
  );
};
