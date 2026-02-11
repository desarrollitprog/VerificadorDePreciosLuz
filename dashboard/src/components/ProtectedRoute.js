import React from 'react';

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = '/'; // Redirige al login si no hay token
    return null;
  }
  return children;
}

export default ProtectedRoute;
