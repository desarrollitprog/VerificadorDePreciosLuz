import React, { useState } from 'react';
import { createBanner } from '../utils/axiosConfig';

function BannerForm({ onUpload }) {
  const [form, setForm] = useState({
    titulo: '',
    tipo: 'image',
    url: '',
    activo: true,
    prioridad: 0,
    FechaInicio: '',
    FechaFin: '',
    duracion_seg: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      // Convertir fechas vacías a null
      const payload = {
        ...form,
        FechaInicio: form.FechaInicio || null,
        FechaFin: form.FechaFin || null,
        duracion_seg: form.duracion_seg ? Number(form.duracion_seg) : null
      };
      await createBanner(payload);
      setSuccess('Banner creado correctamente');
      setForm({
        titulo: '', tipo: 'image', url: '', activo: true, prioridad: 0, FechaInicio: '', FechaFin: '', duracion_seg: ''
      });
      if (onUpload) onUpload();
    } catch (err) {
      setError('Error al crear el banner');
    }
  };

  return (
    <form className="mb-4" onSubmit={handleSubmit}>
      <h4>Agregar/Editar Banner</h4>
      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}
      <div className="row g-2">
        <div className="col-md-3">
          <input name="titulo" value={form.titulo} onChange={handleChange} className="form-control" placeholder="Título" />
        </div>
        <div className="col-md-2">
          <select name="tipo" value={form.tipo} onChange={handleChange} className="form-select">
            <option value="image">Imagen</option>
            <option value="video">Video</option>
          </select>
        </div>
        <div className="col-md-3">
          <input name="url" value={form.url} onChange={handleChange} className="form-control" placeholder="URL o ruta de archivo" />
        </div>
        <div className="col-md-1">
          <input name="activo" type="checkbox" checked={form.activo} onChange={handleChange} className="form-check-input" /> Activo
        </div>
        <div className="col-md-1">
          <input name="prioridad" type="number" value={form.prioridad} onChange={handleChange} className="form-control" placeholder="Prioridad" />
        </div>
        <div className="col-md-2">
          <input name="FechaInicio" type="date" value={form.FechaInicio} onChange={handleChange} className="form-control" />
        </div>
        <div className="col-md-2">
          <input name="FechaFin" type="date" value={form.FechaFin} onChange={handleChange} className="form-control" />
        </div>
        <div className="col-md-2">
          <input name="duracion_seg" type="number" value={form.duracion_seg} onChange={handleChange} className="form-control" placeholder="Duración (seg)" />
        </div>
        <div className="col-md-2">
          <button type="submit" className="btn btn-primary">Guardar</button>
        </div>
      </div>
    </form>
  );
}

export default BannerForm;
