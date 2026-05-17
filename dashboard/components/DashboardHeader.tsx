import React from 'react';
import { useLocation } from 'react-router-dom';
import { Sun, Moon } from 'lucide-react';
import { GeneralNotifications } from './GeneralNotifications';
import { useThemeStore } from '../stores/themeStore';

const breadcrumbMap: Record<string, string> = {
  '/': 'Dashboard',
  '/videos': 'Mis Videos',
  '/servidores': 'Servidores',
  '/usuarios': 'Gestión de Usuarios',
  '/auditoria': 'Auditoría',
  '/calendario': 'Calendario',
};

export const Header: React.FC = () => {
  const location = useLocation();

  const getBreadcrumb = () => {
    return breadcrumbMap[location.pathname] || 'Panel Principal';
  };

  const { isDark, toggle } = useThemeStore();

  return (
    <header className="h-14 flex items-center justify-between pl-16 md:pl-20 pr-4 md:pr-6 border-b border-slate-200/50 dark:border-slate-800/50 bg-white/80 dark:bg-[#111a22]/80 backdrop-blur-sm z-20">
      <div className="flex items-center">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{getBreadcrumb()}</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggle}
          className="p-2 rounded-lg transition-colors text-slate-500 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Toggle dark mode"
        >
          <div className="transition-transform duration-300">
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </div>
        </button>
        <GeneralNotifications />
      </div>
    </header>
  );
};
