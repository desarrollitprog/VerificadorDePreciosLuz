import React from 'react';
import './Sidebar.css'; // Puedes mover los estilos aquí si lo deseas

const Sidebar = () => (
  <aside className="sidebar">
    <div className="sidebar-header">
      <div className="logo">
        <div className="logo-icon">📊</div>
        <div className="logo-text">
          <h1>AdManager</h1>
          <p>Control Publicitario</p>
        </div>
      </div>
    </div>
    <nav className="sidebar-nav">
      <div className="nav-section">
        <div className="nav-section-title">Principal</div>
        <a href="#" className="nav-item active">
          <span className="nav-item-icon">📈</span>
          <span>Dashboard</span>
        </a>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">🎯</span>
          <span>Banners</span>
          <span className="nav-item-badge">24</span>
        </a>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">📅</span>
          <span>Calendario</span>
        </a>
      </div>
      <div className="nav-section">
        <div className="nav-section-title">Analytics</div>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">📊</span>
          <span>Estadísticas</span>
        </a>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">👥</span>
          <span>Audiencia</span>
        </a>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">💰</span>
          <span>Ingresos</span>
        </a>
      </div>
      <div className="nav-section">
        <div className="nav-section-title">Configuración</div>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">⚙️</span>
          <span>Ajustes</span>
        </a>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">🔔</span>
          <span>Notificaciones</span>
        </a>
        <a href="#" className="nav-item">
          <span className="nav-item-icon">👤</span>
          <span>Perfil</span>
        </a>
      </div>
    </nav>
  </aside>
);

export default Sidebar;
