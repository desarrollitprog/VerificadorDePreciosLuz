import React, { useState, useMemo } from 'react';
import { ArrowUpDown } from 'lucide-react';
import { BannerMetrica } from '../../services/resumenService';

interface Props {
  data: BannerMetrica[];
  loading?: boolean;
}

type SortKey = 'banner_id' | 'titulo' | 'inicios' | 'validas_50' | 'vcr';

const BannerMetricsTable: React.FC<Props> = ({ data, loading }) => {
  const [sortKey, setSortKey] = useState<SortKey>('inicios');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const sorted = useMemo(() => {
    const copy = [...data];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'banner_id') cmp = a.banner_id - b.banner_id;
      else if (sortKey === 'titulo') cmp = (a.titulo || '').localeCompare(b.titulo || '');
      else if (sortKey === 'inicios') cmp = a.inicios - b.inicios;
      else if (sortKey === 'validas_50') cmp = a.validas_50 - b.validas_50;
      else if (sortKey === 'vcr') cmp = a.vcr - b.vcr;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [data, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageData = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
    setPage(0);
  };

  const SortHeader = ({ label, sortKey: sk }: { label: string; sortKey: SortKey }) => (
    <th
      className="px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-300 select-none"
      onClick={() => toggleSort(sk)}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown size={12} className={sortKey === sk ? 'text-primary' : 'opacity-40'} />
      </div>
    </th>
  );

  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="h-1 bg-cyan-500" />
        <div className="p-5 animate-pulse">
          <div className="h-4 w-48 bg-slate-200 dark:bg-[#253247] rounded mb-6" />
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-8 bg-slate-200 dark:bg-[#253247] rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="h-1 bg-cyan-500" />
        <div className="p-5">
          <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-3">Métricas por Banner</h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin métricas registradas hoy</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="h-1 bg-cyan-500" />
      <div className="p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-3">Métricas por Banner</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <SortHeader label="ID" sortKey="banner_id" />
                <SortHeader label="Banner" sortKey="titulo" />
                <SortHeader label="Inicios" sortKey="inicios" />
                <SortHeader label="Válidas >50%" sortKey="validas_50" />
                <SortHeader label="VCR" sortKey="vcr" />
              </tr>
            </thead>
            <tbody>
              {pageData.map((b) => (
                <tr key={b.banner_id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                  <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{b.banner_id}</td>
                  <td className="px-3 py-2 text-slate-900 dark:text-white font-medium max-w-[200px] truncate">
                    {b.titulo || `Banner #${b.banner_id}`}
                  </td>
                  <td className="px-3 py-2 text-slate-700 dark:text-slate-300">{b.inicios.toLocaleString()}</td>
                  <td className="px-3 py-2 text-slate-700 dark:text-slate-300">{b.validas_50.toLocaleString()}</td>
                  <td className="px-3 py-2">
                    <span className={`font-semibold ${b.vcr >= 80 ? 'text-emerald-600 dark:text-emerald-400' : b.vcr >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                      {b.vcr}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {sorted.length} banners · Página {page + 1} de {totalPages}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 text-xs rounded bg-slate-100 dark:bg-[#253247] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 transition"
              >
                Anterior
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1 text-xs rounded bg-slate-100 dark:bg-[#253247] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 transition"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BannerMetricsTable;
