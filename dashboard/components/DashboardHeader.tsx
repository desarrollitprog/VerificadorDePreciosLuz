import React from 'react';
import { Bell, ChevronRight, Menu, Search, Sun, Moon } from 'lucide-react';
import { Screen } from '../types';

interface HeaderProps {
  currentScreen: Screen;
  onMenuClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({ currentScreen, onMenuClick }) => { 
  const getBreadcrumb = () => {
    switch (currentScreen) {
      case 'dashboard': return 'My Videos';
      case 'list': return 'Video Library';
      default: return 'Dashboard';
    }
  };

  // Hook para alternar modo claro/oscuro
  const [isDark, setIsDark] = React.useState(() => document.documentElement.classList.contains('dark'));
  const toggleDark = () => {
    document.documentElement.classList.toggle('dark');
    setIsDark(document.documentElement.classList.contains('dark'));
  };

  return (
    <header className="h-16 flex items-center justify-between px-4 md:px-8 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111a22] z-20 shadow-sm">
      <div className="flex items-center gap-4">
        <button 
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
        >
          <Menu size={20} />
        </button>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span className="hover:text-primary transition-colors cursor-pointer">Dashboard</span>
          <ChevronRight size={14} />
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
        <button className="relative p-2 text-slate-400 hover:text-primary transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full">
          <Bell size={20} />
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 border-2 border-white dark:border-[#111a22]"></span>
        </button>
      </div>
    </header>
  );
};