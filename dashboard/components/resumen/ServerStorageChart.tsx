import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ServidorResumen } from '../../services/resumenService';

interface Props {
  data: ServidorResumen[];
  loading?: boolean;
}

function getBarColor(pct: number): string {
  if (pct >= 90) return '#ef4444';
  if (pct >= 70) return '#eab308';
  return '#22d3ee';
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="bg-white dark:bg-[#1c2936] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-900 dark:text-white font-semibold">{row.name}</p>
      <p className="text-slate-500 dark:text-slate-400">{row.used} GB / {row.total} GB ({row.pct}%)</p>
    </div>
  );
};

const ServerStorageChart: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 bg-slate-200 dark:bg-[#253247]" />
        <div className="p-5 animate-pulse">
          <div className="h-4 w-48 bg-slate-200 dark:bg-[#253247] rounded mb-6" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-6 bg-slate-200 dark:bg-[#253247] rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const chartData = data.map((s) => ({
    name: s.nombre,
    pct: s.porcentaje_uso,
    total: Math.round(s.almacenamiento_total / 1073741824 * 10) / 10,
    used: Math.round(s.almacenamiento_usado / 1073741824 * 10) / 10,
  }));

  if (chartData.length === 0) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 w-full bg-cyan-500" />
        <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-cyan-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-cyan-500/5 pointer-events-none" />
        <div className="relative z-10 p-5">
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin datos de sedes</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 overflow-hidden relative group">
      <div className="h-1 w-full bg-cyan-500" />
      <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-cyan-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-cyan-500/5 pointer-events-none" />
      <div className="relative z-10 p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-4">Almacenamiento por Sede</h3>
        <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 48)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 0, bottom: 0 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fill: '#a1a1aa', fontSize: 12 }} tickLine={false} axisLine={false} width={90} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#27272a' }} />
            <Bar dataKey="pct" radius={[0, 4, 4, 0]} barSize={20}>
              {chartData.map((_, idx) => (
                <Cell key={idx} fill={getBarColor(chartData[idx].pct)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ServerStorageChart;
