import React from 'react';
import './BannerTable.css'; // Puedes mover los estilos aquí si lo deseas

const BannerTable = ({ banners = [], onView, onEdit, onDelete }) => (
  <section className="table-section animate-in">
    <div className="table-header">
      <h3>Banners Publicitarios</h3>
      <div className="table-filters">
        <button className="filter-btn active">Todos</button>
        <button className="filter-btn">Activos</button>
        <button className="filter-btn">Inactivos</button>
      </div>
    </div>
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Banner</th>
            <th>Estado</th>
            <th>Impresiones</th>
            <th>CTR</th>
            <th>Fecha Inicio</th>
            <th>Fecha Fin</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {banners.length === 0 ? (
            <tr>
              <td colSpan="7" className="empty-state">No hay banners para mostrar.</td>
            </tr>
          ) : (
            banners.map((banner, idx) => (
              <tr key={banner.id || idx}>
                <td>
                  <div className="banner-name">
                    <div className="banner-thumbnail" style={{background: banner.bg || undefined}}>IMG</div>
                    <div className="banner-info">
                      <h4>{banner.titulo}</h4>
                      <p>{banner.imagenUrl}</p>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`status-badge ${banner.activo ? 'active' : 'inactive'}`}>
                    <span className="status-dot"></span>
                    {banner.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td><strong>{banner.impresiones || '-'}</strong></td>
                <td><strong>{banner.ctr || '-'}</strong></td>
                <td>{banner.fechaInicio || '-'}</td>
                <td>{banner.fechaFin || '-'}</td>
                <td>
                  <div className="action-buttons">
                    <button className="btn-icon" title="Ver" onClick={() => onView && onView(banner)}>👁️</button>
                    <button className="btn-icon" title="Editar" onClick={() => onEdit && onEdit(banner)}>✏️</button>
                    <button className="btn-icon danger" title="Eliminar" onClick={() => onDelete && onDelete(banner)}>🗑️</button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  </section>
);

export default BannerTable;