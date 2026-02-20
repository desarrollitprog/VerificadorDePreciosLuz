import React, { useEffect, useState } from 'react';
import { getVideos, deleteVideo } from '../services/videoService';
import { Search, Filter, ArrowUpDown, MoreHorizontal, FileVideo, AlertCircle, Clock, Edit2, Trash2, UploadCloud, ChevronLeft, ChevronRight, SlidersHorizontal } from 'lucide-react';

const StatusBadge = ({ status }: { status: string }) => {
  switch (status) {
    case 'live':
      return (
        <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
          Live
        </span>
      );
    case 'processing':
      return (
        <span className="inline-flex items-center rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-400 border border-amber-500/20">
          Processing
        </span>
      );
    case 'error':
      return (
        <span className="inline-flex items-center rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
          Error
        </span>
      );
    case 'queued':
      return (
        <span className="inline-flex items-center rounded-full bg-gray-500/10 px-2.5 py-0.5 text-xs font-medium text-gray-400 border border-gray-500/20">
          Queued
        </span>
      );
  }
};

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

export const VideoListScreen: React.FC = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;

  useEffect(() => {
    async function fetchVideos() {
      setLoading(true);
      try {
        const data = await getVideos();
        setVideos(data);
      } catch (err: any) {
        setError('Error loading videos');
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
      setVideos(videos.filter(v => v.id !== videoId));
    } catch (err: any) {
      setError('Error deleting video');
    }
  };

  // Filtrado de videos
  // Filtrado y ordenamiento
  let filteredVideos = videos.filter((v: any) => {
    // Filtro por búsqueda (nombre, tag, id)
    const searchMatch =
      search === '' ||
      v.filename?.toLowerCase().includes(search.toLowerCase()) ||
      v.id?.toString().includes(search) ||
      (v.tag && v.tag.toLowerCase().includes(search.toLowerCase()));
    // Filtro por estatus
    const statusMatch = statusFilter === '' || (v.status && v.status.toLowerCase() === statusFilter);
    // Filtro por fecha de subida (asume v.date en formato YYYY-MM-DD)
    const dateMatch = dateFilter === '' || (v.date && v.date.startsWith(dateFilter));
    // Filtro por tipo (foto/video)
    const typeMatch = typeFilter === '' || (v.tipo && v.tipo.toLowerCase() === typeFilter);
    return searchMatch && statusMatch && dateMatch && typeMatch;
  });
  // Ordenar por fecha descendente (asume v.date en formato YYYY-MM-DD o similar)
  filteredVideos = filteredVideos.sort((a: any, b: any) => (b.date || '').localeCompare(a.date || ''));

  // Paginación
  const totalRows = filteredVideos.length;
  const paginatedVideos = filteredVideos.slice((page - 1) * rowsPerPage, page * rowsPerPage);

  return (
    <div className="flex flex-col h-full gap-6">
        {/* Header Actions */}
      {/* Acciones masivas */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        {selected.length > 0 && (
          <div className="flex gap-2 mb-2">
            <button
              className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700"
              onClick={() => setDeleteId('bulk')}
            >Borrar seleccionados</button>
            <button
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
              onClick={() => alert('Descargar seleccionados (no implementado)')}
            >Descargar seleccionados</button>
          </div>
        )}
        <div>
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Video Library</h2>
          <p className="text-slate-500 mt-1 text-sm">Manage, upload, and organize your video content efficiently.</p>
        </div>
        <button
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-5 py-2.5 rounded-lg font-medium transition-all shadow-lg shadow-primary/20 active:scale-95"
          onClick={() => window.location.href = '/dashboard'}
        >
          <UploadCloud size={20} />
          <span>Quick Upload</span>
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white dark:bg-[#16212b] p-2 rounded-xl border border-slate-200 dark:border-[#324d67]/30 shadow-sm">
        <div className="relative w-full sm:max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="text-slate-400" size={18} />
          </div>
          <input
            type="text"
            className="block w-full rounded-lg bg-slate-50 dark:bg-[#0b1219] border-none py-2.5 pl-10 pr-3 text-sm text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-[#58728a] focus:ring-1 focus:ring-primary"
            placeholder="Filter by filename, tag, or ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2 w-full sm:w-auto items-center">
          {/* Filtro de Estatus */}
          <select
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="">Estatus</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </select>
          {/* Filtro de Fecha de subida */}
          <input
            type="date"
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={dateFilter}
            onChange={e => setDateFilter(e.target.value)}
          />
          <button className="flex items-center gap-2 px-3 py-2.5 bg-slate-50 dark:bg-[#0b1219] hover:bg-slate-100 dark:hover:bg-[#1f2b38] text-slate-600 dark:text-[#92adc9] hover:text-slate-900 dark:hover:text-white rounded-lg transition-colors text-sm font-medium">
            <Filter size={18} />
            Filtrar
          </button>
          {/* Dropdown de tipo (Foto/Video) */}
          <select
            className="rounded-lg px-3 py-2 bg-slate-50 dark:bg-[#0b1219] border-none text-sm text-slate-900 dark:text-white"
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            style={{ minWidth: 100 }}
          >
            <option value="">Tipo</option>
            <option value="video">Video</option>
            <option value="image">Foto</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="flex-1 w-full overflow-hidden rounded-xl border border-slate-200 dark:border-[#324d67]/30 bg-white dark:bg-[#16212b] flex flex-col shadow-xl">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 border-b border-slate-200 dark:border-[#324d67]/50 bg-slate-50 dark:bg-[#1f2b38] px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-[#92adc9]">
          <div className="col-span-1 flex items-center justify-center">
            <input type="checkbox" className="rounded border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#0b1219] text-primary focus:ring-primary focus:ring-offset-0" />
          </div>
          <div className="col-span-5 sm:col-span-4 flex items-center gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Filename
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="col-span-3 hidden sm:flex items-center gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Date Uploaded
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="col-span-2 hidden md:flex items-center justify-end gap-2 cursor-pointer hover:text-slate-700 dark:hover:text-white group">
            Size
            <ArrowUpDown size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="col-span-4 sm:col-span-3 md:col-span-2 flex items-center justify-center sm:justify-start">Status</div>
        </div>

        {/* Table Body */}
        <div className="flex-1 overflow-y-auto">
          {paginatedVideos.map((item) => (
            <div key={item.id} className="group grid grid-cols-12 gap-4 border-b border-slate-100 dark:border-[#324d67]/30 px-4 py-3 hover:bg-slate-50 dark:hover:bg-[#1f2b38] transition-colors items-center">
              <div className="col-span-1 flex items-center justify-center">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#0b1219] text-primary focus:ring-primary focus:ring-offset-0"
                  checked={selected.includes(item.id)}
                  onChange={e => {
                    if (e.target.checked) setSelected([...selected, item.id]);
                    else setSelected(selected.filter(id => id !== item.id));
                  }}
                />
              </div>
              <div className="col-span-5 sm:col-span-4 flex items-center gap-3 overflow-hidden">
                <StatusIcon status={item.status} />
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-medium text-slate-900 dark:text-white truncate" title={item.filename}>{item.filename}</span>
                  <span className="text-xs text-slate-500 dark:text-[#58728a] truncate">ID: {item.id}</span>
                </div>
              </div>
              <div className="col-span-3 hidden sm:flex text-sm text-slate-600 dark:text-[#92adc9]">{item.date}</div>
              <div className="col-span-2 hidden md:flex justify-end text-sm text-slate-600 dark:text-[#92adc9] font-mono">{item.size}</div>
              <div className="col-span-4 sm:col-span-3 md:col-span-2 flex items-center justify-between sm:justify-start gap-4">
                <StatusBadge status={item.status} />
                
                {/* Hover Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                    title="Delete"
                    onClick={() => setDeleteId(item.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                    {/* Modal de confirmación de borrado (individual o masivo) */}
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
                            >Borrar</button>
                            <button
                              className="px-4 py-2 rounded bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white hover:bg-slate-300 dark:hover:bg-slate-600"
                              onClick={() => setDeleteId(null)}
                            >Cancelar</button>
                          </div>
                        </div>
                      </div>
                    )}
              </div>
            </div>
          ))}
        </div>

        {/* Pagination Footer */}
        <div className="bg-slate-50 dark:bg-[#1f2b38] border-t border-slate-200 dark:border-[#324d67]/30 p-3 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-[#92adc9]">
          <div className="flex items-center gap-2">
            <span>Rows per page:</span>
            <select
              className="bg-white dark:bg-[#0b1219] border border-slate-300 dark:border-[#324d67]/30 rounded px-2 py-1 text-slate-900 dark:text-white focus:ring-1 focus:ring-primary focus:border-primary outline-none"
              value={rowsPerPage}
              disabled
            >
              <option>10</option>
            </select>
          </div>
          <div className="flex items-center gap-6">
            <span>{(page - 1) * rowsPerPage + 1}-{Math.min(page * rowsPerPage, totalRows)} of {totalRows}</span>
            <div className="flex items-center gap-1">
              <button
                className="p-1 hover:text-slate-900 dark:hover:text-white disabled:opacity-50"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft size={18} />
              </button>
              <button
                className="p-1 hover:text-slate-900 dark:hover:text-white disabled:opacity-50"
                disabled={page * rowsPerPage >= totalRows}
                onClick={() => setPage(page + 1)}
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div className="pb-4 text-xs text-slate-400 dark:text-[#58728a] text-center lg:text-right">
         Video Management Pro © 2023
      </div>
    </div>
  );
};