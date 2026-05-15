import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { HistorialSubida } from '../../services/resumenService';
import { useThemeStore } from '../../stores/themeStore';

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
    <div className="bg-white dark:bg-[#1c2936] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-500 dark:text-slate-400">{row.fechaCompleta}</p>
      <p className="text-cyan-600 dark:text-cyan-400 font-semibold">{row.cantidad} subidas</p>
    </div>
  );
};

const BannersTimeline: React.FC<Props> = ({ data, loading }) => {
  const isDark = useThemeStore((s) => s.isDark);
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const cursorColor = isDark ? '#334155' : '#f1f5f9';
  const tickColor = isDark ? '#71717a' : '#94a3b8';

  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 bg-slate-200 dark:bg-[#253247]" />
        <div className="p-5 animate-pulse">
          <div className="h-4 w-40 bg-slate-200 dark:bg-[#253247] rounded mb-6" />
          <div className="h-48 bg-slate-200 dark:bg-[#253247] rounded" />
        </div>
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

  const totalSubidas = data.reduce((sum, h) => sum + h.cantidad, 0);

  if (chartData.length === 0) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 w-full bg-cyan-500" />
        <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-cyan-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-cyan-500/5 pointer-events-none" />
        <div className="relative z-10 p-5">
          <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-4">Subidas de Banners (30 días)</h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin datos de subidas</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 overflow-hidden relative group">
      <div className="h-1 w-full bg-cyan-500" />
      <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-cyan-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-cyan-500/5 pointer-events-none" />
      <div className="relative z-10 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-slate-900 dark:text-white font-semibold text-sm">Subidas de Banners (30 días)</h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">{totalSubidas} subidas</span>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="bannerGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
            <XAxis dataKey="fecha" tick={{ fill: tickColor, fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: tickColor, fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: cursorColor }} />
            <Area type="monotone" dataKey="cantidad" stroke="#22d3ee" strokeWidth={2} fill="url(#bannerGradient)" dot={false} activeDot={{ r: 4, fill: '#22d3ee' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default BannersTimeline;
