import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LogOut, X, Users, Server, Calendar, History, LayoutGrid, LayoutDashboard } from 'lucide-react';
import { getUserRole, getUserName } from '../services/tokenUtils';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onLogout: () => void;
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, adminOnly: false },
  { path: '/videos', label: 'Mis Videos', icon: LayoutGrid, adminOnly: false },
  { path: '/calendario', label: 'Calendario', icon: Calendar, adminOnly: false },
  { path: '/servidores', label: 'Servidores', icon: Server, adminOnly: true },
  { path: '/auditoria', label: 'Auditoría', icon: History, adminOnly: true },
  { path: '/usuarios', label: 'Gestión de Usuarios', icon: Users, adminOnly: true },
];

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, onLogout }) => {
  const [role, setRole] = useState<'ADMIN' | 'CLIENTE' | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setRole(getUserRole());
    setUserName(getUserName());
  }, []);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-40
        w-64 flex flex-col bg-[#111a22] border-r border-slate-800/50
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}
    >
      <div className="relative p-6 pr-14">
        <div className="flex items-center gap-3">
          <div className="bg-primary/20 flex items-center justify-center rounded-lg h-10 w-10 text-primary">
            <LayoutGrid size={24} />
          </div>
          <div className="flex flex-col">
            <h1 className="text-white text-lg font-bold leading-tight">Administrador de Videos</h1>
            <p className="text-slate-400 text-xs font-medium">v1.2.4</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="absolute top-4 right-3 h-9 w-9 rounded-md flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Cerrar menú"
        >
          <X size={20} />
        </button>
      </div>

      <nav className="flex-1 px-4 flex flex-col gap-2 overflow-y-auto mt-2">
        {navItems.map((item) => {
          if (item.adminOnly && role !== 'ADMIN') return null;
          const active = isActive(item.path);
          const Icon = item.icon;
          return (
            <button
              key={item.path}
              onClick={() => { navigate(item.path); onClose(); }}
              title={item.label}
              className={`group relative flex items-center gap-3 px-3 justify-start py-3 rounded-lg transition-colors w-full text-left
                ${active
                  ? 'text-primary font-semibold'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white font-medium'
                }`}
            >
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r-full"></span>
              )}
              <Icon size={20} className={active ? 'text-primary' : 'text-slate-500 group-hover:text-white'} />
              <span className="text-sm">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800/30 mt-auto">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800/50 transition-colors cursor-pointer group">
          <div className="h-10 w-10 flex items-center justify-center rounded-full bg-slate-800 border border-slate-700 shadow-sm">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </div>
          <div className="flex flex-col flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate group-hover:text-primary transition-colors">{'Usuario'}</p>
            <span className={`inline-block text-xs font-semibold rounded px-2 py-0.5 ${role === 'ADMIN' ? 'bg-red-700 text-white' : role === 'CLIENTE' ? 'bg-blue-700 text-white' : 'bg-slate-600 text-white'}`}>{userName || 'Sin nombre'}</span>
          </div>
          <button onClick={onLogout} className="ml-3 text-slate-400 hover:text-red-400 transition-colors p-1 rounded-md hover:bg-slate-700/50">
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
