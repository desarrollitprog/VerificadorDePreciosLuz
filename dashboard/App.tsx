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
import { getTokenExpiryMs, hasValidToken, logout } from './services/tokenUtils';
import { LayoutGrid } from 'lucide-react';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>(() => (hasValidToken() ? 'dashboard' : 'login'));
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => {
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
            onClose={() => setIsSidebarOpen(false)}
            onLogout={() => {
              logout();
              setCurrentScreen('login');
            }}
          />
          {!isSidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="fixed top-3 left-3 z-30 text-slate-400 hover:text-primary hover:bg-slate-800/70 transition-colors rounded-lg h-10 w-10 flex items-center justify-center"
              title="Abrir menú"
            >
              <LayoutGrid size={22} />
            </button>
          )}
          <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative transition-all duration-300">
            <Header 
              currentScreen={currentScreen}
            />
            <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 scroll-smooth">
              {renderScreen()}
            </div>
          </main>
          {isSidebarOpen && (
            <div 
              className="fixed inset-0 bg-black/50 z-20 backdrop-blur-sm"
              onClick={() => setIsSidebarOpen(false)}
            />
          )}
          <NotificationContainer />
        </div>
      )}
    </NotificationProvider>
  );
}