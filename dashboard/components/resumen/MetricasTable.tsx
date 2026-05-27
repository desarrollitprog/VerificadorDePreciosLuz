import React, { useState, useMemo } from 'react';
import { ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { SedeMetrica } from '../../services/resumenService';

interface Row {
  sede: string;
  servidor_id: number;
  titulo: string;
  inicios: number;
  validas_50: number;
  vcr: number;
}

interface Props {
  data: SedeMetrica[];
  loading?: boolean;
}

type SortKey = 'sede' | 'titulo' | 'inicios' | 'validas_50' | 'vcr';

const vcrColor = (v: number) =>
  v >= 80 ? '#10b981' : v >= 50 ? '#f59e0b' : '#ef4444';

const vcrBgClass = (v: number) =>
  v >= 80 ? 'text-emerald-600 dark:text-emerald-400' :
  v >= 50 ? 'text-amber-600 dark:text-amber-400' :
  'text-red-600 dark:text-red-400';

const MetricasTable: React.FC<Props> = ({ data, loading }) => {
  const [sortKey, setSortKey] = useState<SortKey>('inicios');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const pageSize = 15;

  const { rows, totals } = useMemo(() => {
    const r: Row[] = [];
    const t: Record<string, { inicios: number; validas_50: number }> = {};
    for (const sede of data) {
      for (const b of sede.banners) {
        r.push({
          sede: sede.nombre,
          servidor_id: sede.servidor_id,
          titulo: b.titulo,
          inicios: b.reproducciones,
          validas_50: b.validas_50,
          vcr: b.vcr,
        });
        if (!t[b.titulo]) t[b.titulo] = { inicios: 0, validas_50: 0 };
        t[b.titulo].inicios += b.reproducciones;
        t[b.titulo].validas_50 += b.validas_50;
      }
    }
    return { rows: r, totals: t };
  }, [data]);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'sede') cmp = a.sede.localeCompare(b.sede);
      else if (sortKey === 'titulo') cmp = a.titulo.localeCompare(b.titulo);
      else if (sortKey === 'inicios') cmp = a.inicios - b.inicios;
      else if (sortKey === 'validas_50') cmp = a.validas_50 - b.validas_50;
      else if (sortKey === 'vcr') cmp = a.vcr - b.vcr;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

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
        <div className="h-1 bg-violet-500" />
        <div className="p-5 animate-pulse space-y-3">
          <div className="h-4 w-48 bg-slate-200 dark:bg-[#253247] rounded" />
          {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-8 bg-slate-200 dark:bg-[#253247] rounded" />)}
        </div>
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="h-1 bg-violet-500" />
        <div className="p-5">
          <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-2">Métricas por Sede</h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin datos de reproducciones hoy</p>
        </div>
      </div>
    );
  }

  const totalKeys = Object.keys(totals).sort();

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="h-1 bg-gradient-to-r from-violet-500 to-purple-500" />
      <div className="p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-3">Métricas por Sede</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-left border-r border-slate-200 dark:border-slate-700 last:border-r-0">#</th>
                <SortHeader label="Sede" sortKey="sede" />
                <SortHeader label="Banner" sortKey="titulo" />
                <SortHeader label="Inicios" sortKey="inicios" />
                <SortHeader label="&gt;50%" sortKey="validas_50" />
                <SortHeader label="VCR" sortKey="vcr" />
              </tr>
            </thead>
            <tbody>
              {pageData.map((row, i) => (
                <tr
                  key={`${row.servidor_id}-${row.titulo}-${i}`}
                  className="border-b border-slate-100 dark:border-slate-800 even:bg-slate-50/50 dark:even:bg-slate-800/20 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-all duration-300"
                >
                  <td className="px-3 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-[10px] border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                    {page * pageSize + i + 1}
                  </td>
                  <td className="px-3 py-2.5 text-slate-900 dark:text-white font-medium border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                    {row.sede}
                  </td>
                  <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 max-w-[180px] truncate border-r border-slate-100 dark:border-slate-800 last:border-r-0" title={row.titulo}>
                    {row.titulo}
                  </td>
                  <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 font-medium tabular-nums text-right border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                    {row.inicios.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 font-medium tabular-nums text-right border-r border-slate-100 dark:border-slate-800 last:border-r-0">
                    {row.validas_50.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 border-r-0">
                    <div className="flex items-center gap-2 w-28 ml-auto">
                      <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${Math.min(row.vcr, 100)}%`, backgroundColor: vcrColor(row.vcr) }} />
                      </div>
                      <span className={`text-xs font-semibold w-10 text-right shrink-0 ${vcrBgClass(row.vcr)}`}>
                        {row.vcr}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
              {totalKeys.length > 1 && (
                <>
                  <tr><td colSpan={6} className="border-b border-slate-200 dark:border-slate-700" /></tr>
                  {totalKeys.map(titulo => {
                    const t = totals[titulo];
                    const vcr = t.inicios > 0 ? Math.round((t.validas_50 / t.inicios) * 100 * 10) / 10 : 0;
                    return (
                      <tr key={`total-${titulo}`} className="bg-slate-100/70 dark:bg-slate-700/20 font-semibold">
                        <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 font-mono text-[10px] border-r border-slate-100 dark:border-slate-800 last:border-r-0">-</td>
                        <td className="px-3 py-2.5 text-slate-600 dark:text-slate-400 uppercase text-[10px] tracking-wider border-r border-slate-100 dark:border-slate-800 last:border-r-0">TOTAL</td>
                        <td className="px-3 py-2.5 text-slate-900 dark:text-white border-r border-slate-100 dark:border-slate-800 last:border-r-0">{titulo}</td>
                        <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 tabular-nums text-right border-r border-slate-100 dark:border-slate-800 last:border-r-0">{t.inicios.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 tabular-nums text-right border-r border-slate-100 dark:border-slate-800 last:border-r-0">{t.validas_50.toLocaleString()}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2 w-28 ml-auto">
                            <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${Math.min(vcr, 100)}%`, backgroundColor: vcrColor(vcr) }} />
                            </div>
                            <span className={`text-xs font-semibold w-10 text-right shrink-0 ${vcrBgClass(vcr)}`}>{vcr}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </>
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              <span className="font-medium text-slate-700 dark:text-slate-300">{sorted.length}</span> filas
              <span className="mx-1.5 text-slate-400">·</span>
              <span className="bg-slate-100 dark:bg-[#253247] px-2 py-0.5 rounded text-[10px]">
                {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sorted.length)} de {sorted.length}
              </span>
            </span>
            <div className="flex gap-1">
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="p-1.5 rounded bg-slate-100 dark:bg-[#253247] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition">
                <ChevronLeft size={14} />
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="p-1.5 rounded bg-slate-100 dark:bg-[#253247] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition">
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricasTable;
