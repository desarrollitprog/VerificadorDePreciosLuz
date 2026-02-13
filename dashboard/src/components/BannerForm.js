import { createBanner } from '../utils/axiosConfig';
import React, { useState } from 'react';
import './BannerForm.css'; // Puedes mover los estilos aquí si lo deseas

  const BannerForm = ({ onSubmit }) => {
    const [form, setForm] = useState({
      titulo: '',
    imagenUrl: '',
      activo: true,
    fechaInicio: '',
    fechaFin: '',
    });
    const [error, setError] = useState('');

    const handleChange = (e) => {
      const { name, value, type, checked } = e.target;
      setForm((prev) => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value,
      }));
    };

    const handleSubmit = (e) => {
      e.preventDefault();
      setError('');
      if (!form.titulo || !form.url) {
        setError('El título y la URL son obligatorios');
        return;
      }
      if (onSubmit) onSubmit(form);
      setForm({ titulo: '', url: '', activo: true, FechaInicio: '', FechaFin: '' });
    };

    return (
      <div className="card mb-4">
        <div className="card-header">
          <h5 className="mb-0">Agregar/Editar Banner</h5>
        </div>
        <div className="card-body">
          {error && <div className="alert alert-danger">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="row g-2 align-items-end">
              <div className="col-md-3">
                <label className="form-label">Título</label>
                <input
                  name="titulo"
                  value={form.titulo}
                  onChange={handleChange}
                  className="form-control"
                  placeholder="Título"
                  required
                />
              </div>
              <div className="col-md-3">
                <label className="form-label">URL de la imagen</label>
                <input
                name="imagenUrl"
                  value={form.url}
                  onChange={handleChange}
                  className="form-control"
                  placeholder="URL o ruta de archivo"
                  required
                />
              </div>
              <div className="col-md-2">
                <label className="form-label">Activo</label>
                <div className="form-check">
                  <input
                    name="activo"
                    type="checkbox"
                    checked={form.activo}
                    onChange={handleChange}
                    className="form-check-input"
                    id="activoCheck"
                  />
                  <label className="form-check-label" htmlFor="activoCheck">
                    Sí
                  </label>
                </div>
              </div>
              <div className="col-md-2">
                <label className="form-label">Fecha Inicio</label>
                <input
                name="fechaInicio"
                  type="date"
                  value={form.FechaInicio}
                  onChange={handleChange}
                  className="form-control"
                />
              </div>
              <div className="col-md-2">
                <label className="form-label">Fecha Fin</label>
                <input
                name="fechaFin"
                  type="date"
                  value={form.FechaFin}
                  onChange={handleChange}
                  className="form-control"
                />
              </div>
              <div className="col-md-2">
                <button type="submit" className="btn btn-primary w-100 mt-3">Guardar</button>
              </div>
            </div>
          </form>
        </div>
      </div>
    );
  };
export default BannerForm;
