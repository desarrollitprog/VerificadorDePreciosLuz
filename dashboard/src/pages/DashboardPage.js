import React, { useEffect, useState } from 'react';
import BannerForm from '../components/BannerForm';
import BannerTable from '../components/BannerTable';
import ProtectedRoute from '../components/ProtectedRoute';
import { getBanners } from '../utils/axiosConfig';

function DashboardPage() {
  const [banners, setBanners] = useState([]);

  useEffect(() => {
    const fetchBanners = async () => {
      const data = await getBanners();
      setBanners(data);
    };
    fetchBanners();
  }, []);

  return (
    <ProtectedRoute>
      <div>
        <BannerForm onUpload={() => {}} />
        <BannerTable banners={banners} onDelete={() => {}} onToggle={() => {}} />
      </div>
    </ProtectedRoute>
  );
}

export default DashboardPage;
