import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { SedeMetrica } from '../../services/resumenService';

interface Props {
  data: SedeMetrica[];
  loading?: boolean;
}

const vcrColor = (v: number) =>
  v >= 80 ? '#10b981' : v >= 50 ? '#f59e0b' : '#ef4444';

const vcrBgClass = (v: number) =>
  v >= 80 ? 'text-emerald-600 dark:text-emerald-400' :
  v >= 50 ? 'text-amber-600 dark:text-amber-400' :
  'text-red-600 dark:text-red-400';

const SedeMetricsTable: React.FC<Props> = ({ data, loading }) => {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="p-5 animate-pulse space-y-3">
          <div className="h-4 w-36 bg-slate-200 dark:bg-[#253247] rounded" />
          {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-200 dark:bg-[#253247] rounded" />)}
        </div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="h-1 bg-violet-500" />
        <div className="p-5">
          <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-2">Métricas por Sede</h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin datos de reproducciones por sede hoy</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="h-1 bg-gradient-to-r from-violet-500 to-purple-500" />
      <div className="p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-3">Métricas por Sede</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
                <th className="px-3 py-2.5 w-8" />
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-left">Sede</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">Inicios</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">>50%</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">VCR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {data.map((sede) => {
                const isOpen = expanded.has(sede.servidor_id);
                return (
                  <React.Fragment key={sede.servidor_id}>
                    <tr
                      className="hover:bg-slate-100 dark:hover:bg-[#253247] transition-colors cursor-pointer"
                      onClick={() => toggle(sede.servidor_id)}
                    >
                      <td className="px-3 py-3">
                        {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                      </td>
                      <td className="px-3 py-3">
                        <span className="text-slate-900 dark:text-white font-medium">{sede.nombre}</span>
                      </td>
                      <td className="px-3 py-3 text-right text-slate-700 dark:text-slate-300 font-medium tabular-nums">
                        {sede.total_reproducciones.toLocaleString()}
                      </td>
                      <td className="px-3 py-3 text-right text-slate-700 dark:text-slate-300 font-medium tabular-nums">
                        {sede.total_validas_50.toLocaleString()}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${Math.min(sede.vcr_general, 100)}%`, backgroundColor: vcrColor(sede.vcr_general) }} />
                          </div>
                          <span className={`text-xs font-semibold w-10 text-right shrink-0 ${vcrBgClass(sede.vcr_general)}`}>
                            {sede.vcr_general}%
                          </span>
                        </div>
                      </td>
                    </tr>
                    {isOpen && sede.banners.map((b, i) => (
                      <tr key={`${sede.servidor_id}-${b.banner_id}`} className="bg-slate-50/50 dark:bg-slate-800/20">
                        <td className="px-3 py-2" />
                        <td className="px-3 py-2 pl-8 text-slate-600 dark:text-slate-400 max-w-[200px] truncate" title={b.titulo}>
                          <span className="text-[10px] text-slate-400 mr-1.5">{i + 1}.</span>
                          {b.titulo}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-700 dark:text-slate-300 tabular-nums">{b.reproducciones.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right text-slate-700 dark:text-slate-300 tabular-nums">{b.validas_50.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={`text-xs font-medium ${vcrBgClass(b.vcr)}`}>{b.vcr}%</span>
                        </td>
                      </tr>
                    ))}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SedeMetricsTable;
