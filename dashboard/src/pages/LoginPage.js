import React, { useState } from 'react';
import LoginForm from '../components/LoginForm';
import DashboardPage from './DashboardPage';

function LoginPage() {
  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem('token'));

  if (loggedIn) {
    return <DashboardPage />;
  }

  return <LoginForm onLogin={() => setLoggedIn(true)} />;
}

export default LoginPage;
