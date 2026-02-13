import React from 'react';

const BannerTable = ({ banners = [], onDelete, onToggle }) => (
  <div className="card mb-4">
    <div className="card-header">
      <h5 className="mb-0">Banners Publicitarios</h5>
    </div>
    <div className="card-body p-0">
      <div className="table-responsive">
        <table className="table table-striped table-hover mb-0">
          <thead className="table-dark">
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
            {banners.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center">No hay banners registrados.</td>
              </tr>
            ) : (
              banners.map((banner) => (
                <tr key={banner.id}>
                  <td>{banner.titulo}</td>
                  <td>
                    {banner.url && (
                      <img src={banner.url} alt={banner.titulo} width={100} style={{ borderRadius: 8 }} />
                    )}
                  </td>
                  <td>
                    <span className={`badge ${banner.activo ? 'bg-success' : 'bg-secondary'}`}>
                      {banner.activo ? 'Sí' : 'No'}
                    </span>
                  </td>
                  <td>{banner.FechaInicio}</td>
                  <td>{banner.FechaFin}</td>
                  <td>
                    <button className="btn btn-sm btn-danger me-2" onClick={() => onDelete && onDelete(banner.id)}>
                      Eliminar
                    </button>
                    <button
                      className={`btn btn-sm ${banner.activo ? 'btn-secondary' : 'btn-success'}`}
                      onClick={() => onToggle && onToggle(banner.id)}
                    >
                      {banner.activo ? 'Desactivar' : 'Activar'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  </div>
);

export default BannerTable;