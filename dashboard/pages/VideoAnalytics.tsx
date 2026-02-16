import React from 'react';
import { 
  Play, 
  Eye, 
  CheckCircle2, 
  Hand, 
  Timer, 
  ArrowUpRight, 
  Download,
  Calendar,
  Building2,
  Store,
  Plane
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceDot
} from 'recharts';

const viewsData = [
  { time: '00:00', views: 50 },
  { time: '04:00', views: 200 },
  { time: '08:00', views: 400 },
  { time: '12:00', views: 845 },
  { time: '16:00', views: 600 },
  { time: '20:00', views: 750 },
  { time: '23:59', views: 300 },
];

const VideoAnalytics: React.FC = () => {
  return (
    <div class="space-y-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Estadísticas Detalladas de Video</h1>
          <p class="text-gray-400 text-sm mt-1">Análisis profundo de rendimiento y retención de audiencia.</p>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex bg-surfaceHighlight rounded-lg border border-gray-700 p-0.5">
            <button class="px-3 py-1.5 text-xs font-medium bg-primary text-white rounded shadow-sm">Hoy</button>
            <button class="px-3 py-1.5 text-xs font-medium text-gray-400 hover:text-white transition-colors">7D</button>
            <button class="px-3 py-1.5 text-xs font-medium text-gray-400 hover:text-white transition-colors">30D</button>
          </div>
          <button class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white bg-surface hover:bg-surfaceHighlight border border-gray-700 rounded-lg transition-colors">
            <Download className="w-4 h-4" />
            Exportar
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Col: Video Info & Quick Actions */}
        <div class="lg:col-span-4 xl:col-span-3 space-y-6">
          <div class="bg-surface rounded-xl border border-gray-800 overflow-hidden shadow-lg">
            <div class="relative aspect-video bg-black group cursor-pointer border-b border-gray-800">
               <img src="https://picsum.photos/seed/analytics/600/338" alt="Video Thumbnail" class="w-full h-full object-cover opacity-80" />
               <div class="absolute inset-0 flex items-center justify-center">
                  <div class="w-12 h-12 bg-white/10 backdrop-blur-md rounded-full flex items-center justify-center border border-white/20 group-hover:bg-primary transition-colors">
                    <Play className="w-6 h-6 text-white ml-0.5" />
                  </div>
               </div>
               <div class="absolute bottom-2 right-2 px-1.5 py-0.5 bg-black/80 rounded text-[10px] font-mono text-white border border-white/10">00:45</div>
               <div class="absolute bottom-0 left-0 right-0 h-1 bg-gray-800">
                  <div class="h-full w-1/3 bg-primary"></div>
               </div>
            </div>
            <div class="p-5">
              <div class="flex justify-between items-start mb-4">
                <div>
                   <h2 class="text-base font-semibold text-white mb-0.5">Promo_Principal_v2.mp4</h2>
                   <p class="text-xs text-gray-500">ID: #AD-88231</p>
                </div>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                   <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span> Activo
                </span>
              </div>
              <div class="grid grid-cols-2 gap-y-4 gap-x-2 py-4 border-t border-gray-800">
                 <div>
                    <span class="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Duración</span>
                    <span class="text-sm font-medium text-gray-200">45 seg</span>
                 </div>
                 <div>
                    <span class="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Resolución</span>
                    <span class="text-sm font-medium text-gray-200">1920 x 1080</span>
                 </div>
                 <div>
                    <span class="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Tamaño</span>
                    <span class="text-sm font-medium text-gray-200">24.5 MB</span>
                 </div>
                 <div>
                    <span class="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Campaña</span>
                    <span class="text-sm font-medium text-gray-200">Verano 2024</span>
                 </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Stats */}
        <div class="lg:col-span-8 xl:col-span-9 space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
             {[
               { icon: Eye, label: 'Vistas Totales', value: '12,450', change: '+12.5%', color: 'blue' },
               { icon: CheckCircle2, label: 'Tasa Completitud', value: '88%', change: '+5.0%', color: 'emerald' },
               { icon: Hand, label: 'Tasa Interrupción', value: '2.4%', change: '-0.5%', color: 'rose' },
               { icon: Timer, label: 'Tiempo Total', value: '145h 30m', change: null, color: 'amber' },
             ].map((stat, i) => (
               <div key={i} class="bg-surface rounded-xl p-5 border border-gray-800 relative overflow-hidden group hover:border-gray-700 transition-colors">
                  <div class="flex justify-between items-start mb-3">
                     <div class={`w-10 h-10 rounded-lg bg-${stat.color}-500/10 flex items-center justify-center text-${stat.color}-500`}>
                        <stat.icon className="w-5 h-5" />
                     </div>
                     {stat.change && (
                       <span class={`flex items-center text-xs font-medium ${stat.change.startsWith('+') ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'} px-1.5 py-0.5 rounded border`}>
                          {stat.change}
                       </span>
                     )}
                     {!stat.change && <span class="text-[10px] font-medium text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded border border-gray-700">Acumulado</span>}
                  </div>
                  <div>
                    <h3 class="text-2xl font-bold text-white mb-1">{stat.value}</h3>
                    <p class="text-xs font-medium text-gray-400 uppercase tracking-wide">{stat.label}</p>
                  </div>
               </div>
             ))}
          </div>

          <div class="bg-surface rounded-xl border border-gray-800 p-6 shadow-sm">
             <div class="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div>
                   <h3 class="text-lg font-bold text-white">Mapa de Calor de Reproducción</h3>
                   <p class="text-sm text-gray-400">Visualización de retención de audiencia.</p>
                </div>
                <div class="flex items-center gap-4 text-xs font-medium text-gray-400">
                   <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-primary"></span> Retención Alta</div>
                   <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-rose-500"></span> Abandono Crítico</div>
                </div>
             </div>
             <div class="relative py-2">
                <div class="h-14 w-full bg-gray-800/50 rounded-lg overflow-hidden flex relative border border-gray-700">
                   {/* Simulated Heatmap Segments */}
                   {[...Array(20)].map((_, i) => {
                      let opacity = 1 - (i * 0.03); 
                      let color = 'bg-primary';
                      if (i > 10) color = 'bg-indigo-500';
                      if (i > 15) color = 'bg-rose-500';
                      return <div key={i} class={`h-full flex-1 ${color}`} style={{ opacity }} title={`${100 - (i*2)}% retention`} />
                   })}
                   {/* Hover marker simulation */}
                   <div class="absolute top-0 bottom-0 w-px bg-white/50 left-[60%] z-20"></div>
                   <div class="absolute -top-10 left-[60%] -translate-x-1/2 bg-gray-900 text-white text-xs px-2.5 py-1.5 rounded shadow-xl border border-gray-700 z-30 whitespace-nowrap">
                      00:27 <span class="text-gray-500">|</span> 72% retención
                   </div>
                </div>
                <div class="flex justify-between mt-2 text-[10px] font-mono text-gray-500 px-1">
                   <span>00:00</span>
                   <span>00:15</span>
                   <span>00:30</span>
                   <span>00:45</span>
                </div>
             </div>
          </div>

          <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
             <div class="bg-surface rounded-xl border border-gray-800 p-6 shadow-sm h-96 flex flex-col relative overflow-hidden">
                <div class="flex items-center justify-between mb-2 relative z-10">
                   <div>
                      <h3 class="text-lg font-bold text-white">Vistas en el Tiempo</h3>
                      <p class="text-xs text-gray-400">Rendimiento últimos 7 días</p>
                   </div>
                   <div class="flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                      <span class="text-xs font-medium text-primary">Live Data</span>
                   </div>
                </div>
                <div class="flex-1 w-full h-full relative mt-4">
                   <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={viewsData}>
                         <defs>
                            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                               <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                               <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                         </defs>
                         <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                         <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                         <Area type="monotone" dataKey="views" stroke="#3b82f6" strokeWidth={3} fill="url(#chartGradient)" />
                         <ReferenceDot x="12:00" y={845} r={4} fill="#fff" stroke="#3b82f6" strokeWidth={2} />
                      </AreaChart>
                   </ResponsiveContainer>
                   <div class="absolute top-[20%] right-[15%] bg-gray-800/90 backdrop-blur border border-gray-600 text-white text-xs p-2.5 rounded-lg shadow-xl pointer-events-none">
                      <div class="flex items-center gap-2 mb-1">
                         <Calendar className="w-3 h-3 text-gray-400" />
                         <span class="font-medium text-gray-300">12 Oct, 12:00</span>
                      </div>
                      <div class="text-lg font-bold">845 <span class="text-xs font-normal text-gray-400">vistas</span></div>
                   </div>
                </div>
             </div>

             <div class="bg-surface rounded-xl border border-gray-800 p-6 shadow-sm h-96 flex flex-col">
                <div class="flex items-center justify-between mb-6">
                   <h3 class="text-lg font-bold text-white">Rendimiento por Sede</h3>
                   <button class="text-xs text-primary hover:text-blue-400 font-medium">Ver Informe Completo</button>
                </div>
                <div class="flex-1 space-y-6 overflow-y-auto pr-2 custom-scrollbar">
                   {[
                     { name: 'Sede Central - Lobby', icon: Building2, color: 'blue', value: 4230, percent: '85%' },
                     { name: 'Sucursal Norte', icon: Store, color: 'orange', value: 3105, percent: '62%' },
                     { name: 'Plaza Comercial Oeste', icon: Store, color: 'emerald', value: 2840, percent: '58%' },
                     { name: 'Sucursal Aeropuerto', icon: Plane, color: 'rose', value: 1950, percent: '40%' },
                   ].map((loc, i) => (
                      <div key={i} class="group">
                         <div class="flex justify-between items-center text-sm mb-2">
                            <div class="flex items-center gap-3">
                               <div class="w-8 h-8 rounded bg-gray-800 flex items-center justify-center text-gray-400">
                                  <loc.icon className="w-4 h-4" />
                               </div>
                               <div>
                                  <div class="font-medium text-gray-200">{loc.name}</div>
                               </div>
                            </div>
                            <span class="font-mono text-white font-bold">{loc.value.toLocaleString()}</span>
                         </div>
                         <div class="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden ml-11 w-[calc(100%-2.75rem)]">
                            <div class={`h-full bg-${loc.color}-500 rounded-full group-hover:bg-${loc.color}-400 transition-colors`} style={{ width: loc.percent }}></div>
                         </div>
                      </div>
                   ))}
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoAnalytics;