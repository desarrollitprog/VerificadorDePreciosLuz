import React from 'react';
import './Header.css'; // Puedes mover los estilos aquí si lo deseas


const Header = () => (
  <header className="content-header">
    <div className="header-inner">
      <div className="header-top">
        <div className="header-title">
          <h2>Gestión de Banners</h2>
          <span className="header-badge">24 Activos</span>
        </div>
        <div className="header-actions">
          <div className="search-box">
            <span role="img" aria-label="Buscar">🔍</span>
            <input type="text" placeholder="Buscar banners..." />
          </div>
          <button className="btn btn-secondary">
            <span role="img" aria-label="Exportar">📥</span>
            Exportar
          </button>
          <button className="btn btn-primary">
            <span role="img" aria-label="Nuevo">➕</span>
            Nuevo Banner
          </button>
        </div>
      </div>
      <div className="breadcrumb">
        <a href="#">Dashboard</a>
        <span className="breadcrumb-separator">›</span>
        <span>Banners Publicitarios</span>
      </div>
    </div>
  </header>
);

export default Header;
