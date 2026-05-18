import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface Props {
  data: { total: number; online: number; offline: number };
  loading?: boolean;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div className="bg-white dark:bg-[#1c2936] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-900 dark:text-white font-semibold">{entry.name}</p>
      <p className="text-slate-500 dark:text-slate-400">{entry.value} dispositivos ({(entry.payload.percent * 100).toFixed(1)}%)</p>
    </div>
  );
};

const DeviceStatusChart: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 bg-slate-200 dark:bg-[#253247]" />
        <div className="p-5 animate-pulse">
          <div className="h-4 w-40 bg-slate-200 dark:bg-[#253247] rounded mb-6" />
          <div className="flex justify-center">
            <div className="h-48 w-48 rounded-full bg-slate-200 dark:bg-[#253247]" />
          </div>
        </div>
      </div>
    );
  }

  const total = data.total || 1;
  const pieData = [
    { name: 'En línea', value: data.online, percent: data.online / total },
    { name: 'Desconectado', value: data.offline, percent: data.offline / total },
  ];

  const COLORS = ['#22c55e', '#ef4444'];

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 overflow-hidden relative group">
      <div className="h-1 w-full bg-emerald-500" />
      <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-emerald-50/30 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-emerald-500/5 pointer-events-none" />
      <div className="relative z-10 p-5">
        <h3 className="text-slate-900 dark:text-white font-semibold text-sm mb-4">Estado de Dispositivos</h3>
        <div className="flex items-center justify-center">
          <div className="relative min-w-[220px]">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={95}
                  dataKey="value"
                  stroke="none"
                >
                  {pieData.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold text-slate-900 dark:text-white">{data.total}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">Total</span>
            </div>
          </div>
          <div className="ml-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-green-500" />
              <span className="text-sm text-slate-600 dark:text-slate-300">{data.online} online</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-red-500" />
              <span className="text-sm text-slate-600 dark:text-slate-300">{data.offline} offline</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeviceStatusChart;
