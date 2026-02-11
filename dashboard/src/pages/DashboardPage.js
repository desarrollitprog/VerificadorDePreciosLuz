import React from 'react';
import BannerForm from '../components/BannerForm';
import BannerTable from '../components/BannerTable';
import ProtectedRoute from '../components/ProtectedRoute';

function DashboardPage() {
  // TODO: Lógica de dashboard principal
  return (
    <ProtectedRoute>
      <div>
        <BannerForm onUpload={() => {}} />
        <BannerTable banners={[]} onDelete={() => {}} onToggle={() => {}} />
      </div>
    </ProtectedRoute>
  );
}

export default DashboardPage;
