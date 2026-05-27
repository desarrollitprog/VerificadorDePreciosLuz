import React from 'react';
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

const MetricasTable: React.FC<Props> = ({ data, loading }) => {
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

  if (!data.length) {
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

  const grupos: Array<{
    nombre: string;
    filas: { titulo: string; inicios: number; validas_50: number; vcr: number }[];
    subtotal: { inicios: number; validas_50: number };
  }> = [];

  let gran_total = { inicios: 0, validas_50: 0 };
  let idx = 0;

  for (const sede of data) {
    const filas: typeof grupos[0]['filas'] = [];
    let sub_inicios = 0;
    let sub_validas = 0;

    for (const b of sede.banners) {
      filas.push({
        titulo: b.titulo,
        inicios: b.reproducciones,
        validas_50: b.validas_50,
        vcr: b.vcr,
      });
      sub_inicios += b.reproducciones;
      sub_validas += b.validas_50;
    }

    filas.sort((a, b) => a.titulo.localeCompare(b.titulo));

    grupos.push({
      nombre: sede.nombre,
      filas,
      subtotal: { inicios: sub_inicios, validas_50: sub_validas },
    });

    gran_total.inicios += sub_inicios;
    gran_total.validas_50 += sub_validas;
  }

  const vcr = (v: number, t: number) =>
    t > 0 ? Math.round((v / t) * 100 * 10) / 10 : 0;

  const VCRBar = ({ value }: { value: number }) => (
    <div className="flex items-center gap-2 w-28 ml-auto">
      <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${Math.min(value, 100)}%`, backgroundColor: vcrColor(value) }} />
      </div>
      <span className={`text-xs font-semibold w-10 text-right shrink-0 ${vcrBgClass(value)}`}>{value}%</span>
    </div>
  );

  const gran_vcr = vcr(gran_total.validas_50, gran_total.inicios);

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="h-1 bg-gradient-to-r from-violet-500 to-purple-500" />
      <div className="p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-3">Métricas por Sede</h3>
        <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-left border-r border-slate-200 dark:border-slate-700">#</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-left border-r border-slate-200 dark:border-slate-700">Sede</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-left border-r border-slate-200 dark:border-slate-700">Banner</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right border-r border-slate-200 dark:border-slate-700">Inicios</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right border-r border-slate-200 dark:border-slate-700">{'>'}50%</th>
                <th className="px-3 py-2.5 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">VCR</th>
              </tr>
            </thead>
            <tbody>
              {grupos.map(g => (
                <React.Fragment key={g.nombre}>
                  {g.filas.map(f => {
                    idx++;
                    return (
                      <tr key={`${g.nombre}-${f.titulo}`} className="border-b border-slate-100 dark:border-slate-800 even:bg-slate-50/50 dark:even:bg-slate-800/20 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-all duration-300">
                        <td className="px-3 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-[10px] border-r border-slate-100 dark:border-slate-800">{idx}</td>
                        <td className="px-3 py-2.5 text-slate-900 dark:text-white font-medium border-r border-slate-100 dark:border-slate-800">{g.nombre}</td>
                        <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 max-w-[180px] truncate border-r border-slate-100 dark:border-slate-800" title={f.titulo}>{f.titulo}</td>
                        <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 font-medium tabular-nums text-right border-r border-slate-100 dark:border-slate-800">{f.inicios.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 font-medium tabular-nums text-right border-r border-slate-100 dark:border-slate-800">{f.validas_50.toLocaleString()}</td>
                        <td className="px-3 py-2.5"><VCRBar value={f.vcr} /></td>
                      </tr>
                    );
                  })}
                  <tr className="bg-slate-100/70 dark:bg-slate-700/20 font-semibold border-b border-slate-200 dark:border-slate-700">
                    <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 font-mono text-[10px] border-r border-slate-100 dark:border-slate-800">-</td>
                    <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 uppercase text-[10px] tracking-wider border-r border-slate-100 dark:border-slate-800" colSpan={2}>TOTAL {g.nombre}</td>
                    <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 tabular-nums text-right font-bold border-r border-slate-100 dark:border-slate-800">{g.subtotal.inicios.toLocaleString()}</td>
                    <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 tabular-nums text-right font-bold border-r border-slate-100 dark:border-slate-800">{g.subtotal.validas_50.toLocaleString()}</td>
                    <td className="px-3 py-2.5"><VCRBar value={vcr(g.subtotal.validas_50, g.subtotal.inicios)} /></td>
                  </tr>
                </React.Fragment>
              ))}
              <tr className="border-b-2 border-slate-300 dark:border-slate-600" />
              <tr className="font-bold bg-slate-200/70 dark:bg-slate-600/30">
                <td className="px-3 py-3 text-slate-500 dark:text-slate-400 font-mono text-[10px] border-r border-slate-100 dark:border-slate-800">-</td>
                <td className="px-3 py-3 text-slate-800 dark:text-white uppercase text-xs tracking-wider border-r border-slate-100 dark:border-slate-800" colSpan={2}>TOTAL GENERAL</td>
                <td className="px-3 py-3 text-slate-800 dark:text-white tabular-nums text-right border-r border-slate-100 dark:border-slate-800">{gran_total.inicios.toLocaleString()}</td>
                <td className="px-3 py-3 text-slate-800 dark:text-white tabular-nums text-right border-r border-slate-100 dark:border-slate-800">{gran_total.validas_50.toLocaleString()}</td>
                <td className="px-3 py-3"><VCRBar value={gran_vcr} /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default MetricasTable;


