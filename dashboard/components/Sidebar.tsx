import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Library, 
  Monitor, 
  Calendar, 
  BarChart2, 
  Settings, 
  LogOut,
  Layers,
  Server
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const navItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: Library, label: 'Media Library', path: '/library' },
    { icon: Monitor, label: 'Dispositivos', path: '/devices' },
    { icon: Calendar, label: 'Programación', path: '/schedules' },
    { icon: BarChart2, label: 'Analíticas', path: '/analytics' },
  ];

  const systemItems = [
    { icon: Server, label: 'Servidores', path: '/servers' },
    { icon: Settings, label: 'Configuración', path: '/settings' },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-gray-800 flex flex-col h-screen fixed left-0 top-0 z-50">
      <div class="h-16 flex items-center px-6 border-b border-gray-800">
        <div class="flex items-center gap-3">
          <div class="bg-gradient-to-br from-blue-600 to-cyan-500 p-1.5 rounded-lg">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-xl text-white tracking-tight">PConnect</span>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-1">
        <div class="px-3 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Menu Principal
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary/10 text-blue-400 border-l-2 border-primary'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}

        <div class="mt-8 px-3 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Sistema
        </div>
        {systemItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary/10 text-blue-400 border-l-2 border-primary'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div class="p-4 border-t border-gray-800">
        <div class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer">
          <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-pink-500" />
          <div class="flex-1 overflow-hidden">
            <p class="text-sm font-medium text-white truncate">Admin Global</p>
            <p class="text-xs text-gray-500 truncate">Sede Central</p>
          </div>
          <LogOut className="w-4 h-4 text-gray-400" />
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;