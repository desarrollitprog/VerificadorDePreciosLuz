import React, { useEffect, useState } from 'react';
import { LayoutGrid, Video, Settings, LogOut, X, Users, Server, User } from 'lucide-react';
import { Screen } from '../types';
import { getUserRole, getUserName } from '../services/authService';

interface SidebarProps {
  currentScreen: Screen;
  onNavigate: (screen: Screen) => void;
  isOpen: boolean;
  onClose: () => void;
  onLogout: () => void;
}
const Sidebar: React.FC<SidebarProps> = ({ currentScreen, onNavigate, isOpen, onClose, onLogout }) => {
  const [role, setRole] = useState<'ADMIN' | 'CLIENTE' | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  useEffect(() => {
    setRole(getUserRole());
    setUserName(getUserName());
  }, []);

  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-40
        w-56 flex flex-col bg-[#111a22] border-r border-slate-800
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}
    >
      <div className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-primary/20 flex items-center justify-center rounded-lg h-10 w-10 text-primary">
            <LayoutGrid size={24} />
          </div>
          <div className="flex flex-col">
            <h1 className="text-white text-lg font-bold leading-tight">Administrador de Videos</h1>
            <p className="text-slate-400 text-xs font-medium">v1.2.4</p>
          </div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white">
          <X size={24} />
        </button>
      </div>

      <nav className="flex-1 px-4 flex flex-col gap-2 overflow-y-auto mt-2">

        <button 
          onClick={() => { onNavigate('dashboard'); onClose(); }}
          title="Mis Videos"
          className={`flex items-center gap-3 px-3 justify-start py-3 rounded-lg transition-colors w-full text-left
            ${currentScreen === 'dashboard' 
              ? 'bg-primary/20 border border-primary/10 text-primary font-semibold' 
              : 'text-slate-400 hover:bg-slate-800 hover:text-white font-medium'
            }`}
        >
          <LayoutGrid size={20} />
          <span className="text-sm">Mis Videos</span>
        </button>

        <button 
          onClick={() => { onNavigate('list'); onClose(); }}
          title="Biblioteca de Videos"
          className={`flex items-center gap-3 px-3 justify-start py-3 rounded-lg transition-colors w-full text-left
            ${currentScreen === 'list' 
              ? 'bg-primary/20 border border-primary/10 text-primary font-semibold' 
              : 'text-slate-400 hover:bg-slate-800 hover:text-white font-medium'
            }`}
        >
          <Video size={20} />
          <span className="text-sm">Biblioteca de Videos</span>
        </button>

        {/* Solo ADMIN puede ver la opción de Servidores */}
        {role === 'ADMIN' && (
          <button 
            onClick={() => { onNavigate('servers'); onClose(); }}
            title="Servidores"
            className={`flex items-center gap-3 px-3 justify-start py-3 rounded-lg transition-colors w-full text-left
              ${currentScreen === 'servers' 
                ? 'bg-primary/20 border border-primary/10 text-primary font-semibold' 
                : 'text-slate-400 hover:bg-slate-800 hover:text-white font-medium'
              }`}
          >
            <Server size={20} />
            <span className="text-sm">Servidores</span>
          </button>
        )}

        <div className="my-2 border-t border-slate-800"></div>

        {/* Gestión de Usuarios solo para ADMIN */}
        {role === 'ADMIN' && (
          <button 
            title="Gestión de Usuarios"
            className="flex items-center gap-3 px-3 justify-start py-3 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors w-full text-left group"
            onClick={() => { onNavigate('users'); onClose(); }}
          >
            <Users size={20} />
            <span className="text-sm font-medium">Gestión de Usuarios</span>
          </button>
        )}

        {/*<button 
          className="flex items-center gap-3 px-3 py-3 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors w-full text-left group"
        >
          <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
          <span className="text-sm font-medium">Configuración</span>
        </button>*/}
      </nav>

      <div className="p-4 border-t border-slate-800 mt-auto">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer group">
          <div className="h-10 w-10 flex items-center justify-center rounded-full bg-slate-700 border border-slate-600 shadow-sm">
            <User size={28} className="text-blue-400" />
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
}
export default Sidebar;