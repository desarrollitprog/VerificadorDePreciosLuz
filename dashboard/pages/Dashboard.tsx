import React from 'react';
import { 
  Monitor, 
  Megaphone, 
  Clock, 
  Database, 
  MoreHorizontal, 
  TrendingUp, 
  Activity, 
  Server, 
  WifiOff, 
  RefreshCw 
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

const data = [
  { time: '00:00', views: 8000 },
  { time: '04:00', views: 12000 },
  { time: '08:00', views: 10000 },
  { time: '12:00', views: 32000 },
  { time: '16:00', views: 28000 },
  { time: '20:00', views: 42500 },
  { time: '23:59', views: 35000 },
];

const Dashboard: React.FC = () => {
  return (
    <div class="space-y-6">
      {/* Header with Date Filter */}
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-white">Resumen de Operaciones</h2>
          <p class="text-sm text-gray-400">Estado en tiempo real de la red global.</p>
        </div>
        <div class="bg-surfaceHighlight p-1 rounded-lg flex items-center border border-gray-700">
          <button class="px-3 py-1 text-xs font-medium bg-primary text-white rounded shadow-sm">24h</button>
          <button class="px-3 py-1 text-xs font-medium text-gray-400 hover:text-white transition-colors">7d</button>
          <button class="px-3 py-1 text-xs font-medium text-gray-400 hover:text-white transition-colors">30d</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="bg-surface border border-gray-800 rounded-xl p-6 relative overflow-hidden group hover:border-blue-500/30 transition-all">
          <div class="flex justify-between items-start mb-4">
            <div class="p-2 bg-blue-500/10 rounded-lg text-blue-500">
              <Monitor className="w-6 h-6" />
            </div>
            <span class="text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">+4.2%</span>
          </div>
          <div class="relative z-10">
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Total Dispositivos</p>
            <h3 class="text-3xl font-bold text-white mb-2">1,240</h3>
            <div class="w-full bg-gray-800 rounded-full h-1.5 mb-2 overflow-hidden flex">
              <div class="bg-emerald-500 h-full" style={{ width: '96%' }}></div>
              <div class="bg-red-500 h-full" style={{ width: '4%' }}></div>
            </div>
            <div class="flex justify-between text-xs text-gray-400">
               <span>1,198 Online</span>
               <span>42 Offline</span>
            </div>
          </div>
        </div>

        <div class="bg-surface border border-gray-800 rounded-xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all">
          <div class="flex justify-between items-start mb-4">
            <div class="p-2 bg-emerald-500/10 rounded-lg text-emerald-500">
              <Megaphone className="w-6 h-6" />
            </div>
            <span class="text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">+5%</span>
          </div>
          <div class="relative z-10">
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Anuncios Activos</p>
            <h3 class="text-3xl font-bold text-white mb-2">342</h3>
            <p class="text-xs text-gray-400 flex items-center gap-1">
              <RefreshCw className="w-3 h-3" /> Updated 5m ago
            </p>
          </div>
        </div>

        <div class="bg-surface border border-gray-800 rounded-xl p-6 relative overflow-hidden group hover:border-indigo-500/30 transition-all">
          <div class="flex justify-between items-start mb-4">
            <div class="p-2 bg-indigo-500/10 rounded-lg text-indigo-500">
              <Clock className="w-6 h-6" />
            </div>
            <span class="text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">+12%</span>
          </div>
          <div class="relative z-10">
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Tiempo de Juego (Hoy)</p>
            <h3 class="text-3xl font-bold text-white mb-2">12h <span class="text-lg text-gray-500 font-normal">45m</span></h3>
             <p class="text-xs text-gray-400">Promedio por dispositivo</p>
          </div>
        </div>

        <div class="bg-surface border border-gray-800 rounded-xl p-6 relative overflow-hidden group hover:border-amber-500/30 transition-all">
          <div class="flex justify-between items-start mb-4">
            <div class="p-2 bg-amber-500/10 rounded-lg text-amber-500">
              <Database className="w-6 h-6" />
            </div>
            <span class="text-xs font-mono text-gray-400 bg-gray-800 px-2 py-0.5 rounded">1.6TB / 2TB</span>
          </div>
          <div class="relative z-10">
            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Almacenamiento</p>
            <h3 class="text-3xl font-bold text-white mb-2">82%</h3>
            <div class="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
              <div class="bg-amber-500 h-full" style={{ width: '82%' }}></div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <div class="lg:col-span-2 bg-surface border border-gray-800 rounded-xl p-6">
          <div class="flex justify-between items-center mb-6">
            <div>
              <h3 class="text-lg font-bold text-white">Tendencias Globales</h3>
              <p class="text-xs text-gray-400">Reproducciones en las últimas 24 horas</p>
            </div>
            <div class="flex items-center gap-2 text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-1 rounded border border-blue-500/20">
               <Activity className="w-3 h-3 animate-pulse" /> Live Data
            </div>
          </div>
          <div class="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis 
                  dataKey="time" 
                  stroke="#6b7280" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false}
                />
                <YAxis 
                  stroke="#6b7280" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false}
                  tickFormatter={(value) => `${value / 1000}k`}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                  itemStyle={{ color: '#fff' }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="views" 
                  stroke="#2563EB" 
                  strokeWidth={3}
                  fillOpacity={1} 
                  fill="url(#colorViews)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Status */}
        <div class="bg-surface border border-gray-800 rounded-xl p-6 flex flex-col">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-lg font-bold text-white">Estado del Sistema</h3>
            <button class="text-gray-500 hover:text-white transition-colors">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
          
          <div class="flex-1 space-y-4">
            <div class="flex items-center justify-between p-3 rounded-lg bg-gray-900/50 border border-gray-800 group hover:border-emerald-500/30 transition-all cursor-pointer">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded bg-emerald-500/10 text-emerald-500">
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <p class="text-sm font-medium text-white">Sede Norte</p>
                  <p class="text-xs text-gray-500">Main Server</p>
                </div>
              </div>
              <div class="text-right">
                <div class="flex items-center justify-end gap-1.5 mb-0.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span class="text-xs font-bold text-emerald-500">Online</span>
                </div>
                <p class="text-[10px] text-gray-500 font-mono">12ms</p>
              </div>
            </div>

            <div class="flex items-center justify-between p-3 rounded-lg bg-gray-900/50 border border-gray-800 group hover:border-amber-500/30 transition-all cursor-pointer">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded bg-amber-500/10 text-amber-500">
                  <RefreshCw className="w-5 h-5" />
                </div>
                <div>
                  <p class="text-sm font-medium text-white">Sede Sur</p>
                  <p class="text-xs text-gray-500">Backup Node</p>
                </div>
              </div>
              <div class="text-right">
                <div class="flex items-center justify-end gap-1.5 mb-0.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                  <span class="text-xs font-bold text-amber-500">Syncing</span>
                </div>
                <p class="text-[10px] text-gray-500 font-mono">85%</p>
              </div>
            </div>

            <div class="flex items-center justify-between p-3 rounded-lg bg-gray-900/50 border border-gray-800 group hover:border-red-500/30 transition-all cursor-pointer">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded bg-red-500/10 text-red-500">
                  <WifiOff className="w-5 h-5" />
                </div>
                <div>
                  <p class="text-sm font-medium text-white">Sede Oeste</p>
                  <p class="text-xs text-gray-500">Regional CDN</p>
                </div>
              </div>
              <div class="text-right">
                <div class="flex items-center justify-end gap-1.5 mb-0.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                  <span class="text-xs font-bold text-red-500">Error</span>
                </div>
                <p class="text-[10px] text-gray-500 font-mono">Timeout</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top Ads */}
      <div class="bg-surface border border-gray-800 rounded-xl p-6">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-2">
             <h3 class="text-lg font-bold text-white">Top 5 Anuncios Más Reproducidos</h3>
             <span class="bg-blue-500/10 text-blue-500 text-[10px] font-bold px-2 py-0.5 rounded border border-blue-500/20">GLOBAL RANKING</span>
          </div>
          <button class="text-sm text-blue-500 hover:text-white transition-colors">Ver Informe Completo</button>
        </div>
        
        <div class="space-y-5">
           {[
             { rank: 1, name: 'Promo Verano 2024 - Spot Principal', plays: 12450, color: 'bg-blue-600', width: '95%' },
             { rank: 2, name: 'Nueva Colección - Video Loop', plays: 10200, color: 'bg-blue-600/80', width: '82%' },
             { rank: 3, name: 'Oferta Fin de Semana', plays: 8150, color: 'bg-blue-600/60', width: '65%' },
             { rank: 4, name: 'Brand Awareness Clip #4', plays: 6300, color: 'bg-blue-600/40', width: '48%' },
             { rank: 5, name: 'Cierre Tienda - Aviso', plays: 4100, color: 'bg-blue-600/20', width: '35%' },
           ].map((item) => (
             <div key={item.rank} class="relative group">
                <div class="flex justify-between items-center mb-2 relative z-10">
                   <div class="flex items-center gap-4">
                      <div class={`flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${item.rank === 1 ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20' : 'bg-gray-800 text-gray-400 border border-gray-700'}`}>
                        {item.rank}
                      </div>
                      <span class="text-sm font-medium text-white group-hover:text-blue-400 transition-colors">{item.name}</span>
                   </div>
                   <span class="text-sm font-bold text-white font-mono">{item.plays.toLocaleString()} <span class="text-gray-500 text-xs font-sans font-normal">plays</span></span>
                </div>
                <div class="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                   <div class={`h-full rounded-full ${item.color}`} style={{ width: item.width }}></div>
                </div>
             </div>
           ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;