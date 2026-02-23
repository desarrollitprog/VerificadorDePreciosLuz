
import React from 'react';
import { Server, AlertCircle, WifiOff, CloudOff, RotateCcw } from 'lucide-react';

export interface ServerData {
  id: string;
  name: string;
  ip: string;
  status: 'critical' | 'offline' | 'healthy';
  heartbeat: string;
  lastSeen?: string;
  devices: number;
  cpuLoad: number;
  storage: number;
}

interface ServerCardProps {
  data: ServerData;
}

export const ServerCard: React.FC<ServerCardProps> = ({ data }) => {
  const isCritical = data.status === 'critical';
  const isOffline = data.status === 'offline';
  
  return (
    <article 
      className={`
        relative flex flex-col rounded-xl border p-4 shadow-sm transition-all
        ${isCritical 
          ? 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161b22] hover:border-red-500/50 hover:shadow-md' 
          : isOffline 
            ? 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161b22] opacity-80 hover:opacity-100 grayscale hover:grayscale-0'
            : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161b22] hover:shadow-md'
        }
      `}
    >
      {isCritical && (
        <div className="absolute right-4 top-4">
          <span aria-label="Status Indicator: Critical" className="flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
        </div>
      )}

      <div className="mb-4 flex items-start gap-3">
        <div className={`
          flex h-10 w-10 shrink-0 items-center justify-center rounded-lg
          ${isCritical 
            ? 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400' 
            : 'bg-slate-100 dark:bg-[#21262d] text-slate-500'
          }
        `}>
          {isOffline ? <WifiOff size={20} /> : <Server size={20} />}
        </div>
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white leading-tight">{data.name}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">{data.ip}</p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-3 gap-2 text-xs">
        <div className="col-span-1 rounded bg-slate-50 dark:bg-[#21262d] p-2 text-center">
          <span className="block text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">Status</span>
          <span className={`inline-flex items-center gap-1 justify-center rounded font-bold ${isCritical ? 'text-red-700 dark:text-red-400' : 'text-slate-600 dark:text-slate-400'}`}>
            {isOffline ? <CloudOff size={14} /> : isCritical ? <AlertCircle size={14} /> : 'OK'}
          </span>
        </div>
        <div className="col-span-1 rounded bg-slate-50 dark:bg-[#21262d] p-2 text-center group/tooltip relative cursor-help">
          <span className="block text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">Heartbeat</span>
          <span className="text-slate-700 dark:text-slate-200 font-medium whitespace-nowrap">{data.heartbeat}</span>
          {data.lastSeen && (
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden w-max rounded bg-black px-2 py-1 text-[10px] text-white group-hover/tooltip:block z-10 shadow-lg border border-slate-800">
              Last seen: {data.lastSeen}
            </div>
          )}
        </div>
        <div className="col-span-1 rounded bg-slate-50 dark:bg-[#21262d] p-2 text-center">
          <span className="block text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">Devices</span>
          <span className="text-slate-700 dark:text-slate-200 font-medium">{data.devices}</span>
        </div>
      </div>

      <div className={`space-y-3 mb-4 ${isOffline ? 'opacity-50' : ''}`}>
        <div>
          <div className="mb-1 flex justify-between text-[10px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            <span>CPU Load</span>
            <span className={data.cpuLoad > 90 ? 'text-red-500' : ''}>{data.cpuLoad}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-[#30363d]">
            <div 
              className={`h-full rounded-full ${data.cpuLoad > 90 ? 'bg-red-500' : 'bg-slate-400'}`} 
              style={{ width: `${data.cpuLoad}%` }}
            ></div>
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between text-[10px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            <span>Storage</span>
            <span className={data.storage > 90 ? 'text-red-500' : data.storage > 70 ? 'text-yellow-500' : ''}>{data.storage}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-[#30363d]">
            <div 
              className={`h-full rounded-full ${data.storage > 90 ? 'bg-red-500' : data.storage > 70 ? 'bg-yellow-500' : 'bg-green-500'}`} 
              style={{ width: `${data.storage}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="mt-auto pt-3 border-t border-slate-100 dark:border-slate-800">
        <button className="w-full text-xs font-semibold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white transition-colors py-1.5 flex items-center justify-center gap-1.5 rounded hover:bg-slate-50 dark:hover:bg-[#21262d] cursor-pointer">
          <RotateCcw size={14} />
          Reset Connection
        </button>
      </div>
    </article>
  );
}
