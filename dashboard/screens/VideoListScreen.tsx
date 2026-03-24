import React, { useEffect, useState } from 'react';
import { getVideos, deleteVideo, updateBannerEstado, updateBannerMetadata } from '../services/videoService';
import { Video } from '../types';
import { Search, FileVideo, AlertCircle, Clock, Edit2, Trash2, Download, Power, ListChecks, ArrowUpDown } from 'lucide-react';

const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'error':
      return <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded bg-red-500/10 text-red-500"><AlertCircle size={16} /></div>;
    case 'queued':
      return <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded bg-gray-700/50 text-gray-400"><Clock size={16} /></div>;
    default:
      return <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded bg-primary/10 text-primary"><FileVideo size={16} /></div>;
  }
};

const getVigenciaStatus = (item: Video): 'vigente' | 'programado' | 'expirado' => {
  const now = Date.now();
  const ini = item.fechaInicio ? new Date(item.fechaInicio).getTime() : null;
  const fin = item.fechaFin ? new Date(item.fechaFin).getTime() : null;

  if (ini && now < ini) return 'programado';
  if (fin && now > fin) return 'expirado';
  return 'vigente';
};

const VigenciaBadge = ({ item }: { item: Video }) => {
  const vigencia = getVigenciaStatus(item);
  if (vigencia === 'programado') {
    return <span className="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">Programado</span>;
  }
  if (vigencia === 'expirado') {
    return <span className="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20">Expirado</span>;
  }
  return <span className="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">Vigente</span>;
};

