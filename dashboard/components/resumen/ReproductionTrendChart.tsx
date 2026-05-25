import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { TendenciaDiaria } from '../../services/resumenService';

interface Props {
  data: TendenciaDiaria[];
  loading?: boolean;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-[#1c2936] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-900 dark:text-white font-semibold mb-1">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} className="text-slate-500 dark:text-slate-400" style={{ color: p.color }}>
          {p.name}: {p.value.toLocaleString()}
        </p>
      ))}
    </div>
  );
};

const ReproductionTrendChart: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="h-1 bg-violet-500" />
        <div className="p-5 animate-pulse">
          <div className="h-4 w-64 bg-slate-200 dark:bg-[#253247] rounded mb-6" />
          <div className="h-48 bg-slate-200 dark:bg-[#253247] rounded" />
        </div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="h-1 bg-violet-500" />
        <div className="p-5">
          <p className="text-slate-500 dark:text-slate-400 text-sm">Sin datos de reproducciones</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="h-1 bg-violet-500" />
      <div className="p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-4">
          Tendencia de reproducciones (últimos 14 días)
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="fecha"
              tick={{ fill: '#71717a', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: string) => {
                const d = new Date(v + 'T00:00:00');
                return d.toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit' });
              }}
            />
            <YAxis tick={{ fill: '#71717a', fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              formatter={(value: string) => {
                if (value === 'tv_estimadas') return 'TV (reproducidas)';
                if (value === 'ver_validas') return 'VER (válidas >50%)';
                return value;
              }}
            />
            <Line
              type="monotone"
              dataKey="tv_estimadas"
              stroke="#94a3b8"
              strokeWidth={2}
              dot={false}
              name="tv_estimadas"
            />
            <Line
              type="monotone"
              dataKey="ver_validas"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="ver_validas"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ReproductionTrendChart;
