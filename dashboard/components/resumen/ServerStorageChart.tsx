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
    <div className="bg-[#27272a] border border-zinc-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-white font-semibold">{row.name}</p>
      <p className="text-zinc-300">{row.used} GB / {row.total} GB ({row.pct}%)</p>
    </div>
  );
};

const ServerStorageChart: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5 animate-pulse">
        <div className="h-4 w-48 bg-zinc-800 rounded mb-6" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-6 bg-zinc-800 rounded" />
          ))}
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
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
        <p className="text-zinc-500 text-sm">Sin datos de servidores</p>
      </div>
    );
  }

  return (
    <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
      <h3 className="text-white font-semibold text-sm mb-4">Almacenamiento por Servidor</h3>
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
  );
};

export default ServerStorageChart;
