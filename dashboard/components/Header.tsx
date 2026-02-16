import React from 'react';
import { Search, Bell, Settings, HelpCircle, Menu } from 'lucide-react';

interface HeaderProps {
  title: string;
  breadcrumbs?: string[];
}

const Header: React.FC<HeaderProps> = ({ title, breadcrumbs }) => {
  return (
    <header class="h-16 bg-surface/80 backdrop-blur-md border-b border-gray-800 flex items-center justify-between px-6 sticky top-0 z-40">
      <div class="flex items-center gap-4">
        <button class="md:hidden text-gray-400 hover:text-white">
          <Menu className="w-6 h-6" />
        </button>
        <div class="hidden md:flex flex-col">
          {breadcrumbs && (
            <div class="flex items-center text-xs text-gray-500 mb-0.5">
              {breadcrumbs.map((crumb, index) => (
                <React.Fragment key={crumb}>
                  {index > 0 && <span class="mx-1">/</span>}
                  <span class={index === breadcrumbs.length - 1 ? 'text-gray-300' : ''}>{crumb}</span>
                </React.Fragment>
              ))}
            </div>
          )}
          <h1 class="text-lg font-bold text-white leading-none">{title}</h1>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <div class="relative hidden md:block group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 w-4 h-4 group-focus-within:text-primary transition-colors" />
          <input
            type="text"
            placeholder="Buscar..."
            class="bg-gray-900 border border-gray-700 rounded-lg pl-9 pr-4 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary w-64 transition-all"
          />
        </div>
        
        <div class="h-6 w-px bg-gray-700 mx-1 hidden md:block"></div>

        <button class="relative text-gray-400 hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
          <span class="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border-2 border-surface"></span>
        </button>
        
        <button class="text-gray-400 hover:text-white transition-colors">
          <Settings className="w-5 h-5" />
        </button>
        
        <button class="text-gray-400 hover:text-white transition-colors">
          <HelpCircle className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
};

export default Header;