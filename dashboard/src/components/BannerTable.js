import React from 'react';

const mockBanners = [
  {
    id: 1,
    titulo: 'Banner Promoción 1',
    url: '/static/banners/banner1.jpg',
    activo: true,
    FechaInicio: '2026-02-01',
    FechaFin: '2026-02-28',
  },
  {
    id: 2,
    titulo: 'Banner Promoción 2',
    url: '/static/banners/banner2.jpg',
    activo: false,
    FechaInicio: '2026-03-01',
    FechaFin: '2026-03-31',
  },
];

function BannerTable({ banners = mockBanners, onDelete, onToggle }) {
  return (
    <div className="container">
      <h2>Banners Publicitarios</h2>
      <table className="table table-striped">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Imagen</th>
            <th>Activo</th>
            <th>Fecha Inicio</th>
            <th>Fecha Fin</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {banners.map((banner) => (
            <tr key={banner.id}>
              <td>{banner.titulo}</td>
              <td><img src={banner.url} alt={banner.titulo} width={100} /></td>
              <td>{banner.activo ? 'Sí' : 'No'}</td>
              <td>{banner.FechaInicio}</td>
              <td>{banner.FechaFin}</td>
              <td>
                <button className="btn btn-sm btn-danger me-2" onClick={() => onDelete && onDelete(banner.id)}>Eliminar</button>
                <button className="btn btn-sm btn-secondary" onClick={() => onToggle && onToggle(banner.id)}>
                  {banner.activo ? 'Desactivar' : 'Activar'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default BannerTable;
