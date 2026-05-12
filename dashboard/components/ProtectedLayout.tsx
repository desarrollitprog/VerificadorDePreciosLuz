import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { getTokenExpiryMs, logout as tokenLogout } from '../services/tokenUtils';
import Sidebar from './Sidebar';
import { Header } from './DashboardHeader';
import { useSessionStore } from '../stores/sessionStore';

export const ProtectedLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const sessionLogout = useSessionStore((s) => s.logout);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const expiryMs = getTokenExpiryMs();
    if (!expiryMs) {
      sessionLogout();
      navigate('/login', { replace: true });
      return;
    }
    const delay = expiryMs - Date.now();
    if (delay <= 0) {
      sessionLogout();
      navigate('/login', { replace: true });
      return;
    }
    const timeout = window.setTimeout(() => {
      sessionLogout();
      navigate('/login', { replace: true });
    }, delay);
    return () => window.clearTimeout(timeout);
  }, [isAuthenticated, navigate, sessionLogout]);

  if (!isAuthenticated) return null;

  return (
    <div className="flex min-h-screen w-full overflow-hidden bg-background-light dark:bg-background-dark text-slate-900 dark:text-white">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onLogout={() => {
          sessionLogout();
          navigate('/login');
        }}
      />
      {!isSidebarOpen && (
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="fixed top-3 left-3 z-30 text-slate-400 hover:text-primary hover:bg-slate-800/70 transition-colors rounded-lg h-10 w-10 flex items-center justify-center"
          title="Abrir menú"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/></svg>
        </button>
      )}
      <main className="flex-1 flex flex-col min-h-full min-w-0 overflow-hidden relative transition-all duration-300">
        <Header />
        <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 scroll-smooth animate-fade-in">
          <Outlet />
        </div>
      </main>
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 backdrop-blur-sm"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
    </div>
  );
};
