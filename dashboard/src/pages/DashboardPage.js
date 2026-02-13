import React, { useEffect, useState } from 'react';
import ProtectedRoute from '../components/ProtectedRoute';
import DashboardLayout from '../components/DashboardLayout';
import { getBanners, createBanner, deleteBanner } from '../utils/axiosConfig';

function DashboardPage() {
  const [banners, setBanners] = useState([]);

  useEffect(() => {
    const fetchBanners = async () => {
      try {
        const data = await getBanners();
        setBanners(data);
      } catch (err) {
        // Manejo de error opcional
      }
    };
    fetchBanners();
  }, []);

  const handleBannerSubmit = async (banner) => {
    try {
      await createBanner(banner);
      const data = await getBanners();
      setBanners(data);
    } catch (err) {
      // Manejo de error opcional
    }
  };

  const handleBannerDelete = async (banner) => {
    try {
      await deleteBanner(banner.IdPublicidad || banner.id);
      setBanners(banners.filter(b => (b.IdPublicidad || b.id) !== (banner.IdPublicidad || banner.id)));
    } catch (err) {
      // Manejo de error opcional
    }
  };

  const handleBannerView = (banner) => {
    // Lógica para ver detalles del banner
    alert('Ver banner: ' + banner.Titulo || banner.titulo);
  };

  const handleBannerEdit = (banner) => {
    // Lógica para editar banner (puedes implementar modal o navegación)
    alert('Editar banner: ' + banner.Titulo || banner.titulo);
  };

  return (
    <ProtectedRoute>
      <DashboardLayout
        banners={banners}
        onBannerView={handleBannerView}
        onBannerEdit={handleBannerEdit}
        onBannerDelete={handleBannerDelete}
        onBannerSubmit={handleBannerSubmit}
      />
    </ProtectedRoute>
  );
}

export default DashboardPage;
