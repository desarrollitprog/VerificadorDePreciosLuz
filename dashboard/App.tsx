import React, { useEffect, useState } from 'react';
import { NotificationProvider } from './components/NotificationContext';
import { NotificationContainer } from './components/NotificationContainer';
import { LoginScreen } from './screens/LoginScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { VideoListScreen } from './screens/VideoListScreen';
import { UsersScreen } from './screens/UsersScreen';

import { Screen } from './types';
import Sidebar from './components/Sidebar';
import { Header } from './components/DashboardHeader';
import { ServerDashboard } from './components/ServerDashboard';
import { getTokenExpiryMs, hasValidToken, logout } from './services/authService';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>(() => (hasValidToken() ? 'dashboard' : 'login'));
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem('sidebarCollapsed') === '1';
  });

  const toggleSidebar = () => {
    if (typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches) {
      setIsSidebarCollapsed((prev) => !prev);
      return;
    }
    setIsSidebarOpen((prev) => !prev);
  };

  useEffect(() => {
    if (currentScreen === 'login') {
      return;
    }

    const expiryMs = getTokenExpiryMs();
    if (!expiryMs) {
      logout();
      setCurrentScreen('login');
      return;
    }

    const delay = expiryMs - Date.now();
    if (delay <= 0) {
      logout();
      setCurrentScreen('login');
      return;
    }

    const timeout = window.setTimeout(() => {
      logout();
      setCurrentScreen('login');
    }, delay);

    return () => window.clearTimeout(timeout);
  }, [currentScreen]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('sidebarCollapsed', isSidebarCollapsed ? '1' : '0');
  }, [isSidebarCollapsed]);

  const renderScreen = () => {
    switch (currentScreen) {
      case 'login':
        return <LoginScreen onLogin={() => setCurrentScreen('dashboard')} />;
      case 'dashboard':
        return <DashboardScreen />;
      case 'list':
        return <VideoListScreen />;
      case 'servers':
        return <ServerDashboard />;
      case 'users':
        return <UsersScreen />;
      default:
        return <LoginScreen onLogin={() => setCurrentScreen('dashboard')} />;
    }
  };

  return (
    <NotificationProvider>
      {currentScreen === 'login' ? (
        renderScreen()
      ) : (
        <div className="flex h-screen w-full overflow-hidden bg-background-light dark:bg-background-dark text-slate-900 dark:text-white">
          <Sidebar 
            currentScreen={currentScreen} 
            onNavigate={setCurrentScreen} 
            isOpen={isSidebarOpen}
            isCollapsed={isSidebarCollapsed}
            onClose={() => setIsSidebarOpen(false)}
            onLogout={() => {
              logout();
              setCurrentScreen('login');
            }}
          />
          <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative transition-all duration-300">
            <Header 
              currentScreen={currentScreen} 
              onMenuClick={toggleSidebar}
            />
            <div className={`flex-1 overflow-y-auto p-4 md:p-6 ${isSidebarCollapsed ? 'lg:p-5' : 'lg:p-8'} scroll-smooth`}>
              {renderScreen()}
            </div>
          </main>
          {/* Mobile Sidebar Overlay */}
          {isSidebarOpen && (
            <div 
              className="fixed inset-0 bg-black/50 z-20 lg:hidden backdrop-blur-sm"
              onClick={() => setIsSidebarOpen(false)}
            />
          )}
          <NotificationContainer />
        </div>
      )}
    </NotificationProvider>
  );
}