const OperativoBadge = ({ activo }: { activo?: boolean }) => (
  <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold border ${
    activo
      ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
      : 'bg-slate-500/10 text-slate-500 border-slate-500/20'
  }`}>
    {activo ? 'Activo' : 'Inactivo'}
  </span>
);

const toInputDateTime = (iso?: string | null): string => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
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

export const VideoListScreen: React.FC = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [vigenciaFilter, setVigenciaFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [editItem, setEditItem] = useState<Video | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editForm, setEditForm] = useState({
    activo: true,
    fechaInicio: '',
    fechaFin: '',
  });
  const [page, setPage] = useState(1);
  const rowsPerPage = 8;

  useEffect(() => {
    async function fetchVideos() {
      setLoading(true);
      try {
        const data = await getVideos();
        setVideos(Array.isArray(data) ? data : []);
      } catch {
        setError('Error Cargando Videos');
        setVideos([]);
      } finally {
        setLoading(false);
      }
    }
    fetchVideos();
  }, []);

  const handleDelete = async (videoId: string) => {
    setError(null);
    try {
      await deleteVideo(videoId);
      setVideos((prev) => prev.filter((v) => v.id !== videoId));
    } catch {
      setError('Error Borrando Videos');
    }
  };

  const handleToggleActivo = async (videoId: string, nextActivo: boolean) => {
    setError(null);
    try {
      await updateBannerEstado(videoId, nextActivo);
      setVideos((prev) => prev.map((v) => (v.id === videoId ? { ...v, activo: nextActivo } : v)));
    } catch {
      setError('Error actualizando estado del video');
    }
  };

  const openEditVigencia = (item: Video) => {
    setEditItem(item);
    setEditForm({
      activo: !!item.activo,
      fechaInicio: toInputDateTime(item.fechaInicio),
      fechaFin: toInputDateTime(item.fechaFin),
    });
  };

  const saveEditVigencia = async () => {
    if (!editItem) return;
    const ini = editForm.fechaInicio ? new Date(editForm.fechaInicio) : null;
    const fin = editForm.fechaFin ? new Date(editForm.fechaFin) : null;

    if (ini && fin && ini.getTime() > fin.getTime()) {
      setError('Rango inválido: FechaInicio no puede ser mayor que FechaFin.');
      return;
    }

    setSavingEdit(true);
    setError(null);
    try {
      await updateBannerMetadata(editItem.id, {
        activo: editForm.activo,
        fecha_inicio: toIsoOrNull(editForm.fechaInicio),
        fecha_fin: toIsoOrNull(editForm.fechaFin),
      });

      setVideos((prev) =>
        prev.map((v) =>
          v.id === editItem.id
            ? {
                ...v,
                activo: editForm.activo,
                fechaInicio: toIsoOrNull(editForm.fechaInicio),
                fechaFin: toIsoOrNull(editForm.fechaFin),
              }
            : v
        )
      );
      setEditItem(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error actualizando vigencia.');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleBulkSetActivo = async (nextActivo: boolean) => {
    if (!selected.length) return;
    let ok = 0;
    let fail = 0;

    for (const id of selected) {
      try {
        await updateBannerEstado(id, nextActivo);
        ok += 1;
      } catch {
        fail += 1;
      }
    }

    setVideos((prev) => prev.map((v) => (selected.includes(v.id) ? { ...v, activo: nextActivo } : v)));
    setSelected([]);
    setError(fail ? `Actualizados: ${ok}. Fallaron: ${fail}.` : null);
  };

  const downloadVideoFile = (item: Video) => {
    if (!item.url) return;
    const link = document.createElement('a');
    link.href = item.url;
    link.download = item.filename || `video-${item.id}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleBulkDownload = () => {
    const selectedItems = videos.filter((v) => selected.includes(v.id));
    selectedItems.forEach((item, index) => {
      window.setTimeout(() => downloadVideoFile(item), index * 120);
    });
  };

  let filteredVideos = videos.filter((v: Video) => {
    const searchMatch =
      search === '' ||
      v.filename?.toLowerCase().includes(search.toLowerCase()) ||
      v.id?.toString().includes(search);

    const statusMatch =
      statusFilter === '' ||
      (statusFilter === 'activo' && v.activo === true) ||
      (statusFilter === 'inactivo' && v.activo === false);

    const vig = getVigenciaStatus(v);
    const vigenciaMatch = vigenciaFilter === '' || vigenciaFilter === vig;

    const dateMatch = dateFilter === '' || (v.date && v.date.startsWith(dateFilter));
    const typeMatch = typeFilter === '' || (v.tipo && v.tipo.toLowerCase() === typeFilter);
    return searchMatch && statusMatch && vigenciaMatch && dateMatch && typeMatch;
  });

  filteredVideos = filteredVideos.sort((a: Video, b: Video) => (b.date || '').localeCompare(a.date || ''));

  const paginatedVideos = filteredVideos.slice((page - 1) * rowsPerPage, page * rowsPerPage);

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
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">BIBLIOTECA DE VIDEOS</h2>
          <p className="text-slate-500 mt-1 text-sm">CHECKEA EL ESTATUS ACTUAL DE LOS VIDEOS O ELIMINA Y DESCARGA EL CONTENIDO</p>
        </div>
      </div>

      <div className="flex flex-col gap-4 bg-white/80 dark:bg-[#16212b]/80 p-4 rounded-xl border border-slate-200/50 dark:border-[#324d67]/30 backdrop-blur-sm">
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="text-slate-400" size={18} />
          </div>
          <input
            type="text"
            className="block w-full rounded-lg bg-slate-50/50 dark:bg-[#0b1219]/50 border-none py-2.5 pl-10 pr-3 text-sm text-slate-800 dark:text-white placeholder-slate-400 dark:placeholder-[#58728a] focus:ring-1 focus:ring-primary/50"
            placeholder="Coloca el Nombre del Archivo"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2 w-full sm:w-auto items-center flex-wrap">
          <select
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Estatus</option>
            <option value="activo">Activos</option>
            <option value="inactivo">Inactivos</option>
          </select>
          <select
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={vigenciaFilter}
            onChange={(e) => setVigenciaFilter(e.target.value)}
          >
            <option value="">Vigencia</option>
            <option value="vigente">Vigente</option>
            <option value="programado">Programado</option>
            <option value="expirado">Expirado</option>
          </select>
          <input
            type="date"
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          />
          <select
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            style={{ minWidth: 100 }}
          >
            <option value="">Tipo</option>
            <option value="video">Video</option>
            <option value="image">Foto</option>
          </select>
        </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-500 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="flex-1 w-full rounded-xl border border-slate-200 dark:border-[#324d67]/30 bg-white dark:bg-[#16212b] flex flex-col shadow-xl overflow-hidden" style={{ minHeight: '600px', height: 'auto' }}>
        <div className="grid grid-cols-12 gap-2 border-b border-slate-200 dark:border-[#324d67]/50 bg-slate-50 dark:bg-[#1f2b38] px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-[#92adc9]">
          <div className="col-span-1 flex items-center justify-center gap-1" title="Seleccionar todo el contenido">
            <input
              type="checkbox"
              className="rounded border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#0b1219] text-primary focus:ring-primary focus:ring-offset-0"
              checked={paginatedVideos.length > 0 && paginatedVideos.every((item) => selected.includes(item.id))}
              onChange={(e) => {
                if (e.target.checked) {
                  const ids = paginatedVideos.map((item) => item.id);
                  setSelected((prev) => Array.from(new Set([...prev, ...ids])));
                } else {
                  const ids = new Set(paginatedVideos.map((item) => item.id));
                  setSelected((prev) => prev.filter((id) => !ids.has(id)));
                }
              }}
            />
            <ListChecks size={13} className="text-slate-400 dark:text-[#92adc9]" />
          </div>
          <div className="col-span-5 sm:col-span-4 md:col-span-3 lg:col-span-2 flex items-center gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Nombre del Archivo
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="col-span-3 hidden sm:flex md:col-span-2 items-center gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Fecha de Subida
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="hidden lg:flex lg:col-span-2 items-center gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Fecha Inicio
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="hidden lg:flex lg:col-span-2 items-center gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Fecha Fin
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="col-span-1 hidden md:flex lg:hidden items-center justify-end gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Tamaño
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="col-span-3 sm:col-span-2 md:col-span-2 lg:col-span-1 flex items-center justify-start">Estatus</div>
        </div>
        <div>
          {Array.isArray(paginatedVideos) && paginatedVideos.map((item) => (
            <div key={item.id} className="group grid grid-cols-12 gap-2 border-b border-slate-100 dark:border-[#324d67]/30 px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-[#1f2b38] transition-colors items-center">
              <div className="col-span-1 flex items-center justify-center">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#0b1219] text-primary focus:ring-primary focus:ring-offset-0"
                  checked={selected.includes(item.id)}
                  onChange={(e) => {
                    if (e.target.checked) setSelected([...selected, item.id]);
                    else setSelected(selected.filter((id) => id !== item.id));
                  }}
                />
              </div>
              <div className="col-span-5 sm:col-span-4 md:col-span-3 lg:col-span-2 flex items-center gap-3 overflow-hidden">
                <StatusIcon status={item.status} />
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-medium text-slate-900 dark:text-white truncate" title={item.filename}>{item.filename}</span>
                  <span className="text-xs text-slate-500 dark:text-[#58728a] truncate">ID: {item.id}</span>
                </div>
              </div>
              <div className="col-span-3 hidden sm:flex md:col-span-2 text-xs text-slate-600 dark:text-[#92adc9] truncate" title={item.date}>{formatCaracasTime(item.date)}</div>
              <div className="hidden lg:flex lg:col-span-2 text-xs text-slate-600 dark:text-[#92adc9] truncate" title={item.fechaInicio || undefined}>{formatCaracasTime(item.fechaInicio)}</div>
              <div className="hidden lg:flex lg:col-span-2 text-xs text-slate-600 dark:text-[#92adc9] truncate" title={item.fechaFin || undefined}>{formatCaracasTime(item.fechaFin)}</div>
              <div className="col-span-1 hidden md:flex lg:hidden justify-end text-xs text-slate-600 dark:text-[#92adc9] font-mono">{item.size}</div>
              <div className="col-span-3 sm:col-span-2 md:col-span-2 lg:col-span-1 flex items-center gap-1.5 flex-wrap">
                <OperativoBadge activo={item.activo} />
                <VigenciaBadge item={item} />
              </div>
              <div className="col-span-3 sm:col-span-2 md:col-span-2 flex items-center justify-center gap-1 whitespace-nowrap">
                <button
                  className="p-1.5 rounded text-blue-500 hover:text-blue-600 hover:bg-blue-500/10"
                  title="Editar vigencia"
                  onClick={() => openEditVigencia(item)}
                >
                  <Edit2 size={16} />
                </button>
                <button
                  className="p-1.5 rounded text-sky-500 hover:text-sky-600 hover:bg-sky-500/10"
                  title="Descargar"
                  onClick={() => downloadVideoFile(item)}
                >
                  <Download size={16} />
                </button>
                <button
                  className={`p-1.5 rounded transition-colors ${
                    item.activo
                      ? 'text-amber-500 hover:text-amber-600 hover:bg-amber-500/10'
                      : 'text-emerald-500 hover:text-emerald-600 hover:bg-emerald-500/10'
                  }`}
                  title={item.activo ? 'Desactivar' : 'Activar'}
                  onClick={() => handleToggleActivo(item.id, !item.activo)}
                >
                  <Power size={16} />
                </button>
                <button
                  className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                  title="Delete"
                  onClick={() => setDeleteId(item.id)}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {paginatedVideos.length < rowsPerPage && Array.from({ length: rowsPerPage - paginatedVideos.length }).map((_, idx) => (
            <div key={`empty-row-${idx}`} className="grid grid-cols-12 gap-2 px-3 py-2.5" style={{ minHeight: '60px' }} />
          ))}
        </div>
        <div className="sticky bottom-0 z-10 bg-slate-50 dark:bg-[#1f2b38] border-t border-slate-200 dark:border-[#324d67]/30 p-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 dark:text-[#92adc9]">
          <span className="text-xs text-slate-500 dark:text-[#92adc9]">Seleccionados: {selected.length}</span>
          <div className="flex items-center gap-2">
            <button
            className="px-3 py-1 rounded bg-slate-100 dark:bg-[#0b1219] text-slate-700 dark:text-[#92adc9] hover:bg-slate-200 dark:hover:bg-[#1f2b38] text-xs disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => setPage(page - 1)}
            disabled={page <= 1}
          >Anterior</button>
          <span className="text-xs text-slate-500 dark:text-[#92adc9]">Página {page}</span>
            <button
              className="px-3 py-1 rounded bg-slate-100 dark:bg-[#0b1219] text-slate-700 dark:text-[#92adc9] hover:bg-slate-200 dark:hover:bg-[#1f2b38] text-xs disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={() => setPage(page + 1)}
              disabled={page * rowsPerPage >= filteredVideos.length}
            >Siguiente</button>

            <button
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-100 dark:bg-[#0b1219] text-slate-700 dark:text-[#92adc9] hover:bg-slate-200 dark:hover:bg-[#1f2b38] text-xs disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={handleBulkDownload}
              title="Descargar seleccionados"
              disabled={!selected.length}
            >
              <Download size={14} />
              Descargar
            </button>
            <button
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700 text-xs disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={() => setDeleteId('bulk')}
              title="Borrar seleccionados"
              disabled={!selected.length}
            >
              <Trash2 size={14} />
              Borrar
            </button>
          </div>
        </div>
      </div>

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-[#16212b] rounded-lg p-6 shadow-xl w-full max-w-xs flex flex-col items-center">
            <p className="mb-4 text-center text-slate-800 dark:text-white">
              {deleteId === 'bulk'
                ? `¿Seguro que deseas borrar ${selected.length} elementos seleccionados?`
                : '¿Seguro que deseas borrar este video?'}
            </p>
            <div className="flex gap-4">
              <button
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700"
                onClick={async () => {
                  if (deleteId === 'bulk') {
                    for (const id of selected) {
                      await handleDelete(id);
                    }
                    setSelected([]);
                  } else {
                    await handleDelete(deleteId);
                  }
                  setDeleteId(null);
                }}
              >
                Borrar
              </button>
              <button
                className="px-4 py-2 rounded bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white hover:bg-slate-300 dark:hover:bg-slate-600"
                onClick={() => setDeleteId(null)}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {editItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-[#16212b] rounded-lg p-5 w-full max-w-md border border-slate-200 dark:border-slate-700">
            <h3 className="text-lg font-semibold mb-4 text-slate-900 dark:text-white">Editar vigencia</h3>
            <div className="space-y-3">
              <label className="block text-sm text-slate-700 dark:text-slate-300">
                <span className="mb-1 block">FechaInicio</span>
                <input
                  type="datetime-local"
                  value={editForm.fechaInicio}
                  onChange={(e) => setEditForm((p) => ({ ...p, fechaInicio: e.target.value }))}
                  className="w-full rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border border-slate-200 dark:border-slate-700"
                />
              </label>

              <label className="block text-sm text-slate-700 dark:text-slate-300">
                <span className="mb-1 block">FechaFin</span>
                <input
                  type="datetime-local"
                  value={editForm.fechaFin}
                  onChange={(e) => setEditForm((p) => ({ ...p, fechaFin: e.target.value }))}
                  className="w-full rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border border-slate-200 dark:border-slate-700"
                />
              </label>

              <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={editForm.activo}
                  onChange={(e) => setEditForm((p) => ({ ...p, activo: e.target.checked }))}
                />
                Activo
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                className="px-4 py-2 rounded bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white"
                onClick={() => setEditItem(null)}
                disabled={savingEdit}
              >
                Cancelar
              </button>
              <button
                className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                onClick={saveEditVigencia}
                disabled={savingEdit}
              >
                {savingEdit ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="pb-4 text-xs text-slate-400 dark:text-[#58728a] text-center lg:text-right">
        © 2026 Verificador de Precios Luz. Todos los derechos reservados.
      </div>
    </div>
  );
};