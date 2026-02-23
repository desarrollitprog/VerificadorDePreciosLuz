
import { RefreshCw, Plus, Search } from 'lucide-react';

export function ServerMonitorHeader() {
  return (
    <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161b22] px-6 py-4 sticky top-0 z-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Server Status Monitor</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Real-time monitoring and heartbeat analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-500/20 transition-colors cursor-pointer">
            <RefreshCw size={18} />
            Refresh
          </button>
          <button className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700 transition-colors shadow-sm shadow-blue-500/20 cursor-pointer">
            <Plus size={18} />
            Add Server
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2">
          <button aria-label="Show all servers" className="flex items-center gap-2 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#21262d] px-4 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-[#30363d] transition-colors cursor-pointer">
            All
            <span className="ml-1 rounded bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-500 dark:text-slate-400">124</span>
          </button>
          <button aria-label="Filter by critical status" className="flex items-center gap-2 rounded-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/30 px-4 py-1.5 text-xs font-bold text-red-700 dark:text-red-400 cursor-pointer">
            Critical
            <span className="ml-1 rounded bg-red-100 dark:bg-red-900/40 px-1.5 py-0.5 text-[10px]">3</span>
          </button>
          <button aria-label="Filter by offline status" className="flex items-center gap-2 rounded-full bg-slate-100 dark:bg-slate-700/30 border border-slate-300 dark:border-slate-600 px-4 py-1.5 text-xs font-bold text-slate-700 dark:text-slate-300 cursor-pointer">
            Offline
            <span className="ml-1 rounded bg-slate-200 dark:bg-slate-600 px-1.5 py-0.5 text-[10px]">4</span>
          </button>
          <button aria-label="Filter by healthy status" className="flex items-center gap-2 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#21262d] px-4 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-[#30363d] transition-colors opacity-60 cursor-pointer">
            Healthy
            <span className="ml-1 rounded bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-500 dark:text-slate-400">117</span>
          </button>
        </div>
        
        <div className="relative w-full max-w-xs">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
            <Search size={18} />
          </span>
          <input 
            className="w-full rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#21262d] py-1.5 pl-9 pr-4 text-xs text-slate-700 dark:text-slate-200 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
            placeholder="Search server name..." 
            type="text" 
          />
        </div>
      </div>
    </header>
  );
}
// Exportación por defecto opcional
// export default ServerMonitorHeader;
