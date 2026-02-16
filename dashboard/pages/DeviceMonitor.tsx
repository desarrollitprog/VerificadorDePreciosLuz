import React from 'react';
import { 
  Wifi, 
  WifiOff, 
  Battery, 
  BatteryWarning, 
  MoreVertical, 
  RefreshCw, 
  Power,
  Search,
  MapPin,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react';
import { Device } from '../types';

const mockDevices: Device[] = [
  {
    id: '1',
    name: 'Tablet-Recepción-01',
    location: 'Sede Norte - Principal',
    ip: '192.168.1.45',
    status: 'online',
    battery: 98,
    wifiSignal: -42,
    currentContent: 'Promo_Verano_2024.mp4',
    lastSync: 'Now',
    thumbnail: 'https://picsum.photos/seed/dev1/400/225'
  },
  {
    id: '2',
    name: 'Tablet-Cafetería-03',
    location: 'Sede Norte - Principal',
    ip: '192.168.1.48',
    status: 'warning',
    battery: 15,
    wifiSignal: -58,
    currentContent: 'Menu_Cafeteria_V2.mp4',
    lastSync: '5m ago',
    thumbnail: 'https://picsum.photos/seed/dev2/400/225'
  },
  {
    id: '3',
    name: 'Tablet-Pasillo-Norte',
    location: 'Sede Norte - Principal',
    ip: '192.168.1.12',
    status: 'offline',
    battery: 0,
    wifiSignal: 0,
    currentContent: 'Unknown',
    lastSync: '45m ago',
    thumbnail: 'https://picsum.photos/seed/dev3/400/225'
  },
  {
    id: '4',
    name: 'Tablet-Tienda-02',
    location: 'Sede Norte - Principal',
    ip: '192.168.1.50',
    status: 'online',
    battery: 100,
    wifiSignal: -38,
    currentContent: 'Oferta_Zapatos.mp4',
    lastSync: 'Now',
    thumbnail: 'https://picsum.photos/seed/dev4/400/225'
  },
  {
    id: '5',
    name: 'Tablet-SalaJuntas-01',
    location: 'Sede Norte - Principal',
    ip: '192.168.1.62',
    status: 'online',
    battery: 77,
    wifiSignal: -35,
    currentContent: 'Corporativo_2024.mp4',
    lastSync: 'Now',
    thumbnail: 'https://picsum.photos/seed/dev5/400/225'
  }
];

const DeviceMonitor: React.FC = () => {
  return (
    <div class="flex h-[calc(100vh-4rem)]">
      {/* Main Grid */}
      <div class="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-gray-700">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-4">
             <div class="relative group">
                <div class="flex items-center gap-2 cursor-pointer bg-surface border border-gray-700 rounded-lg px-3 py-2">
                   <MapPin className="w-5 h-5 text-gray-400" />
                   <select class="bg-transparent font-semibold text-white focus:outline-none cursor-pointer appearance-none pr-8">
                      <option>Sede Norte - Principal</option>
                      <option>Sede Sur - Almacén</option>
                      <option>Sede Este - Oficinas</option>
                   </select>
                </div>
             </div>
             <div class="hidden md:flex gap-2">
                <span class="px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 text-sm font-medium border border-emerald-500/20">12 Online</span>
                <span class="px-3 py-1.5 rounded-full bg-red-500/10 text-red-400 text-sm font-medium border border-red-500/20">2 Offline</span>
             </div>
          </div>
          
          <div class="flex items-center gap-4">
            <div class="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 w-4 h-4" />
              <input 
                type="text" 
                placeholder="Buscar dispositivos..." 
                class="bg-surface border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-primary w-64"
              />
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
          {mockDevices.map((device) => (
            <div key={device.id} class={`group bg-surface rounded-xl border ${device.status === 'offline' ? 'border-red-900/50' : device.status === 'warning' ? 'border-amber-900/50' : 'border-gray-800'} shadow-sm hover:shadow-lg transition-all flex flex-col overflow-hidden`}>
              <div class="relative h-48 bg-gray-900">
                <img 
                  src={device.thumbnail} 
                  alt={device.name} 
                  class={`w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 ${device.status === 'offline' ? 'opacity-40 grayscale' : 'opacity-90'}`} 
                />
                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent"></div>
                
                {/* Status Badge */}
                <div class="absolute top-3 left-3">
                  <span class={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium backdrop-blur-md border ${
                    device.status === 'online' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                    device.status === 'warning' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                    'bg-red-500/20 text-red-400 border-red-500/30'
                  }`}>
                    <span class={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                      device.status === 'online' ? 'bg-emerald-400 animate-pulse' :
                      device.status === 'warning' ? 'bg-amber-400' :
                      'bg-red-400'
                    }`}></span>
                    {device.status.charAt(0).toUpperCase() + device.status.slice(1)}
                  </span>
                </div>

                {/* Tech Specs */}
                {device.status !== 'offline' && (
                  <div class="absolute top-3 right-3 flex gap-2 text-white/90 text-xs font-medium backdrop-blur-sm bg-black/30 p-1 rounded-lg">
                    <div class={`flex items-center px-1 ${device.battery < 20 ? 'text-amber-400' : ''}`}>
                      {device.battery < 20 ? <BatteryWarning className="w-3 h-3 mr-1" /> : <Battery className="w-3 h-3 mr-1" />}
                      {device.battery}%
                    </div>
                    <div class="flex items-center px-1 border-l border-white/20">
                      <Wifi className="w-3 h-3 mr-1" /> {device.wifiSignal}dB
                    </div>
                  </div>
                )}

                {/* Content Info */}
                <div class="absolute bottom-0 left-0 right-0 p-3">
                   {device.status === 'offline' ? (
                      <div class="flex flex-col items-center justify-center text-red-400 pb-8">
                         <WifiOff className="w-8 h-8 mb-2 opacity-50" />
                      </div>
                   ) : (
                      <>
                        <p class="text-xs text-gray-300 mb-1 truncate">Playing: {device.currentContent}</p>
                        <div class="w-full bg-white/20 rounded-full h-1">
                          <div class="bg-primary h-1 rounded-full" style={{ width: Math.random() * 100 + '%' }}></div>
                        </div>
                      </>
                   )}
                </div>
              </div>

              <div class="p-4 flex flex-col flex-1">
                 <div class="flex justify-between items-start mb-3">
                    <div>
                       <h3 class="text-sm font-semibold text-white">{device.name}</h3>
                       <p class={`text-xs mt-0.5 ${device.status === 'offline' ? 'text-red-400' : 'text-gray-500'}`}>
                          {device.status === 'offline' ? 'No connection since 45m' : `IP: ${device.ip}`}
                       </p>
                    </div>
                    <button class="text-gray-400 hover:text-white"><MoreVertical className="w-4 h-4" /></button>
                 </div>
                 
                 <div class="mt-auto grid grid-cols-2 gap-2 pt-2 border-t border-gray-800">
                    {device.status === 'offline' ? (
                       <button class="col-span-2 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-white bg-red-600/90 hover:bg-red-600 rounded-lg transition-colors">
                          <Power className="w-3 h-3" /> Force Remote Reboot
                       </button>
                    ) : (
                       <>
                          <button class="flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                             <RefreshCw className="w-3 h-3" /> Reboot
                          </button>
                          <button class="flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm shadow-primary/20">
                             <RefreshCw className="w-3 h-3" /> Sync
                          </button>
                       </>
                    )}
                 </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Alerts Sidebar */}
      <aside class="w-80 bg-surface border-l border-gray-800 hidden xl:flex flex-col z-20">
         <div class="h-16 flex items-center justify-between px-6 border-b border-gray-800">
            <h2 class="text-lg font-semibold text-white">Alertas Recientes</h2>
            <button class="text-xs font-medium text-primary hover:underline">Ver todo</button>
         </div>
         <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <div class="flex gap-3 items-start p-3 rounded-lg bg-red-500/10 border border-red-500/20">
               <WifiOff className="w-5 h-5 text-red-500 mt-0.5" />
               <div>
                  <h4 class="text-sm font-semibold text-gray-200">Pérdida de Conexión</h4>
                  <p class="text-xs text-gray-400 mt-1">Sede Este: Tablet-Pasillo-Norte perdió conexión con el servidor.</p>
                  <p class="text-[10px] text-gray-500 mt-2 font-mono">Hace 45 min</p>
               </div>
            </div>
            <div class="flex gap-3 items-start p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
               <BatteryWarning className="w-5 h-5 text-amber-500 mt-0.5" />
               <div>
                  <h4 class="text-sm font-semibold text-gray-200">Batería Crítica</h4>
                  <p class="text-xs text-gray-400 mt-1">Sede Norte: Tablet-Cafetería-03 está al 15% de batería.</p>
                  <p class="text-[10px] text-gray-500 mt-2 font-mono">Hace 1 hora</p>
               </div>
            </div>
            <div class="flex gap-3 items-start p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
               <RefreshCw className="w-5 h-5 text-blue-500 mt-0.5" />
               <div>
                  <h4 class="text-sm font-semibold text-gray-200">Actualización Exitosa</h4>
                  <p class="text-xs text-gray-400 mt-1">Sede Sur: 4 dispositivos actualizaron contenido.</p>
                  <p class="text-[10px] text-gray-500 mt-2 font-mono">Hace 2 horas</p>
               </div>
            </div>
            <div class="flex gap-3 items-start p-3 rounded-lg bg-gray-800 border border-gray-700">
               <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5" />
               <div>
                  <h4 class="text-sm font-semibold text-gray-200">Reinicio Programado</h4>
                  <p class="text-xs text-gray-400 mt-1">Sede Norte: Reinicio diario completado.</p>
                  <p class="text-[10px] text-gray-500 mt-2 font-mono">Ayer 11:00 PM</p>
               </div>
            </div>
         </div>
      </aside>
    </div>
  );
};

export default DeviceMonitor;