import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { GeneralNotifications } from './GeneralNotifications';
import { Screen } from '../types';

interface HeaderProps {
  currentScreen: Screen;
}

export const Header: React.FC<HeaderProps> = ({ currentScreen }) => { 
  const getBreadcrumb = () => {
    switch (currentScreen) {
      case 'dashboard': return 'Mis Videos';
      case 'list': return 'Biblioteca de Videos';
      case 'servers': return 'Servidores';
      case 'users': return 'Gestión de Usuarios';
      default: return 'Panel Principal';
    }
  };

  // Hook para alternar modo claro/oscuro
  const [isDark, setIsDark] = React.useState(() => document.documentElement.classList.contains('dark'));
  const toggleDark = () => {
    document.documentElement.classList.toggle('dark');
    setIsDark(document.documentElement.classList.contains('dark'));
  };

  return (
    <header className="h-16 flex items-center justify-between pl-16 md:pl-20 pr-4 md:pr-8 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111a22] z-20 shadow-sm">
      <div className="flex items-center gap-2">
        <div className="flex items-center text-sm text-slate-500">
          <span className="text-slate-900 dark:text-white font-medium">{getBreadcrumb()}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={toggleDark}
          className="p-2 rounded-full transition-colors text-slate-400 hover:text-yellow-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Toggle dark mode"
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <GeneralNotifications />
      </div>
    </header>
  );
};