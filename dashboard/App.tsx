import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { NotificationProvider } from './components/NotificationContext';
import { NotificationContainer } from './components/NotificationContainer';
import { ProtectedLayout } from './components/ProtectedLayout';
import { LoginScreen } from './screens/LoginScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { ResumenScreen } from './screens/ResumenScreen';
import { UsersScreen } from './screens/UsersScreen';
import { CalendarScreen } from './screens/CalendarScreen';
import { AuditoriaScreen } from './screens/AuditoriaScreen';
import { ServerDashboard } from './components/ServerDashboard';
import { useSessionStore } from './stores/sessionStore';

export default function App() {
  return (
    <BrowserRouter>
      <NotificationProvider>
        <Routes>
          <Route path="/login" element={<LoginRoute />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<ResumenScreen />} />
            <Route path="/videos" element={<DashboardScreen />} />
            <Route path="/servidores" element={<ServerDashboard />} />
            <Route path="/usuarios" element={<UsersScreen />} />
            <Route path="/calendario" element={<CalendarScreen />} />
            <Route path="/auditoria" element={<AuditoriaScreen />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <NotificationContainer />
      </NotificationProvider>
    </BrowserRouter>
  );
}

function LoginRoute() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <LoginScreen onLogin={useSessionStore.getState().login} />;
}
