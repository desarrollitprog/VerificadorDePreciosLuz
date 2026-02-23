
import { ServerMonitorHeader } from './ServerMonitorHeader';
import { ServerCard, ServerData } from './ServerCard';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const mockServers: ServerData[] = [
  {
    id: '1',
    name: 'Server-Beta-04',
    ip: '192.168.1.14',
    status: 'critical',
    heartbeat: '5m ago',
    lastSeen: 'Oct 24, 14:32:01 UTC',
    devices: 142,
    cpuLoad: 98,
    storage: 88
  },
  {
    id: '2',
    name: 'Server-Alpha-01',
    ip: '192.168.1.10',
    status: 'offline',
    heartbeat: '2m ago',
    lastSeen: 'Oct 24, 14:35:12 UTC',
    devices: 0,
    cpuLoad: 0,
    storage: 45
  },
  {
    id: '3',
    name: 'Server-Gamma-09',
    ip: '192.168.1.22',
    status: 'critical',
    heartbeat: '8m ago',
    lastSeen: 'Oct 24, 14:29:45 UTC',
    devices: 89,
    cpuLoad: 95,
    storage: 92
  },
  {
    id: '4',
    name: 'Server-Delta-02',
    ip: '192.168.1.11',
    status: 'offline',
    heartbeat: '12m ago',
    lastSeen: 'Oct 24, 14:25:30 UTC',
    devices: 0,
    cpuLoad: 0,
    storage: 30
  },
  {
    id: '5',
    name: 'Server-Epsilon-05',
    ip: '192.168.1.15',
    status: 'critical',
    heartbeat: '15m ago',
    lastSeen: 'Oct 24, 14:22:15 UTC',
    devices: 210,
    cpuLoad: 99,
    storage: 95
  },
  {
    id: '6',
    name: 'Server-Zeta-08',
    ip: '192.168.1.25',
    status: 'offline',
    heartbeat: '22m ago',
    lastSeen: 'Oct 24, 14:15:05 UTC',
    devices: 0,
    cpuLoad: 0,
    storage: 60
  },
  {
    id: '7',
    name: 'Server-Iota-33',
    ip: '192.168.1.55',
    status: 'offline',
    heartbeat: '40m ago',
    lastSeen: 'Oct 24, 13:57:05 UTC',
    devices: 0,
    cpuLoad: 0,
    storage: 12
  }
];

export function ServerDashboard() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-50 dark:bg-[#0d1117]">
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <ServerMonitorHeader />
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {mockServers.map(server => (
              <ServerCard key={server.id} data={server} />
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-8 flex justify-center pb-8">
            <nav className="flex items-center gap-1">
              <a className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#161b22] text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-[#21262d] transition-colors" href="#">
                <ChevronLeft size={20} />
              </a>
              <a className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-500/30" href="#">1</a>
              <a className="flex h-10 w-10 items-center justify-center rounded-lg border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-[#21262d] transition-colors" href="#">2</a>
              <a className="flex h-10 w-10 items-center justify-center rounded-lg border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-[#21262d] transition-colors" href="#">3</a>
              <span className="flex h-10 w-10 items-center justify-center text-slate-400">...</span>
              <a className="flex h-10 w-10 items-center justify-center rounded-lg border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-[#21262d] transition-colors" href="#">12</a>
              <a className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#161b22] text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-[#21262d] transition-colors" href="#">
                <ChevronRight size={20} />
              </a>
            </nav>
          </div>
        </div>
      </main>
    </div>
  );
}
