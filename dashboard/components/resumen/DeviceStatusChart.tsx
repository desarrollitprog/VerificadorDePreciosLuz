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
    <div className="bg-[#27272a] border border-zinc-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-white font-semibold">{entry.name}</p>
      <p className="text-zinc-300">{entry.value} dispositivos ({(entry.payload.percent * 100).toFixed(1)}%)</p>
    </div>
  );
};

const DeviceStatusChart: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5 animate-pulse">
        <div className="h-4 w-40 bg-zinc-800 rounded mb-6" />
        <div className="flex justify-center">
          <div className="h-48 w-48 rounded-full bg-zinc-800" />
        </div>
      </div>
    );
  }

  const total = data.total || 1;
  const pieData = [
    { name: 'Online', value: data.online, percent: data.online / total },
    { name: 'Offline', value: data.offline, percent: data.offline / total },
  ];

  const COLORS = ['#22c55e', '#ef4444'];
  const centerValue = data.online;
  const centerLabel = 'Online';

  return (
    <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5">
      <h3 className="text-white font-semibold text-sm mb-4">Estado de Dispositivos</h3>
      <div className="flex items-center justify-center">
        <div className="relative">
          <ResponsiveContainer width={220} height={220}>
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
            <span className="text-2xl font-bold text-white">{data.total}</span>
            <span className="text-xs text-zinc-400">Total</span>
          </div>
        </div>
        <div className="ml-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-green-500" />
            <span className="text-sm text-zinc-300">{data.online} online</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-red-500" />
            <span className="text-sm text-zinc-300">{data.offline} offline</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeviceStatusChart;
