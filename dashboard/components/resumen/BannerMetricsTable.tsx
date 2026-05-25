import React, { useState, useMemo } from 'react';
import { ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { BannerMetrica } from '../../services/resumenService';

interface Props {
  data: BannerMetrica[];
  loading?: boolean;
}

type SortKey = 'banner_id' | 'titulo' | 'inicios' | 'validas_50' | 'vcr';

const vcrColor = (v: number) =>
  v >= 80 ? '#10b981' : v >= 50 ? '#f59e0b' : '#ef4444';

const vcrBgClass = (v: number) =>
  v >= 80 ? 'text-emerald-600 dark:text-emerald-400' :
  v >= 50 ? 'text-amber-600 dark:text-amber-400' :
  'text-red-600 dark:text-red-400';

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
      className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-300 select-none border-r border-slate-200 dark:border-slate-700 last:border-r-0"
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
      <div className="h-1 bg-gradient-to-r from-cyan-500 to-blue-500" />
      <div className="p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-3">Métricas por Banner</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-left border-r border-slate-200 dark:border-slate-700 last:border-r-0">
                  #
                </th>
                <SortHeader label="Banner" sortKey="titulo" />
                <SortHeader label="Inicios" sortKey="inicios" />
                <SortHeader label=">50%" sortKey="validas_50" />
                <SortHeader label="VCR" sortKey="vcr" />
              </tr>
            </thead>
            <tbody>
              {pageData.map((b, i) => (
                  <tr
                    key={b.banner_id}
                    className="border-b border-slate-100 dark:border-slate-800 even:bg-slate-50/50 dark:even:bg-slate-800/20 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-all duration-300"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <td className="px-3 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-[10px] border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                      {page * pageSize + i + 1}
                    </td>
                    <td className="px-3 py-2.5 text-slate-900 dark:text-white font-medium max-w-[180px] truncate border-r border-slate-100 dark:border-slate-800 last:border-r-0" title={b.titulo || `Banner #${b.banner_id}`}>
                      {b.titulo || `Banner #${b.banner_id}`}
                    </td>
                    <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 font-medium tabular-nums border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                      {b.inicios.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 font-medium tabular-nums border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                      {b.validas_50.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5 border-r-0">
                      <div className="flex items-center gap-2 w-28">
                        <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700 ease-out"
                            style={{ width: `${Math.min(b.vcr, 100)}%`, backgroundColor: vcrColor(b.vcr) }}
                          />
                        </div>
                        <span className={`text-xs font-semibold w-10 text-right shrink-0 ${vcrBgClass(b.vcr)}`}>
                          {b.vcr}%
                        </span>
                      </div>
                    </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              <span className="font-medium text-slate-700 dark:text-slate-300">{sorted.length}</span> banners
              <span className="mx-1.5 text-slate-400">·</span>
              <span className="bg-slate-100 dark:bg-[#253247] px-2 py-0.5 rounded text-[10px]">
                {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sorted.length)} de {sorted.length}
              </span>
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1.5 rounded bg-slate-100 dark:bg-[#253247] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded bg-slate-100 dark:bg-[#253247] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BannerMetricsTable;
