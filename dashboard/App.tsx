import React, { useState } from 'react';
import { NotificationProvider } from './components/NotificationContext';
import { NotificationContainer } from './components/NotificationContainer';
import { LoginScreen } from './screens/LoginScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { VideoListScreen } from './screens/VideoListScreen';

import { Screen } from './types';
import Sidebar from './components/Sidebar';
import { Header } from './components/DashboardHeader';
import { ServerDashboard } from './components/ServerDashboard';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

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
            onLogout={() => setCurrentScreen('login')}
          />
          <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative transition-all duration-300">
            <Header 
              currentScreen={currentScreen} 
              onMenuClick={toggleSidebar}
            />
            <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 scroll-smooth">
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