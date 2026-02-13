
import React from 'react';
import {
  CCard,
  CCardBody,
  CCardHeader,
  CTable,
  CTableBody,
  CTableDataCell,
  CTableHead,
  CTableHeaderCell,
  CTableRow,
  CButton,
  CBadge,
} from '@coreui/react';

function BannerTable({ banners = [], onDelete, onToggle }) {
  return (
    <CCard className="mb-4">
      <CCardHeader>
        <h5 className="mb-0">Banners Publicitarios</h5>
      </CCardHeader>
      <CCardBody>
        <CTable striped hover responsive align="middle">
          <CTableHead color="dark">
            <CTableRow>
              <CTableHeaderCell>Nombre</CTableHeaderCell>
              <CTableHeaderCell>Imagen</CTableHeaderCell>
              <CTableHeaderCell>Activo</CTableHeaderCell>
              <CTableHeaderCell>Fecha Inicio</CTableHeaderCell>
              <CTableHeaderCell>Fecha Fin</CTableHeaderCell>
              <CTableHeaderCell>Acciones</CTableHeaderCell>
            </CTableRow>
          </CTableHead>
          <CTableBody>
            {banners.map((banner) => (
              <CTableRow key={banner.id}>
                <CTableDataCell>{banner.titulo}</CTableDataCell>
                <CTableDataCell>
                  <img src={banner.url} alt={banner.titulo} width={100} style={{ borderRadius: 8 }} />
                </CTableDataCell>
                <CTableDataCell>
                  <CBadge color={banner.activo ? 'success' : 'secondary'}>
                    {banner.activo ? 'Sí' : 'No'}
                  </CBadge>
                </CTableDataCell>
                <CTableDataCell>{banner.FechaInicio}</CTableDataCell>
                <CTableDataCell>{banner.FechaFin}</CTableDataCell>
                <CTableDataCell>
                  <CButton color="danger" size="sm" className="me-2" onClick={() => onDelete && onDelete(banner.id)}>
                    Eliminar
                  </CButton>
                  <CButton color={banner.activo ? 'secondary' : 'success'} size="sm" onClick={() => onToggle && onToggle(banner.id)}>
                    {banner.activo ? 'Desactivar' : 'Activar'}
                  </CButton>
                </CTableDataCell>
              </CTableRow>
            ))}
          </CTableBody>
        </CTable>
      </CCardBody>
    </CCard>
  );
}

export default BannerTable;
