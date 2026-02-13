import { createBanner, uploadBanner } from '../utils/axiosConfig';
import React, { useState } from 'react';
import './BannerForm.css'; // Puedes mover los estilos aquí si lo deseas


const BannerForm = ({ onSubmit }) => {
  const [form, setForm] = useState({
    titulo: '',
    url: '',
    activo: true,
    fechaInicio: '',
    fechaFin: '',
  });
  const [error, setError] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    if (selectedFile) {
      setUploading(true);
      try {
        const res = await uploadBanner(selectedFile);
        setForm((prev) => ({ ...prev, url: res.url }));
        setError('');
      } catch (err) {
        setError('Error al subir el archivo');
      } finally {
        setUploading(false);
      }
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (!form.titulo || !form.url) {
      setError('El título y el archivo son obligatorios');
      return;
    }
    if (onSubmit) onSubmit(form);
    setForm({ titulo: '', url: '', activo: true, fechaInicio: '', fechaFin: '' });
    setFile(null);
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
              <label className="form-label">Archivo (imagen o video)</label>
              <input
                type="file"
                accept="image/*,video/*"
                className="form-control"
                onChange={handleFileChange}
              />
              {uploading && <small className="text-muted">Subiendo archivo...</small>}
              {form.url && (
                <div>
                  <small className="text-success">Archivo subido correctamente</small>
                </div>
              )}
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
                value={form.fechaInicio}
                onChange={handleChange}
                className="form-control"
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">Fecha Fin</label>
              <input
                name="fechaFin"
                type="date"
                value={form.fechaFin}
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
