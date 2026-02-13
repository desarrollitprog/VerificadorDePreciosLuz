import React, { useState } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import BannerForm from '../components/BannerForm';
import BannerTable from '../components/BannerTable';

const DashboardPage = () => {
  const [banners, setBanners] = useState([]);

  const handleAddBanner = (newBanner) => {
    setBanners([...banners, { ...newBanner, id: Date.now() }]);
  };

  const handleDeleteBanner = (id) => {
    setBanners(banners.filter(b => b.id !== id));
  };

  const handleToggleBanner = (id) => {
    setBanners(
      banners.map(b =>
        b.id === id ? { ...b, activo: !b.activo } : b
      )
    );
  };

  return (
    <DashboardLayout>
      <BannerForm onSubmit={handleAddBanner} />
      <BannerTable banners={banners} onDelete={handleDeleteBanner} onToggle={handleToggleBanner} />
    </DashboardLayout>
  );
};

export default DashboardPage;