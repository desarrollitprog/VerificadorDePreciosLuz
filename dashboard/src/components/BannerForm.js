
import React, { useState } from 'react';
import { createBanner } from '../utils/axiosConfig';
import {
  CForm,
  CFormInput,
  CFormSelect,
  CFormSwitch,
  CButton,
  CRow,
  CCol,
  CAlert,
} from '@coreui/react';


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
  const [touched, setTouched] = useState({});
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Validaciones simples
  const validate = () => {
    const errors = {};
    if (!form.titulo) errors.titulo = 'El título es obligatorio';
    if (!form.url) errors.url = 'La URL es obligatoria';
    if (!form.FechaInicio) errors.FechaInicio = 'La fecha de inicio es obligatoria';
    if (!form.FechaFin) errors.FechaFin = 'La fecha de fin es obligatoria';
    if (form.FechaInicio && form.FechaFin && form.FechaFin < form.FechaInicio) errors.FechaFin = 'La fecha de fin debe ser posterior a la de inicio';
    return errors;
  };
  const errors = validate();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleBlur = (e) => {
    setTouched((prev) => ({ ...prev, [e.target.name]: true }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    // Marcar todos como tocados para mostrar errores
    setTouched({ titulo: true, url: true, FechaInicio: true, FechaFin: true });
    if (Object.keys(errors).length > 0) return;
    try {
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
      setTouched({});
      if (onUpload) onUpload();
    } catch (err) {
      setError('Error al crear el banner');
    }
  };

  return (
    <CForm className="mb-4" onSubmit={handleSubmit} noValidate>
      <h4>Agregar/Editar Banner</h4>
      {error && <CAlert color="danger">{error}</CAlert>}
      {success && <CAlert color="success">{success}</CAlert>}
      <CRow className="g-2 align-items-end">
        <CCol md={3}>
          <CFormInput
            name="titulo"
            value={form.titulo}
            onChange={handleChange}
            onBlur={handleBlur}
            label="Título"
            placeholder="Título"
            invalid={touched.titulo && !!errors.titulo}
            feedback={touched.titulo && errors.titulo}
            required
          />
        </CCol>
        <CCol md={2}>
          <CFormSelect name="tipo" value={form.tipo} onChange={handleChange} label="Tipo">
            <option value="image">Imagen</option>
            <option value="video">Video</option>
          </CFormSelect>
        </CCol>
        <CCol md={3}>
          <CFormInput
            name="url"
            value={form.url}
            onChange={handleChange}
            onBlur={handleBlur}
            label="URL o ruta de archivo"
            placeholder="URL o ruta de archivo"
            invalid={touched.url && !!errors.url}
            feedback={touched.url && errors.url}
            required
          />
        </CCol>
        <CCol md={1} className="d-flex align-items-center">
          <CFormSwitch name="activo" checked={form.activo} onChange={handleChange} label="Activo" />
        </CCol>
        <CCol md={1}>
          <CFormInput name="prioridad" type="number" value={form.prioridad} onChange={handleChange} label="Prioridad" placeholder="Prioridad" />
        </CCol>
        <CCol md={2}>
          <CFormInput
            name="FechaInicio"
            type="date"
            value={form.FechaInicio}
            onChange={handleChange}
            onBlur={handleBlur}
            label="Fecha Inicio"
            invalid={touched.FechaInicio && !!errors.FechaInicio}
            feedback={touched.FechaInicio && errors.FechaInicio}
            required
          />
        </CCol>
        <CCol md={2}>
          <CFormInput
            name="FechaFin"
            type="date"
            value={form.FechaFin}
            onChange={handleChange}
            onBlur={handleBlur}
            label="Fecha Fin"
            invalid={touched.FechaFin && !!errors.FechaFin}
            feedback={touched.FechaFin && errors.FechaFin}
            required
          />
        </CCol>
        <CCol md={2}>
          <CFormInput name="duracion_seg" type="number" value={form.duracion_seg} onChange={handleChange} label="Duración (seg)" placeholder="Duración (seg)" />
        </CCol>
        <CCol md={2}>
          <CButton type="submit" color="primary">Guardar</CButton>
        </CCol>
      </CRow>
    </CForm>
  );
}

export default BannerForm;
