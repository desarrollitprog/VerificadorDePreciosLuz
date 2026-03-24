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

  const [isDark, setIsDark] = React.useState(() => document.documentElement.classList.contains('dark'));
  const toggleDark = () => {
    document.documentElement.classList.toggle('dark');
    setIsDark(document.documentElement.classList.contains('dark'));
  };

  return (
    <header className="h-14 flex items-center justify-between pl-16 md:pl-20 pr-4 md:pr-6 border-b border-slate-200/50 dark:border-slate-800/50 bg-white/80 dark:bg-[#111a22]/80 backdrop-blur-sm z-20">
      <div className="flex items-center">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{getBreadcrumb()}</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleDark}
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