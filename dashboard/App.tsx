import React from 'react';
import { HashRouter as Router, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import MediaLibrary from './pages/MediaLibrary';
import VideoAnalytics from './pages/VideoAnalytics';
import DeviceMonitor from './pages/DeviceMonitor';
import Login from './pages/Login';

// Layout wrapper to handle Sidebar + Header structure logic
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  
  const getHeaderTitle = (path: string) => {
    switch (path) {
      case '/': return 'Resumen Global';
      case '/library': return 'Media Library';
      case '/analytics': return 'Analíticas';
      case '/devices': return 'Monitor de Dispositivos';
      case '/schedules': return 'Programación';
      default: return 'Dashboard';
    }
  };

  const getBreadcrumbs = (path: string) => {
    // Simple breadcrumb logic for demo purposes
    if (path === '/') return ['Panel de Control', 'Resumen'];
    if (path === '/library') return ['Panel de Control', 'Media'];
    if (path === '/analytics') return ['Panel de Control', 'Analíticas', 'Promo_Principal_v2.mp4'];
    if (path === '/devices') return ['Panel de Control', 'Dispositivos'];
    return ['Panel de Control'];
  };

  return (
    <div class="flex h-screen bg-background text-white overflow-hidden font-sans">
      <Sidebar />
      <div class="flex-1 flex flex-col ml-64 transition-all duration-300">
        <Header 
          title={getHeaderTitle(location.pathname)} 
          breadcrumbs={getBreadcrumbs(location.pathname)} 
        />
        <main class="flex-1 overflow-hidden relative">
           <div class="absolute inset-0 bg-gradient-to-b from-blue-900/5 to-transparent pointer-events-none z-0"></div>
           <div class="relative z-10 h-full overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-gray-700">
             {children}
           </div>
        </main>
      </div>
    </div>
  );
};


// Simple auth check
const isAuthenticated = () => {
  return Boolean(localStorage.getItem('token'));
};

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/library" element={<MediaLibrary />} />
                  <Route path="/analytics" element={<VideoAnalytics />} />
                  <Route path="/devices" element={<DeviceMonitor />} />
                  {/* Fallback for routes not fully implemented in this demo */}
                  <Route path="*" element={<div className="flex items-center justify-center h-full text-gray-500">Page under construction</div>} />
                </Routes>
              </AppLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
};

export default App;