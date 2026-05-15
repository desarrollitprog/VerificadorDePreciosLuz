import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { HistorialSubida } from '../../services/resumenService';

interface Props {
  data: HistorialSubida[];
  loading?: boolean;
}

function formatFecha(fecha: string): string {
  const d = new Date(fecha + 'T00:00:00');
  return d.toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit' });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="bg-[#27272a] border border-zinc-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-zinc-400">{row.fechaCompleta}</p>
      <p className="text-cyan-400 font-semibold">{row.cantidad} subidas</p>
    </div>
  );
};

const BannersTimeline: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5 animate-pulse">
        <div className="h-4 w-40 bg-zinc-800 rounded mb-6" />
        <div className="h-48 bg-zinc-800 rounded" />
      </div>
    );
  }

  const chartData = data.map((h) => {
    const d = new Date(h.fecha + 'T00:00:00');
    return {
      fecha: formatFecha(h.fecha),
      fechaCompleta: d.toLocaleDateString('es-VE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
      cantidad: h.cantidad,
    };
  });

  if (chartData.length === 0) {
    return (
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
        <h3 className="text-white font-semibold text-sm mb-4">Subidas de Banners (30 días)</h3>
        <p className="text-zinc-500 text-sm">Sin datos de subidas</p>
      </div>
    );
  }

  return (
    <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
      <h3 className="text-white font-semibold text-sm mb-4">Subidas de Banners (30 días)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="bannerGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
          <XAxis dataKey="fecha" tick={{ fill: '#71717a', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#71717a', fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#27272a' }} />
          <Area type="monotone" dataKey="cantidad" stroke="#22d3ee" strokeWidth={2} fill="url(#bannerGradient)" dot={false} activeDot={{ r: 4, fill: '#22d3ee' }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default BannersTimeline;
