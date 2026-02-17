import React from 'react';
import { Bell, ChevronRight, Menu, Search } from 'lucide-react';
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
        <div className="hidden md:flex relative items-center">
            <Search size={16} className="absolute left-3 text-slate-500" />
            <input 
                type="text" 
                placeholder="Quick search..." 
                className="bg-slate-100 dark:bg-[#1c2936] text-sm rounded-full pl-9 pr-4 py-1.5 w-48 border-none focus:ring-1 focus:ring-primary text-slate-900 dark:text-white placeholder:text-slate-500"
            />
        </div>
        <button className="relative p-2 text-slate-400 hover:text-primary transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full">
          <Bell size={20} />
          <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 border-2 border-white dark:border-[#111a22]"></span>
        </button>
      </div>
    </header>
  );
};